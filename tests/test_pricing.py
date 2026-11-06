# tests/test_pricing.py
from types import SimpleNamespace
from backend.services.pricing import compute_agent_fee, compute_money_view, get_effective_price


def test_agent_fee_normal():
    # 2% of 100,000 = 2,000 (falls comfortably between min 1000 and max 50000)
    agent = SimpleNamespace(fee_percent=2.0, min_fee=1000, max_fee=50000)
    fee = compute_agent_fee(100000, agent)
    assert fee == 2000


def test_agent_fee_enforces_min_fee():
    # 2% of 10,000 is 200, which is below min_fee (1000). Must return min_fee (1000)
    agent = SimpleNamespace(fee_percent=2.0, min_fee=1000, max_fee=50000)
    fee = compute_agent_fee(10000, agent)
    assert fee == 1000


def test_agent_fee_enforces_max_fee():
    # 2% of 10,000,000 is 200,000, which is above max_fee (50000). Must cap at max_fee (50000)
    agent = SimpleNamespace(fee_percent=2.0, min_fee=1000, max_fee=50000)
    fee = compute_agent_fee(10000000, agent)
    assert fee == 50000


def test_agent_fee_none_agent():
    # If agent is None, fee must be 0
    fee = compute_agent_fee(100000, None)
    assert fee == 0


def test_compute_money_view_integration():
    # Verify compute_money_view accurately splits buyer_pays and seller_gets using agent fee
    agent = SimpleNamespace(fee_percent=2.0, min_fee=1000, max_fee=50000)
    # Base amount 50,000 -> 2% = 1,000 (equal to min_fee)
    result = compute_money_view(50000, agent)
    assert result["agent_fee"] == 1000
    assert result["buyer_pays"] == 51000
    assert result["seller_gets"] == 49000
