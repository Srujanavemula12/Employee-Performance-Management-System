
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "employee_performance.db"


@pytest.fixture
def db():
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    yield connection
    connection.close()


def test_database_integrity(db):
    result = db.execute("PRAGMA integrity_check").fetchone()[0]
    assert result == "ok"


def test_foreign_key_integrity(db):
    errors = db.execute("PRAGMA foreign_key_check").fetchall()
    assert errors == []


@pytest.mark.parametrize(
    "table, expected",
    [
        ("employees", 3000),
        ("goals", 10000),
        ("key_results", 20000),
        ("check_ins", 20000),
        ("reviews", 3000),
        ("feedback", 6000),
        ("review_competencies", 15000),
        ("development_plans", 3000),
        ("evidence", 3000),
        ("evidence_links", 3000),
    ],
)
def test_expected_record_counts(db, table, expected):
    count = db.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    assert count == expected


def test_checkins_belong_to_goal_owners(db):
    invalid = db.execute("""
        SELECT COUNT(*)
        FROM check_ins c
        JOIN goals g ON g.goal_id = c.goal_id
        WHERE c.employee_id <> g.employee_id
    """).fetchone()[0]

    assert invalid == 0


def test_key_result_values_are_valid(db):
    invalid = db.execute("""
        SELECT COUNT(*)
        FROM key_results
        WHERE target_value <= 0 OR current_value < 0
    """).fetchone()[0]

    assert invalid == 0


def test_submitted_reviews_have_timestamps(db):
    invalid = db.execute("""
        SELECT COUNT(*)
        FROM reviews
        WHERE status IN ('SUBMITTED', 'APPROVED')
          AND submitted_at IS NULL
    """).fetchone()[0]

    assert invalid == 0


def test_approved_reviews_have_timestamps(db):
    invalid = db.execute("""
        SELECT COUNT(*)
        FROM reviews
        WHERE status = 'APPROVED'
          AND approved_at IS NULL
    """).fetchone()[0]

    assert invalid == 0


def test_submitted_feedback_has_timestamps(db):
    invalid = db.execute("""
        SELECT COUNT(*)
        FROM feedback
        WHERE status = 'SUBMITTED'
          AND submitted_at IS NULL
    """).fetchone()[0]

    assert invalid == 0


def test_every_review_has_audit_record(db):
    missing = db.execute("""
        SELECT COUNT(*)
        FROM reviews r
        WHERE NOT EXISTS (
            SELECT 1
            FROM audit_events a
            WHERE a.entity_type = 'REVIEW'
              AND a.entity_id = r.review_id
        )
    """).fetchone()[0]

    assert missing == 0


def test_evidence_links_reference_existing_entities(db):
    invalid = db.execute("""
        SELECT COUNT(*)
        FROM evidence_links l
        WHERE
            (l.entity_type = 'CHECK_IN' AND NOT EXISTS (
                SELECT 1 FROM check_ins c
                WHERE c.check_in_id = l.entity_id
            ))
            OR
            (l.entity_type = 'FEEDBACK' AND NOT EXISTS (
                SELECT 1 FROM feedback f
                WHERE f.feedback_id = l.entity_id
            ))
            OR
            (l.entity_type = 'DEVELOPMENT_PLAN' AND NOT EXISTS (
                SELECT 1 FROM development_plans d
                WHERE d.development_plan_id = l.entity_id
            ))
    """).fetchone()[0]

    assert invalid == 0


def test_approval_decision_timestamps(db):
    invalid = db.execute("""
        SELECT COUNT(*)
        FROM approvals
        WHERE
            (decision = 'PENDING' AND decided_at IS NOT NULL)
            OR
            (decision IN ('APPROVED', 'REJECTED')
             AND decided_at IS NULL)
            OR
            (decision = 'REJECTED' AND decision_reason IS NULL)
    """).fetchone()[0]

    assert invalid == 0


def test_review_version_snapshots_exist(db):
    missing = db.execute("""
        SELECT COUNT(*)
        FROM reviews r
        WHERE NOT EXISTS (
            SELECT 1
            FROM record_versions v
            WHERE v.entity_type = 'REVIEW'
              AND v.entity_id = r.review_id
              AND v.version_number = r.version
        )
    """).fetchone()[0]

    assert missing == 0