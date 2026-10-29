
import json
import shutil
import sqlite3
from pathlib import Path

from scripts import detect_anomalies


def test_detector_finds_missing_review_audit(tmp_path, monkeypatch):
    original_db = detect_anomalies.DB_PATH
    test_db = tmp_path / "test_employee_performance.db"
    test_report = tmp_path / "anomaly_report.json"

    # Work on a copy; never alter the real database.
    shutil.copy2(original_db, test_db)

    with sqlite3.connect(test_db) as conn:
        review_id = conn.execute("""
            SELECT review_id
            FROM reviews
            ORDER BY review_id
            LIMIT 1
        """).fetchone()[0]

        conn.execute("""
            DELETE FROM audit_events
            WHERE entity_type = 'REVIEW'
              AND entity_id = ?
        """, (review_id,))

    monkeypatch.setattr(detect_anomalies, "DB_PATH", test_db)
    monkeypatch.setattr(detect_anomalies, "REPORT_PATH", test_report)

    detect_anomalies.main()

    report = json.loads(test_report.read_text(encoding="utf-8"))

    matches = [
        finding for finding in report["findings"]
        if finding["rule"] == "REVIEW_MISSING_AUDIT"
        and finding["entity_id"] == review_id
    ]

    assert len(matches) == 1


def test_detector_reports_clean_database(tmp_path, monkeypatch):
    original_db = detect_anomalies.DB_PATH
    test_db = tmp_path / "clean_employee_performance.db"
    test_report = tmp_path / "clean_report.json"

    shutil.copy2(original_db, test_db)

    monkeypatch.setattr(detect_anomalies, "DB_PATH", test_db)
    monkeypatch.setattr(detect_anomalies, "REPORT_PATH", test_report)

    detect_anomalies.main()

    report = json.loads(test_report.read_text(encoding="utf-8"))

    assert report["total_findings"] == 0