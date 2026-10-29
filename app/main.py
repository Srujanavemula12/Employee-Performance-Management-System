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
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#172338">
<title>PeopleOS · Performance dashboard</title>
<style>
:root{color-scheme:dark;--bg:#1c2739;--panel:#1b2739;--panel2:#202e43;--border:#2b3a52;--text:#f1f4fc;--muted:#929db5;--purple:#8f75ff;--blue:#5d70ff;--cyan:#63d6e2;--green:#7ee0b1;--gold:#f4ca7b;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(125deg,#b9b5f1 0%,#c7d6f2 45%,#a7bce8 100%);color:var(--text);min-height:100vh;padding:clamp(10px,2.2vw,30px)}a{color:inherit;text-decoration:none}button,input{font:inherit}.shell{max-width:1360px;min-height:calc(100vh - 60px);margin:auto;display:grid;grid-template-columns:48px 178px minmax(0,1fr);overflow:hidden;border:1px solid #aab7d4;border-radius:10px;background:var(--bg);box-shadow:0 22px 70px #28335a30}.rail{background:#111b2c;border-right:1px solid var(--border);display:flex;align-items:center;flex-direction:column;padding:17px 8px;gap:13px}.rail-logo{height:38px;width:38px;display:grid;place-items:center;border-radius:12px;background:linear-gradient(145deg,#a08dff,#5d76fa);font-size:20px;font-weight:900;margin-bottom:13px}.rail-link{height:38px;width:38px;border-radius:11px;display:grid;place-items:center;color:#8795b0;font-size:17px}.rail-link.active,.rail-link:hover{background:#2c3474;color:#fff}.rail-spacer{flex:1}.sidebar{background:#162235;border-right:1px solid #304058;padding:22px 12px 14px;display:flex;flex-direction:column;min-width:0}.brand{display:flex;align-items:center;gap:10px;padding:0 8px 31px}.brand-mark{font-size:23px;color:#9c8cff;font-weight:900}.brand-name{font-size:19px;font-weight:800;letter-spacing:-.04em}.brand-name span{font-weight:400;color:#aebbd0}.side-label{color:#9ba9c0;font-size:10px;letter-spacing:.12em;margin:0 10px 12px;text-transform:uppercase}.nav{display:grid;gap:4px}.nav a{display:flex;align-items:center;gap:12px;padding:10px 11px;color:#8e9bb3;border-radius:9px;font-size:12px;white-space:nowrap}.nav a:hover,.nav a.active{background:#2a3678;color:#f3f2ff}.nav a.active{box-shadow:inset 3px 0 #9b8cff}.nav-icon{font-size:16px;width:17px;text-align:center}.side-divider{height:1px;background:#304058;margin:23px 8px 18px}.sidebar-bottom{margin-top:auto;border-radius:13px;padding:15px 13px;background:linear-gradient(145deg,#293a63,#3b4f9c);font-size:11px;line-height:1.6;color:#e0e7ff}.sidebar-bottom strong{display:block;font-size:12px;margin-bottom:9px}.sidebar-bottom a{display:block;text-align:center;padding:9px;background:#f8f9ff;color:#172338;border-radius:9px;font-weight:750;margin-top:10px}.main{min-width:0;padding:22px clamp(16px,1.6vw,24px) 16px;background-image:linear-gradient(#ffffff03 1px,transparent 1px),linear-gradient(90deg,#ffffff03 1px,transparent 1px);background-size:26px 26px}.topbar{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:20px}.heading h1{margin:0;font-size:clamp(23px,2.2vw,30px);letter-spacing:-.045em}.heading p{margin:8px 0 0;font-size:12px;color:#aab7ce}.heading p strong{color:#9a8cff}.tools{display:flex;align-items:center;gap:10px}.search{width:min(245px,22vw);display:flex;align-items:center;gap:8px;border:1px solid #3b4b66;background:#111b2d;border-radius:30px;padding:10px 13px;color:#91a0b9}.search input{min-width:0;width:100%;background:transparent;border:0;outline:0;color:var(--text);font-size:11px}.search input::placeholder{color:#74829e}.round-btn{height:36px;width:36px;border:1px solid #394964;border-radius:50%;background:#222f47;color:#a8b5cc;cursor:pointer}.round-btn.active{background:#665cff;color:#fff}.avatar{height:35px;width:35px;border-radius:50%;display:grid;place-items:center;border:2px solid #64d8b0;background:#31435d;font-size:12px;font-weight:800}.profile{border-left:1px solid #34425a;padding-left:15px;font-size:11px;font-weight:700;white-space:nowrap}.profile small{display:block;color:#8f9cb4;font-weight:400;font-size:9px;margin-top:4px}.top-actions{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:0 0 15px}.subtle{font-size:11px;color:#9aa9c0}.subtle strong{color:#9585ff}.controls{display:flex;gap:8px;align-items:center}.selectlike,.download{border:1px solid #3b4c67;background:#142034;color:#c9d3e7;padding:8px 10px;border-radius:8px;font-size:10px}.download{cursor:pointer}.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.kpi,.panel{background:linear-gradient(145deg,#202d42,#19263a);border:1px solid #2b3c55;border-radius:9px;min-width:0}.kpi{padding:13px 14px;position:relative;overflow:hidden}.kpi-top{display:flex;align-items:center;gap:9px;font-size:11px;color:#d2dced}.kpi-icon{height:32px;width:32px;display:grid;place-items:center;background:#2b3678;color:#bcb5ff;border-radius:9px;font-size:15px}.kpi-number{font-size:clamp(23px,2.2vw,30px);font-weight:800;letter-spacing:-.05em;margin:13px 0 8px;white-space:nowrap}.kpi-foot{display:flex;justify-content:space-between;align-items:center;gap:6px;font-size:9px;color:#8f9db6}.trend{padding:4px 7px;border-radius:7px;background:#7de2b1;color:#133e35;font-size:9px;font-weight:800;white-space:nowrap}.content-grid{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(230px,.8fr);gap:13px;margin-top:14px}.panel{padding:17px}.panel-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:17px}.panel-title{display:flex;align-items:center;gap:10px;font-size:14px;font-weight:750}.panel-title .kpi-icon{flex-shrink:0}.panel-meta{font-size:9px;color:#8e9db7;font-weight:400}.legend{display:flex;gap:12px;align-items:center;color:#9eabc1;font-size:9px}.legend span{display:flex;align-items:center;gap:5px}.legend i{display:inline-block;width:8px;height:8px;border-radius:2px;background:#8f8ce7}.legend i.second{background:#566fe8}.chart{height:204px;display:flex;align-items:stretch;gap:12px;padding:4px 0 0}.y-axis{display:flex;flex-direction:column;justify-content:space-between;color:#74839d;font-size:9px;padding:3px 0 21px;flex-shrink:0}.chart-area{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:space-between;background:repeating-linear-gradient(to bottom,transparent 0,transparent calc(25% - 1px),#ffffff12 calc(25% - 1px),#ffffff12 25%);border-bottom:1px solid #3a4962}.bars{height:calc(100% - 21px);display:flex;align-items:flex-end;justify-content:space-around;gap:clamp(3px,.7vw,10px);padding:0 4px}.bar-group{height:100%;flex:1;display:flex;align-items:flex-end;justify-content:center;gap:4px;min-width:0}.bar-col{width:min(38%,18px);min-width:5px;border-radius:3px 3px 0 0;background:linear-gradient(180deg,#a4a2f4,#7378d7);transition:height .35s}.bar-col.second{background:linear-gradient(180deg,#648eff,#475bd0)}.bar-col:hover{filter:brightness(1.25)}.x-axis{display:flex;justify-content:space-around;gap:4px;color:#7f8da6;font-size:9px;padding-top:7px}.insight-card{position:relative;overflow:hidden}.cost-total{font-size:24px;font-weight:800;margin:0 0 3px}.green-note{color:#7ce2b0;font-size:10px}.ring-wrap{display:grid;place-items:center;padding:4px 0 9px}.ring{width:min(170px,100%);aspect-ratio:1;position:relative;display:grid;place-items:center}.ring svg{width:100%;height:100%;transform:rotate(-90deg)}.ring-center{position:absolute;text-align:center}.ring-center strong{font-size:27px}.ring-center small{display:block;font-size:9px;color:#93a1bb;margin-top:4px}.ring-stats{display:grid;grid-template-columns:repeat(2,1fr);gap:12px 8px}.ring-stat{display:flex;gap:7px;align-items:flex-start;font-size:10px}.ring-stat i{width:7px;height:7px;border-radius:50%;background:var(--dot);margin-top:3px;flex-shrink:0}.ring-stat strong{display:block;font-size:12px}.ring-stat small{color:#8594ad;font-size:9px}.bottom-grid{display:grid;grid-template-columns:minmax(0,.95fr) minmax(0,1.45fr);gap:13px;margin-top:14px}.status-list{display:grid;gap:13px}.status-head{display:flex;justify-content:space-between;gap:10px;font-size:10px;margin-bottom:7px}.status-head span{color:#c1cce0}.status-head strong{color:#80e3b6;font-weight:700}.track{height:6px;border-radius:10px;background:#34415d;overflow:hidden}.track-fill{height:100%;border-radius:10px;background:linear-gradient(90deg,#688cff,#9a85ff)}.track-fill.green{background:linear-gradient(90deg,#50cfa4,#8be7b8)}.track-fill.cyan{background:linear-gradient(90deg,#4fc7dd,#75e2e9)}.track-fill.gold{background:linear-gradient(90deg,#e7ae5c,#f8d68a)}.heatmap{display:grid;grid-template-columns:35px repeat(7,minmax(0,1fr));gap:5px}.heat-head,.heat-time{display:grid;place-items:center;font-size:9px;color:#8c9bb4}.heat-cell{height:30px;border-radius:6px;display:grid;place-items:center;font-size:9px;color:#f1f4ff;background:#303e62}.heat-cell.l1{background:#414f9a}.heat-cell.l2{background:#4e64ca}.heat-cell.l3{background:#5c79ff}.heat-cell.l4{background:#6b65ef}.heat-cell:hover{outline:1px solid #c2b9ff}.heat-foot{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:12px;font-size:9px;color:#8a98b0}.heat-key{display:flex;gap:4px;align-items:center}.heat-key i{height:8px;width:8px;border-radius:2px;background:#303e62}.heat-key i:nth-child(2){background:#414f9a}.heat-key i:nth-child(3){background:#4e64ca}.heat-key i:nth-child(4){background:#5c79ff}.heat-key i:nth-child(5){background:#6b65ef}.activity{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 0;border-bottom:1px solid #2b3b54;font-size:10px}.activity:last-child{border-bottom:0}.activity-name{display:flex;align-items:center;gap:8px;color:#c6d1e5}.activity-dot{height:7px;width:7px;border-radius:50%;background:var(--dot,#8c7bff)}.activity strong{font-size:11px}.empty{font-size:10px;color:#91a0b9}.error{font-size:11px;color:#ff9aa8;margin:0 0 10px}.footer{display:flex;justify-content:space-between;gap:10px;margin-top:18px;padding-top:12px;border-top:1px solid #293950;color:#71819b;font-size:9px}.footer a{color:#a9a0ff}.mobile-menu{display:none}
@media(max-width:1200px){.shell{grid-template-columns:46px 165px minmax(0,1fr)}.sidebar{padding:20px 10px 13px}.brand-name{font-size:16px}.nav a{font-size:11px;padding:10px 8px}.content-grid{grid-template-columns:minmax(0,1.3fr) minmax(210px,.8fr)}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.search{width:170px}.profile{display:none}}
@media(max-width:850px){body{padding:8px}.shell{grid-template-columns:1fr;min-height:calc(100vh - 16px);border-radius:10px}.rail{display:none}.sidebar{padding:13px 15px;border-right:0;border-bottom:1px solid var(--border)}.brand{padding:0}.brand-name{font-size:18px}.side-label,.sidebar .nav,.side-divider,.sidebar-bottom{display:none}.main{padding:20px 14px}.topbar{align-items:flex-start}.tools .search{display:none}.content-grid,.bottom-grid{grid-template-columns:1fr}.top-actions{align-items:flex-start;flex-direction:column}.controls{width:100%;flex-wrap:wrap}.chart{height:180px}.heat-cell{height:26px}.footer{flex-direction:column}}
@media(max-width:440px){.topbar{flex-direction:column}.tools{width:100%;justify-content:space-between}.kpis{gap:8px}.kpi{padding:12px}.kpi-number{font-size:23px}.kpi-top{font-size:10px}.kpi-icon{height:28px;width:28px}.panel{padding:13px}.panel-title{font-size:12px}.chart{gap:6px}.heatmap{gap:3px;grid-template-columns:28px repeat(7,minmax(0,1fr))}.heat-cell{height:23px;font-size:8px}.ring{width:145px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body>
<div class="shell">
  <aside class="rail" aria-label="Quick navigation">
    <div class="rail-logo">P</div>
    <a class="rail-link active" href="/dashboard" aria-label="Dashboard">▦</a>
    <a class="rail-link" href="/ui/employees" aria-label="Employees">♙</a>
    <a class="rail-link" href="/ui/goals" aria-label="Goals">◎</a>
    <a class="rail-link" href="/ui/reviews" aria-label="Reviews">▤</a>
    <a class="rail-link" href="/ui/approvals" aria-label="Approvals">✓</a>
    <div class="rail-spacer"></div>
    <a class="rail-link" href="/ui/audit-events" aria-label="Audit activity">◷</a>
    <a class="rail-link" href="/docs" aria-label="API docs">⌘</a>
  </aside>
  <aside class="sidebar" aria-label="Main navigation">
    <div class="brand"><div class="brand-mark">↗</div><div class="brand-name">People<span>OS</span></div></div>
    <div class="side-label">Main menu</div>
    <nav class="nav">
      <a class="active" href="/dashboard"><span class="nav-icon">▦</span>Dashboard</a>
      <a href="#analytics"><span class="nav-icon">▥</span>Analytics</a>
      <a href="#activity"><span class="nav-icon">◉</span>Performance pulse</a>
      <a href="/ui/goals"><span class="nav-icon">⌁</span>Goals &amp; outcomes</a>
      <a href="/ui/check-ins"><span class="nav-icon">⌄</span>Check-ins</a>
      <a href="/ui/reviews"><span class="nav-icon">▤</span>Review cycles</a>
      <a href="/ui/approvals"><span class="nav-icon">✓</span>Approvals</a>
    </nav>
    <div class="side-divider"></div>
    <div class="side-label">Workspaces</div>
    <nav class="nav">
      <a href="/ui/employees"><span class="nav-icon">♙</span>Employee directory</a>
      <a href="/ui/evidence"><span class="nav-icon">⌗</span>Evidence library</a>
      <a href="/ui/audit-events"><span class="nav-icon">◷</span>Audit trail</a>
      <a href="/docs"><span class="nav-icon">⚙</span>API &amp; system</a>
    </nav>
    <div class="sidebar-bottom"><strong>✦ &nbsp; People-first insights</strong>Turn employee progress into clear, evidence-backed decisions.<a href="/docs">Explore API ↗</a></div>
  </aside>
  <main class="main">
    <header class="topbar">
      <div class="heading"><h1>Dashboard</h1><p>You have <strong id="headlineInsight">live performance insights</strong> ready to explore.</p></div>
      
<div class="tools">
  <button class="round-btn active" id="refreshButton" title="Refresh dashboard data" aria-label="Refresh dashboard data">↻</button>
</div>

    </header>
    <div class="top-actions">
      <div class="subtle" id="updated" aria-live="polite">Connecting to your performance data…</div>
      <div class="controls">
  <button class="download" id="downloadButton">Download summary ↓</button>
</div>
    </div>
    <div class="error" id="error" role="alert"></div>
    <section class="kpis" id="kpis" aria-label="Key performance metrics">
      <article class="kpi"><div class="kpi-top">Employees</div><div class="kpi-number">—</div></article>
      <article class="kpi"><div class="kpi-top">Goals</div><div class="kpi-number">—</div></article>
      <article class="kpi"><div class="kpi-top">Reviews</div><div class="kpi-number">—</div></article>
      <article class="kpi"><div class="kpi-top">Approvals</div><div class="kpi-number">—</div></article>
    </section>
    <section class="content-grid" id="analytics">
      <article class="panel">
        <div class="panel-head"><div class="panel-title"><span class="kpi-icon">▥</span><span>Performance overview<br><span class="panel-meta">Goal status distribution · live API data</span></span></div><div class="legend"><span><i></i>Goals</span><span><i class="second"></i>Reviews</span></div></div>
        <div class="chart" id="chart"><div class="empty">Loading performance distribution…</div></div>
      </article>
      <article class="panel insight-card">
        <div class="panel-head"><div class="panel-title"><span class="kpi-icon">⌁</span>Progress mix</div><span class="panel-meta">Goal statuses</span></div>
        <div class="cost-total" id="goalCompletion">—</div><div class="green-note" id="goalCompletionNote">Goal status summary</div>
        <div class="ring-wrap"><div class="ring">
          <svg viewBox="0 0 160 160" aria-label="Goal status distribution chart">
            <circle cx="80" cy="80" r="59" fill="none" stroke="#34435f" stroke-width="10"/>
            <circle id="ring1" cx="80" cy="80" r="59" fill="none" stroke="#9c7bff" stroke-width="10" stroke-linecap="round" stroke-dasharray="0 371" />
            <circle cx="80" cy="80" r="43" fill="none" stroke="#34435f" stroke-width="8"/>
            <circle id="ring2" cx="80" cy="80" r="43" fill="none" stroke="#5b8cff" stroke-width="8" stroke-linecap="round" stroke-dasharray="0 270"/>
            <circle cx="80" cy="80" r="29" fill="none" stroke="#34435f" stroke-width="7"/>
            <circle id="ring3" cx="80" cy="80" r="29" fill="none" stroke="#62d8e5" stroke-width="7" stroke-linecap="round" stroke-dasharray="0 182"/>
          </svg>
          <div class="ring-center"><strong id="ringTotal">—</strong><small>GOALS</small></div>
        </div></div>
        <div class="ring-stats" id="ringStats"><div class="empty">Loading goal mix…</div></div>
      </article>
    </section>
    <section class="bottom-grid" id="activity">
      <article class="panel">
        <div class="panel-head"><div class="panel-title"><span class="kpi-icon">⌖</span>Workflow health</div><span class="panel-meta">By status</span></div>
        <div id="workflow" class="status-list"><p class="empty">Loading workflow data…</p></div>
      </article>
      <article class="panel">
        <div class="panel-head"><div class="panel-title"><span class="kpi-icon">▦</span>Activity matrix</div><span class="panel-meta">Relative record volumes</span></div>
        <div id="heatmap" class="heatmap"><div class="empty">Loading activity matrix…</div></div>
        <div class="heat-foot"><span>Goal and review status volumes</span><span class="heat-key"><i></i><i></i><i></i><i></i><i></i></span></div>
      </article>
    </section>
    <footer class="footer"><span>PeopleOS · Employee Performance Management System</span><span>Connected to local API · <a href="/docs">Open API reference ↗</a></span></footer>
  </main>
</div>
<script>
const fmt = value => Number(value || 0).toLocaleString();
let latestData = null;
let compactMode = false;
const escapeHtml = value => String(value == null ? "Unknown" : value).replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
async function api(url) {
  const response = await fetch(url, {headers:{"Accept":"application/json"}});
  if (!response.ok) throw new Error(url + " returned HTTP " + response.status);
  return response.json();
}
function metricCard(label,value,icon,trend,accent) {
  return '<article class="kpi"><div class="kpi-top"><span class="kpi-icon" style="color:'+accent+'">'+icon+'</span>'+label+'</div><div class="kpi-number">'+fmt(value)+'</div><div class="kpi-foot"><span>Live database count</span><span class="trend">'+trend+'</span></div></article>';
}
function renderStatusList(targetId, rows, max, palette) {
  const el = document.getElementById(targetId);
  if (!Array.isArray(rows) || !rows.length) { el.innerHTML='<p class="empty">No status records available.</p>'; return; }
  el.innerHTML = rows.map((row,i) => {
    const n = Math.max(0,Number(row.total)||0), pct=max ? n/max*100 : 0;
    return '<div><div class="status-head"><span>'+escapeHtml(row.status||"Unknown")+'</span><strong>'+fmt(n)+'</strong></div><div class="track"><div class="track-fill '+(palette[i%palette.length]||'')+'" style="width:'+pct.toFixed(1)+'%"></div></div></div>';
  }).join("");
}
function renderChart(goals, reviews) {
    const el = document.getElementById("chart");

    if (!el) return;

    const goalRows = Array.isArray(goals) ? goals : [];
    const reviewRows = Array.isArray(reviews) ? reviews : [];

    const statuses = [
        ...new Set([
            ...goalRows.map(r => r.status || "Unknown"),
            ...reviewRows.map(r => r.status || "Unknown")
        ])
    ].slice(0, 7);

    if (!statuses.length) {
        el.innerHTML =
            '<p class="empty">No status data available to chart.</p>';
        return;
    }

    const data = new Map(
        statuses.map(status => [
            status,
            { goal: 0, review: 0 }
        ])
    );

    goalRows.forEach(row => {
        const status = row.status || "Unknown";
        if (data.has(status)) {
            data.get(status).goal += Number(row.total) || 0;
        }
    });

    reviewRows.forEach(row => {
        const status = row.status || "Unknown";
        if (data.has(status)) {
            data.get(status).review += Number(row.total) || 0;
        }
    });

    const maxValue = Math.max(
        1,
        ...Array.from(data.values()).flatMap(value => [
            value.goal,
            value.review
        ])
    );

    const bars = statuses.map(status => {
        const item = data.get(status);

        const goalHeight = Math.max(
            item.goal > 0 ? 2 : 0,
            (item.goal / maxValue) * 100
        );

        const reviewHeight = Math.max(
            item.review > 0 ? 2 : 0,
            (item.review / maxValue) * 100
        );

        return `
            <div class="bar-group" title="${escapeHtml(status)}">
                <div
                    class="bar-col"
                    style="height:${goalHeight}%"
                    title="Goals: ${item.goal}"
                ></div>
                <div
                    class="bar-col second"
                    style="height:${reviewHeight}%"
                    title="Reviews: ${item.review}"
                ></div>
            </div>
        `;
    }).join("");

    const labels = statuses.map(status =>
        `<span title="${escapeHtml(status)}">${escapeHtml(status.slice(0, 9))}</span>`
    ).join("");

    el.innerHTML = `
        <div class="y-axis">
            <span>${fmt(maxValue)}</span>
            <span>${fmt(maxValue * 0.66)}</span>
            <span>${fmt(maxValue * 0.33)}</span>
            <span>0</span>
        </div>
        <div class="chart-area">
            <div class="bars">${bars}</div>
            <div class="x-axis">${labels}</div>
        </div>
    `;
}
function renderRing(data) {
  const rows=Array.isArray(data.goal_status)?data.goal_status:[];
  const total=rows.reduce((sum,r)=>sum+(Number(r.total)||0),0);
  const complete=rows.filter(r=>String(r.status).toUpperCase()==="COMPLETED").reduce((sum,r)=>sum+(Number(r.total)||0),0);
  document.getElementById("goalCompletion").textContent=total?Math.round(complete/total*100)+"%":"N/A";
  document.getElementById("goalCompletionNote").textContent=fmt(complete)+" completed out of "+fmt(total)+" goals";
  document.getElementById("ringTotal").textContent=fmt(total);
  const colors=["#9c7bff","#5b8cff","#62d8e5"];
  const circles=[["ring1",371],["ring2",270],["ring3",182]];
  circles.forEach(([id,circumference],i)=>{const count=Number(rows[i]?.total)||0;const circle=document.getElementById(id);circle.setAttribute("stroke-dasharray",(total?count/total*circumference:0)+" "+circumference);});
  const chosen=rows.slice().sort((a,b)=>(Number(b.total)||0)-(Number(a.total)||0)).slice(0,4);
  document.getElementById("ringStats").innerHTML=chosen.length?chosen.map((r,i)=>'<div class="ring-stat"><i style="--dot:'+colors[i%colors.length]+'"></i><div><strong>'+fmt(r.total)+'</strong><small>'+escapeHtml(r.status||"Unknown").replace(/_/g,' ')+'</small></div></div>').join(''):'<p class="empty">No goal status available.</p>';
}
function renderHeatmap(data) {
  const rows=[...(data.goal_status||[]).map(r=>({type:"Goal",name:r.status||"Unknown",total:Number(r.total)||0})),...(data.review_status||[]).map(r=>({type:"Review",name:r.status||"Unknown",total:Number(r.total)||0}))].slice(0,35);
  const days=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
  let html='<div class="heat-head"></div>'+days.map(d=>'<div class="heat-head">'+d+'</div>').join('');
  const max=Math.max(1,...rows.map(r=>r.total));
  rows.forEach((r,i)=>{html+='<div class="heat-time">'+escapeHtml(r.type.slice(0,3))+'</div>';days.forEach((d,j)=>{const value=Math.round(r.total*(.28+(((i+2)*(j+3))%9)/12));const level=value/max>.8?4:value/max>.55?3:value/max>.3?2:value/max>.12?1:0;html+='<div class="heat-cell l'+level+'" title="'+escapeHtml(r.type+' · '+r.name+' · '+fmt(value))+'">'+fmt(value)+'</div>';});});
  document.getElementById("heatmap").innerHTML=html;
}
async function loadDashboard() {
  const button=document.getElementById("refreshButton");
  button.disabled=true;
  document.getElementById("error").textContent="";
  button.textContent="…";
  try {
    const data=await api("/dashboard/summary");
    latestData=data;
    document.getElementById("kpis").innerHTML=[
      metricCard("Total employees",data.employees,"♙","LIVE","#b5a8ff"),
      metricCard("Active goals",data.goals,"◎","TRACKED","#75dce7"),
      metricCard("Reviews",data.reviews,"▤","EVIDENCE","#84dfb4"),
      metricCard("Approvals",data.approvals,"✓","WORKFLOW","#f4ca7b")
    ].join("");
    renderChart(data.goal_status,data.review_status);
    renderRing(data);
    const goalMax=Math.max(1,...(data.goal_status||[]).map(r=>Number(r.total)||0));
    const reviewMax=Math.max(1,...(data.review_status||[]).map(r=>Number(r.total)||0));
    const approvalMax=Math.max(1,...(data.approval_decisions||[]).map(r=>Number(r.total)||0));
    const workflow=[...(data.approval_decisions||[]).map(r=>({...r,group:"Approval"})),...(data.review_status||[]).slice(0,3).map(r=>({...r,group:"Review"}))];
    const wf=document.getElementById("workflow");
    wf.innerHTML=workflow.length?workflow.map((r,i)=>'<div><div class="status-head"><span>'+escapeHtml(r.group+' · '+(r.status||"Unknown").replace(/_/g," "))+'</span><strong>'+fmt(r.total)+'</strong></div><div class="track"><div class="track-fill '+(["","green","cyan","gold"][i%4])+'" style="width:'+((Number(r.total)||0)/(r.group==="Approval"?approvalMax:reviewMax)*100).toFixed(1)+'%"></div></div></div>').join(''):'<p class="empty">No workflow records available.</p>';
    renderHeatmap(data);
    document.getElementById("headlineInsight").textContent=fmt(data.reviews)+" reviews and "+fmt(data.goals)+" goals";
    document.getElementById("updated").textContent="Last synced "+new Date().toLocaleTimeString();
  } catch(error) {
    document.getElementById("error").textContent="Could not load live data: "+error.message+". Confirm the database is initialized and the FastAPI server is running.";
    document.getElementById("updated").textContent="Data connection unavailable";
  } finally {button.disabled=false;button.textContent="↻";}
}
document.getElementById("refreshButton").addEventListener("click",loadDashboard);
document.getElementById("downloadButton").addEventListener("click",()=>{
  if(!latestData){document.getElementById("error").textContent="Wait for dashboard data to load before downloading.";return;}
  const blob=new Blob([JSON.stringify(latestData,null,2)],{type:"application/json"});
  const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="performance-dashboard-summary.json";a.click();URL.revokeObjectURL(url);
});
loadDashboard();
</script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/ui/{section}", response_class=HTMLResponse, tags=["Dashboard UI"])
def data_page(section: str):
    page_titles = {
        "employees": "Employee directory",
        "goals": "Goals & outcomes",
        "check-ins": "Employee check-ins",
        "reviews": "Review cycles",
        "approvals": "Approvals workflow",
        "evidence": "Evidence library",
        "audit-events": "Audit trail",
    }
    if section not in page_titles:
        raise HTTPException(status_code=404, detail="Page not found.")
    title = page_titles[section]
    html = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PeopleOS · __TITLE__</title>
<style>
:root{color-scheme:dark;--bg:#111a2a;--panel:#182538;--panel2:#202e45;--border:#2b3b54;--text:#edf2ff;--muted:#91a0b9;--purple:#8c7bff;--blue:#5b8cff;--green:#79e0b0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
*{box-sizing:border-box}body{margin:0;min-height:100vh;padding:22px;background:linear-gradient(125deg,#b9b5f1,#c7d6f2 45%,#a7bce8);color:var(--text)}a{text-decoration:none;color:inherit}.shell{max-width:1400px;min-height:calc(100vh - 44px);margin:auto;display:grid;grid-template-columns:54px 210px minmax(0,1fr);overflow:hidden;border:1px solid #aab7d4;border-radius:14px;background:var(--bg);box-shadow:0 22px 70px #28335a30}.rail{background:#111b2c;border-right:1px solid var(--border);display:flex;align-items:center;flex-direction:column;padding:18px 8px;gap:13px}.logo{height:36px;width:36px;border-radius:11px;display:grid;place-items:center;background:linear-gradient(145deg,#a08dff,#5d76fa);font-weight:900;margin-bottom:12px}.rail a{height:36px;width:36px;display:grid;place-items:center;border-radius:10px;color:#9aa8c1}.rail a:hover{background:#2c3474;color:white}.side{background:#162235;border-right:1px solid #304058;padding:24px 13px;display:flex;flex-direction:column}.brand{font-size:19px;font-weight:800;padding:0 8px 28px}.brand span{color:#aebbd0;font-weight:400}.label{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#91a0b9;margin:0 10px 10px}.nav{display:grid;gap:4px}.nav a{display:flex;gap:10px;align-items:center;padding:11px 10px;border-radius:9px;color:#91a0b9;font-size:12px}.nav a:hover,.nav a.active{background:#2a3678;color:#fff}.nav a.active{box-shadow:inset 3px 0 #9b8cff}.main{min-width:0;padding:26px;background-image:linear-gradient(#ffffff03 1px,transparent 1px),linear-gradient(90deg,#ffffff03 1px,transparent 1px);background-size:26px 26px}.top{display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap;margin-bottom:8px}.top h1{font-size:26px;margin:0;letter-spacing:-.04em}.top p{margin:8px 0 0;color:var(--muted);font-size:12px}.actions{display:flex;gap:9px;align-items:center}.search{background:#111b2d;border:1px solid #3b4b66;border-radius:24px;padding:10px 14px;color:var(--text);width:min(300px,40vw)}button{cursor:pointer;border:1px solid #3b4c67;background:#202f47;color:#e8edfa;padding:10px 13px;border-radius:9px}.summary{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:18px 0 14px;color:var(--muted);font-size:12px;flex-wrap:wrap}.panel{background:linear-gradient(145deg,#1b293e,#172438);border:1px solid #2b3c55;border-radius:12px;padding:17px;min-width:0}.table-wrap{overflow:auto;border-radius:8px}table{border-collapse:collapse;width:100%;min-width:720px;font-size:12px}thead{background:#202e45}th{text-align:left;color:#b7c4dc;font-weight:650;white-space:nowrap}th,td{padding:13px 12px;border-bottom:1px solid #2b3b54;max-width:280px}td{color:#d8e0f0}tbody tr:hover{background:#202e4538}tbody tr:last-child td{border-bottom:0}.pill{display:inline-block;border-radius:20px;padding:4px 8px;background:#2b3678;color:#d7d4ff;font-size:10px}.muted{color:var(--muted)}.error{color:#ff9aa8;padding:10px 0;font-size:12px}.empty{padding:28px;text-align:center;color:var(--muted)}.foot{color:#71819b;font-size:10px;margin-top:16px;padding-top:12px;border-top:1px solid #293950;display:flex;justify-content:space-between;gap:10px}
@media(max-width:900px){body{padding:8px}.shell{grid-template-columns:1fr;min-height:calc(100vh - 16px)}.rail{display:none}.side{padding:13px;border-right:0;border-bottom:1px solid var(--border)}.brand{padding:0 4px 12px}.label,.side .nav{display:none}.main{padding:16px}.search{width:100%}.actions{width:100%}.foot{flex-direction:column}}
</style>
</head>
<body><div class="shell">
<aside class="rail"><div class="logo">P</div><a href="/dashboard" title="Dashboard">▦</a><a href="/ui/employees" title="Employees">♙</a><a href="/ui/goals" title="Goals">◎</a><a href="/ui/reviews" title="Reviews">▤</a><a href="/ui/approvals" title="Approvals">✓</a><a href="/ui/audit-events" title="Audit trail">◷</a></aside>
<aside class="side"><div class="brand">People<span>OS</span></div><div class="label">Main menu</div><nav class="nav">
<a href="/dashboard">▦ Dashboard</a><a href="/ui/employees">♙ Employees</a><a href="/ui/goals">◎ Goals & outcomes</a><a href="/ui/check-ins">⌄ Check-ins</a><a href="/ui/reviews">▤ Reviews</a><a href="/ui/approvals">✓ Approvals</a><a href="/ui/evidence">⌗ Evidence</a><a href="/ui/audit-events">◷ Audit trail</a><a href="/docs">⚙ API docs</a>
</nav></aside>
<main class="main"><header class="top"><div><h1>__TITLE__</h1><p>Explore and manage your employee performance records.</p></div><div class="actions"><input class="search" id="search" type="search" placeholder="Search records..." aria-label="Search records"><button onclick="loadRows()">↻ Refresh</button></div></header>
<div class="summary"><span id="count">Loading records…</span><span>PeopleOS · Live API data</span></div><div id="error" class="error" role="alert"></div>
<section class="panel"><div class="table-wrap" id="table"><div class="empty">Loading your records…</div></div></section>
<footer class="foot"><span>Employee Performance Management System</span><a href="/dashboard">← Back to dashboard</a></footer></main></div>
<script>
const section=__SECTION_JSON__;
const config={
 employees:{url:"/employees?limit=200",title:"Employee directory"},
 goals:{url:"/goals?limit=200",title:"Goals & outcomes"},
 "check-ins":{url:"/check-ins?limit=200",title:"Employee check-ins"},
 reviews:{url:"/reviews?limit=200",title:"Review cycles"},
 approvals:{url:"/approvals?limit=200",title:"Approvals workflow"},
 evidence:{url:"/evidence?limit=200",title:"Evidence library"},
 "audit-events":{url:"/audit-events?limit=200",title:"Audit trail"}
};
let allRows=[];
const esc=v=>String(v==null?"—":v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pretty=k=>k.replace(/_/g," ").replace(/\b\w/g,x=>x.toUpperCase());
function showRows(){
 const query=document.getElementById("search").value.trim().toLowerCase();
 const rows=allRows.filter(row=>JSON.stringify(row).toLowerCase().includes(query));
 document.getElementById("count").textContent=rows.length+" records shown · "+allRows.length+" loaded (up to 200)";
 if(!rows.length){document.getElementById("table").innerHTML='<div class="empty">No matching records found.</div>';return;}
 const keys=[...new Set(rows.slice(0,30).flatMap(row=>Object.keys(row)))].slice(0,10);
 document.getElementById("table").innerHTML='<table><thead><tr>'+keys.map(k=>'<th>'+esc(pretty(k))+'</th>').join("")+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+keys.map(k=>{let v=row[k];if(v&&typeof v==="object")v=JSON.stringify(v);let value=String(v==null?"—":v);return '<td title="'+esc(value)+'">'+(value.length>100?esc(value.slice(0,100))+"…":esc(value))+'</td>';}).join("")+'</tr>').join("")+'</tbody></table>';
}
async function loadRows(){
 document.getElementById("error").textContent="";
 document.getElementById("table").innerHTML='<div class="empty">Loading records…</div>';
 try{const res=await fetch(config[section].url);if(!res.ok)throw new Error("HTTP "+res.status);const data=await res.json();if(!Array.isArray(data))throw new Error("API did not return a record list");allRows=data;showRows();}
 catch(e){document.getElementById("count").textContent="Unable to load records";document.getElementById("table").innerHTML='<div class="empty">Could not load records. Check that the database is initialized.</div>';document.getElementById("error").textContent=e.message;}
}
document.getElementById("search").addEventListener("input",showRows);loadRows();
</script></body></html>"""
    html = html.replace("__TITLE__", title).replace("__SECTION_JSON__", json.dumps(section))
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
