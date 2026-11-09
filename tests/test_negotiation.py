# tests/test_negotiation.py

def test_full_negotiation_and_auto_deal_creation(
    client, test_user, test_user2, test_user3, test_agent_user,
    auth_headers, auth_headers_buyer, auth_headers_buyer2, auth_headers_agent
):
    # 1. Seller lists a property in Delhi
    add_prop_res = client.post("/properties/add", headers=auth_headers, json={
        "description": "Luxurious 2BHK in Connaught Place",
        "city": "Delhi",
        "state": "Delhi",
        "pincode": "110001",
        "price": 1000000,
        "property_type": "apartment",
        "purpose": "buy",
        "bedrooms": 2,
        "bathrooms": 2,
        "area": 1200.0,
        "is_available": True
    })
    assert add_prop_res.status_code == 201
    prop_id = add_prop_res.json()["id"]

    # 2. Agent verifies the property listing
    verify_res = client.patch(
        f"/agents/verify/property/{prop_id}?action=verified",
        headers=auth_headers_agent
    )
    assert verify_res.status_code == 200

    # 3. Buyer 1 places a bid (900,000)
    bid1_res = client.post(f"/bid/{prop_id}", headers=auth_headers_buyer, json={
        "bid_amount": 900000,
        "message": "Ready to purchase immediately"
    })
    assert bid1_res.status_code == 201
    interest1_id = bid1_res.json()["interest_id"]

    # 4. Buyer 2 places a competing bid (850,000)
    bid2_res = client.post(f"/bid/{prop_id}", headers=auth_headers_buyer2, json={
        "bid_amount": 850000,
        "message": "Serious buyer here"
    })
    assert bid2_res.status_code == 201
    interest2_id = bid2_res.json()["interest_id"]

    # 5. Seller counters Buyer 1 with 950,000
    counter_res = client.patch(f"/bid/{interest1_id}", headers=auth_headers, json={
        "action": "counter",
        "counter_amount": 950000
    })
    assert counter_res.status_code == 200
    assert counter_res.json()["status"] == "countered"

    # 6. Buyer 1 accepts the counter-offer
    # Tests our Phase 1 Pydantic V2 fix: counter_amount is None/omitted and succeeds!
    accept_res = client.patch(f"/bid/{interest1_id}", headers=auth_headers_buyer, json={
        "action": "accept_counter"
    })
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "agreed"

    # 7. VERIFY THE ENTIRE SYSTEM STATE:
    # A) Check Deal Creation via GET /deals/my
    deals_res = client.get("/deals/my", headers=auth_headers_buyer)
    assert deals_res.status_code == 200
    deals = deals_res.json()
    assert len(deals) == 1
    deal = deals[0]
    assert deal["property_id"] == prop_id
    assert deal["seller_price"] == 950000
    # 2% fee on 950,000 = 19,000
    assert deal["agent_fee"] == 19000
    assert deal["final_price"] == 969000
    assert deal["status"] == "created"

    # B) Check Property Availability: must be False now
    prop_detail = client.get(f"/properties/{prop_id}", headers=auth_headers_buyer)
    assert prop_detail.status_code == 200
    assert prop_detail.json()["is_available"] is False

    # C) Check Buyer 2's Competing Bid: must be automatically REJECTED!
    buyer2_bids = client.get("/bid/buyer", headers=auth_headers_buyer2)
    assert buyer2_bids.status_code == 200
    bids = buyer2_bids.json()
    assert len(bids) == 1
    assert bids[0]["interest_id"] == interest2_id
    assert bids[0]["status"] == "rejected"


def test_seller_cannot_bid_on_own_property(client, test_user, auth_headers):
    # List property
    res = client.post("/properties/add", headers=auth_headers, json={
        "description": "My own property",
        "city": "Delhi",
        "state": "Delhi",
        "pincode": "110001",
        "price": 500000,
        "property_type": "apartment",
        "purpose": "buy",
        "is_available": True
    })
    prop_id = res.json()["id"]

    # Seller attempts to bid on their own property -> 403 Forbidden
    bid_res = client.post(f"/bid/{prop_id}", headers=auth_headers, json={
        "bid_amount": 400000
    })
    assert bid_res.status_code == 403
    assert "cannot bid on your own property" in bid_res.json()["detail"].lower()


def test_buyer_duplicate_bid_rejected(client, test_user, test_user2, auth_headers, auth_headers_buyer):
    res = client.post("/properties/add", headers=auth_headers, json={
        "description": "Property for duplicate bid test",
        "city": "Delhi",
        "state": "Delhi",
        "pincode": "110001",
        "price": 500000,
        "property_type": "apartment",
        "purpose": "buy",
        "is_available": True
    })
    prop_id = res.json()["id"]

    # First bid -> 201
    first_bid = client.post(f"/bid/{prop_id}", headers=auth_headers_buyer, json={"bid_amount": 450000})
    assert first_bid.status_code == 201

    # Second bid on same property by same buyer -> 409 Conflict
    second_bid = client.post(f"/bid/{prop_id}", headers=auth_headers_buyer, json={"bid_amount": 460000})
    assert second_bid.status_code == 409
    assert "already placed a bid" in second_bid.json()["detail"].lower()



def test_cannot_act_on_unavailable_property(client, test_user, test_user2, test_user3, auth_headers, auth_headers_buyer, auth_headers_buyer2):
    # 1. Seller lists property
    res = client.post("/properties/add", headers=auth_headers, json={
        "description": "Property for availability race condition test",
        "city": "Delhi",
        "state": "Delhi",
        "pincode": "110001",
        "price": 500000,
        "property_type": "apartment",
        "purpose": "buy",
        "is_available": True
    })
    prop_id = res.json()["id"]

    # 2. Both buyers place bids
    b1 = client.post(f"/bid/{prop_id}", headers=auth_headers_buyer, json={"bid_amount": 480000})
    b2 = client.post(f"/bid/{prop_id}", headers=auth_headers_buyer2, json={"bid_amount": 490000})
    interest1_id = b1.json()["interest_id"]
    interest2_id = b2.json()["interest_id"]

    # 3. Seller accepts Buyer 1's bid -> property is marked is_available = False!
    accept_res = client.patch(f"/bid/{interest1_id}", headers=auth_headers, json={"action": "accept_bid"})
    assert accept_res.status_code == 200

    # 4. Buyer 2 attempts to act on the interest for the sold property -> 400 Bad Request
    res2 = client.patch(f"/bid/{interest2_id}", headers=auth_headers_buyer2, json={"action": "withdraw"})
    assert res2.status_code == 400
    detail = res2.json()["detail"].lower()
    assert "no longer available" in detail or "finalized" in detail
