# Employee Performance Management System

## Data Dictionary



### 1. Project Overview



Purpose:

Manage employee goals, measurable key results, periodic check-ins,

competency feedback, review cycles, performance reviews, and

development plans with evidence-based progress tracking.



### 2. Data Generation Standards



- Data type: Synthetic data only.

- Random seed: 20261022.

- Employee ID format: EMP-000001.

- Review cycle ID format: CYCLE-2026-H1.

- Goal ID format: GOAL-<employee-id>-001.

- Key result ID format: KR-<goal-id>-01.

- Review ID format: REV-2026-000001.

- IDs must be unique and immutable.

- Foreign keys must reference existing records.

- Derived progress must be calculated from key results.

- Changes to important records must preserve audit history.

- Known anomaly labels must be stored separately from input data.



### 3. Common Validation Standards



- Required fields cannot be NULL or empty.

- Primary keys must be unique.

- Foreign keys must reference valid parent records.

- Dates must follow chronological business rules.

- Enumerated fields must use documented allowed values.

- Progress percentages must remain between 0 and 100

&#x20; unless a separately labelled anomaly is deliberately introduced.

- Derived values must reconcile with their source records.

- Historical changes must be traceable.


### 4. Employee Entity

Purpose:
Store synthetic employee details and organizational relationships.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| employee_id | TEXT | Yes | Primary key; format EMP-000001; immutable |
| first_name | TEXT | Yes | Non-empty synthetic first name |
| last_name | TEXT | Yes | Non-empty synthetic last name |
| email | TEXT | Yes | Unique; valid email format; synthetic domain |
| department | TEXT | Yes | Must match a documented department |
| job_title | TEXT | Yes | Non-empty job title |
| hire_date | DATE | Yes | Must not be later than the generation date |
| employment_status | TEXT | Yes | ACTIVE, ON_LEAVE, or TERMINATED |
| manager_id | TEXT | No | References an existing employee acting as manager |
| effective_from | DATE | Yes | Start of this employee record's validity |
| effective_to | DATE | No | Must be on or after effective_from |
| created_at | DATETIME | Yes | Record creation timestamp |

Rules:
- employee_id is unique and never reused.
- Email addresses are unique.
- A manager must exist before being assigned.
- An employee cannot directly manage themselves.
- Organizational hierarchy must not contain cycles.
- Manager changes must preserve the previous assignment history.
- Employee records referenced by historical reviews must not be
  physically deleted.
- The full dataset must contain 3,000 employees.

### 5. Manager Entity

Purpose:
Store manager-specific information and connect managers to employees.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| manager_id | TEXT | Yes | Primary key; format MGR-000001; immutable |
| employee_id | TEXT | Yes | Foreign key to Employee; unique |
| management_level | TEXT | Yes | TEAM_LEAD, MANAGER, SENIOR_MANAGER, or DIRECTOR |
| team_name | TEXT | Yes | Non-empty team name |
| effective_from | DATE | Yes | Start date of manager assignment |
| effective_to | DATE | No | Must be on or after effective_from |
| created_at | DATETIME | Yes | Record creation timestamp |

Rules:
- Every manager must reference one existing employee.
- An employee can have at most one active manager profile.
- Manager assignments must respect effective dates.
- Manager transfers must preserve previous assignments.
- Review permissions must be checked against the effective
  reporting relationship at the time of the review.
- The full dataset must contain 500 managers.

### 6. ReviewCycle Entity

Purpose:
Define performance review periods, deadlines, and lifecycle states.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| cycle_id | TEXT | Yes | Primary key; format CYCLE-2026-H1; immutable |
| cycle_name | TEXT | Yes | Unique, non-empty cycle name |
| start_date | DATE | Yes | Beginning of review period |
| end_date | DATE | Yes | Must be after start_date |
| self_review_deadline | DATE | Yes | Must be on or after end_date |
| manager_review_deadline | DATE | Yes | Must be on or after self_review_deadline |
| status | TEXT | Yes | PLANNED, ACTIVE, IN_REVIEW, CLOSED |
| created_at | DATETIME | Yes | Creation timestamp |
| closed_at | DATETIME | No | Required when status is CLOSED |
| version | INTEGER | Yes | Starts at 1; increases for every authorized change |

