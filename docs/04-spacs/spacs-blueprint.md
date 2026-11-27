# SPACS Module — Module Blueprint

**Module:** SPACS — Awards & Scholarships (`spacs`)  
**Specification Reference:** `01_SPACS_Problem_Statement_v1.0_SYNCHRONIZED.docx`, `02_SPACS_Requirements_Registry_CFR_AFR_v1.1_FINAL.docx`, `03_SPACS_Use_Case_Specifications_v1.1_FINAL.docx`, `04_SPACS_Business_Rule_Specifications_v1.1_FINAL.docx`, `05_SPACS_Workflow_Specifications_v1.1_FINAL.docx`  
**Status:** **APPROVED by Student 2 (Peer Reviewer / Module Pair Sign-Off)** — 23 November 2026

---

## Step 3.1 (a) — Traceability Table

| Specification ID | Description | Architectural Layer | Enforcement Point | Notes |
|---|---|---|---|---|
| **BR-SPACS-001** | Minimum CPI qualification requirement | `domain/` | `domain/eligibility.py::evaluate_cpi_threshold()` | Compares applicant CPI against scheme threshold |
| **BR-SPACS-002** | Parental income ceiling verification | `domain/` | `domain/eligibility.py::evaluate_income_ceiling()` | Verifies annual parental income ceiling |
| **BR-SPACS-003** | Academic standing / active student check | `domain/` | `domain/eligibility.py::evaluate_student_standing()` | Ensures student is active and not on academic probation |
| **BR-SPACS-004** | Disciplinary clearance check | `domain/` | `domain/eligibility.py::evaluate_disciplinary_clearance()` | Ensures applicant has no active major disciplinary penalties |
| **BR-SPACS-005** | Dual-benefit / scholarship exclusivity rule | `domain/` | `domain/rules.py::evaluate_dual_benefit_restriction()` | Prevents receiving multiple major financial aid packages |
| **BR-SPACS-006** | Mandatory supporting documents check | `domain/` | `domain/rules.py::evaluate_document_completeness()` | Enforces required document categories before submission |
| **BR-SPACS-007** | Application submission deadline window | `domain/` | `domain/rules.py::is_within_application_window()` | Enforces catalogue window start and end dates |
| **BR-SPACS-008** | Verifier separation of duty | `domain/` | `domain/rules.py::validate_verifier_eligibility()` | Applicant cannot verify their own application |
| **BR-SPACS-009** | Verification outcome actions and constraints | `domain/` | `domain/state_machine.py::transition_application()` | Transitions: verified, correction_required, concern_raised |
| **BR-SPACS-010** | Student correction modification window | `domain/` | `domain/rules.py::is_within_correction_window()` | Enforces grace period for applicant corrections |
| **BR-SPACS-011** | Committee decision authority and quorum | `domain/` | `domain/rules.py::validate_committee_decision_authority()` | Only Convener / Committee records final sanctions |
| **BR-SPACS-012** | Sanction order reference requirement | `domain/` | `domain/rules.py::validate_sanction_order_ref()` | Sanction reference mandatory upon approval |
| **BR-SPACS-013** | Institutional approval reference for awards | `domain/` | `domain/rules.py::validate_institutional_approval()` | Institutional approval ref required before award publication |
| **BR-SPACS-014** | Award candidate pool eligibility filtering | `domain/` | `domain/rules.py::filter_award_candidates()` | Filters graduating cohort meeting medal/award criteria |
| **BR-SPACS-015** | Merit ranking and score tie-break criteria | `domain/` | `domain/rules.py::rank_award_candidates()` | Tie-breaking by CPI, coursework credits, and committee score |
| **BR-SPACS-016** | Award winner selection cardinality | `domain/` | `domain/rules.py::validate_winner_cardinality()` | Exactly one winner per medal scheme unless joint award sanctioned |
| **BR-SPACS-017** | Award cycle state progression sequence | `domain/` | `domain/state_machine.py::transition_award_cycle()` | Enforces CW-SPACS-02 progression |
| **BR-SPACS-018** | Catalogue version immutability upon publication | `domain/` | `domain/state_machine.py::transition_catalogue_version()` | Published version criteria cannot be edited; must draft new version |
| **BR-SPACS-019** | Scholarship renewal eligibility continuity | `domain/` | `domain/eligibility.py::evaluate_renewal_eligibility()` | Maintains minimum CPI and active standing across academic years |
| **BR-SPACS-020** | Renewal window timing constraints | `domain/` | `domain/rules.py::is_within_renewal_window()` | Enforces renewal submission window dates |
| **BR-SPACS-021** | Review SLA threshold and escalation trigger | `domain/` | `domain/rules.py::is_sla_breached()` | Flags applications exceeding SLA threshold days |
| **BR-SPACS-022** | Audit trail append-only immutability | `models/` | `models/audit.py::AuditEvent` | Write-only events recorded for every state change |
| **BR-SPACS-023** | Notification dispatch rate limiting and backoff | `domain/` | `domain/rules.py::calculate_notification_backoff()` | Rate limit: 20/day, exponential backoff with max 5 retries |
| **UC-SPACS-001** | Apply for Scholarship | `services/` | `services/applications.py::create_application()` | Submits student application with validated criteria |
| **UC-SPACS-002** | Verify Scholarship Application | `services/` | `services/verification.py::record_verification_finding()` | Verification finding by Assistant (absorbs retired UC-SPACS-009) |
| **UC-SPACS-003** | Modify / Correct Pending Application | `services/` | `services/applications.py::resubmit_application()` | Student updates correction fields and resubmits |
| **UC-SPACS-004** | Withdraw Application | `services/` | `services/applications.py::withdraw_application()` | Student withdraws application (absorbs retired UC-SPACS-005) |
| **UC-SPACS-006** | Make Scholarship Decision | `services/` | `services/decisions.py::record_decision()` | Convener records approval/rejection (absorbs retired UC-SPACS-013) |
| **UC-SPACS-007** | Download / Print Application | `api/` | `api/views.py::ApplicationSummaryDownloadView` | Generates structured JSON/PDF application export |
| **UC-SPACS-008** | Check Application Status | `selectors/` | `selectors/applications.py::get_application_detail()` | Student tracks live status and history |
| **UC-SPACS-010** | Create Catalogue Entry | `services/` | `services/catalogue.py::create_catalogue_entry()` | Creates new scholarship/award entry |
| **UC-SPACS-011** | Modify Catalogue Entry / Version | `services/` | `services/catalogue.py::create_draft_version()` | Creates or edits draft criteria version |
| **UC-SPACS-012** | Retire / Deactivate Catalogue Entry | `services/` | `services/catalogue.py::retire_entry()` | Deactivates entry and archives criteria |
| **UC-SPACS-014** | Browse Scholarship & Award Catalogue | `selectors/` | `selectors/catalogue.py::list_published_schemes()` | Public/student listing of available opportunities |
| **UC-SPACS-015** | Apply for Scholarship Renewal | `services/` | `services/renewals.py::apply_renewal()` | Submits renewal application linked to prior award |
| **UC-SPACS-017** | Prepare Award Candidate Pool | `services/` | `services/awards.py::prepare_candidate_pool()` | Generates graduating student cohort pool |
| **UC-SPACS-018** | Evaluate and Shortlist Candidates | `services/` | `services/awards.py::evaluate_candidate()` | Committee records scores and shortlist flag |
| **UC-SPACS-019** | Record Final Award Outcome | `services/` | `services/awards.py::record_outcome()` | Designates final winner and runner-up |
| **UC-SPACS-020** | Publish Award Results | `services/` | `services/awards.py::publish_award_cycle()` | Publishes award with institutional sanction |
| **UC-SPACS-021** | View SPACS Audit Trail | `selectors/` | `selectors/audit.py::list_audit_events()` | Administrative audit log viewer |
| **UC-SPACS-023** | Publish Catalogue Version | `services/` | `services/catalogue.py::publish_version()` | Activates version and closes prior versions |
| **UC-SPACS-024** | Issue SLA Reminder / Escalation | `services/` | `services/tasks.py::check_review_slas()` | Sweeps overdue applications and enqueues alerts |
| **UC-SPACS-025** | Send Scholarship Renewal Reminder | `services/` | `services/tasks.py::send_renewal_reminders()` | Sweeps expiring awards approaching renewal window |
| **UC-SPACS-026** | Reassign Pending Tasks | `services/` | `services/tasks.py::reassign_pending_tasks()` | Administrative reassignment of pending verifications |
| **BW-SPACS-01** | Student Application Submission Workflow | `services/` | `services/applications.py` | Full multi-step submission and validation |
| **BW-SPACS-02** | Application Verification Workflow | `services/` | `services/verification.py` | Assistant verification lifecycle |
| **BW-SPACS-03** | Defect Correction and Resubmission | `services/` | `services/applications.py` | Student correction cycle |
| **BW-SPACS-04** | Convener Sanction Workflow | `services/` | `services/decisions.py` | Sanction decision and notification |
| **BW-SPACS-05** | Scholarship Renewal Workflow | `services/` | `services/renewals.py` | Multi-year renewal verification |
| **BW-SPACS-06** | Award Candidate Pool Preparation | `services/` | `services/awards.py` | Convocation cohort nomination |
| **BW-SPACS-07** | Committee Award Evaluation | `services/` | `services/awards.py` | Committee scoring and ranking |
| **BW-SPACS-08** | Institutional Sanction & Publication | `services/` | `services/awards.py` | Senate approval and public announcement |
| **BW-SPACS-09** | Catalogue Lifecycle Management | `services/` | `services/catalogue.py` | Draft -> Published -> Archived |
| **BW-SPACS-10** | SLA Escalation Sweep | `services/` | `services/tasks.py` | Periodic background escalation |
| **BW-SPACS-11** | Renewal Notification Sweep | `services/` | `services/tasks.py` | Periodic background renewal prompt |
| **CW-SPACS-01** | Scholarship Application State Lifecycle | `domain/` | `domain/state_machine.py` | Complete application finite state machine |
| **CW-SPACS-02** | Award Cycle State Lifecycle | `domain/` | `domain/state_machine.py` | Complete award cycle finite state machine |
| **CW-SPACS-03** | Catalogue Version State Lifecycle | `domain/` | `domain/state_machine.py` | Complete catalogue version state machine |

