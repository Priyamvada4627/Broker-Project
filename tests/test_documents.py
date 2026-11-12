from io import BytesIO
from backend.services import cloudinary_service


def _create_deal(client, auth_headers, auth_headers_buyer):
    prop_res = client.post(
        "/properties/add",
        headers=auth_headers,
        json={
            "description": "Deal Property for Document Test",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "price": 800000,
            "property_type": "apartment",
            "purpose": "buy",
            "is_available": True,
        },
    )
    assert prop_res.status_code == 201
    prop_id = prop_res.json()["id"]

    bid_res = client.post(
        f"/bid/{prop_id}",
        headers=auth_headers_buyer,
        json={"bid_amount": 780000},
    )
    assert bid_res.status_code == 201
    interest_id = bid_res.json()["interest_id"]

    accept_res = client.patch(
        f"/bid/{interest_id}",
        headers=auth_headers,
        json={"action": "accept_bid"},
    )
    assert accept_res.status_code == 200

    deals_res = client.get("/deals/my", headers=auth_headers_buyer)
    assert deals_res.status_code == 200
    return deals_res.json()[0]["deal_id"]


def test_upload_document_async_success(
    client, test_user, test_user2, auth_headers, auth_headers_buyer, monkeypatch
):
    deal_id = _create_deal(client, auth_headers, auth_headers_buyer)

    upload_calls = []

    def fake_cloudinary_upload(file_bytes: bytes, filename: str, d_id: int) -> dict:
        upload_calls.append((len(file_bytes), filename, d_id))
        return {
            "url": f"https://res.cloudinary.com/demo/{filename}",
            "public_id": f"deal_documents/deal_{d_id}/{filename}",
        }

    # Patch the sync underlying uploader so asyncio.to_thread executes our fake in a worker thread
    monkeypatch.setattr(cloudinary_service, "upload_verification_file", fake_cloudinary_upload)

    file_content = b"%PDF-1.4 fake pdf bytes"
    res = client.post(
        f"/deals/{deal_id}/documents",
        headers=auth_headers_buyer,
        data={"document_type": "id_proof"},
        files={"file": ("aadhar.pdf", BytesIO(file_content), "application/pdf")},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["message"] == "Document uploaded"
    assert body["file_url"].startswith("https://res.cloudinary.com/demo/id_proof_")
    assert len(upload_calls) == 1
    assert upload_calls[0][0] == len(file_content)
    assert upload_calls[0][2] == deal_id


def test_upload_document_rejects_invalid_mime_type(
    client, test_user, test_user2, auth_headers, auth_headers_buyer
):
    deal_id = _create_deal(client, auth_headers, auth_headers_buyer)

    res = client.post(
        f"/deals/{deal_id}/documents",
        headers=auth_headers_buyer,
        data={"document_type": "id_proof"},
        files={"file": ("malware.exe", BytesIO(b"MZ"), "application/x-msdownload")},
    )
    assert res.status_code == 400
    assert "unsupported file type" in res.json()["detail"].lower()


def test_upload_document_unauthorized_user_forbidden(
    client, test_user, test_user2, test_user3, auth_headers, auth_headers_buyer, auth_headers_buyer2
):
    deal_id = _create_deal(client, auth_headers, auth_headers_buyer)

    res = client.post(
        f"/deals/{deal_id}/documents",
        headers=auth_headers_buyer2,
        data={"document_type": "id_proof"},
        files={"file": ("id.png", BytesIO(b"pngbytes"), "image/png")},
    )
    assert res.status_code == 403
