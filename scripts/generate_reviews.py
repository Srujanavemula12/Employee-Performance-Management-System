
import random
import sqlite3
from pathlib import Path

SEED = 20261022
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "employee_performance.db"

random.seed(SEED)


def main():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        existing = conn.execute(
            "SELECT COUNT(*) FROM reviews"
        ).fetchone()[0]

        if existing:
            raise RuntimeError(
                "Reviews already exist. Refusing to create duplicates."
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

        competencies = [
            row[0] for row in conn.execute(
                "SELECT competency_id FROM competencies ORDER BY competency_id"
            )
        ]

        manager_employees = [
            row[0] for row in conn.execute(
                "SELECT employee_id FROM managers ORDER BY manager_id"
            )
        ]

        if not all([
            employees, cycles, competencies, manager_employees
        ]):
            raise RuntimeError(
                "Required master data is missing. "
                "Run the earlier generators first."
            )

        review_rows = []
        feedback_rows = []
        competency_rows = []
        plan_rows = []

        for i, employee_id in enumerate(employees, start=1):
            cycle_id = cycles[(i - 1) % len(cycles)]
            manager_id = random.choice(manager_employees)

            status = random.choice([
                "NOT_STARTED",
                "IN_PROGRESS",
                "SUBMITTED",
                "APPROVED",
                "INCOMPLETE",
            ])

            self_rating = round(random.uniform(2, 5), 1)
            manager_rating = round(random.uniform(2, 5), 1)
            score = round((self_rating + manager_rating) / 2, 2)

            submitted_at = (
                "2026-10-15 12:00:00"
                if status in ("SUBMITTED", "APPROVED")
                else None
            )

            approved_at = (
                "2026-10-20 12:00:00"
                if status == "APPROVED"
                else None
            )

            review_id = f"REV-2026-{i:06d}"

            review_rows.append((
                review_id,
                employee_id,
                cycle_id,
                manager_id,
                self_rating,
                manager_rating,
                score,
                status,
                submitted_at,
                approved_at,
                1,
            ))

            # SUBMITTED feedback requires submitted_at.
            feedback_status = (
                "SUBMITTED" if submitted_at is not None else "DRAFT"
            )

            feedback_rows.append((
                f"FDB-{i:06d}-SELF",
                review_id,
                employee_id,
                employee_id,
                "SELF",
                "Synthetic self-reflection for testing.",
                self_rating,
                submitted_at,
                feedback_status,
            ))

            feedback_rows.append((
                f"FDB-{i:06d}-MGR",
                review_id,
                manager_id,
                employee_id,
                "MANAGER",
                "Synthetic manager feedback for testing.",
                manager_rating,
                submitted_at,
                feedback_status,
            ))

            for competency_id in competencies:
                competency_rows.append((
                    f"RC-{i:06d}-{competency_id}",
                    review_id,
                    competency_id,
                    random.randint(1, 5),
                    "Synthetic competency assessment.",
                    manager_id,
                ))

            plan_rows.append((
                f"DP-{i:06d}",
                employee_id,
                review_id,
                random.choice(competencies),
                "Improve a role-related skill",
                "Complete learning and demonstrate progress",
                "2027-03-31",
                "DRAFT",
                None,
                None,
            ))

        conn.executemany(
            """
            INSERT INTO reviews (
                review_id, employee_id, cycle_id, manager_employee_id,
                self_rating, manager_rating, calculated_score, status,
                submitted_at, approved_at, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            review_rows,
        )

        conn.executemany(
            """
            INSERT INTO feedback (
                feedback_id, review_id, reviewer_employee_id,
                subject_employee_id, feedback_type, comments,
                rating, submitted_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            feedback_rows,
        )

        conn.executemany(
            """
            INSERT INTO review_competencies (
                review_competency_id, review_id, competency_id,
                rating, comments, assessed_by_employee_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            competency_rows,
        )

        conn.executemany(
            """
            INSERT INTO development_plans (
                development_plan_id, employee_id, review_id,
                competency_id, objective, action_items, target_date,
                status, approved_by_employee_id, approved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            plan_rows,
        )

        print("Reviews generated:", len(review_rows))
        print("Feedback records generated:", len(feedback_rows))
        print("Review competency ratings generated:", len(competency_rows))
        print("Development plans generated:", len(plan_rows))


if __name__ == "__main__":
    main()