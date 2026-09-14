"""
Creates the SQLite database and loads the starting repair-cost dataset.
Run this once before starting the app: python init_db.py
"""
import sqlite3
import os
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "fixwise.db")
CSV_PATH = os.path.join(BASE_DIR, "data", "repair_costs.csv")


def init_db():
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS repair_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_type TEXT NOT NULL,
            category TEXT NOT NULL,
            low_cost INTEGER NOT NULL,
            high_cost INTEGER NOT NULL,
            repairability_score INTEGER NOT NULL,
            typical_life_years INTEGER NOT NULL,
            description TEXT,
            UNIQUE(device_type, category)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_type TEXT,
            age INTEGER,
            problem_text TEXT,
            quote INTEGER,
            category TEXT,
            confidence TEXT,
            recommendation TEXT,
            created_at TEXT
        )
    """)
        # Add brand and model columns to existing databases.
    existing_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(reports)").fetchall()
    }

    if "brand" not in existing_columns:
        conn.execute("ALTER TABLE reports ADD COLUMN brand TEXT")

    if "model" not in existing_columns:
        conn.execute("ALTER TABLE reports ADD COLUMN model TEXT")

    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(
                """INSERT OR IGNORE INTO repair_costs
                   (device_type, category, low_cost, high_cost,
                    repairability_score, typical_life_years, description)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    row["device_type"],
                    row["category"],
                    int(row["low_cost"]),
                    int(row["high_cost"]),
                    int(row["repairability_score"]),
                    int(row["typical_life_years"]),
                    row["description"],
                ),
            )

    conn.commit()
    conn.close()
    print("Database ready at", DB_PATH)


if __name__ == "__main__":
    init_db()