---

## Step 3.2 (b) — Domain Model

### Entities, Invariants, and Database Constraints

1. **`CatalogueEntry` (`models/catalogue.py`)**
   - Identity: `code` (slug, unique).
   - Invariants: `title`, `kind` (`scholarship` or `award`), `status` (`active` or `retired`).
   - Constraints: `UniqueConstraint(fields=["code"], name="unique_catalogue_entry_code")`.

2. **`CatalogueVersion` (`models/catalogue.py`)**
   - Identity: `(entry_id, version_number)` unique.
   - Invariants: `valid_from <= valid_to`; `application_window_start <= application_window_end`; `renewal_window_start <= renewal_window_end`; `min_cpi >= 0.0`; `max_income_ceiling >= 0`.
   - Constraints:
     - `UniqueConstraint(fields=["entry", "version_number"], name="unique_entry_version_number")`.
     - `CheckConstraint(check=Q(min_cpi__gte=0.0) & Q(min_cpi__lte=10.0), name="check_catalogue_cpi_range")`.

3. **`Application` (`models/applications.py`)**
   - Identity: `id` (autoincrement).
   - Invariants: `student_user_id` is an integer; at most one active application per student per catalogue version in non-terminal states; `status` follows CW-SPACS-01.
   - Constraints:
     - Partial Unique Index: `UniqueConstraint(fields=["catalogue_version", "student_user_id"], condition=~Q(status__in=["withdrawn", "rejected"]), name="unique_active_application_per_student_scheme")`.

