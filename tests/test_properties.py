# tests/test_properties.py
from backend import models


def test_location_deduplication(client, test_user, auth_headers, db):
    # 1. Post first property in Delhi, 110001
    res1 = client.post("/properties/add", headers=auth_headers, json={
        "description": "First Property in Connaught Place",
        "city": "Delhi",
        "state": "Delhi",
        "pincode": "110001",
        "price": 500000,
        "property_type": "apartment",
        "purpose": "buy",
        "is_available": True
    })
    assert res1.status_code == 201
    prop1_id = res1.json()["id"]

    # 2. Post second property in Delhi, 110001 (same location, different casing)
    res2 = client.post("/properties/add", headers=auth_headers, json={
        "description": "Second Property in Connaught Place",
        "city": "delhi",
        "state": "delhi",
        "pincode": "110001",
        "price": 750000,
        "property_type": "apartment",
        "purpose": "buy",
        "is_available": True
    })
    assert res2.status_code == 201
    prop2_id = res2.json()["id"]

    # 3. VERIFY: locations table must contain ONLY 1 row for 110001!
    locations_count = db.query(models.Location).filter(models.Location.pincode == "110001").count()
    assert locations_count == 1

    # 4. Both properties must share the EXACT same location_id
    p1 = db.query(models.Property).filter(models.Property.id == prop1_id).first()
    p2 = db.query(models.Property).filter(models.Property.id == prop2_id).first()
    assert p1.location_id == p2.location_id


def test_seller_can_update_unverified_property(client, test_user, auth_headers):
    # Create listing
    res = client.post("/properties/add", headers=auth_headers, json={
        "description": "Initial description",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400001",
        "price": 1000000,
        "property_type": "apartment",
        "purpose": "buy",
        "is_available": True
    })
    prop_id = res.json()["id"]

    # Update description & price
    update_res = client.patch(f"/properties/{prop_id}", headers=auth_headers, json={
        "price": 950000,
        "description": "Updated luxurious description"
    })
    assert update_res.status_code == 200
    assert "updated" in update_res.json()["message"].lower()

    # Verify changes
    detail_res = client.get(f"/properties/{prop_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["description"] == "Updated luxurious description"


def test_cannot_delete_verified_property(client, test_user, test_agent_user, auth_headers, auth_headers_agent):
    res = client.post("/properties/add", headers=auth_headers, json={
        "description": "Property to be verified",
        "city": "Delhi",
        "state": "Delhi",
        "pincode": "110001",
        "price": 600000,
        "property_type": "apartment",
        "purpose": "buy",
        "is_available": True
    })
    prop_id = res.json()["id"]

    # Agent verifies property
    client.patch(f"/agents/verify/property/{prop_id}?action=verified", headers=auth_headers_agent)

    # Seller attempts to delete verified property -> must fail with 400
    del_res = client.delete(f"/properties/{prop_id}", headers=auth_headers)
    assert del_res.status_code == 400
    assert "cannot delete a verified property" in del_res.json()["detail"].lower()
