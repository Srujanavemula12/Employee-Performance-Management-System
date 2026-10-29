
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
<meta name="theme-color" content="#0b0d14">
<title>Pulse — Performance Intelligence</title>
<style>
:root{color-scheme:dark;--bg:#0b0d14;--surface:#121621;--surface2:#171c29;--line:#252c3b;--text:#eef2ff;--muted:#929bb0;--purple:#9b8cff;--cyan:#55d6e8;--green:#55d6a0;--amber:#f7c76b;--red:#ff8292;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 75% -15%,rgba(117,90,255,.13),transparent 42%),var(--bg);color:var(--text);min-height:100vh}button,a{font:inherit}a{color:inherit;text-decoration:none}.app{display:grid;grid-template-columns:246px minmax(0,1fr);min-height:100vh}.sidebar{position:sticky;top:0;height:100vh;background:rgba(14,17,26,.94);border-right:1px solid var(--line);padding:25px 17px;display:flex;flex-direction:column}.brand{display:flex;align-items:center;gap:11px;padding:0 10px 31px}.brand-mark{display:grid;place-items:center;width:36px;height:36px;border-radius:12px;background:linear-gradient(145deg,#9b8cff,#5d6cff);color:#fff;font-weight:900;box-shadow:0 6px 25px #7165ff38}.brand-name{font-weight:800;letter-spacing:.02em}.brand-sub{font-size:11px;color:var(--muted);margin-top:3px}.nav-label{font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:#687187;padding:0 12px;margin:12px 0 9px}.nav{display:grid;gap:5px}.nav a{display:flex;align-items:center;gap:12px;padding:11px 12px;border-radius:10px;color:#9da6ba;font-size:13px;transition:.18s}.nav a:hover,.nav a.active{background:#24243a;color:#e8e4ff}.nav a.active{box-shadow:inset 2px 0 var(--purple)}.nav-icon{width:18px;text-align:center;font-size:15px}.sidebar-bottom{margin-top:auto;padding:15px 11px 0}.health-pill{display:flex;align-items:center;gap:8px;font-size:11px;color:#a7b3c8;background:#151c27;border:1px solid var(--line);border-radius:10px;padding:11px}.dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 10px #55d6a066}.version{font-size:10px;color:#667087;padding:14px 4px 0}.main{min-width:0;padding:27px clamp(18px,3.1vw,43px) 30px}.topbar{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:30px}.eyebrow{font-size:10px;color:var(--purple);text-transform:uppercase;letter-spacing:.18em;font-weight:800;margin-bottom:8px}.page-title{font-size:clamp(24px,3vw,31px);letter-spacing:-.04em;margin:0;font-weight:750}.page-subtitle{color:var(--muted);font-size:13px;margin:8px 0 0}.top-actions{display:flex;align-items:center;gap:10px}.period{border:1px solid var(--line);border-radius:9px;background:var(--surface);color:#c5cce0;padding:10px 12px;font-size:12px}.refresh{border:0;border-radius:9px;background:linear-gradient(135deg,#8d7bff,#6b72ff);color:white;font-size:12px;font-weight:750;padding:11px 15px;cursor:pointer;box-shadow:0 5px 20px #7d70ff26}.refresh:hover{filter:brightness(1.1)}.refresh:focus-visible,a:focus-visible{outline:2px solid var(--cyan);outline-offset:3px}.section-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 14px}.section-head h2{font-size:14px;letter-spacing:-.01em;margin:0}.section-note{font-size:11px;color:var(--muted)}.error{color:var(--red);font-size:12px;margin:0 0 14px}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px}.metric,.panel{background:linear-gradient(145deg,rgba(23,28,41,.98),rgba(17,21,32,.98));border:1px solid var(--line);border-radius:15px;box-shadow:0 8px 30px #00000012}.metric{padding:17px 18px;min-width:0;position:relative;overflow:hidden}.metric:after{content:"";position:absolute;width:75px;height:75px;right:-28px;top:-32px;border-radius:50%;background:var(--glow,#9b8cff);opacity:.1;filter:blur(2px)}.metric-top{display:flex;align-items:center;justify-content:space-between;gap:8px}.metric-label{font-size:11px;color:#a1abc0}.metric-icon{width:29px;height:29px;display:grid;place-items:center;border:1px solid var(--line);border-radius:9px;color:var(--accent,var(--purple));background:#ffffff04;font-size:14px}.metric-value{font-size:clamp(25px,2.5vw,32px);font-weight:800;letter-spacing:-.05em;margin:15px 0 5px;font-variant-numeric:tabular-nums}.metric-foot{font-size:10px;color:#7f899f}.metric-foot span{color:var(--accent,var(--green));font-weight:700}.workspace{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(280px,.8fr);gap:14px;margin-top:23px}.panel{padding:20px;min-width:0}.status-list{display:grid;gap:19px}.status-head{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:8px;font-size:12px}.status-name{color:#cbd2e4}.status-value{font-variant-numeric:tabular-nums;font-weight:750}.track{height:7px;border-radius:99px;background:#252c3b;overflow:hidden}.bar{height:100%;border-radius:99px;background:linear-gradient(90deg,#7669ff,#b1a5ff);min-width:0}.bar.cyan{background:linear-gradient(90deg,#38bcd4,#75e2ed)}.bar.green{background:linear-gradient(90deg,#29b985,#6be6b1)}.bar.amber{background:linear-gradient(90deg,#c58b32,#ffd889)}.empty{color:var(--muted);font-size:12px}.summary-list{display:grid;gap:0}.summary-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 0;border-bottom:1px solid #252c3b;font-size:12px}.summary-row:last-child{border-bottom:0}.summary-label{display:flex;align-items:center;gap:9px;color:#b9c2d6}.summary-bullet{width:7px;height:7px;border-radius:3px;background:var(--bullet,var(--purple))}.summary-value{font-weight:750;font-variant-numeric:tabular-nums}.insight-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px;margin-top:14px}.insight{padding:16px 17px;background:#111722;border:1px solid var(--line);border-radius:13px}.insight-label{font-size:10px;color:var(--muted);margin-bottom:9px}.insight-value{font-size:19px;font-weight:800;letter-spacing:-.03em}.insight-note{font-size:10px;color:#7e8aa1;margin-top:6px}.insight-value.purple{color:var(--purple)}.insight-value.cyan{color:var(--cyan)}.insight-value.green{color:var(--green)}.anomaly-banner{display:flex;align-items:center;gap:13px;margin-top:15px;padding:15px 17px;border:1px solid #4a3b2a;background:linear-gradient(100deg,#241e19,#171923);border-radius:13px}.anomaly-icon{width:37px;height:37px;display:grid;place-items:center;border-radius:11px;background:#f7c76b14;color:var(--amber);font-size:17px;flex-shrink:0}.anomaly-copy{min-width:0}.anomaly-title{font-size:12px;font-weight:750}.anomaly-sub{font-size:10px;color:var(--muted);margin-top:4px}.anomaly-count{margin-left:auto;font-size:22px;font-weight:850;color:var(--amber);font-variant-numeric:tabular-nums}.footer{display:flex;justify-content:space-between;gap:12px;margin-top:25px;padding-top:16px;border-top:1px solid var(--line);font-size:10px;color:#69748b}.footer a{color:#a9a0ff}.loading{opacity:.65}.mobile-brand{display:none}
@media(max-width:1100px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.workspace{grid-template-columns:1fr 1fr}.sidebar{width:220px}.app{grid-template-columns:220px minmax(0,1fr)}}
@media(max-width:760px){.app{display:block}.sidebar{position:static;width:auto;height:auto;padding:13px 17px;border-right:0;border-bottom:1px solid var(--line)}.brand{padding:0}.sidebar .nav-label,.sidebar .nav,.sidebar-bottom{display:none}.main{padding:22px 15px}.topbar{align-items:flex-start;flex-direction:column;margin-bottom:23px}.top-actions{width:100%}.period{flex:1}.workspace{grid-template-columns:1fr}.insight-grid{grid-template-columns:1fr 1fr}.footer{flex-direction:column}.page-title{font-size:26px}}
@media(max-width:400px){.metrics{grid-template-columns:1fr 1fr;gap:9px}.metric{padding:13px}.metric-value{font-size:25px}.metric-label{font-size:10px}.panel{padding:16px}.insight-grid{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar" aria-label="Main navigation">
    <div class="brand"><div class="brand-mark">P</div><div><div class="brand-name">PULSE</div><div class="brand-sub">People Intelligence</div></div></div>
    <div class="nav-label">Workspace</div>
    <nav class="nav">
      <a class="active" href="/dashboard" aria-current="page"><span class="nav-icon">◫</span>Overview</a>
      <a href="/employees"><span class="nav-icon">♙</span>Employees</a>
      <a href="/goals"><span class="nav-icon">◎</span>Goals &amp; outcomes</a>
      <a href="/check-ins"><span class="nav-icon">↗</span>Check-ins</a>
      <a href="/reviews"><span class="nav-icon">▤</span>Performance reviews</a>
      <a href="/approvals"><span class="nav-icon">✓</span>Approvals</a>
      <a href="/evidence"><span class="nav-icon">⌁</span>Evidence library</a>
    </nav>
    <div class="nav-label">Governance</div>
    <nav class="nav"><a href="/audit-events"><span class="nav-icon">◷</span>Audit activity</a><a href="/docs"><span class="nav-icon">⌘</span>API reference</a></nav>
    <div class="sidebar-bottom"><div class="health-pill"><span class="dot"></span><span>Dashboard connected to API</span></div><div class="version">EMPLOYEE PERFORMANCE SUITE · V1.0</div></div>
  </aside>
  <main class="main">
    <header class="topbar">
      <div><div class="eyebrow">Performance intelligence / Overview</div><h1 class="page-title">Good work starts with clarity.</h1><p class="page-subtitle">A live view of goals, feedback and review activity across your organization.</p></div>
      <div class="top-actions"><div class="period">◷ &nbsp; Current dataset</div><button class="refresh" id="refreshButton" onclick="loadDashboard()">↻ &nbsp; Refresh data</button></div>
    </header>
    <div class="section-head"><h2>Workforce snapshot</h2><span class="section-note" id="updated" aria-live="polite">Loading live metrics…</span></div>
    <div class="error" id="error" role="alert"></div>
    <section class="metrics" id="cards" aria-label="Workforce metrics">
      <article class="metric loading"><div class="metric-label">Loading metrics</div><div class="metric-value">—</div></article>
      <article class="metric loading"><div class="metric-label">Loading metrics</div><div class="metric-value">—</div></article>
      <article class="metric loading"><div class="metric-label">Loading metrics</div><div class="metric-value">—</div></article>
      <article class="metric loading"><div class="metric-label">Loading metrics</div><div class="metric-value">—</div></article>
    </section>
    <section class="workspace">
      <article class="panel"><div class="section-head"><h2>Goal progress status</h2><span class="section-note">Distribution</span></div><div class="status-list" id="goals"><p class="empty">Loading goal status…</p></div></article>
      <article class="panel"><div class="section-head"><h2>Review cycle health</h2><span class="section-note">Current records</span></div><div class="status-list" id="reviews"><p class="empty">Loading review status…</p></div></article>
    </section>
    <section class="workspace">
      <article class="panel"><div class="section-head"><h2>Approval decisions</h2><span class="section-note">Workflow overview</span></div><div class="status-list" id="approvals"><p class="empty">Loading approvals…</p></div></article>
      <article class="panel"><div class="section-head"><h2>Activity at a glance</h2><span class="section-note">Connected records</span></div>
        <div class="summary-list">
          <div class="summary-row"><span class="summary-label"><i class="summary-bullet" style="--bullet:#9b8cff"></i>Key results</span><span class="summary-value" id="keyResults">—</span></div>
          <div class="summary-row"><span class="summary-label"><i class="summary-bullet" style="--bullet:#55d6e8"></i>Check-ins</span><span class="summary-value" id="checkIns">—</span></div>
          <div class="summary-row"><span class="summary-label"><i class="summary-bullet" style="--bullet:#55d6a0"></i>Feedback entries</span><span class="summary-value" id="feedback">—</span></div>
          <div class="summary-row"><span class="summary-label"><i class="summary-bullet" style="--bullet:#f7c76b"></i>Development plans</span><span class="summary-value" id="developmentPlans">—</span></div>
          <div class="summary-row"><span class="summary-label"><i class="summary-bullet" style="--bullet:#ff8292"></i>Evidence records</span><span class="summary-value" id="evidence">—</span></div>
        </div>
      </article>
    </section>
    <section class="insight-grid" aria-label="Workflow indicators">
      <article class="insight"><div class="insight-label">GOALS TRACKED</div><div class="insight-value purple" id="goalTotal">—</div><div class="insight-note">Across the dataset</div></article>
      <article class="insight"><div class="insight-label">REVIEWS RECORDED</div><div class="insight-value cyan" id="reviewTotal">—</div><div class="insight-note">Performance review records</div></article>
      <article class="insight"><div class="insight-label">APPROVAL ITEMS</div><div class="insight-value green" id="approvalTotal">—</div><div class="insight-note">Review and workflow approvals</div></article>
    </section>
    <section class="anomaly-banner" aria-live="polite"><div class="anomaly-icon">⚑</div><div class="anomaly-copy"><div class="anomaly-title">Data quality monitor</div><div class="anomaly-sub" id="anomalyMessage">Checking the latest anomaly report…</div></div><div class="anomaly-count" id="anomalyCount">—</div></section>
    <footer class="footer"><span>Pulse · Employee Performance Management System</span><span>Live local API data · <a href="/docs">Explore API documentation ↗</a></span></footer>
  </main>
</div>
<script>
const number = value => Number(value || 0).toLocaleString();
const safeText = value => String(value == null ? "Unknown" : value).replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
async function getJson(url) {
  const response = await fetch(url, {headers:{"Accept":"application/json"}});
  if (!response.ok) throw new Error(url + " returned HTTP " + response.status);
  return response.json();
}
function renderStatuses(targetId, rows, palette) {
  const target = document.getElementById(targetId);
  if (!Array.isArray(rows) || !rows.length) {
    target.innerHTML = '<p class="empty">No status data available.</p>';
    return;
  }
  const total = rows.reduce((sum, row) => sum + Math.max(0, Number(row.total) || 0), 0);
  const colors = palette || ["", "cyan", "green", "amber"];
  target.innerHTML = rows.map((row, index) => {
    const count = Math.max(0, Number(row.total) || 0);
    const width = total ? count / total * 100 : 0;
    const color = colors[index % colors.length];
    return '<div class="status-row"><div class="status-head"><span class="status-name">' +
      safeText(row.status || "Unknown") + '</span><strong class="status-value">' + number(count) +
      '</strong></div><div class="track" role="img" aria-label="' + safeText(row.status || "Unknown") +
      ': ' + number(count) + ' records"><div class="bar ' + color + '" style="width:' + width.toFixed(2) +
      '%"></div></div></div>';
  }).join("");
}
function metric(label, value, hint, icon, accent) {
  return '<article class="metric" style="--accent:' + accent + ';--glow:' + accent +
    '"><div class="metric-top"><div class="metric-label">' + label +
    '</div><div class="metric-icon">' + icon + '</div></div><div class="metric-value">' +
    number(value) + '</div><div class="metric-foot">' + hint + '</div></article>';
}
async function loadDashboard() {
  const button = document.getElementById("refreshButton");
  const error = document.getElementById("error");
  button.disabled = true;
  button.classList.add("loading");
  button.textContent = "↻  Refreshing…";
  error.textContent = "";
  try {
    const data = await getJson("/dashboard/summary");
    document.getElementById("cards").innerHTML = [
      metric("Employees",data.employees,"People in the workforce","♙","#9b8cff"),
      metric("Goals",data.goals,"Tracked performance goals","◎","#55d6e8"),
      metric("Reviews",data.reviews,"Performance review records","▤","#55d6a0"),
      metric("Approvals",data.approvals,"Workflow decisions","✓","#f7c76b")
    ].join("");
    renderStatuses("goals",data.goal_status,["","cyan","green","amber"]);
    renderStatuses("reviews",data.review_status,["","cyan","green","amber"]);
    renderStatuses("approvals",data.approval_decisions,["","cyan","green","amber"]);
    document.getElementById("keyResults").textContent = number(data.key_results);
    document.getElementById("checkIns").textContent = number(data.check_ins);
    document.getElementById("feedback").textContent = number(data.feedback);
    document.getElementById("developmentPlans").textContent = number(data.development_plans);
    document.getElementById("evidence").textContent = number(data.evidence);
    document.getElementById("goalTotal").textContent = number(data.goals);
    document.getElementById("reviewTotal").textContent = number(data.reviews);
    document.getElementById("approvalTotal").textContent = number(data.approvals);
    try {
      const report = await getJson("/dashboard/anomalies");
      document.getElementById("anomalyCount").textContent =
        report.total_findings == null ? "N/A" : number(report.total_findings);
      document.getElementById("anomalyMessage").textContent = report.total_findings == null
        ? "Run scripts/detect_anomalies.py to generate a report."
        : Number(report.total_findings) === 0
          ? "No findings reported in the latest anomaly scan."
          : "Findings are present in the latest anomaly report. Review the report before taking action.";
    } catch (_) {
      document.getElementById("anomalyCount").textContent = "N/A";
      document.getElementById("anomalyMessage").textContent = "Anomaly report is currently unavailable.";
    }
    document.getElementById("updated").textContent = "Updated " + new Date().toLocaleTimeString();
  } catch (err) {
    error.textContent = "Could not load dashboard data. Make sure the API is running and the database is initialized. " + err.message;
    document.getElementById("updated").textContent = "Live data unavailable";
  } finally {
    button.disabled = false;
    button.classList.remove("loading");
    button.textContent = "↻  Refresh data";
  }
}
loadDashboard();
</script>
</body>
</html>
""""""
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