4. **`ApplicationDocument` (`models/documents.py`)**
   - Identity: `id`.
   - Invariants: Associated with an `Application`; `document_type` in known categories; `status` (`pending`, `valid`, `invalid`).

5. **`VerificationFinding` (`models/verification.py`)**
   - Identity: `id`.
   - Invariants: Linked to `Application`; `reviewer_id` cannot equal `student_user_id`; `action` in `{"verified", "correction_required", "concern_raised"}`.

6. **`ScholarshipDecision` (`models/decisions.py`)**
   - Identity: `id`.
   - Invariants: Linked to `Application`; `decision` in `{"approved", "rejected", "returned_for_correction"}`; `sanction_order_ref` mandatory on approval.

7. **`AwardCycle` (`models/awards.py`)**
   - Identity: `id`.
   - Invariants: Unique cycle for `(catalogue_version, convocation_year)`; `status` follows CW-SPACS-02.
   - Constraints:
     - `UniqueConstraint(fields=["catalogue_version", "convocation_year"], name="unique_cycle_per_award_year")`.

8. **`AwardCandidate` (`models/awards.py`)**
   - Identity: `id`.
   - Invariants: Linked to `AwardCycle`; `user_id` unique within cycle; `cpi >= 0.0`.
   - Constraints:
     - `UniqueConstraint(fields=["award_cycle", "user_id"], name="unique_candidate_per_cycle")`.

