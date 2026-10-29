
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

SEED = 20261022
GOAL_COUNT = 10_000
KEY_RESULTS_PER_GOAL = 2

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "employee_performance.db"

random.seed(SEED)

GOAL_TITLES = [
    "Improve delivery quality",
    "Automate recurring workflows",
    "Reduce operational errors",
    "Improve customer satisfaction",
    "Strengthen security practices",
    "Improve team documentation",
    "Increase process efficiency",
    "Develop technical expertise",
    "Improve reporting accuracy",
    "Complete professional development"
]

CATEGORIES = ["PERFORMANCE", "DEVELOPMENT", "OPERATIONAL", "STRATEGIC"]


def main():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        existing_goals = conn.execute(
            "SELECT COUNT(*) FROM goals"
        ).fetchone()[0]

        if existing_goals:
            raise RuntimeError(
                "Goals already exist. Refusing to create duplicates."
            )

        employees = [
            row[0] for row in conn.execute(
                "SELECT employee_id FROM employees ORDER BY employee_id"
            )
        ]

        cycles = [
            row[0] for row in conn.execute(
                "SELECT cycle_id FROM review_cycles ORDER BY cycle_id"
            )
        ]

        if not employees or not cycles:
            raise RuntimeError("Generate employees and review cycles first.")

        goal_rows = []
        key_result_rows = []
        start_date = date(2026, 1, 1)

        for i in range(1, GOAL_COUNT + 1):
            employee_id = random.choice(employees)
            cycle_id = random.choice(cycles)
            start = start_date + timedelta(days=random.randint(0, 180))
            due = start + timedelta(days=random.randint(30, 180))
            goal_id = f"GOAL-{i:06d}"

            goal_rows.append((
                goal_id,
                employee_id,
                cycle_id,
                random.choice(GOAL_TITLES),
                "Synthetic performance goal generated for testing.",
                random.choice(CATEGORIES),
                100.0,
                start.isoformat(),
                due.isoformat(),
                "IN_PROGRESS",
                1
            ))

            for j in range(1, KEY_RESULTS_PER_GOAL + 1):
                key_result_rows.append((
                    f"KR-{i:06d}-{j:02d}",
                    goal_id,
                    f"Measurable result {j} for goal {i}",
                    "NUMERIC",
                    100.0,
                    float(random.randint(0, 100)),
                    "units",
                    1.0,
                    "IN_PROGRESS"
                ))

        conn.executemany(
            """
            INSERT INTO goals (
                goal_id, employee_id, cycle_id, title, description,
                category, weight, start_date, due_date, status, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            goal_rows
        )

        conn.executemany(
            """
            INSERT INTO key_results (
                key_result_id, goal_id, title, metric_type,
                target_value, current_value, unit, weight, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            key_result_rows
        )

        print("Goals generated:", len(goal_rows))
        print("Key results generated:", len(key_result_rows))


if __name__ == "__main__":
    main()