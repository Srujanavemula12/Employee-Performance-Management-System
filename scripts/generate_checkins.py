
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

SEED = 20261022
CHECKIN_COUNT = 20_000

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "employee_performance.db"

random.seed(SEED)


def main():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        existing = conn.execute(
            "SELECT COUNT(*) FROM check_ins"
        ).fetchone()[0]

        if existing:
            raise RuntimeError(
                "Check-ins already exist. Refusing to create duplicates."
            )

        goals = conn.execute(
            "SELECT goal_id, employee_id, start_date FROM goals ORDER BY goal_id"
        ).fetchall()

        if not goals:
            raise RuntimeError("No goals found. Generate goals first.")

        rows = []
        base_date = date(2026, 1, 1)

        for i in range(1, CHECKIN_COUNT + 1):
            goal_id, employee_id, start_date = random.choice(goals)
            start = date.fromisoformat(start_date)
            checkin_date = max(
                start, base_date + timedelta(days=random.randint(0, 290))
            )

            rows.append((
                f"CHK-{i:06d}",
                goal_id,
                employee_id,
                checkin_date.isoformat(),
                "Synthetic progress update for validation.",
                round(random.uniform(0, 100), 2),
                random.choice(["LOW", "MEDIUM", "HIGH"]),
                random.choice(["NONE", "MINOR", "MAJOR"])
            ))

        conn.executemany(
            """
            INSERT INTO check_ins (
                check_in_id, goal_id, employee_id, check_in_date,
                progress_update, reported_progress, confidence_level,
                blocker_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows
        )

        print("Check-ins generated:", len(rows))


if __name__ == "__main__":
    main()