9. **`NotificationOutbox` (`models/notifications.py`)**
   - Identity: `id`.
   - Invariants: `dedupe_key` unique to guarantee idempotency; status in `{"pending", "sent", "failed", "suppressed"}`; `attempts <= max_attempts`.
   - Constraints:
     - `UniqueConstraint(fields=["dedupe_key"], name="unique_notification_dedupe_key")`.

10. **`AuditEvent` (`models/audit.py`)**
    - Identity: `id`.
    - Invariants: Append-only ledger; records `actor_user_id`, `target_type`, `target_id`, `event_type`, `payload`, `timestamp`.

---

## Step 3.3 (c) — State Machines

### 1. CW-SPACS-01: Scholarship Application Lifecycle

```
[draft]
   │ (submit by student)
   ▼
[submitted] ◄─────────────────────────────────────────────┐
   │ (assign/begin by assistant)                          │ (resubmit by student)
   ▼                                                      │
[under_verification] ──► (request correction) ──► [correction_required]
   │               │
   │ (mark verified) (raise concern)
   ▼               ▼
[verified]      [verification_concern]
   │               │
   └───────┬───────┘
           │ (convener decision)
           ├──► [approved]  (terminal)
           └──► [rejected]  (terminal)

[withdrawn] (terminal: accessible from [draft], [submitted], [under_verification], [correction_required])
```

#### Transition Table
| Source State | Event | Trigger Actor | Destination State | Invariant Guards |
|---|---|---|---|---|
| `draft` | `submit` | Student | `submitted` | Mandatory documents uploaded, within window |
| `submitted` | `begin_verification` | Assistant / System | `under_verification` | Assigned verifier != student |
| `under_verification` | `verify` | Assistant | `verified` | All documents reviewed |
| `under_verification` | `request_correction`| Assistant | `correction_required` | Defect reason specified |
| `under_verification` | `raise_concern` | Assistant | `verification_concern` | Detailed concern noted |
| `correction_required`| `resubmit` | Student | `submitted` | Correction fields updated |
| `verified` | `approve` | Convener | `approved` | Sanction order ref provided |
| `verified` | `reject` | Convener | `rejected` | Rationale provided |
| `verification_concern`| `approve` | Convener | `approved` | Sanction order ref provided |
| `verification_concern`| `reject` | Convener | `rejected` | Rationale provided |
| `* (non-terminal)` | `withdraw` | Student | `withdrawn` | Prior state not approved/rejected |

### 2. CW-SPACS-02: Award Cycle Lifecycle

```
[cycle_open]
   │ (prepare pool)
   ▼
[candidate_pool_prepared]
   │ (committee scoring)
   ▼
[under_committee_evaluation]
   │ (record outcomes)
   ▼
[committee_result_recorded]
   │ (submit for institutional approval)
   ▼
[awaiting_institutional_approval]
   │ (record Senate sanction ref)
   ▼
[ready_for_publication]
   │ (publish results)
   ▼
[published] (terminal)
```

### 3. CW-SPACS-03: Catalogue Version Lifecycle

```
[draft] ──(publish)──► [published] ──(supersede/expire)──► [archived]
```

---

## Step 3.4 (d) — Permission List

### Module Registration and RBAC Model (`modules/spacs/registry.py`)

- **Module Code:** `spacs`
- **Module Name:** `Awards & Scholarships`
- **Prefix:** `spacs`

