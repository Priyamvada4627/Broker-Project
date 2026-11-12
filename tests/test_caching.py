import fnmatch
import redis
from backend.services import cache as cache_service


class FakeRedis:
    """In-memory mock of redis.Redis supporting get, setex, scan_iter, and delete."""

    def __init__(self):
        self.store = {}
        self.get_calls = 0
        self.setex_calls = 0
        self.delete_calls = 0

    def get(self, key: str):
        self.get_calls += 1
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str):
        self.setex_calls += 1
        self.store[key] = value

    def scan_iter(self, match: str = "*"):
        for key in list(self.store.keys()):
            if fnmatch.fnmatch(key, match):
                yield key

    def delete(self, *keys):
        self.delete_calls += 1
        for key in keys:
            self.store.pop(key, None)


class BrokenRedis:
    """Simulates a downed Redis instance raising ConnectionError."""

    def get(self, key: str):
        raise redis.ConnectionError("Simulated Redis outage")

    def setex(self, key: str, ttl: int, value: str):
        raise redis.ConnectionError("Simulated Redis outage")

    def scan_iter(self, match: str = "*"):
        raise redis.ConnectionError("Simulated Redis outage")

    def delete(self, *keys):
        raise redis.ConnectionError("Simulated Redis outage")


def test_property_list_cache_aside_hit_and_miss(
    client, test_user, test_user2, auth_headers, auth_headers_buyer, monkeypatch
):
    fake_redis = FakeRedis()
    monkeypatch.setattr(cache_service, "get_redis_client", lambda: fake_redis)

    # Seller creates a property (also triggers invalidation, store is empty)
    res = client.post(
        "/properties/add",
        headers=auth_headers,
        json={
            "description": "Cached Villa in Jaipur",
            "city": "Jaipur",
            "state": "Rajasthan",
            "pincode": "302001",
            "price": 1000000,
            "property_type": "house",
            "purpose": "buy",
            "is_available": True,
        },
    )
    assert res.status_code == 201

    # 1. First GET /properties/all -> Cache Miss, stores result in Redis
    resp1 = client.get("/properties/all?city=Jaipur", headers=auth_headers_buyer)
    assert resp1.status_code == 200
    assert len(resp1.json()) == 1
    assert resp1.json()[0]["description"] == "Cached Villa in Jaipur"
    assert fake_redis.get_calls == 1
    assert fake_redis.setex_calls == 1
    assert len(fake_redis.store) == 1

    # 2. Second GET /properties/all -> Cache Hit, setex NOT called again
    resp2 = client.get("/properties/all?city=Jaipur", headers=auth_headers_buyer)
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()
    assert fake_redis.get_calls == 2
    assert fake_redis.setex_calls == 1


def test_cache_invalidation_on_property_add_and_bid_accept(
    client, test_user, test_user2, auth_headers, auth_headers_buyer, monkeypatch
):
    fake_redis = FakeRedis()
    monkeypatch.setattr(cache_service, "get_redis_client", lambda: fake_redis)

    # Seed 1 property
    res = client.post(
        "/properties/add",
        headers=auth_headers,
        json={
            "description": "Initial Flat",
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411001",
            "price": 500000,
            "property_type": "flat",
            "purpose": "buy",
            "is_available": True,
        },
    )
    assert res.status_code == 201
    prop_id = res.json()["id"]

    # Populate cache
    list_res = client.get("/properties/all?city=Pune", headers=auth_headers_buyer)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert len(fake_redis.store) == 1

    # Adding a second property must invalidate existing cache
    res2 = client.post(
        "/properties/add",
        headers=auth_headers,
        json={
            "description": "Second Flat",
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411001",
            "price": 600000,
            "property_type": "flat",
            "purpose": "buy",
            "is_available": True,
        },
    )
    assert res2.status_code == 201
    assert len(fake_redis.store) == 0

    # Re-populate cache: now returns both properties
    list_res2 = client.get("/properties/all?city=Pune", headers=auth_headers_buyer)
    assert len(list_res2.json()) == 2
    assert len(fake_redis.store) == 1

    # Buyer bids and seller accepts -> marks property unavailable & invalidates cache
    bid_res = client.post(f"/bid/{prop_id}", headers=auth_headers_buyer, json={"bid_amount": 490000})
    assert bid_res.status_code == 201
    interest_id = bid_res.json()["interest_id"]

    accept_res = client.patch(f"/bid/{interest_id}", headers=auth_headers, json={"action": "accept_bid"})
    assert accept_res.status_code == 200
    assert len(fake_redis.store) == 0

    # Fresh fetch shows updated availability (False)
    list_res3 = client.get("/properties/all?city=Pune", headers=auth_headers_buyer)
    sold_item = [item for item in list_res3.json() if item["property_id"] == prop_id][0]
    assert sold_item["is_available"] is False


def test_graceful_degradation_when_redis_is_down(
    client, test_user, test_user2, auth_headers, auth_headers_buyer, monkeypatch
):
    broken_redis = BrokenRedis()
    monkeypatch.setattr(cache_service, "get_redis_client", lambda: broken_redis)

    # Even with Redis throwing ConnectionError, write and read endpoints succeed
    add_res = client.post(
        "/properties/add",
        headers=auth_headers,
        json={
            "description": "Resilient Condo",
            "city": "Kochi",
            "state": "Kerala",
            "pincode": "682001",
            "price": 750000,
            "property_type": "apartment",
            "purpose": "buy",
            "is_available": True,
        },
    )
    assert add_res.status_code == 201

    get_res = client.get("/properties/all?city=Kochi", headers=auth_headers_buyer)
    assert get_res.status_code == 200
    assert len(get_res.json()) == 1
    assert get_res.json()[0]["description"] == "Resilient Condo"