Rules:
- Each review cycle has a unique identifier.
- Review deadlines must follow chronological order.
- Valid lifecycle: PLANNED -> ACTIVE -> IN_REVIEW -> CLOSED.
- Closed cycles cannot accept ordinary edits.
- Any authorized correction to a closed cycle must be recorded
  as a separate auditable event.
- Cycle status changes must preserve previous states.
- Employees may participate in multiple review cycles.
- The baseline dataset will contain CYCLE-2026-H1 and
  CYCLE-2026-H2.

### 7. Goal Entity

Purpose:
Define measurable employee objectives linked to a review cycle.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| goal_id | TEXT | Yes | Primary key; GOAL-<employee-id>-001 |
| employee_id | TEXT | Yes | Foreign key to Employee |
| cycle_id | TEXT | Yes | Foreign key to ReviewCycle |
| title | TEXT | Yes | Non-empty goal title |
| description | TEXT | Yes | Explains the expected outcome |
| category | TEXT | Yes | BUSINESS, TECHNICAL, CUSTOMER, DEVELOPMENT |
| weight | REAL | Yes | Greater than 0 and at most 100 |
| start_date | DATE | Yes | Within the applicable goal period |
| due_date | DATE | Yes | On or after start_date |
| status | TEXT | Yes | DRAFT, ACTIVE, CHANGED, COMPLETED, CANCELLED |
| version | INTEGER | Yes | Starts at 1; increases after authorized changes |
| created_at | DATETIME | Yes | Record creation timestamp |

Rules:
- Every goal belongs to one employee and one review cycle.
- An employee may have multiple goals in a review cycle.
- Goal IDs must be unique and immutable.
- Goal changes must preserve the previous version and an audit event.
- Goal ownership must match the assigned employee.
- Goals must have measurable key results.
- Goal progress must be calculated from its key results.
- A goal's due date must not precede its start date.
- The baseline dataset must contain 10,000 goals.
- Deliberate owner-mismatch cases must be labelled in ground truth.


### 8. KeyResult Entity

Purpose:
Store measurable outcomes used to calculate goal progress.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| key_result_id | TEXT | Yes | Primary key; KR-<goal-id>-01 |
| goal_id | TEXT | Yes | Foreign key to Goal |
| title | TEXT | Yes | Non-empty measurable outcome |
| metric_type | TEXT | Yes | NUMBER, PERCENTAGE, CURRENCY, or BOOLEAN |
| target_value | REAL | Yes | Must be greater than zero |
| current_value | REAL | Yes | Measured value; must follow metric rules |
| unit | TEXT | Yes | Unit consistent with metric_type |
| weight | REAL | Yes | Greater than 0 and at most 100 |
| status | TEXT | Yes | NOT_STARTED, IN_PROGRESS, COMPLETED, BLOCKED |
| updated_at | DATETIME | Yes | Timestamp of latest measurement |

Rules:
- Every key result belongs to exactly one goal.
- A goal may contain multiple key results.
- Key result IDs must be unique and immutable.
- Target and current values must use compatible units.
- Progress must be calculated from current_value and target_value.
- Progress must be capped at 100% in normal records.
- Values exceeding the permitted scale must be handled through
  documented validation and separately labelled anomaly records.
- Goal progress must be calculated from the weighted key results.
- The baseline dataset must contain 20,000 key results.

### 9. CheckIn Entity

Purpose:
Record periodic employee progress updates linked to goals.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| check_in_id | TEXT | Yes | Primary key; unique and immutable |
| goal_id | TEXT | Yes | Foreign key to Goal |
| employee_id | TEXT | Yes | Foreign key to Employee |
| check_in_date | DATE | Yes | Within the applicable reporting period |
| progress_update | TEXT | Yes | Non-empty progress summary |
| reported_progress | REAL | Yes | Between 0 and 100 for normal records |
| confidence_level | TEXT | Yes | LOW, MEDIUM, HIGH |
| blocker_status | TEXT | Yes | NONE, AT_RISK, BLOCKED |
| created_at | DATETIME | Yes | Record creation timestamp |

Rules:
- Every check-in must reference an existing goal and employee.
- The employee must own the goal when the check-in is submitted.
- Evidence must be linked through a separate evidence table.
- Check-in history must be preserved rather than silently overwritten.
- Reported progress is not the authoritative goal progress;
  authoritative progress is calculated from key results.