#### Permissions
1. `spacs.catalogue.view` — Browse active and archived schemes
2. `spacs.catalogue.manage` — Author, update criteria, and publish versions
3. `spacs.application.view` — View own scholarship applications
4. `spacs.application.apply` — Submit initial or renewal scholarship applications
5. `spacs.application.withdraw` — Withdraw pending scholarship application
6. `spacs.verification.view` — Access verification queue and applicants
7. `spacs.verification.review` — Record verification findings, request corrections
8. `spacs.decision.view` — Access decision queue and applicant profiles
9. `spacs.decision.make` — Record convener approval/rejection sanction orders
10. `spacs.award_cycle.view` — Browse open and published award cycles
11. `spacs.award_cycle.manage` — Prepare candidate pools, record committee outcomes, publish
12. `spacs.audit.view` — View compliance audit log events

#### System Permissions (Automated / Scheduled)
- `spacs.notifications.deliver`
- `spacs.tasks.sla_sweep`
- `spacs.tasks.renewal_sweep`

#### Role Grants (Keyed by ERP Designations)
| Role / Designation | Granted Permissions | Purpose |
|---|---|---|
| `student` | `catalogue.view`, `application.view`, `application.apply`, `application.withdraw`, `award_cycle.view` | Student applicant |
| `SPACS Assistant` | `catalogue.view`, `application.view`, `verification.view`, `verification.review`, `award_cycle.view` | Office verification staff |
| `SPACS Convener` | `catalogue.view`, `catalogue.manage`, `application.view`, `decision.view`, `decision.make`, `award_cycle.view`, `award_cycle.manage`, `audit.view` | Executive scholarship convener |
| `SPACS Committee Member` | `catalogue.view`, `decision.view`, `award_cycle.view` | Evaluation committee member |
| `Dean Academic` | `catalogue.view`, `decision.view`, `award_cycle.view`, `audit.view` | Institutional oversight |
| `Director` | `catalogue.view`, `decision.view`, `award_cycle.view`, `audit.view` | Final institutional authority |

---

## Step 3.5 (e) — Endpoint List, Routes, and Sidebar

### REST Endpoints (`/api/v1/spacs/`)

| Method | Path | Required Permission | Throttle Scope | Description |
|---|---|---|---|---|
| `GET` | `catalogue/` | `catalogue.view` | `spacs:read` | List published catalogue entries |
| `GET` | `catalogue/<pk>/` | `catalogue.view` | `spacs:read` | Retrieve catalogue entry detail |
| `POST`| `catalogue/` | `catalogue.manage` | `spacs:write` | Create draft catalogue version |
| `POST`| `catalogue/<pk>/publish/` | `catalogue.manage` | `spacs:write` | Publish catalogue version |
| `GET` | `applications/` | `application.view` | `spacs:read` | List applications (scoped to role) |
| `POST`| `applications/` | `application.apply` | `spacs:apply` | Submit new scholarship application |
| `GET` | `applications/<pk>/` | `application.view` | `spacs:read` | Application detail & document list |
| `POST`| `applications/<pk>/withdraw/`| `application.withdraw`| `spacs:write` | Withdraw application |
| `POST`| `applications/<pk>/resubmit/`| `application.apply` | `spacs:apply` | Resubmit corrected application |
| `POST`| `applications/renew/` | `application.apply` | `spacs:apply` | Submit renewal application |
| `GET` | `applications/<pk>/download/`| `application.view` | `spacs:read` | Download summary export |
| `GET` | `verification/queue/` | `verification.view` | `spacs:read` | List pending verification queue |
| `POST`| `verification/<pk>/finding/` | `verification.review` | `spacs:write` | Record verification finding |
| `GET` | `decisions/queue/` | `decision.view` | `spacs:read` | List pending decision queue |
| `POST`| `decisions/<pk>/record/` | `decision.make` | `spacs:write` | Record convener decision |
| `GET` | `awards/` | `award_cycle.view` | `spacs:read` | List award cycles |
| `POST`| `awards/` | `award_cycle.manage` | `spacs:write` | Open new award cycle |
| `POST`| `awards/<pk>/pool/` | `award_cycle.manage` | `spacs:write` | Prepare candidate pool |
| `POST`| `awards/<pk>/evaluate/` | `award_cycle.manage` | `spacs:write` | Record committee evaluations |
| `POST`| `awards/<pk>/publish/` | `award_cycle.manage` | `spacs:write` | Sanction and publish award cycle |
| `GET` | `audit/` | `audit.view` | `spacs:read` | List audit log events |

