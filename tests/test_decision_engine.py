"""
Run with: pytest
Covers the quote-check and repair-vs-replace rules described in the project plan.
Assumes init_db.py has already been run so data/fixwise.db exists.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decision_engine import get_cost_range, check_quote, repair_vs_replace


def test_get_cost_range_known_category():
    low, high, repairability, life = get_cost_range("Laptop", "battery")
    assert low == 2500
    assert high == 4500
    assert repairability == 85


def test_get_cost_range_unknown_category_falls_back_to_other():
    low, high, repairability, life = get_cost_range("Laptop", "nonexistent_category")
    other_low, other_high, other_rep, other_life = get_cost_range("Laptop", "other")
    assert low == other_low
    assert high == other_high


def test_check_quote_no_quote():
    status, msg = check_quote(None, 2500, 4500)
    assert status == "unknown"


def test_check_quote_high():
    status, msg = check_quote(7000, 2500, 4500)
    assert status == "high"


def test_check_quote_low():
    status, msg = check_quote(1000, 2500, 4500)
    assert status == "low"


def test_check_quote_fair():
    status, msg = check_quote(3500, 2500, 4500)
    assert status == "fair"


def test_repair_vs_replace_safety_flag_forces_inspect():
    rec, msg = repair_vs_replace(
        age=2, low=2000, high=15000, replacement_value=35000,
        category="liquid_damage", confidence="Medium", safety_flag=False,
    )
    assert rec == "inspect"


def test_repair_vs_replace_recommends_repair_for_cheap_young_device():
    rec, msg = repair_vs_replace(
        age=1, low=800, high=1800, replacement_value=35000,
        category="overheating", confidence="High", safety_flag=False,
    )
    assert rec == "repair"


def test_repair_vs_replace_recommends_replace_for_old_expensive_repair():
    rec, msg = repair_vs_replace(
        age=6, low=8000, high=18000, replacement_value=35000,
        category="screen", confidence="High", safety_flag=False,
    )
    assert rec == "replace"