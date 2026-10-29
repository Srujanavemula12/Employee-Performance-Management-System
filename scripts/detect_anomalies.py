
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "employee_performance.db"
REPORT_PATH = ROOT / "reports" / "anomaly_report.json"


def main():
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    findings = []

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        def add_finding(rule, entity_type, entity_id, details):
            findings.append({
                "rule": rule,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "details": details,
            })

        rows = conn.execute("""
            SELECT c.check_in_id, c.employee_id, g.employee_id AS owner_id
            FROM check_ins c
            JOIN goals g ON g.goal_id = c.goal_id
            WHERE c.employee_id <> g.employee_id
        """).fetchall()

        for row in rows:
            add_finding(
                "CHECKIN_OWNER_MISMATCH",
                "CHECK_IN",
                row["check_in_id"],
                f"Check-in employee {row['employee_id']} differs "
                f"from goal owner {row['owner_id']}.",
            )

        rows = conn.execute("""
            SELECT key_result_id, current_value, target_value
            FROM key_results
            WHERE current_value > target_value
        """).fetchall()

        for row in rows:
            add_finding(
                "KEY_RESULT_EXCEEDS_TARGET",
                "KEY_RESULT",
                row["key_result_id"],
                f"Current value {row['current_value']} exceeds "
                f"target {row['target_value']}.",
            )

        rows = conn.execute("""
            SELECT review_id
            FROM reviews
            WHERE status IN ('SUBMITTED', 'APPROVED')
              AND submitted_at IS NULL
        """).fetchall()

        for row in rows:
            add_finding(
                "REVIEW_MISSING_SUBMISSION_TIMESTAMP",
                "REVIEW",
                row["review_id"],
                "Submitted or approved review has no submission timestamp.",
            )

        rows = conn.execute("""
            SELECT review_id
            FROM reviews
            WHERE status = 'APPROVED' AND approved_at IS NULL
        """).fetchall()

        for row in rows:
            add_finding(
                "APPROVED_REVIEW_MISSING_TIMESTAMP",
                "REVIEW",
                row["review_id"],
                "Approved review has no approval timestamp.",
            )

        rows = conn.execute("""
            SELECT feedback_id
            FROM feedback
            WHERE status = 'SUBMITTED' AND submitted_at IS NULL
        """).fetchall()

        for row in rows:
            add_finding(
                "FEEDBACK_MISSING_TIMESTAMP",
                "FEEDBACK",
                row["feedback_id"],
                "Submitted feedback has no submission timestamp.",
            )

        rows = conn.execute("""
            SELECT r.review_id
            FROM reviews r
            WHERE NOT EXISTS (
                SELECT 1 FROM audit_events a
                WHERE a.entity_type = 'REVIEW'
                  AND a.entity_id = r.review_id
            )
        """).fetchall()

        for row in rows:
            add_finding(
                "REVIEW_MISSING_AUDIT",
                "REVIEW",
                row["review_id"],
                "No audit event exists for this review.",
            )

        link_checks = [
            ("CHECK_IN", "check_ins", "check_in_id"),
            ("FEEDBACK", "feedback", "feedback_id"),
            (
                "DEVELOPMENT_PLAN",
                "development_plans",
                "development_plan_id",
            ),
        ]

        for entity_type, table, id_column in link_checks:
            rows = conn.execute(f"""
                SELECT l.evidence_link_id, l.entity_id
                FROM evidence_links l
                WHERE l.entity_type = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM {table} e
                      WHERE e.{id_column} = l.entity_id
                  )
            """, (entity_type,)).fetchall()

            for row in rows:
                add_finding(
                    "EVIDENCE_LINK_TARGET_MISSING",
                    "EVIDENCE_LINK",
                    row["evidence_link_id"],
                    f"Linked {entity_type} {row['entity_id']} does not exist.",
                )

        rows = conn.execute("""
            SELECT approval_id
            FROM approvals
            WHERE (decision = 'PENDING' AND decided_at IS NOT NULL)
               OR (decision IN ('APPROVED', 'REJECTED')
                   AND decided_at IS NULL)
               OR (decision = 'REJECTED' AND decision_reason IS NULL)
        """).fetchall()

        for row in rows:
            add_finding(
                "INVALID_APPROVAL_STATE",
                "APPROVAL",
                row["approval_id"],
                "Approval decision, timestamp, or rejection reason is inconsistent.",
            )

        rows = conn.execute("""
            SELECT a.approval_id, a.entity_id, a.decision, r.status
            FROM approvals a
            JOIN reviews r ON r.review_id = a.entity_id
            WHERE a.entity_type = 'REVIEW'
              AND (
                  (r.status = 'APPROVED' AND a.decision <> 'APPROVED')
                  OR
                  (r.status = 'SUBMITTED' AND a.decision = 'APPROVED')
              )
        """).fetchall()

        for row in rows:
            add_finding(
                "REVIEW_APPROVAL_STATUS_MISMATCH",
                "APPROVAL",
                row["approval_id"],
                f"Review {row['entity_id']} is {row['status']} but "
                f"approval is {row['decision']}.",
            )

    report = {
        "database": str(DB_PATH.name),
        "rules_checked": 9,
        "total_findings": len(findings),
        "findings_by_rule": {},
        "findings": findings,
    }

    for finding in findings:
        rule = finding["rule"]
        report["findings_by_rule"][rule] = (
            report["findings_by_rule"].get(rule, 0) + 1
        )

    REPORT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("ANOMALY DETECTION REPORT")
    print("=======================")
    print("Rules checked:", report["rules_checked"])
    print("Total findings:", report["total_findings"])

    for rule, count in sorted(report["findings_by_rule"].items()):
        print(f"{rule}: {count}")

    print("JSON report:", REPORT_PATH)


if __name__ == "__main__":
    main()