### Frontend Routes (`client/src/modules/spacs/routes.tsx`)

| Path | Component | Guard Permission | Description |
|---|---|---|---|
| `/spacs/catalogue` | `CataloguePage` | `catalogue.view` | Public / student scheme browsing |
| `/spacs/catalogue/admin` | `CatalogueAdminPage`| `catalogue.manage` | Scheme administration & versioning |
| `/spacs/my-applications` | `MyApplicationsPage`| `application.apply` | Student application management |
| `/spacs/verification` | `VerificationQueuePage`| `verification.review` | Verification queue for staff |
| `/spacs/decisions` | `DecisionQueuePage` | `decision.make` | Convener sanction queue |
| `/spacs/awards` | `AwardsPage` | `award_cycle.view` | Convocation awards and medals |
| `/spacs/audit` | `AuditPage` | `audit.view` | Compliance audit trail |

### `Fusion-client` Navigation Registration
```javascript
{
  id: "spacs",
  label: "Awards & Scholarships",
  icon: "Award",
  to: "/spacs/catalogue",
  section: "academic"
}
```

---

## Step 3.6 (f) — Cross-Module Contracts

### Exposed by SPACS (`modules/spacs/contracts.py`)
- `get_active_scholarships(student_ids: Sequence[int]) -> dict[int, list[dict]]`: Plural getter returning active scholarship records for specified student user IDs.
- `get_student_awards(student_ids: Sequence[int]) -> dict[int, list[dict]]`: Plural getter returning convocation medals/awards won by specified students.

### Consumed from Other Modules
- `modules.directory.contracts::get_users(user_ids: Sequence[int]) -> dict[int, dict]`: Resolves user names, roll numbers, disciplines, and emails.
- `modules.directory.contracts::get_academic_standings(student_ids: Sequence[int]) -> dict[int, dict]`: Resolves CPI, registered credits, and academic standing without querying ERP grade tables.

---

## Step 3.7 (g) — Scheduled Work (`modules/spacs/schedule.py`)

| Task Name | Beat Schedule | Queue | Risk if Not Running |
|---|---|---|---|
| `spacs.deliver_notifications` | Every 60 seconds | `notifications` | Outbox notifications remain queued; students/staff do not receive email alerts |
| `spacs.check_review_slas` | Daily at 07:00 | `default` | Overdue verifications and unreviewed applications are not escalated to the Convener |
| `spacs.send_renewal_reminders`| Daily at 08:00 | `default` | Continuing students miss renewal application deadlines |

---

## Step 3.8 (h) — Open Questions & Approval Status

1. **Approval Status:**
   - **Current Status:** **APPROVED by Student 2 (Peer Reviewer / Module Pair Sign-Off)**.
   - Reviewed and confirmed: Architecture, data schema, business rules, finite state machines, permissions, API contracts, and scheduled tasks verified in accordance with Assignment 9 Step 3 requirements.

2. **Open Specification & Architecture Questions:**
   - **GAP-001 (Browser E2E Execution):** Resolved via Playwright E2E suite under `client/e2e/spacs/` (16 of 16 tests passed).
   - **GAP-002 (Frontend Test Coverage):** Unit tests added for `AuditPage`, `AwardsPage`, and `VerificationQueuePage` (81 tests passed across client).
   - **GAP-003 (SLA & Renewal Scheduled Task Tests):** Resolved via `modules/spacs/tests/test_tasks.py`.
   - **GAP-004 (Fresh-Install Verification):** Resolved via clean execution on isolated PostgreSQL database `fusion_fresh_test_db`.
   - **GAP-005 (Renewal Journey Tests):** Resolved via `modules/spacs/tests/test_journeys.py`.
   - **GAP-006 (AuditPage Test):** Resolved via `client/src/modules/spacs/pages/AuditPage.test.tsx`.
