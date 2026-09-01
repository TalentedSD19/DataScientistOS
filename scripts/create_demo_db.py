from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "demo.db"


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)

    if DB_PATH.exists():
        DB_PATH.unlink()

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            age INTEGER,
            segment TEXT,
            monthly_charges REAL,
            tenure_months INTEGER,
            churn INTEGER
        )
        """
    )

    customers = [
        (1, 25, "A", 40.0, 4, 1),
        (2, 35, "A", 55.0, 24, 0),
        (3, 45, "B", 70.0, 36, 0),
        (4, 29, "B", 65.0, 6, 1),
        (5, 52, "C", 95.0, 48, 0),
        (6, 41, "C", 85.0, 18, 1),
        (7, 23, "A", 45.0, 3, 1),
        (8, 37, "B", 60.0, 30, 0),
        (9, 48, "C", 90.0, 42, 0),
        (10, 27, "A", 50.0, 8, 1),
        (11, 44, "B", 75.0, 40, 0),
        (12, 31, "C", 80.0, 12, 1),
    ]

    cursor.executemany(
        """
        INSERT INTO customers
        (customer_id, age, segment, monthly_charges, tenure_months, churn)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        customers,
    )

    connection.commit()
    connection.close()

    print(f"Created {DB_PATH}")


if __name__ == "__main__":
    main()