- Invalid or conflicting check-ins must be flagged for investigation.
- The baseline dataset must contain 20,000 check-ins.


### 10. Competency Entity

Purpose:
Define skills and behavioral criteria used in performance reviews.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| competency_id | TEXT | Yes | Primary key; unique and immutable |
| competency_name | TEXT | Yes | Required; unique competency name |
| description | TEXT | Yes | Non-empty competency description |
| category | TEXT | Yes | TECHNICAL, COMMUNICATION, LEADERSHIP, TEAMWORK |
| rating_scale_min | INTEGER | Yes | Must be 1 |
| rating_scale_max | INTEGER | Yes | Must be 5 |
| is_active | BOOLEAN | Yes | Indicates whether competency is currently active |
| created_at | DATETIME | Yes | Record creation timestamp |

Rules:
- Each competency has a unique identifier.
- Competency ratings must remain between 1 and 5.
- A competency may be used in many reviews.
- Reviews may evaluate multiple competencies.
- The many-to-many relationship between Review and Competency
  must be represented through a review_competencies bridge table.
- Inactive competencies must remain available for historical reviews.
- Competency definitions must not be silently overwritten.

### 11. Feedback Entity

Purpose:
Store self, manager, and peer feedback with traceable supporting evidence.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| feedback_id | TEXT | Yes | Primary key; unique and immutable |
| review_id | TEXT | Yes | Foreign key to Review |
| reviewer_employee_id | TEXT | Yes | Foreign key to Employee |
| subject_employee_id | TEXT | Yes | Foreign key to Employee |
| feedback_type | TEXT | Yes | SELF, MANAGER, PEER |
| comments | TEXT | Yes | Non-empty feedback comments |
| rating | INTEGER | No | Integer between 1 and 5 |
| submitted_at | DATETIME | Yes | Submission timestamp |
| status | TEXT | Yes | DRAFT, SUBMITTED, WITHDRAWN |

Rules:
- Each feedback record belongs to one review.
- Reviewer and subject must reference existing employees.
- SELF feedback requires reviewer and subject to be the same employee.
- MANAGER feedback requires a valid manager-subordinate relationship.
- PEER feedback requires an eligible peer relationship.
- Reviewers must have permission to submit feedback.
- Submitted feedback must retain its history.
- Evidence must be linked through a separate evidence table.
- Feedback without required evidence must be flagged.
- Conflicting feedback must be retained and flagged, not silently deleted.
- Ground-truth labels must identify deliberately injected anomalies.

### 12. Review Entity

Purpose:
Store formal performance reviews, calculated outcomes, and approval status.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| review_id | TEXT | Yes | Primary key; format REV-2026-000001 |
| employee_id | TEXT | Yes | Foreign key to Employee |
| cycle_id | TEXT | Yes | Foreign key to ReviewCycle |
| manager_employee_id | TEXT | Yes | Foreign key to Employee |
| self_rating | REAL | No | Between 1 and 5 |
| manager_rating | REAL | No | Between 1 and 5 |
| calculated_score | REAL | No | Derived from documented scoring rules |
| status | TEXT | Yes | NOT_STARTED, IN_PROGRESS, SUBMITTED, APPROVED, INCOMPLETE |
| submitted_at | DATETIME | No | Required when submitted |
| approved_at | DATETIME | No | Required when approved |
| version | INTEGER | Yes | Starts at 1; increases after authorized changes |
| created_at | DATETIME | Yes | Record creation timestamp |

Rules:
- Each review belongs to one employee and one review cycle.
- Each review must have an authorized reviewing manager.
- A review cycle may contain many reviews.
- Review IDs must be unique and immutable.
- Ratings must follow the documented rating scale.
- Scores must be calculated from available validated inputs.
- Incomplete reviews must not be treated as completed reviews.
- Approval requires all mandatory review inputs.
- Review permissions must be enforced.
- Changes must create version history and audit events.
- Closed cycles must reject unauthorized edits.
- Competency ratings must be linked through a review_competencies bridge table.
- Completion metrics must derive from actual review states.

### 13. DevelopmentPlan Entity

