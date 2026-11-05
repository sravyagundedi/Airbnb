import pytest
import random
from app.budget.split import even_split, weighted_split, calculate_running_totals


def test_three_way_split_of_1000_cents():
    # €10.00 split 3 ways -> 1000 cents = 334, 333, 333
    shares = even_split(1000, 3)
    assert len(shares) == 3
    assert shares == [334, 333, 333]
    assert sum(shares) == 1000


def test_weighted_split_exact_sum():
    # €100.00 (10000 cents) with weights [1.0, 2.0, 3.0]
    weights = [1.0, 2.0, 3.0]
    shares = weighted_split(10000, weights)
    assert len(shares) == 3
    assert sum(shares) == 10000
    # Expected: 1667, 3333, 5000 -> sum 10000
    assert shares == [1667, 3333, 5000]


def test_property_based_random_splits():
    # 500 iterations of random total cents and weights
    for _ in range(500):
        total_cents = random.randint(1, 1_000_000)
        n = random.randint(1, 20)
        
        # Even split property
        e_shares = even_split(total_cents, n)
        assert len(e_shares) == n
        assert sum(e_shares) == total_cents
        assert max(e_shares) - min(e_shares) <= 1  # Difference between shares is at most 1 cent

        # Weighted split property
        weights = [random.uniform(0.1, 10.0) for _ in range(n)]
        w_shares = weighted_split(total_cents, weights)
        assert len(w_shares) == n
        assert sum(w_shares) == total_cents


def test_single_participant_edge_case():
    assert even_split(4250, 1) == [4250]
    assert weighted_split(4250, [1.0]) == [4250]


def test_zero_weight_fallback():
    # All zero weights fall back to even split
    shares = weighted_split(999, [0.0, 0.0, 0.0])
    assert shares == [333, 333, 333]
    assert sum(shares) == 999


def test_running_totals_calculation():
    participants = [101, 102, 103]
    items = [
        {"id": 1, "cost_cents": 3000, "attendees": [101, 102, 103]},  # 1000 each
        {"id": 2, "cost_cents": 2000, "attendees": [101, 102]},       # 1000 each
        {"id": 3, "cost_cents": 1500, "attendees": [103]},            # 1500 to 103
    ]
    totals = calculate_running_totals(items, participants)
    assert totals[101] == 2000
    assert totals[102] == 2000
    assert totals[103] == 2500
    assert sum(totals.values()) == 6500
