from backend.models import Deal
from backend.services.pricing import get_accepted_amount, compute_money_view
from backend.services.agent import get_platform_agent
from .. import models

def create_deal_from_interest(db, interest):
    """
    Adds a Deal to the session but does NOT commit.
    Caller is responsible for calling db.commit().
    """
    # Guard 1: only final states
    if interest.status not in ("accepted", "agreed"):
        return None

    # Guard 2: prevent duplicate deals
    existing = db.query(Deal).filter(
        Deal.interest_id == interest.id
    ).first()
    if existing:
        return existing

    base_amount = get_accepted_amount(interest)

    agent = db.query(models.Agent).filter(models.Agent.id == interest.agent_id).first()

    money = compute_money_view(base_amount, agent)

    deal = Deal(
        interest_id=interest.id,
        buyer_id=interest.buyer_id,
        seller_id=interest.property.seller_id,
        property_id=interest.property_id,
        agent_id=agent.id,
        seller_price=base_amount,
        agent_fee=money["agent_fee"],
        final_price=money["buyer_pays"],
    )

    db.add(deal)
    return deal