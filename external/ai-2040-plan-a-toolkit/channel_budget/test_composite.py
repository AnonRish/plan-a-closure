from channel_budget.composite import *
def test_channel_budget_composes_upper_bounds():
    x=compose_budget(ChannelBudget(CapacityInterval(0,10),CapacityInterval(0,20),CapacityInterval(0,30)))
    assert x["combined_capacity_bits_per_second"]["high"]==60