Purpose:
Track employee development goals, activities, and approval decisions.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| development_plan_id | TEXT | Yes | Primary key; unique and immutable |
| employee_id | TEXT | Yes | Foreign key to Employee |
| review_id | TEXT | Yes | Foreign key to Review |
| competency_id | TEXT | No | Foreign key to Competency |
| objective | TEXT | Yes | Non-empty development objective |
| action_items | TEXT | Yes | Documented development activities |
| target_date | DATE | Yes | Must follow plan creation date |
| status | TEXT | Yes | DRAFT, PENDING_APPROVAL, APPROVED, IN_PROGRESS, COMPLETED, REJECTED |
| approved_by_employee_id | TEXT | No | Foreign key to Employee |
| approved_at | DATETIME | No | Required when approved |
| created_at | DATETIME | Yes | Record creation timestamp |

Rules:
- Every development plan belongs to one employee and one review.
- A review may have multiple development plans.
- A plan may optionally reference a competency.
- Approval must be performed by an authorized manager or HR partner.
- Approval decisions must record the approver and timestamp.
- Rejected plans must retain their rejection history.
- Plan changes must be versioned and auditable.
- Completed plans must have documented completion evidence.

### 14. Evidence Entity

Purpose:
Store references to supporting evidence without embedding sensitive files
directly into employee performance records.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| evidence_id | TEXT | Yes | Primary key; unique and immutable |
| submitted_by_employee_id | TEXT | Yes | Foreign key to Employee |
| evidence_type | TEXT | Yes | DOCUMENT, LINK, METRIC, DELIVERABLE |
| evidence_uri | TEXT | Yes | Valid synthetic reference or permitted URL |
| description | TEXT | Yes | Non-empty evidence description |
| created_at | DATETIME | Yes | Evidence submission timestamp |
| status | TEXT | Yes | ACTIVE, WITHDRAWN |

Rules:
- Evidence must reference an existing employee.
- Evidence references must not contain credentials or confidential data.
- Evidence must be linked to relevant records using bridge tables.
- Withdrawn evidence must remain traceable in historical records.
- Evidence must be validated before it supports a review decision.

### 15. AuditEvent Entity

Purpose:
Preserve an append-only history of important business actions and changes.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| audit_event_id | TEXT | Yes | Primary key; unique and immutable |
| actor_employee_id | TEXT | No | Foreign key to Employee; null for system actions |
| entity_type | TEXT | Yes | Type of affected business entity |
| entity_id | TEXT | Yes | ID of the affected record |
| action | TEXT | Yes | CREATE, UPDATE, SUBMIT, APPROVE, REJECT, CLOSE |
| old_value_json | TEXT | No | Previous state as JSON |
| new_value_json | TEXT | No | New state as JSON |
| reason | TEXT | No | Required for authorized corrections |
| occurred_at | DATETIME | Yes | Event timestamp |
| correlation_id | TEXT | Yes | Groups related events |

Rules:
- Audit events must be append-only.
- Important state changes must create audit events.
- Updates must preserve the previous state.
- Authorized corrections to closed cycles require a reason,
  a versioned correction record, and an audit event.
- Unauthorized edits must be rejected and recorded where possible.
- Audit history must not be silently overwritten or deleted.
- Audit records must be validated against the corresponding entity
  and change history.

### 16. EvidenceLink Entity

Purpose:
Connect evidence records to the business records they support.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| evidence_link_id | TEXT | Yes | Primary key; unique and immutable |
| evidence_id | TEXT | Yes | Foreign key to Evidence |
| entity_type | TEXT | Yes | CHECK_IN, FEEDBACK, DEVELOPMENT_PLAN |
| entity_id | TEXT | Yes | ID of the supported record |
| linked_at | DATETIME | Yes | Timestamp when evidence was linked |
| linked_by_employee_id | TEXT | Yes | Foreign key to Employee |

Rules:
- Each evidence link must reference an existing Evidence record.
- Each evidence link must reference an existing employee.
- Evidence may support multiple business records.
- A business record may have multiple evidence links.
- Evidence links must be validated against the referenced record.
- Untraceable feedback must be flagged as an anomaly.
- Evidence links must preserve their history.

### 17. ReviewCompetency Entity

