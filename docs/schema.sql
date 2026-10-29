
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    department TEXT NOT NULL,
    job_title TEXT NOT NULL,
    hire_date TEXT NOT NULL,
    employment_status TEXT NOT NULL
        CHECK (employment_status IN ('ACTIVE', 'INACTIVE', 'TERMINATED')),
    manager_id TEXT,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

      CHECK (effective_to IS NULL OR effective_to >= effective_from),
    CHECK (manager_id IS NULL OR manager_id <> employee_id),
    FOREIGN KEY (manager_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT
        DEFERRABLE INITIALLY DEFERRED
);


CREATE TABLE IF NOT EXISTS managers (
    manager_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL UNIQUE,
    management_level TEXT NOT NULL
        CHECK (management_level IN ('TEAM_LEAD', 'MANAGER', 'SENIOR_MANAGER', 'DIRECTOR')),
    team_name TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (effective_to IS NULL OR effective_to >= effective_from),

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS review_cycles (
    cycle_id TEXT PRIMARY KEY,
    cycle_name TEXT NOT NULL UNIQUE,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    self_review_deadline TEXT NOT NULL,
    manager_review_deadline TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PLANNED'
        CHECK (status IN ('PLANNED', 'ACTIVE', 'IN_REVIEW', 'CLOSED')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TEXT,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),

    CHECK (end_date >= start_date),
    CHECK (self_review_deadline >= start_date),
    CHECK (manager_review_deadline >= self_review_deadline),
    CHECK (closed_at IS NULL OR status = 'CLOSED')
);
CREATE TABLE IF NOT EXISTS goals (
    goal_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    cycle_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL
        CHECK (category IN ('PERFORMANCE', 'DEVELOPMENT', 'OPERATIONAL', 'STRATEGIC')),
    weight REAL NOT NULL CHECK (weight > 0 AND weight <= 100),
    start_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'NOT_STARTED'
        CHECK (status IN ('NOT_STARTED', 'IN_PROGRESS', 'AT_RISK', 'COMPLETED', 'CANCELLED')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (due_date >= start_date),

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT,
    FOREIGN KEY (cycle_id)
        REFERENCES review_cycles(cycle_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS key_results (
    key_result_id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL,
    title TEXT NOT NULL,
    metric_type TEXT NOT NULL
        CHECK (metric_type IN ('NUMERIC', 'PERCENTAGE', 'BOOLEAN')),
    target_value REAL NOT NULL,
    current_value REAL NOT NULL DEFAULT 0,
    unit TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1 CHECK (weight > 0),
    status TEXT NOT NULL DEFAULT 'IN_PROGRESS'
        CHECK (status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (target_value > 0),
    CHECK (current_value >= 0),

    FOREIGN KEY (goal_id)
        REFERENCES goals(goal_id)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS check_ins (
    check_in_id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    check_in_date TEXT NOT NULL,
    progress_update TEXT NOT NULL,
    reported_progress REAL
        CHECK (reported_progress IS NULL OR
               (reported_progress >= 0 AND reported_progress <= 100)),
    confidence_level TEXT NOT NULL
        CHECK (confidence_level IN ('LOW', 'MEDIUM', 'HIGH')),
    blocker_status TEXT NOT NULL DEFAULT 'NONE'
        CHECK (blocker_status IN ('NONE', 'MINOR', 'MAJOR')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (goal_id)
        REFERENCES goals(goal_id) ON DELETE RESTRICT,
    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS competencies (
    competency_id TEXT PRIMARY KEY,
    competency_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    category TEXT NOT NULL
        CHECK (category IN ('TECHNICAL', 'COMMUNICATION', 'LEADERSHIP', 'TEAMWORK')),
    rating_scale_min INTEGER NOT NULL DEFAULT 1,
    rating_scale_max INTEGER NOT NULL DEFAULT 5,
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (rating_scale_min >= 1),
    CHECK (rating_scale_max > rating_scale_min)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    cycle_id TEXT NOT NULL,
    manager_employee_id TEXT NOT NULL,
    self_rating REAL CHECK (self_rating IS NULL OR (self_rating >= 1 AND self_rating <= 5)),
    manager_rating REAL CHECK (manager_rating IS NULL OR (manager_rating >= 1 AND manager_rating <= 5)),
    calculated_score REAL CHECK (calculated_score IS NULL OR (calculated_score >= 1 AND calculated_score <= 5)),
    status TEXT NOT NULL DEFAULT 'NOT_STARTED'
        CHECK (status IN ('NOT_STARTED', 'IN_PROGRESS', 'SUBMITTED', 'APPROVED', 'INCOMPLETE')),
    submitted_at TEXT,
    approved_at TEXT,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (employee_id, cycle_id),

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT,
    FOREIGN KEY (cycle_id)
        REFERENCES review_cycles(cycle_id) ON DELETE RESTRICT,
    FOREIGN KEY (manager_employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT,

    CHECK (approved_at IS NULL OR submitted_at IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    reviewer_employee_id TEXT NOT NULL,
    subject_employee_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL
        CHECK (feedback_type IN ('SELF', 'MANAGER', 'PEER')),
    comments TEXT NOT NULL,
    rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    submitted_at TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'SUBMITTED', 'WITHDRAWN')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (review_id)
        REFERENCES reviews(review_id) ON DELETE RESTRICT,
    FOREIGN KEY (reviewer_employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT,
    FOREIGN KEY (subject_employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT,

    CHECK (status <> 'SUBMITTED' OR submitted_at IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS development_plans (
    development_plan_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    review_id TEXT NOT NULL,
    competency_id TEXT,
    objective TEXT NOT NULL,
    action_items TEXT NOT NULL,
    target_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN (
            'DRAFT', 'PENDING_APPROVAL', 'APPROVED',
            'IN_PROGRESS', 'COMPLETED', 'REJECTED'
        )),
    approved_by_employee_id TEXT,
    approved_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT,
    FOREIGN KEY (review_id)
        REFERENCES reviews(review_id) ON DELETE RESTRICT,
    FOREIGN KEY (competency_id)
        REFERENCES competencies(competency_id) ON DELETE RESTRICT,
    FOREIGN KEY (approved_by_employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT,

    CHECK (
        (status <> 'APPROVED' AND status <> 'IN_PROGRESS' AND status <> 'COMPLETED')
        OR (approved_by_employee_id IS NOT NULL AND approved_at IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    submitted_by_employee_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL
        CHECK (evidence_type IN ('DOCUMENT', 'LINK', 'METRIC', 'DELIVERABLE')),
    evidence_uri TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'WITHDRAWN')),

    FOREIGN KEY (submitted_by_employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS audit_events (
    audit_event_id TEXT PRIMARY KEY,
    actor_employee_id TEXT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (
        action IN ('CREATE', 'UPDATE', 'SUBMIT', 'APPROVE', 'REJECT', 'CLOSE')
    ),
    old_value_json TEXT,
    new_value_json TEXT,
    reason TEXT,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    correlation_id TEXT,

    FOREIGN KEY (actor_employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS evidence_links (
    evidence_link_id TEXT PRIMARY KEY,
    evidence_id TEXT NOT NULL,
    entity_type TEXT NOT NULL
        CHECK (entity_type IN ('CHECK_IN', 'FEEDBACK', 'DEVELOPMENT_PLAN')),
    entity_id TEXT NOT NULL,
    linked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    linked_by_employee_id TEXT NOT NULL,

    FOREIGN KEY (evidence_id)
        REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    FOREIGN KEY (linked_by_employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS review_competencies (
    review_competency_id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    competency_id TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comments TEXT,
    assessed_by_employee_id TEXT NOT NULL,
    assessed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (review_id, competency_id),

    FOREIGN KEY (review_id)
        REFERENCES reviews(review_id) ON DELETE RESTRICT,
    FOREIGN KEY (competency_id)
        REFERENCES competencies(competency_id) ON DELETE RESTRICT,
    FOREIGN KEY (assessed_by_employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS record_versions (
    version_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    version_number INTEGER NOT NULL CHECK (version_number >= 1),
    record_json TEXT NOT NULL,
    changed_by_employee_id TEXT,
    change_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (entity_type, entity_id, version_number),

    FOREIGN KEY (changed_by_employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('DEVELOPMENT_PLAN', 'REVIEW')),
    entity_id TEXT NOT NULL,
    requested_by_employee_id TEXT NOT NULL,
    approver_employee_id TEXT NOT NULL,
    decision TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (decision IN ('PENDING', 'APPROVED', 'REJECTED')),
    decision_reason TEXT,
    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at TEXT,

    FOREIGN KEY (requested_by_employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT,
    FOREIGN KEY (approver_employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT,

    CHECK (
        (decision = 'PENDING' AND decided_at IS NULL)
        OR
        (decision IN ('APPROVED', 'REJECTED') AND decided_at IS NOT NULL)
    ),
    CHECK (decision <> 'REJECTED' OR decision_reason IS NOT NULL)
);

-- Support traceability integrity checks and entity history lookups at scale.
CREATE INDEX IF NOT EXISTS idx_audit_events_entity
    ON audit_events (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_record_versions_entity_version
    ON record_versions (entity_type, entity_id, version_number);
