# services/pricing.py

def get_accepted_amount(interest):
    if interest.status == "accepted":
        return interest.bid_amount

    if interest.status == "agreed":
        if interest.counter_amount is None:
            raise ValueError("Agreed without counter_amount")
        return interest.counter_amount

    raise ValueError("Interest not agreed")


def compute_money_view(base_amount: int, agent):
    agent_fee = int(base_amount * agent.fee_percent / 100)
    return {
        "buyer_pays": base_amount + agent_fee,
        "seller_gets": base_amount - agent_fee,
        "agent_fee": agent_fee
    }


def get_effective_price(property_price: int, interest) -> int:
    if interest.status == "accepted":
        return interest.bid_amount

    if interest.status in ("countered", "agreed") and interest.counter_amount:
        return interest.counter_amount

    return property_price

def compute_agent_fee(price: int, agent) -> int:
    if not agent:
        return 0

    percent_fee = int(price * agent.fee_percent / 100)

    if percent_fee < agent.min_fee:
        return agent.min_fee

    if percent_fee > agent.max_fee:
        return agent.max_fee

    return percent_fee