Purpose:
Connect performance reviews to the competencies being assessed.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| review_competency_id | TEXT | Yes | Primary key; unique and immutable |
| review_id | TEXT | Yes | Foreign key to Review |
| competency_id | TEXT | Yes | Foreign key to Competency |
| rating | INTEGER | Yes | Integer between 1 and 5 |
| comments | TEXT | No | Supporting assessment comments |
| assessed_by_employee_id | TEXT | Yes | Foreign key to Employee |
| assessed_at | DATETIME | Yes | Assessment timestamp |

Rules:
- Every bridge record must reference an existing review and competency.
- The combination of review_id and competency_id must be unique.
- Ratings must remain between 1 and 5.
- The assessor must have permission to assess the competency.
- Historical assessments must be preserved.
- Review scores must derive from documented scoring rules.

### 18. RecordVersion Entity

Purpose:
Preserve previous versions of important business records.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| version_id | TEXT | Yes | Primary key; unique and immutable |
| entity_type | TEXT | Yes | Type of versioned business entity |
| entity_id | TEXT | Yes | ID of the versioned record |
| version_number | INTEGER | Yes | Positive integer, increasing sequentially |
| record_json | TEXT | Yes | Snapshot of the record at this version |
| changed_by_employee_id | TEXT | No | Foreign key to Employee; null for system changes |
| change_reason | TEXT | No | Required for authorized corrections |
| created_at | DATETIME | Yes | Version creation timestamp |

Rules:
- Each version must have a unique entity, ID, and version number combination.
- Version numbers must increase sequentially for each entity.
- Previous versions must never be overwritten.
- Important updates must create a version snapshot and audit event.
- Closed-cycle corrections must include a reason and authorization.
- Version history must be consistent with the audit event history.

### 19. Approval Entity

Purpose:
Record workflow approval decisions with traceability.

| Field | Type | Required | Constraints and Validation |
|---|---|---|---|
| approval_id | TEXT | Yes | Primary key; unique and immutable |
| entity_type | TEXT | Yes | DEVELOPMENT_PLAN or REVIEW |
| entity_id | TEXT | Yes | ID of the record requiring approval |
| requested_by_employee_id | TEXT | Yes | Foreign key to Employee |
| approver_employee_id | TEXT | Yes | Foreign key to Employee |
| decision | TEXT | Yes | PENDING, APPROVED, REJECTED |
| decision_reason | TEXT | No | Required for rejection |
| requested_at | DATETIME | Yes | Request timestamp |
| decided_at | DATETIME | No | Required after approval or rejection |

Rules:
- Every approval must reference valid employees.
- The approver must have permission for the requested action.
- A requester cannot approve their own request where separation of duties applies.
- Decisions must be preserved as historical records.
- Rejected requests must include a reason.
- Approval decisions must create corresponding audit events.
- Pending approvals must not be counted as completed workflows.

### 20. Entity Relationships

| Parent Entity | Child Entity | Relationship | Rule |
|---|---|---|---|
| Employee | Manager | One-to-zero-or-one | A manager record belongs to one employee |
| Employee | Goal | One-to-many | An employee can own multiple goals |
| ReviewCycle | Goal | One-to-many | A cycle can contain multiple goals |
| Goal | KeyResult | One-to-many | A goal contains multiple key results |
| Goal | CheckIn | One-to-many | A goal can have multiple check-ins |
| Employee | CheckIn | One-to-many | An employee can submit multiple check-ins |
| Employee | Review | One-to-many | An employee can have multiple reviews over time |
| ReviewCycle | Review | One-to-many | A cycle can contain multiple reviews |
| Review | Feedback | One-to-many | A review can contain multiple feedback records |
| Employee | Feedback | One-to-many | An employee can give or receive feedback |
| Review | Competency | Many-to-many | Implemented through ReviewCompetency |
| Employee | DevelopmentPlan | One-to-many | An employee can have multiple development plans |
| Evidence | Business Records | One-to-many links | Implemented through EvidenceLink |
| Business Records | AuditEvent | One-to-many | Changes must be traceable |
| Business Records | RecordVersion | One-to-many | Historical versions must be preserved |
| Employee | Approval | One-to-many | Employees can request or decide approvals |

Relationship Validation Rules:
- Every foreign key must reference an existing record.
- Required relationships cannot be NULL.
- Optional relationships may be NULL only when permitted by the schema.
- Many-to-many relationships must use bridge tables.
- Deleting a referenced record must not silently destroy audit history.
- Invalid relationships must be reported during validation.