
import sqlite3
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "employee_performance.db"

app = FastAPI(
    title="Employee Performance Management API",
    description=(
        "Read-only API for employee goals, check-ins, reviews, "
        "feedback, evidence, approvals and performance metrics."
    ),
    version="1.0.0",
)


def fetch_all(sql, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [
            dict(row)
            for row in conn.execute(sql, params).fetchall()
        ]


def fetch_one(sql, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def get_record(table, id_column, record_id):
    # Table and column names below are supplied only by our own routes.
    return fetch_one(
        f"SELECT * FROM {table} WHERE {id_column} = ?",
        (record_id,),
    )


def count_records(table):
    return fetch_one(
        f"SELECT COUNT(*) AS total FROM {table}"
    )["total"]


def status_counts(table, column="status"):
    return fetch_all(
        f"""
        SELECT {column} AS status, COUNT(*) AS total
        FROM {table}
        GROUP BY {column}
        ORDER BY {column}
        """
    )


@app.get("/", tags=["System"])
def root():
    return {
        "message": "Employee Performance Management API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["System"])
def health():
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Database file not found.",
        )

    try:
        result = fetch_one("PRAGMA integrity_check")
        if not result or result.get("integrity_check") != "ok":
            raise HTTPException(
                status_code=503,
                detail="Database integrity check failed.",
            )
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc

    return {
        "status": "healthy",
        "database": "connected",
        "integrity": "ok",
    }


@app.get("/dashboard/summary", tags=["Dashboard"])
def dashboard_summary():
    return {
        "employees": count_records("employees"),
        "goals": count_records("goals"),
        "key_results": count_records("key_results"),
        "check_ins": count_records("check_ins"),
        "reviews": count_records("reviews"),
        "feedback": count_records("feedback"),
        "development_plans": count_records("development_plans"),
        "evidence": count_records("evidence"),
        "approvals": count_records("approvals"),
        "goal_status": status_counts("goals"),
        "review_status": status_counts("reviews"),
        "approval_decisions": status_counts("approvals", "decision"),
    }


@app.get("/employees", tags=["Employees"])
def list_employees(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return fetch_all(
        """
        SELECT * FROM employees
        ORDER BY employee_id
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )


@app.get("/employees/{employee_id}", tags=["Employees"])
def get_employee(employee_id: str):
    employee = get_record("employees", "employee_id", employee_id)

    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found.")

    return employee


@app.get("/goals", tags=["Goals"])
def list_goals(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    sql = "SELECT * FROM goals WHERE 1=1"
    params = []

    if employee_id is not None:
        sql += " AND employee_id = ?"
        params.append(employee_id)

    if status is not None:
        sql += " AND status = ?"
        params.append(status.upper())

    sql += " ORDER BY goal_id LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    return fetch_all(sql, params)


@app.get("/goals/{goal_id}", tags=["Goals"])
def get_goal(goal_id: str):
    goal = get_record("goals", "goal_id", goal_id)

    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found.")

    goal["key_results"] = fetch_all(
        """
        SELECT * FROM key_results
        WHERE goal_id = ?
        ORDER BY key_result_id
        """,
        (goal_id,),
    )

    goal["check_ins"] = fetch_all(
        """
        SELECT * FROM check_ins
        WHERE goal_id = ?
        ORDER BY check_in_date DESC
        LIMIT 50
        """,
        (goal_id,),
    )

    return goal


@app.get("/check-ins", tags=["Check-ins"])
def list_check_ins(
    employee_id: Optional[str] = None,
    goal_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    sql = "SELECT * FROM check_ins WHERE 1=1"
    params = []

    if employee_id is not None:
        sql += " AND employee_id = ?"
        params.append(employee_id)

    if goal_id is not None:
        sql += " AND goal_id = ?"
        params.append(goal_id)

    sql += " ORDER BY check_in_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    return fetch_all(sql, params)


@app.get("/reviews", tags=["Reviews"])
def list_reviews(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    sql = "SELECT * FROM reviews WHERE 1=1"
    params = []

    if employee_id is not None:
        sql += " AND employee_id = ?"
        params.append(employee_id)

    if status is not None:
        sql += " AND status = ?"
        params.append(status.upper())

    sql += " ORDER BY review_id LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    return fetch_all(sql, params)


@app.get("/reviews/{review_id}", tags=["Reviews"])
def get_review(review_id: str):
    review = get_record("reviews", "review_id", review_id)

    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")

    review["feedback"] = fetch_all(
        """
        SELECT * FROM feedback
        WHERE review_id = ?
        ORDER BY feedback_id
        """,
        (review_id,),
    )

    review["competencies"] = fetch_all(
        """
        SELECT * FROM review_competencies
        WHERE review_id = ?
        ORDER BY competency_id
        """,
        (review_id,),
    )

    review["development_plans"] = fetch_all(
        """
        SELECT * FROM development_plans
        WHERE review_id = ?
        ORDER BY development_plan_id
        """,
        (review_id,),
    )

    review["approvals"] = fetch_all(
        """
        SELECT * FROM approvals
        WHERE entity_type = 'REVIEW' AND entity_id = ?
        ORDER BY approval_id
        """,
        (review_id,),
    )

    return review


@app.get("/approvals", tags=["Approvals"])
def list_approvals(
    decision: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    sql = "SELECT * FROM approvals WHERE 1=1"
    params = []

    if decision is not None:
        sql += " AND decision = ?"
        params.append(decision.upper())

    sql += " ORDER BY requested_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    return fetch_all(sql, params)


@app.get("/evidence", tags=["Evidence"])
def list_evidence(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return fetch_all(
        """
        SELECT * FROM evidence
        ORDER BY evidence_id
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )


@app.get("/audit-events", tags=["Audit"])
def list_audit_events(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    sql = "SELECT * FROM audit_events WHERE 1=1"
    params = []

    if entity_type is not None:
        sql += " AND entity_type = ?"
        params.append(entity_type.upper())

    if entity_id is not None:
        sql += " AND entity_id = ?"
        params.append(entity_id)

    sql += " ORDER BY occurred_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    return fetch_all(sql, params)


@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
def dashboard_page():
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Employee Performance Dashboard</title>
<style>
:root {
  font-family: Inter, Segoe UI, Arial, sans-serif;
  color: #172033;
  background: #f4f7fb;
}
* { box-sizing: border-box; }
body { margin: 0; }
header {
  background: #172554;
  color: white;
  padding: 25px clamp(18px, 4vw, 48px);
}
header h1 { margin: 0 0 7px; font-size: clamp(22px, 3vw, 30px); }
header p { margin: 0; color: #cbd5e1; }
main { max-width: 1250px; margin: auto; padding: 25px 18px 45px; }
.toolbar { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:20px; flex-wrap:wrap; }
button {
  background:#2563eb; color:white; border:0; border-radius:9px;
  padding:11px 16px; cursor:pointer; font-weight:600;
}
button:hover { background:#1d4ed8; }
#updated { color:#64748b; font-size:13px; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(175px,1fr)); gap:15px; }
.card, .panel {
  background:white; border:1px solid #e2e8f0; border-radius:14px;
  padding:20px; box-shadow:0 3px 12px rgba(15,23,42,.035);
}
.card .label { color:#64748b; font-size:13px; }
.card .value { font-size:30px; font-weight:750; margin-top:10px; }
.card .hint { color:#64748b; font-size:12px; margin-top:7px; }
.panels { display:grid; grid-template-columns:repeat(auto-fit,minmax(290px,1fr)); gap:17px; margin-top:20px; }
.panel h2 { font-size:17px; margin:0 0 18px; }
.status-row { margin:13px 0; }
.status-head { display:flex; justify-content:space-between; gap:12px; font-size:13px; margin-bottom:7px; }
.track { height:9px; background:#e9eef6; border-radius:20px; overflow:hidden; }
.bar { height:100%; background:#3b82f6; border-radius:20px; }
.empty { color:#64748b; font-size:13px; }
.alert { border-left:4px solid #f59e0b; background:#fffbeb; padding:14px; border-radius:7px; }
.alert strong { font-size:25px; display:block; margin-bottom:5px; }
footer { text-align:center; color:#64748b; font-size:12px; padding:18px; }
#error { color:#b91c1c; margin:10px 0; }
</style>
</head>
<body>
<header>
  <h1>Employee Performance</h1>
  <p>Goals, reviews, approvals and workforce insights</p>
</header>
<main>
  <div class="toolbar">
    <div><strong>Performance overview</strong><div id="updated">Loading dashboard data...</div></div>
    <button onclick="loadDashboard()">Refresh data</button>
  </div>
  <div id="error"></div>
  <section class="cards" id="cards"></section>
  <section class="panels">
    <div class="panel"><h2>Goal status</h2><div id="goals"></div></div>
    <div class="panel"><h2>Review status</h2><div id="reviews"></div></div>
    <div class="panel">
      <h2>Approval overview</h2>
      <div id="approvals"></div>
      <div class="alert" style="margin-top:18px">
        <strong id="anomalyCount">?</strong>
        <span>Findings in the latest anomaly report</span>
      </div>
    </div>
  </section>
</main>
<footer>Employee Performance Management System ? Live data from the local API</footer>
<script>
const number = n => Number(n || 0).toLocaleString();
function renderStatuses(targetId, rows) {
  const target = document.getElementById(targetId);
  if (!rows || !rows.length) {
    target.innerHTML = '<p class="empty">No status data available.</p>';
    return;
  }
  const max = Math.max(...rows.map(r => Number(r.total)), 1);
  target.innerHTML = rows.map(row => `
    <div class="status-row">
      <div class="status-head"><span>${row.status || "Unknown"}</span><strong>${number(row.total)}</strong></div>
      <div class="track"><div class="bar" style="width:${Number(row.total)/max*100}%"></div></div>
    </div>`).join("");
}
async function loadDashboard() {
  document.getElementById("error").textContent = "";
  try {
    const response = await fetch("/dashboard/summary");
    if (!response.ok) throw new Error("Dashboard API returned HTTP " + response.status);
    const data = await response.json();
    const metrics = [
      ["Employees", data.employees, "People in the workforce"],
      ["Goals", data.goals, "Tracked performance goals"],
      ["Key results", data.key_results, "Measurable outcomes"],
      ["Check-ins", data.check_ins, "Progress updates"],
      ["Reviews", data.reviews, "Performance review records"],
      ["Approvals", data.approvals, "Approval workflow records"],
      ["Feedback", data.feedback, "Feedback records"],
      ["Development plans", data.development_plans, "Growth plans"]
    ];
    document.getElementById("cards").innerHTML = metrics.map(([label,value,hint]) => `
      <article class="card"><div class="label">${label}</div>
      <div class="value">${number(value)}</div><div class="hint">${hint}</div></article>
    `).join("");
    renderStatuses("goals", data.goal_status);
    renderStatuses("reviews", data.review_status);
    renderStatuses("approvals", data.approval_decisions);
    try {
      const a = await fetch("/dashboard/anomalies");
      const report = await a.json();
      document.getElementById("anomalyCount").textContent =
        number(report.total_findings);
    } catch (_) {
      document.getElementById("anomalyCount").textContent = "N/A";
    }
    document.getElementById("updated").textContent =
      "Last refreshed: " + new Date().toLocaleString();
  } catch (error) {
    document.getElementById("error").textContent =
      "Could not load dashboard data. Check that the FastAPI server is running. " + error.message;
    document.getElementById("updated").textContent = "Refresh after checking the API server.";
  }
}
loadDashboard();
</script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/dashboard/anomalies", tags=["Dashboard"])
def dashboard_anomalies():
    report_path = ROOT / "reports" / "anomaly_report.json"
    if not report_path.exists():
        return {
            "total_findings": None,
            "message": "Run scripts/detect_anomalies.py to generate the report."
        }

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read anomaly report."
        ) from exc

    return {
        "total_findings": report.get("total_findings", 0),
        "findings_by_rule": report.get("findings_by_rule", {}),
    }