"""
All pricing and repair-vs-replace logic lives here as plain, readable rules
backed by the repair_costs table. The AI layer is only ever allowed to pick
a category — it never sets or influences a price. That separation is the
whole point of the product: an AI that could quietly nudge prices around
would defeat the reason anyone would trust it.
"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "fixwise.db")

ALL_CATEGORIES = [
    "battery", "overheating", "screen", "motherboard_power",
    "keyboard", "storage_ram", "liquid_damage",
    "charging", "power", "other",
]

QUESTIONS = {
    "battery": [
        "Is the replacement battery genuine or a compatible third-party one?",
        "What is the battery's rated capacity?",
        "Is there a warranty on the new battery?",
    ],
    "overheating": [
        "Is this just a cleaning and thermal-paste job, or is a fan being replaced?",
        "Will you show me the old thermal paste before reapplying?",
        "Is labour the main cost here, or are parts involved?",
    ],
    "screen": [
        "Is it the panel itself or the cable — have both actually been tested?",
        "Is the replacement panel original spec for this model?",
        "What happens if the issue returns after the cable is reseated?",
    ],
    "motherboard_power": [
        "What test confirmed it's the motherboard and not the charger or adapter?",
        "Is there a cheaper possibility being ruled out first?",
        "What happens if this diagnosis turns out to be wrong?",
    ],
    "keyboard": [
        "Is the whole keyboard being replaced or just a key mechanism?",
        "Is there any sign of liquid damage underneath it?",
        "Is this a genuine part for this exact model?",
    ],
    "storage_ram": [
        "Would an SSD upgrade or more RAM fix this, or is something else slowing it down?",
        "Can the data be backed up before any change is made?",
        "Is this a permanent fix or a temporary improvement?",
    ],
    "liquid_damage": [
        "Has the board actually been opened and inspected, or is this a guess?",
        "Which specific components are confirmed damaged?",
        "Is there a real chance this fails again in a few months?",
    ],
    "charging": [
        "Was the device tested with a known-good charger and cable?",
        "Is the charging port damaged, or is the problem in the charging circuit?",
        "Is the replacement part original/OEM or compatible, and what warranty comes with it?",
    ],
    "power": [
        "What test confirmed the power supply or internal power circuit is faulty?",
        "Which specific component was found to be defective?",
        "Does the quoted repair include testing the device after the replacement?",
    ],
    "other": [
        "What specifically was tested to reach this diagnosis?",
        "Is there a cheaper first step worth trying before this repair?",
        "What warranty applies to the work being done?",
    ],
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_cost_range(device_type, category):
    """Looks up the cost range and repairability score
    for a specific device type and problem category."""
    conn = get_db()

    row = conn.execute(
        "SELECT low_cost, high_cost, repairability_score, typical_life_years "
        "FROM repair_costs WHERE device_type = ? AND category = ?",
        (device_type, category),
    ).fetchone()

    if row is None:
        row = conn.execute(
            "SELECT low_cost, high_cost, repairability_score, typical_life_years "
            "FROM repair_costs WHERE device_type = ? AND category = 'other'",
            (device_type,),
        ).fetchone()

    conn.close()

    return (
        row["low_cost"],
        row["high_cost"],
        row["repairability_score"],
        row["typical_life_years"],
    )


def check_quote(quote, low, high):
    """Checks a technician quote against the estimated repair range."""

    if quote is None:
        return (
            "unknown",
            "No quote entered yet — once you have one, compare it against the range above."
        )

    if quote < low * 0.70:
        return (
            "low",
            f"This quote is unusually low compared with the typical range of ₹{low:,}–₹{high:,}. "
            "Ask what parts and labour are included."
        )

    if quote > high * 1.25:
        return (
            "high",
            f"This quote is unusually high compared with the typical range of ₹{low:,}–₹{high:,}. "
            "Ask for an itemised breakdown and consider getting a second quote."
        )

    if quote > high:
        return (
            "slightly_high",
            f"This quote is above the typical range of ₹{low:,}–₹{high:,}, "
            "but not far enough above it to call it unusually high. "
            "Ask what additional parts or labour are included."
        )

    if quote < low:
        return (
            "slightly_low",
            f"This quote is below the typical range of ₹{low:,}–₹{high:,}. "
            "Confirm the part quality and warranty before proceeding."
        )

    return (
        "fair",
        f"This quote falls within the typical range of ₹{low:,}–₹{high:,}."
    )


def repair_vs_replace(age, low, high, replacement_value, category, confidence, safety_flag):
    """Decides repair / replace / inspect using plain, explainable rules —
    never a black-box score the user can't follow."""
    if safety_flag or confidence == "Low" or category in ("liquid_damage", "motherboard_power"):
        return "inspect", (
            "This kind of fault is hard to size up from a description alone. "
            "Get it physically inspected before approving any repair or replacement."
        )

    mid_cost = (low + high) / 2
    cost_ratio = mid_cost / replacement_value if replacement_value else 1

    if cost_ratio > 0.6:
        return "replace", (
            f"At an estimated Rs.{mid_cost:,.0f}, this repair costs more than half of a typical "
            f"replacement (Rs.{replacement_value:,}). Replacement is likely the better value."
        )

    if age >= 5 and cost_ratio > 0.35:
        return "replace", (
            f"At {age} years old, spending close to Rs.{mid_cost:,.0f} on this repair is a large "
            "share of a replacement's cost. Worth comparing both before deciding."
        )

    return "repair", (
        "At this age and cost, repairing is the more sensible option — this is a well-understood, "
        "commonly fixed issue."
    )


def get_questions(category):
    return QUESTIONS.get(category, QUESTIONS["other"])