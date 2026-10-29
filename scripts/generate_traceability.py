
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "employee_performance.db"
LIMIT = 1000


def rows_as_dicts(conn, table, limit=LIMIT):
    conn.row_factory = sqlite3.Row
    if limit is None:
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
    else:
        rows = conn.execute(
            f"SELECT * FROM {table} ORDER BY rowid LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def main():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        tables = [
            "evidence",
            "evidence_links",
            "audit_events",
            "record_versions",
            "approvals",
        ]

        counts = {
            table: conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            for table in tables
        }

        if any(counts.values()):
            raise RuntimeError(
                "Traceability data already exists. "
                "Inspect the tables before retrying."
            )

        employees = [
            row[0] for row in conn.execute(
                "SELECT employee_id FROM employees ORDER BY employee_id"
            )
        ]

        if not employees:
            raise RuntimeError("Employees are missing.")

        evidence_rows = []
        link_rows = []
        audit_rows = []
        version_rows = []
        approval_rows = []

        # Generate evidence linked to real existing records.
        evidence_sources = [
            ("CHECK_IN", "check_ins", "check_in_id", "employee_id"),
            ("FEEDBACK", "feedback", "feedback_id", "reviewer_employee_id"),
            (
                "DEVELOPMENT_PLAN",
                "development_plans",
                "development_plan_id",
                "employee_id",
            ),
        ]

        evidence_counter = 0

        for entity_type, table, id_column, actor_column in evidence_sources:
            source_rows = rows_as_dicts(conn, table)

            for row in source_rows:
                evidence_counter += 1
                evidence_id = f"EVD-{evidence_counter:06d}"
                actor = row[actor_column]
                entity_id = row[id_column]

                evidence_rows.append((
                    evidence_id,
                    actor,
                    "DOCUMENT",
                    f"synthetic://evidence/{evidence_id}",
                    f"Generated supporting evidence for {entity_type} {entity_id}",
                    "2026-10-28 10:00:00",
                    "ACTIVE",
                ))

                link_rows.append((
                    f"EVL-{evidence_counter:06d}",
                    evidence_id,
                    entity_type,
                    entity_id,
                    "2026-10-28 10:05:00",
                    actor,
                ))

        # Create initial audit records and version snapshots.
        audit_sources = [
            ("GOAL", "goals", "goal_id", "employee_id"),
            ("CHECK_IN", "check_ins", "check_in_id", "employee_id"),
            ("REVIEW", "reviews", "review_id", "manager_employee_id"),
            ("FEEDBACK", "feedback", "feedback_id", "reviewer_employee_id"),
            (
                "DEVELOPMENT_PLAN",
                "development_plans",
                "development_plan_id",
                "employee_id",
            ),
        ]

        for entity_type, table, id_column, actor_column in audit_sources:
            # Audit and version history must cover every row, not only a sample.
            source_rows = rows_as_dicts(conn, table, limit=None)

            for index, row in enumerate(source_rows, start=1):
                entity_id = row[id_column]
                actor = row.get(actor_column)
                status = row.get("status", "")

                if entity_type == "REVIEW" and status == "APPROVED":
                    action = "APPROVE"
                elif status == "SUBMITTED":
                    action = "SUBMIT"
                else:
                    action = "CREATE"

                audit_rows.append((
                    f"AUD-{entity_type}-{index:06d}",
                    actor,
                    entity_type,
                    entity_id,
                    action,
                    None,
                    json.dumps(row, sort_keys=True),
                    "Generated initial audit record",
                    "2026-10-28 10:10:00",
                    f"TRACE-{entity_type}-{index:06d}",
                ))

                version_number = row.get("version", 1)

                version_rows.append((
                    f"VER-{entity_type}-{index:06d}",
                    entity_type,
                    entity_id,
                    version_number,
                    json.dumps(row, sort_keys=True),
                    actor,
                    "Generated initial record snapshot",
                    "2026-10-28 10:10:00",
                ))

        # Create pending approval requests for development plans.
        plans = rows_as_dicts(conn, "development_plans")

        for index, plan in enumerate(plans, start=1):
            review = conn.execute(
                """
                SELECT manager_employee_id
                FROM reviews
                WHERE review_id = ?
                """,
                (plan["review_id"],),
            ).fetchone()

            if review is None:
                raise RuntimeError(
                    f"Review missing for development plan "
                    f"{plan['development_plan_id']}"
                )

            approval_rows.append((
                f"APR-DP-{index:06d}",
                "DEVELOPMENT_PLAN",
                plan["development_plan_id"],
                plan["employee_id"],
                review[0],
                "PENDING",
                None,
                "2026-10-28 10:15:00",
                None,
            ))

        # Create review approval records consistent with review status.
        eligible_reviews = conn.execute(
            """
            SELECT review_id, employee_id, manager_employee_id, status
            FROM reviews
            WHERE status IN ('SUBMITTED', 'APPROVED')
            ORDER BY review_id
            """
        ).fetchall()

        for index, review in enumerate(eligible_reviews, start=1):
            review_id, employee_id, approver, review_status = review

            decision = (
                "APPROVED"
                if review_status == "APPROVED"
                else "PENDING"
            )

            approval_rows.append((
                f"APR-REV-{index:06d}",
                "REVIEW",
                review_id,
                employee_id,
                approver,
                decision,
                None,
                "2026-10-28 10:15:00",
                "2026-10-28 10:20:00"
                if decision == "APPROVED"
                else None,
            ))

        # Insert evidence and links.
        conn.executemany(
            """
            INSERT INTO evidence (
                evidence_id, submitted_by_employee_id, evidence_type,
                evidence_uri, description, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            evidence_rows,
        )

        conn.executemany(
            """
            INSERT INTO evidence_links (
                evidence_link_id, evidence_id, entity_type, entity_id,
                linked_at, linked_by_employee_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            link_rows,
        )

        # Insert audit history.
        conn.executemany(
            """
            INSERT INTO audit_events (
                audit_event_id, actor_employee_id, entity_type, entity_id,
                action, old_value_json, new_value_json, reason,
                occurred_at, correlation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            audit_rows,
        )

        # Insert record snapshots.
        conn.executemany(
            """
            INSERT INTO record_versions (
                version_id, entity_type, entity_id, version_number,
                record_json, changed_by_employee_id, change_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            version_rows,
        )

        # Insert approval workflow records.
        conn.executemany(
            """
            INSERT INTO approvals (
                approval_id, entity_type, entity_id,
                requested_by_employee_id, approver_employee_id,
                decision, decision_reason, requested_at, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            approval_rows,
        )

        print("Evidence records:", len(evidence_rows))
        print("Evidence links:", len(link_rows))
        print("Audit events:", len(audit_rows))
        print("Record versions:", len(version_rows))
        print("Approval records:", len(approval_rows))


if __name__ == "__main__":
    main()