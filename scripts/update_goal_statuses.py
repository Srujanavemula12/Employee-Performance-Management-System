import json
import random
import shutil
import sqlite3
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "employee_performance.db"
SEED = 20261029

DISTRIBUTION = [
    ("NOT_STARTED", 1000),
    ("IN_PROGRESS", 5500),
    ("AT_RISK", 1500),
    ("COMPLETED", 1500),
    ("CANCELLED", 500),
]


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.with_name(
        f"employee_performance_backup_{timestamp}.db"
    )
    shutil.copy2(DB_PATH, backup_path)
    print("Backup created:", backup_path)

    rng = random.Random(SEED)
    counts = Counter()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        goals = conn.execute(
            "SELECT * FROM goals ORDER BY goal_id"
        ).fetchall()

        if len(goals) != 10000:
            raise RuntimeError(
                f"Expected 10000 goals; found {len(goals)}. "
                "Database was not modified."
            )

        key_result_count = conn.execute(
            "SELECT COUNT(*) FROM key_results"
        ).fetchone()[0]
        if key_result_count != 20000:
            raise RuntimeError(
                f"Expected 20000 key results; found {key_result_count}. "
                "Database was not modified."
            )

        assignments = []
        for status, count in DISTRIBUTION:
            assignments.extend([status] * count)

        rng.shuffle(assignments)
        rng.shuffle(goals)

        try:
            conn.execute("BEGIN IMMEDIATE")

            for goal, new_status in zip(goals, assignments):
                goal_id = goal["goal_id"]
                old_status = goal["status"]

                if old_status == new_status:
                    counts[new_status] += 1
                    continue

                old_goal = dict(goal)
                new_version = goal["version"] + 1

                if new_status == "COMPLETED":
                    conn.execute("""
                        UPDATE key_results
                        SET current_value = target_value,
                            status = 'COMPLETED',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE goal_id = ?
                    """, (goal_id,))
                elif new_status == "NOT_STARTED":
                    conn.execute("""
                        UPDATE key_results
                        SET current_value = 0,
                            status = 'NOT_STARTED',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE goal_id = ?
                    """, (goal_id,))
                elif new_status == "CANCELLED":
                    conn.execute("""
                        UPDATE key_results
                        SET status = 'CANCELLED',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE goal_id = ?
                    """, (goal_id,))
                else:
                    conn.execute("""
                        UPDATE key_results
                        SET status = 'IN_PROGRESS',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE goal_id = ?
                    """, (goal_id,))

                conn.execute("""
                    UPDATE goals
                    SET status = ?, version = ?
                    WHERE goal_id = ?
                """, (new_status, new_version, goal_id))

                updated = conn.execute(
                    "SELECT * FROM goals WHERE goal_id = ?",
                    (goal_id,)
                ).fetchone()
                new_goal = dict(updated)

                latest_snapshot = conn.execute("""
                    SELECT MAX(version_number)
                    FROM record_versions
                    WHERE entity_type = 'GOAL' AND entity_id = ?
                """, (goal_id,)).fetchone()[0] or 0

                snapshot_version = max(new_version, latest_snapshot + 1)

                conn.execute("""
                    INSERT INTO record_versions (
                        version_id, entity_type, entity_id,
                        version_number, record_json,
                        changed_by_employee_id, change_reason
                    ) VALUES (?, 'GOAL', ?, ?, ?, NULL, ?)
                """, (
                    f"VER-GOAL-{uuid.uuid4().hex}",
                    goal_id,
                    snapshot_version,
                    json.dumps(new_goal, sort_keys=True),
                    "Deterministic synthetic goal-status distribution",
                ))

                conn.execute("""
                    INSERT INTO audit_events (
                        audit_event_id, actor_employee_id,
                        entity_type, entity_id, action,
                        old_value_json, new_value_json, reason,
                        correlation_id
                    ) VALUES (?, NULL, 'GOAL', ?, 'UPDATE', ?, ?, ?, ?)
                """, (
                    f"AUD-GOAL-{uuid.uuid4().hex}",
                    goal_id,
                    json.dumps({
                        "status": old_status,
                        "version": goal["version"],
                    }),
                    json.dumps({
                        "status": new_status,
                        "version": new_version,
                    }),
                    "Synthetic data quality improvement",
                    f"GOAL-STATUS-{timestamp}",
                ))

                counts[new_status] += 1

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        print("\nGOAL STATUS COUNTS")
        for row in conn.execute("""
            SELECT status, COUNT(*) AS total
            FROM goals
            GROUP BY status
            ORDER BY status
        """):
            print(f"{row['status']}: {row['total']:,}")

        print("\nTotal goals:", conn.execute(
            "SELECT COUNT(*) FROM goals"
        ).fetchone()[0])
        print("Total key results:", conn.execute(
            "SELECT COUNT(*) FROM key_results"
        ).fetchone()[0])
        print("Foreign-key check:", conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall())
        print("Database integrity:", conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0])
        print("Updated goal snapshots and audit events recorded.")


if __name__ == "__main__":
    main()