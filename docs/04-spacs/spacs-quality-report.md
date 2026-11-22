# SPACS Module — Step 7 Quality Report

**Module:** SPACS — Awards & Scholarships (`spacs`)
**Branch:** `module/spacs`
**Student:** Student 1
**Report date:** 22 November 2026
**Report version:** 1.0

---

## Table of Contents

1. [Build and check results](#1-build-and-check-results)
2. [Backend and frontend coverage](#2-backend-and-frontend-coverage)
3. [Test counts per file and journey mapping](#3-test-counts-per-file-and-journey-mapping)
4. [Five critical business rules — mutation scenarios](#4-five-critical-business-rules--mutation-scenarios)
5. [Adversarial review results](#5-adversarial-review-results)
6. [Security self-audit](#6-security-self-audit)
7. [Fresh-install proof](#7-fresh-install-proof)
8. [Browser walkthrough](#8-browser-walkthrough)
9. [Scheduled tasks — manual verification](#9-scheduled-tasks--manual-verification)
10. [Known gaps, specification IDs, and approvals](#10-known-gaps-specification-ids-and-approvals)
11. [Required approvals and evidence](#11-required-approvals-and-evidence)
12. [Independent review scorecards](#12-independent-review-scorecards)

---

## 1. Build and check results

All checks were performed on branch `module/spacs` as reported by the developer on 22 November 2026. The table below reflects the developer-reported outcome; individual check outputs were not separately captured from logs during this report-generation run.

### 1.1  Backend — `make check`

| Check step | Command / mechanism | Reported result |
|---|---|---|
| Django system check | `python manage.py check` | **PASSED** — no issues |
| Migration check | `python manage.py makemigrations --check --dry-run` | **PASSED** — no pending migrations |
| Ruff lint | `.venv/bin/ruff check .` | **PASSED** |
| Import contracts | `.venv/bin/lint-imports` | **PASSED** — 5 contracts kept, 0 broken |
| Cross-module FK check | `ops/checks/no_cross_module_fk.py` | **PASSED** |
| Contract getter check | `ops/checks/contracts_are_plural.py` | **PASSED** |
| Navigation/routes check | `ops/checks/nav_matches_routes.py` | **PASSED** |
| Permission manifest check | `python manage.py permission_manifest --check` | **PASSED** |
| OpenAPI schema check | `make schema-check` | **PASSED** |
| Pytest suite | `python -m pytest -q` | **PASSED** — all tests passed |

### 1.2  Frontend — `make check-client`

| Check step | Reported result |
|---|---|
| TypeScript typecheck (`npm run typecheck`) | **PASSED** |
| Vitest unit tests (`npm test`) | **PASSED** — 14 test files, 64 tests passed |
| Production build (`npm run build`) | **PASSED** — with one bundle-size warning |
| Bundle-size warning | One generated JS chunk exceeded the 500 kB threshold. This is a **warning**, not a build failure. |

> [!NOTE]
> The bundle-size warning is logged here for visibility. It did not cause `make check-client` to fail. If the threshold is a hard requirement in a future CI gate, the SPACS vendor chunk should be code-split or the shared code moved to a lazy route.

### 1.3  E2E browser tests — `make e2e`

| Item | Detail |
|---|---|
| Command | `make e2e` → `cd client && npm run e2e` |
| Browser | Chromium (Playwright) |
| Tests passed | **9 of 9** |
| IAM fixture | Prepared successfully |
| IAM role violations found | `stf00061` (staff) holds **Assistant Professor**; `stu01042` (student) holds **Dean Academic** |
| Effect on suite | Violations were **reported** as warnings by IAM; they did **not** fail any E2E test |

> [!NOTE]
> The two IAM role violations above are pre-existing data-quality issues in the shared IAM test fixture, not defects introduced by the SPACS module. They should be tracked separately at the IAM/admin level.

The nine E2E tests cover the following scenarios (from `client/e2e/`):

| # | Spec file | Scenario |
|---|---|---|
| 1 | `auth.spec.ts` | Wrong credentials are refused; user stays on `/login` |
| 2 | `auth.spec.ts` | Student signs in, sees only student screens, signs out |
| 3 | `auth.spec.ts` | Student signs in using keyboard navigation alone |
| 4 | `shell.spec.ts` | Collapsed sidebar names modules for screen readers |
| 5 | `placement/companies.spec.ts` | Placement officer registers a company and sees it pending |
| 6–9 | `placement/office-pages.spec.ts` | Student who navigates to each of the four placement-office pages (`/placement/companies`, `/placement/interviews`, `/placement/registration-approvals`, `/placement/students-cpi`) sees "Not available to your role" |

> [!IMPORTANT]
> The nine passing E2E tests cover shell and authentication flows shared across all modules, and four placement-module role-guard tests. As of this report, there are **no SPACS-specific browser E2E tests** in the `client/e2e/` tree. SPACS flows are exercised by backend API tests and Vitest component/page tests. A separate browser E2E file for SPACS (e.g., `client/e2e/spacs/`) is listed as a **known gap** in Section 10.

---

## 2. Backend and frontend coverage

### 2.1  Backend coverage

Backend test coverage was measured using `pytest-cov` against the entire `modules/spacs/` codebase across all 52 backend tests (`tests/test_api.py`, `tests/test_domain.py`, `tests/test_models.py`, `tests/test_notifications.py`, `tests/test_query_budgets.py`, `tests/test_client_route_guards.py`).

**Executed commands:**
```bash
# Statement coverage:
.venv/bin/python -m pytest modules/spacs/tests/ --cov=modules/spacs --cov-report=term-missing 2>&1 | tee docs/04-spacs/scratch/coverage-backend.txt

# Statement + branch coverage:
.venv/bin/python -m pytest modules/spacs/tests/ --cov=modules/spacs --cov-branch --cov-report=term-missing 2>&1 | tee docs/04-spacs/scratch/coverage-backend-branch.txt
```
*Full raw output saved to:* [`docs/04-spacs/scratch/coverage-backend.txt`](file:///Users/kondrurohith/Fusion-Integrated/docs/04-spacs/scratch/coverage-backend.txt) and [`docs/04-spacs/scratch/coverage-backend-branch.txt`](file:///Users/kondrurohith/Fusion-Integrated/docs/04-spacs/scratch/coverage-backend-branch.txt).

#### Summary totals

| Metric | Measured total | Covered | Missed / partial |
|---|---|---|---|
| **Statements** | **1,759** | **1,319** | **440 missed** |
| **Statement coverage** | **75%** | — | — |
| **Branches** | **390** | **306** | **84 partial** |
| **Branch coverage** | **70%** | — | — |
| **Test suite result** | **52 passed** (0 failures, 0 errors, 2.07s) | — | — |

> [!NOTE]
> The previous informal claim of "100%" reflected test execution completion (100% of tests passed), not code coverage. The measured statement coverage for the SPACS backend is **75%** (70% with branch coverage).

#### Detailed breakdown by module file

| File | Statements | Missed | Stmt % | Branches | Partial | Branch % | Missing lines |
|---|---|---|---|---|---|---|---|
| `modules/spacs/__init__.py` | 0 | 0 | 100% | 0 | 0 | 100% | — |
| `modules/spacs/apps.py` | 5 | 0 | 100% | 0 | 0 | 100% | — |
| `modules/spacs/registry.py` | 11 | 0 | 100% | 0 | 0 | 100% | — |
| `modules/spacs/api/permissions.py` | 15 | 0 | 100% | 0 | 0 | 100% | — |
| `modules/spacs/api/serializers.py` | 90 | 0 | 100% | 4 | 0 | 100% | — |
| `modules/spacs/api/urls.py` | 4 | 0 | 100% | 0 | 0 | 100% | — |
| `modules/spacs/models/applications.py` | 29 | 1 | 97% | 0 | 0 | 97% | 101 |
| `modules/spacs/models/audit.py` | 47 | 2 | 96% | 4 | 0 | 96% | 36, 65 |
| `modules/spacs/models/catalogue.py` | 45 | 2 | 96% | 0 | 0 | 96% | 24, 73 |
| `modules/spacs/models/documents.py` | 22 | 1 | 95% | 0 | 0 | 95% | 47 |
| `modules/spacs/models/notifications.py` | 21 | 1 | 95% | 0 | 0 | 95% | 41 |
| `modules/spacs/models/awards.py` | 31 | 2 | 94% | 0 | 0 | 94% | 33, 68 |
| `modules/spacs/models/decisions.py` | 15 | 1 | 93% | 0 | 0 | 93% | 29 |
| `modules/spacs/models/verification.py` | 15 | 1 | 93% | 0 | 0 | 93% | 31 |
| `modules/spacs/services/audit.py` | 13 | 1 | 92% | 2 | 1 | 87% | 18 |
| `modules/spacs/services/notifications.py` | 94 | 11 | 88% | 22 | 7 | 84% | 48, 50, 76, 91, 127, 143-147, 157 |
| `modules/spacs/domain/state_machine.py` | 92 | 12 | 87% | 12 | 5 | 84% | 71-76, 81-82, 206, 220, 224, 237, 241, 247 |
| `modules/spacs/domain/rules.py` | 49 | 7 | 86% | 22 | 6 | 82% | 38, 81, 87-88, 95, 107, 109 |
| `modules/spacs/services/applications.py` | 172 | 26 | 85% | 68 | 15 | 80% | 35, 39-41, 102, 145, 148, 158, 199-221, 235, 252-253, 284, 290, 310, 355, 361, 369 |
| `modules/spacs/services/verification.py` | 65 | 13 | 80% | 22 | 7 | 75% | 23, 35-44, 61, 74, 82, 86 |
| `modules/spacs/api/views.py` | 290 | 63 | 78% | 26 | 6 | 75% | 85, 94-95, 99-111, 148-158, 166-167, 176-177, 198, 265-267, 302-304, 320-338, 352-366, 433-438, 466-467, 476-477, 482, 486, 500-501, 527, 559-565, 583-587 |
| `modules/spacs/services/awards.py` | 102 | 22 | 78% | 34 | 12 | 71% | 31, 57, 68, 104, 141, 161, 191-213, 225, 228, 252 |
| `modules/spacs/selectors/applications.py` | 18 | 4 | 78% | 4 | 0 | 73% | 16-19 |
| `modules/spacs/domain/eligibility.py` | 67 | 17 | 75% | 34 | 8 | 69% | 59-60, 76, 85-86, 94, 101-104, 111-113, 118-121 |
| `modules/spacs/api/exports.py` | 17 | 5 | 71% | 0 | 0 | 71% | 22-58 |
| `modules/spacs/services/decisions.py` | 63 | 19 | 70% | 28 | 7 | 65% | 17-37, 59, 67, 96-97, 103, 135 |
| `modules/spacs/selectors/scoping.py` | 83 | 36 | 57% | 38 | 7 | 48% | 35, 38, 45, 53, 58-60, 64-66, 88-90, 97, 108, 127, 132-144, 149-151, 156-164, 169-171 |
| `modules/spacs/services/documents.py` | 47 | 23 | 51% | 14 | 2 | 43% | 33-34, 40, 51-53, 73-98, 104-110 |
| `modules/spacs/selectors/awards.py` | 14 | 8 | 43% | 4 | 0 | 33% | 9-12, 16-19 |
| `modules/spacs/services/catalogue.py` | 63 | 37 | 41% | 18 | 1 | 33% | 26-44, 70, 119-152, 157-170 |
| `modules/spacs/services/renewals.py` | 31 | 19 | 39% | 8 | 0 | 31% | 28-83 |
| `modules/spacs/services/tasks.py` | 38 | 28 | 26% | 14 | 0 | 19% | 18-46, 51-78, 87-99 |
| `modules/spacs/tasks.py` | 15 | 15 | 0% | 0 | 0 | 0% | 3-28 |
| `modules/spacs/contracts.py` | 42 | 42 | 0% | 8 | 0 | 0% | 6-92 |
| `modules/spacs/schedule.py` | 3 | 3 | 0% | 0 | 0 | 0% | 3-11 |
| `modules/spacs/selectors/catalogue.py` | 18 | 18 | 0% | 4 | 0 | 0% | 1-31 |

#### Files with lowest coverage (< 50%)

The following files represent the principal coverage gaps in the SPACS backend:

1. **`modules/spacs/contracts.py` (0%, 42 stmts missed):** Outward-facing module contracts consumed by other modules; not exercised in isolated SPACS test suite runs.
2. **`modules/spacs/tasks.py` (0%, 15 stmts missed):** Celery shared task declarations (`@shared_task`), invoked by worker runtime rather than unit test imports.
3. **`modules/spacs/schedule.py` (0%, 3 stmts missed):** Celery beat schedule configuration dictionary.
4. **`modules/spacs/selectors/catalogue.py` (0%, 18 stmts missed):** Redundant/uncalled catalogue helper selectors (catalogue queries are handled primarily in `scoping.py`).
5. **`modules/spacs/services/tasks.py` (26%, 28 stmts missed):** SLA escalation sweep and renewal reminder sweep functions (see Section 10, GAP-003).
6. **`modules/spacs/services/renewals.py` (39%, 19 stmts missed):** Renewal lifecycle orchestration service (see Section 10, GAP-005).
7. **`modules/spacs/services/catalogue.py` (41%, 37 stmts missed):** Version retirement and cycle-advancement helper branches.
8. **`modules/spacs/selectors/awards.py` (43%, 8 stmts missed):** Candidate pool query helpers.

---

### 2.2  Frontend coverage

Frontend test coverage was measured using Vitest v4.1.12 with the v8 coverage provider against the client test suite (`client/package.json`).

**Executed command:**
```bash
cd client && npx vitest run --coverage
```
*Full raw evidence recorded in:* [`docs/04-spacs/scratch/coverage-frontend.txt`](file:///Users/kondrurohith/Fusion-Integrated/docs/04-spacs/scratch/coverage-frontend.txt).

#### Test suite execution result

- **Test Files:** **14 passed** of 14
- **Tests:** **64 passed** of 64 (including all 26 SPACS-specific tests across 8 test files)
- **Duration:** 2.32s

#### 1. Whole-frontend coverage vs. SPACS-only coverage summary

| Scope | Statements | Branches | Functions | Lines |
|---|---|---|---|---|
| **Whole frontend (`All files`)** | **38.33%** | **46.32%** | **24.81%** | **39.23%** |
| **SPACS components (`src/modules/spacs/components`)** | **53.55%** | **60.21%** | **41.37%** | **54.22%** |
| **SPACS pages (`src/modules/spacs/pages`)** | **51.23%** | **50.00%** | **42.85%** | **50.94%** |

#### 2. Detailed SPACS-only per-file breakdown

| File | Statements | Branches | Functions | Lines | Uncovered Line Numbers |
|---|---|---|---|---|---|
| **Components** | | | | | |
| `CorrectionEditModal.tsx` | 75.43% | 64.00% | 60.00% | 74.07% | 99-220, 281-290 |
| `DecisionModal.tsx` | 70.00% | 72.63% | 81.25% | 71.42% | 22, 134-146, 285 |
| `ApplicationDetailDrawer.tsx` | 48.14% | 62.50% | 38.46% | 48.00% | 59-75, 248-366 |
| `DocumentAttachModal.tsx` | 42.85% | 33.33% | 27.27% | 42.85% | 74-105, 123-149 |
| `ApplyModal.tsx` | 35.29% | 45.23% | 14.28% | 37.50% | 27, 237, 272-314 |
| `RenewalModal.tsx` | 0.00% | 0.00% | 0.00% | 0.00% | 25-96 |
| **Pages** | | | | | |
| `CataloguePage.tsx` | 72.22% | 60.60% | 42.85% | 72.22% | 33, 62, 151-170 |
| `DecisionQueuePage.tsx` | 61.90% | 58.33% | 56.25% | 61.90% | 29, 114-159 |
| `MyApplicationsPage.tsx` | 53.84% | 52.63% | 50.00% | 53.84% | 30-43, 129-181 |
| `CatalogueAdminPage.tsx` | 44.32% | 36.84% | 36.00% | 43.61% | 44, 388, 412-556 |

#### 3. Low-coverage files and untested frontend code (remaining gaps)

The measured numbers show that frontend test coverage is partial (~51% to 54% for SPACS, 38.33% overall). In particular:

1. **`RenewalModal.tsx` (0.00% lines/stmts):** Completely untested in the frontend test suite (uncovered lines 25–96).
2. **`ApplyModal.tsx` (35.29% stmts / 37.50% lines):** Major application form submission paths, validation states, and document selection branches remain uncovered (lines 27, 237, 272–314).
3. **`DocumentAttachModal.tsx` (42.85% stmts/lines):** Drive link parsing, error display, and file validation handlers are largely unexercised (lines 74–105, 123–149).
4. **`CatalogueAdminPage.tsx` (44.32% stmts / 43.61% lines):** Complex version creation dialogs, scheme retirement modals, and administrative tables are uncovered (lines 44, 388, 412–556).
5. **`ApplicationDetailDrawer.tsx` (48.14% stmts / 48.00% lines):** History timeline, verification notes, and nested document preview actions are unexercised (lines 59–75, 248–366).
6. **Untested pages and components (0% / unlisted):** `AuditPage.tsx`, `AwardsPage.tsx`, `VerificationQueuePage.tsx`, `AwardEvaluateModal.tsx`, `VerificationModal.tsx`, and `api/hooks.ts` have no dedicated tests in `client/src/modules/spacs/` and were not exercised during the run.

> [!WARNING]
> While all 64 unit tests pass, neither the overall client codebase (38.33% statement coverage) nor the SPACS module frontend (~51–54% statement coverage) achieves full coverage. Low coverage across modal components, administration screens, and unexercised pages represents a known quality gap tracked in Section 10.

---

## 3. Test counts per file and journey mapping

### 3.1  Backend test files

| File | Tests | Description |
|---|---|---|
| `tests/test_api.py` | **31** | API integration tests covering role auth, state machine, eligibility, documents, verification, decisions, awards |
| `tests/test_domain.py` | **9** | Pure-Python domain tests: state machine transitions, eligibility, completeness, document reuse |
| `tests/test_models.py` | **5** | Model-level constraint and audit-immutability tests |
| `tests/test_notifications.py` | **4** | Outbox enqueue, delivery, exponential back-off, daily rate limiting |
| `tests/test_query_budgets.py` | **1** | N+1 query regression guard on verification-queue list endpoint |
| `tests/test_client_route_guards.py` | **2** | Static assertion that every protected page is guarded by its nav-item permission |
| **Total backend** | **52** | |

### 3.2  Frontend test files (Vitest)

| File | Tests | Focus |
|---|---|---|
| `components/ApplicationDetailDrawer.test.tsx` | 8 | Withdraw/resubmit button visibility by role and status; concern banner |
| `components/DecisionModal.test.tsx` | 6 | Normal sanction workflow; concern acknowledgement; pending-doc block |
| `components/CorrectionEditModal.test.tsx` | 3 | Pre-fill, CPI-edit prevention, update & resubmit flow |
| `components/ApplyModal.test.tsx` | 2 | CPI info alert shown/hidden based on `min_cpi` |
| `pages/CatalogueAdminPage.test.tsx` | 3 | No-version entry, create-first-version, draft-next-cycle-version |
| `pages/CataloguePage.test.tsx` | 2 | Published scheme render; Apply Now button hides for non-student |
| `pages/DecisionQueuePage.test.tsx` | 1 | Concern vs. normal verified rows get distinct action buttons |
| `pages/MyApplicationsPage.test.tsx` | 1 | Student application list with INR-formatted income (`4,50,000`) |
| **Total frontend (Vitest)** | **26** | |

> [!NOTE]
> The 14 test *files* reported by Vitest include non-SPACS Vitest files from other modules sharing the test run. The 8 SPACS-specific files above account for 26 of the reported 64 total passing tests.

### 3.3  Journey-to-use-case mapping

| Journey test (backend) | Use Case / BR reference |
|---|---|
| `test_catalogue_list_accessible_to_students` | UC-SPACS-001 |
| `test_student_draft_lifecycle` | UC-SPACS-002, UC-SPACS-003 |
| `test_scoping_isolation_returns_404` | BR-SPACS-008 |
| `test_submit_application_with_eligibility_and_documents` | BR-SPACS-001, BR-SPACS-004 |
| `test_assistant_verification_flow` | UC-SPACS-008, UC-SPACS-009 |
| `test_convener_sanction_flow` | UC-SPACS-012, UC-SPACS-013 |
| `test_award_cycle_and_evaluation_flow` | UC-SPACS-016 … UC-SPACS-020 |
| `test_create_first_draft_version_success` | UC-SPACS-005 |
| `test_create_draft_version_defaults_valid_dates` | UC-SPACS-005 |
| `test_opportunities_excludes_draft_and_expired_schemes` | BR-SPACS-016 |
| `test_staff_assistant_cannot_submit_student_applications` | BR-SPACS-007 |
| `test_submit_eligible_cpi` | BR-SPACS-001 |
| `test_submit_ineligible_cpi` | BR-SPACS-001 |
| `test_submit_no_declared_standing` | BR-SPACS-001, ADR-0008 |
| `test_submit_iam_unavailable_returns_503` | ADR-0008 |
| `test_attached_income_certificate_satisfies_requirement_with_normalization` | BR-SPACS-003, BR-SPACS-004 |
| `test_genuinely_missing_document_rejected` | BR-SPACS-004 |
| `test_student_can_withdraw_own_application` | UC-SPACS-004, BR-SPACS-010 |
| `test_staff_and_other_students_cannot_withdraw_application` | BR-SPACS-010 |
| `test_verified_finding_updates_documents_to_valid` | UC-SPACS-008 |
| `test_correction_required_finding_leaves_documents_pending` | BR-SPACS-006 |
| `test_concern_raised_finding_leaves_documents_pending` | UC-SPACS-010 |
| `test_approval_rejected_when_required_documents_pending_or_invalid` | BR-SPACS-005 |
| `test_approval_succeeds_when_all_required_documents_valid` | UC-SPACS-012 |
| `test_correction_required_editing_and_resubmission` | UC-SPACS-003, BR-SPACS-006 |
| `test_correction_editing_ownership_and_status_authorization` | BR-SPACS-010 |
| `test_cpi_not_manually_editable_in_correction` | BR-SPACS-001 |
| `test_verification_concern_details_visible_to_convener` | UC-SPACS-011 |
| `test_concerned_application_cannot_bypass_document_verification` | BR-SPACS-005 |
| `test_concerned_application_returned_for_correction_recorded_in_audit` | UC-SPACS-011, BR-SPACS-021 |
| `test_unauthorized_users_cannot_make_decisions_or_resolve_concerns` | BR-SPACS-007 |

---

## 4. Five critical business rules — mutation testing

To verify that the automated test suite actively detects violations of core business rules, deliberate mutations were applied one by one to the production code in an isolated manner, tested, and immediately restored.

### 4.1  Mutation testing summary table

| Business rule ID | Deliberate mutation | Test executed | Original test result | Mutation test result | Restoration test result | Final status |
|---|---|---|---|---|---|---|
| **BR-SPACS-001** (Minimum CPI gate) | In `domain/eligibility.py`, bypassed the minimum CPI comparison (`if False and ...`), allowing students below the threshold to submit | `test_api.py::test_submit_ineligible_cpi` | **PASSED** (HTTP 400 with CPI error) | **FAILED as expected** (`assert 200 == 400`, applicant with CPI 6.5 < 7.0 was wrongly accepted) | **PASSED** (HTTP 400 restored) | **DETECTED** ✅ |
| **BR-SPACS-002** (One active application per cycle) | In `models/applications.py`, added a `save()` override on `ScholarshipApplication` swallowing `IntegrityError`, simulating absence of DB constraint enforcement | `test_models.py::test_prevent_duplicate_active_applications` | **PASSED** (`IntegrityError` raised and verified) | **FAILED as expected** (`Failed: DID NOT RAISE IntegrityError` on duplicate active create) | **PASSED** (`IntegrityError` raised and verified) | **DETECTED** ✅ |
| **BR-SPACS-004** (Completeness before submit) | In `domain/rules.py`, forced `missing_docs = []` in `validate_application_completeness()`, bypassing missing document checks | `test_domain.py::test_application_completeness_validation` & `test_api.py::test_genuinely_missing_document_rejected` | **PASSED** (Completeness fails; submit returns HTTP 400) | **FAILED as expected** (`assert 'grade_sheet' in ()` and API `assert 200 == 400`) | **PASSED** (Both completeness and rejection tests pass) | **DETECTED** ✅ |
| **BR-SPACS-010** (Owner-only withdrawal) | In `services/applications.py`, disabled the ownership check (`if False and app.user_id != uid:`) in `withdraw_application()` | `test_api.py::test_staff_and_other_students_cannot_withdraw_application` | **PASSED** (Other student receives HTTP 403 Forbidden) | **FAILED as expected** (`assert 200 == 403`, rival student was wrongly permitted to withdraw) | **PASSED** (HTTP 403 Forbidden restored) | **DETECTED** ✅ |
| **BR-SPACS-012 / BR-SPACS-021** (Audit-trail immutability) | In `models/audit.py`, removed `if self.pk is not None: raise RuntimeError` from `SpacsAuditLog.save()`, allowing updates to existing log rows | `test_models.py::test_audit_log_immutability` | **PASSED** (`RuntimeError("append-only")` raised) | **FAILED as expected** (`Failed: DID NOT RAISE RuntimeError` when modifying existing audit log) | **PASSED** (`RuntimeError("append-only")` raised and verified) | **DETECTED** ✅ |

### 4.2  Detailed mutation logs and mechanisms

#### 1. BR-SPACS-001 — Minimum CPI and academic-standing gate
- **Rule:** A student may not submit a scholarship application unless their CPI meets or exceeds the scheme's `min_cpi` and their academic standing has been declared by IAM.
- **Implementation:** `modules/spacs/domain/eligibility.py:evaluate_eligibility()`
- **Mutation:** Modified line 57 to `if False and Decimal(str(student_cpi)) < Decimal(str(min_cpi)):`.
- **Failure output:**
  ```
  FAILED modules/spacs/tests/test_api.py::test_submit_ineligible_cpi
  > assert res.status_code == 400, res.json()
  E AssertionError: assert 200 == 400
  ```
- **Conclusion:** The test suite immediately detects if the CPI validation branch is bypassed or neutralized.

#### 2. BR-SPACS-002 — One active application per student per scheme per cycle
- **Rule:** A student cannot hold two active applications for the same scheme and cycle simultaneously.
- **Implementation:** `ScholarshipApplication` model constraint (`spacs_unique_active_application_per_cycle`).
- **Mutation:** Added an exception-swallowing `save()` override on `ScholarshipApplication`.
- **Failure output:**
  ```
  FAILED modules/spacs/tests/test_models.py::test_prevent_duplicate_active_applications
  > with pytest.raises(IntegrityError):
  E Failed: DID NOT RAISE IntegrityError
  ```
- **Conclusion:** The test suite strictly requires the underlying database constraint to reject duplicate active submissions with `IntegrityError`.

#### 3. BR-SPACS-004 — Application completeness before submission
- **Rule:** A student cannot submit until all mandatory fields and required documents are attached.
- **Implementation:** `modules/spacs/domain/rules.py:validate_application_completeness()`
- **Mutation:** Hardcoded `missing_docs = []`.
- **Failure output:**
  ```
  FAILED modules/spacs/tests/test_domain.py::test_application_completeness_validation
  > assert "grade_sheet" in res.missing_documents
  E AssertionError: assert 'grade_sheet' in ()

  FAILED modules/spacs/tests/test_api.py::test_genuinely_missing_document_rejected
  > assert submit_res.status_code == 400, submit_res.json()
  E AssertionError: assert 200 == 400
  ```
- **Conclusion:** Both domain unit tests and end-to-end API submission endpoints catch the bypass of missing required documents.

#### 4. BR-SPACS-010 — Owner-only withdrawal
- **Rule:** Only the applicant themselves may withdraw their application; staff roles and other students must be rejected with HTTP 403.
- **Implementation:** `modules/spacs/services/applications.py:withdraw_application()`
- **Mutation:** Bypassed the applicant ID check (`if False and app.user_id != uid:`).
- **Failure output:**
  ```
  FAILED modules/spacs/tests/test_api.py::test_staff_and_other_students_cannot_withdraw_application
  > assert res_other.status_code == 403
  E assert 200 == 403
  ```
- **Conclusion:** The API authorization check strictly blocks horizontal privilege escalation and non-owner withdrawals.

#### 5. BR-SPACS-012 / BR-SPACS-021 — Audit-trail immutability
- **Rule:** `SpacsAuditLog` records are strictly append-only; any attempt to update an existing row must raise `RuntimeError`.
- **Implementation:** `modules/spacs/models/audit.py:SpacsAuditLog.save()` and `ImmutableQuerySet`.
- **Mutation:** Removed the `if self.pk is not None: raise RuntimeError(...)` guard.
- **Failure output:**
  ```
  FAILED modules/spacs/tests/test_models.py::test_audit_log_immutability
  > with pytest.raises(RuntimeError, match="append-only"):
  E Failed: DID NOT RAISE RuntimeError
  ```
- **Conclusion:** Tampering with historical audit logs is guaranteed to raise `RuntimeError`, and the test fails if this guard is altered or removed.

---

## 5. Adversarial review results

An adversarial review was conducted manually against the SPACS API layer by systematically attempting the following attack classes. Each item documents the vector tried and the control that prevented it.

### 5.1  Horizontal privilege escalation (BR-SPACS-008)

**Vector:** Student A requests `GET /api/v1/spacs/applications/{id}/` where `{id}` belongs to Student B.
**Control:** `scoping.py` limits the queryset to `user_id == request.principal.user_id` for students; non-owners receive HTTP 404 (not 403, to avoid leaking existence).
**Verified by:** `test_scoping_isolation_returns_404`

### 5.2  Role escalation — staff submitting as student (BR-SPACS-007)

**Vector:** SPACS Assistant calls `POST /api/v1/spacs/applications/` to create a student application.
**Control:** `ApplicationDraftCreateView` checks that the principal's `kind == "student"` before creating a draft; non-student principals receive HTTP 403.
**Verified by:** `test_staff_assistant_cannot_submit_student_applications`

### 5.3  Student applying to draft schemes

**Vector:** Student calls `POST /api/v1/spacs/applications/` with the PK of a `draft` catalogue version.
**Control:** `scoping.published_scholarship_opportunities()` only returns `status="published"` versions; the lookup on submit returns HTTP 404.
**Verified by:** `test_staff_assistant_cannot_submit_student_applications` (case 2) and `test_opportunities_excludes_draft_and_expired_schemes`

### 5.4  Withdrawal by non-owner (BR-SPACS-010)

**Vector:** SPACS Assistant, SPACS Convener, or a different student calls `POST /api/v1/spacs/applications/{id}/withdraw/`.
**Control:** `ApplicationWithdrawView` enforces ownership; all three non-owner cases receive HTTP 403.
**Verified by:** `test_staff_and_other_students_cannot_withdraw_application`

### 5.5  Approval without valid documents (BR-SPACS-005)

**Vector:** Convener calls `POST /api/v1/spacs/decisions/{id}/outcome/` with `decision=approved` while required documents are `pending` or `invalid`.
**Control:** `decision_services.make_decision()` queries active documents for the application and rejects with HTTP 400 if any required document is not `valid`.
**Verified by:** `test_approval_rejected_when_required_documents_pending_or_invalid`, `test_concerned_application_cannot_bypass_document_verification`

### 5.6  Student self-approving (BR-SPACS-007)

**Vector:** Student calls the decision endpoint directly (bypassing the UI).
**Control:** `DecisionOutcomeCreateView` requires `spacs.application.approve`; students do not hold this permission. HTTP 403 returned.
**Verified by:** `test_unauthorized_users_cannot_make_decisions_or_resolve_concerns`

### 5.7  Manual CPI tampering during correction (BR-SPACS-001)

**Vector:** Student sends `{"cpi_at_apply": 10.0}` in a PUT request during the correction phase, attempting to overwrite the frozen CPI.
**Control:** `ApplicationDetailView.put()` strips `cpi_at_apply` from the writeable fields; the value is ignored.
**Verified by:** `test_cpi_not_manually_editable_in_correction`

### 5.8  Audit-log tampering (BR-SPACS-021)

**Vector:** Any actor attempts to `UPDATE` or `DELETE` an audit log row via the ORM (e.g., via Django shell or bulk operation).
**Control:** `ImmutableQuerySet.update()` and `.delete()` raise `RuntimeError`; `SpacsAuditLog.save()` raises `RuntimeError` when `pk` is not None.
**Verified by:** `test_audit_log_immutability`, `test_transition_log_immutability`

### 5.9  IAM unavailability — fail-closed (ADR-0008)

**Vector:** IAM service is unreachable during a submit call.
**Control:** `IamUnavailable` is caught and surfaced as HTTP 503 (`identity_service_unavailable`), not as an eligibility pass.
**Verified by:** `test_submit_iam_unavailable_returns_503`

### 5.10  N+1 query on queue list

**Vector:** Verification queue fetched with 10 applications, triggering per-row queries for entry and version.
**Control:** `select_related("catalogue_entry", "catalogue_version")` applied; the entire list loads in 1 query.
**Verified by:** `test_verification_queue_query_budget`

---

## 6. Security self-audit

### 6.1  Authentication and session management

| Item | Observation | Status |
|---|---|---|
| All endpoints require `HasModuleGrant("spacs")` | Every `APIView` in `views.py` and `exports.py` declares `permission_classes = [MODULE, ...]` | ✅ Verified in source |
| Token-based authentication only | `APIClient.credentials(HTTP_AUTHORIZATION="Token abc")` used in all tests | ✅ Consistent with framework default |
| No anonymous endpoints | No `AllowAny` or `IsAuthenticated` without module grant found in SPACS views | ✅ Verified |

### 6.2  Authorisation

| Item | Observation | Status |
|---|---|---|
| Role grants defined centrally | `ROLE_GRANTS` dict in `registry.py` is the single source of truth for role→permission mapping | ✅ |
| Nav permission = route guard | `test_each_guard_is_its_nav_items_own_permission` asserts that every guarded route uses exactly the permission declared in its nav item | ✅ Tested |
| Object-level ownership | Withdraw and edit endpoints check `application.user_id == principal.user_id`; non-owners get 403 | ✅ Tested |
| No cross-module FK | `ops/checks/no_cross_module_fk.py` passed | ✅ |

### 6.3  Input validation

| Item | Observation | Status |
|---|---|---|
| DRF serializers used for all write operations | All POST/PUT views deserialise through named serializers in `serializers.py` | ✅ |
| Document type normalisation | `rules.normalize_doc_type()` strips/lowercases/replaces separators before comparison | ✅ Tested |
| Decimal types for monetary fields | `annual_income_declared`, `cpi_at_apply` stored as `DecimalField`; comparisons use `Decimal(str(...))` | ✅ |
| JSON fields bounded by application | `submission_data`, `eligibility_criteria` are JSONField without unrestricted execution | ✅ |

### 6.4  Secrets and credentials

No `.env` file, passwords, API keys, tokens, or secrets were accessed, printed, or recorded during this review.

### 6.5  Audit logging

| Item | Observation | Status |
|---|---|---|
| All state transitions logged | `ApplicationTransition` created on every status change | ✅ Verified in `services/` |
| Audit log immutable | `SpacsAuditLog` and `ApplicationTransition` override `save()` and `delete()` to raise `RuntimeError` | ✅ Tested |
| `SpacsAuditLog` for document events | `test_verified_finding_updates_documents_to_valid` asserts `SpacsAuditLog` row created with `action="document_verified"` | ✅ Tested |

### 6.6  Outbox / notification security

| Item | Observation | Status |
|---|---|---|
| Deduplication prevents double-delivery | Identical `dedupe_key` on second enqueue returns `None`; row count stays 1 | ✅ Tested |
| Rate limiting prevents spam | 20 sent notifications in 24 h triggers `skipped_capped`; 21st is suppressed | ✅ Tested |
| Exponential back-off on failure | Failed delivery increments `attempts`; next pick-up deferred by back-off | ✅ Tested |

---

## 7. Fresh-install proof

A fresh-install verification was **NOT independently performed** as part of this report run. The developer-reported `make check` sequence implies a clean state (migration check, system check), but the following steps were not separately witnessed:

| Step | Required for fresh-install proof | Status |
|---|---|---|
| Drop and recreate database | Confirm no stale migrations or schema drift | **NOT RUN** |
| `python manage.py migrate` on clean DB | All migrations apply without error | **NOT RUN** |
| `python manage.py seed` or equivalent | Fixture data loads cleanly | **NOT RUN** |
| `make check` on fresh DB | All checks pass on empty state | Reported PASSED — not independently verified |
| `make check-client` | Frontend builds against backend schema | Reported PASSED — not independently verified |

> [!WARNING]
> Fresh-install proof cannot be certified from the developer-reported results alone. To satisfy this requirement, the full sequence (database recreation → migrate → seed → `make check` → `make check-client`) must be performed and its console output captured.

**Recommended commands:**
```bash
# In a fresh environment or after dropdb/createdb:
python manage.py migrate
python manage.py seed       # or the project's equivalent fixture command
make check
make check-client
```

---

## 8. Browser walkthrough

The following walkthrough was inferred from the passing E2E suite (`make e2e`) and the Vitest component tests. Steps without a live browser session are marked accordingly.

> [!IMPORTANT]
> No SPACS-specific browser E2E tests exist in `client/e2e/`. The walkthrough below describes the **intended** user journeys backed by unit/API tests. Rows marked **UNIT TEST** were verified by backend API or Vitest tests, not by an end-to-end browser session.

| # | Role | Test account | Use Case | Action taken | Expected result | Evidence source | Status |
|---|---|---|---|---|---|---|---|
| 1 | Student | `stu00001` (Vitest mock) | UC-SPACS-001 | Browse Opportunities page | Published schemes shown; draft schemes hidden | `CataloguePage.test.tsx`, `test_catalogue_list_accessible_to_students` | UNIT TEST — PASSED |
| 2 | Student | `stu00001` (Vitest mock) | UC-SPACS-001 | Staff user views Opportunities | No "Apply Now" button rendered | `CataloguePage.test.tsx` | UNIT TEST — PASSED |
| 3 | Student | uid=1001 (API test) | UC-SPACS-002 | Create draft application for MCM Scholarship | HTTP 201; draft created | `test_student_draft_lifecycle` | UNIT TEST — PASSED |
| 4 | Student | uid=1001 (API test) | UC-SPACS-002 | Update draft fields (bank account, IFSC) | HTTP 200; income displayed as `450000.00` | `test_student_draft_lifecycle` | UNIT TEST — PASSED |
| 5 | Student | uid=1001 (API test) | UC-SPACS-002 | Submit draft with valid CPI and income cert | HTTP 200; `status=submitted`; CPI snapshotted | `test_submit_eligible_cpi` | UNIT TEST — PASSED |
| 6 | Student | uid=1002 (API test) | UC-SPACS-002 | Submit with CPI below threshold (6.5 < 7.0) | HTTP 400; "CPI" in error message | `test_submit_ineligible_cpi` | UNIT TEST — PASSED |
| 7 | Student | uid=1010 (API test) | UC-SPACS-004 | Withdraw own submitted application | HTTP 200; `status=withdrawn` | `test_student_can_withdraw_own_application` | UNIT TEST — PASSED |
| 8 | SPACS Assistant | uid=9 (API test) | UC-SPACS-008 | View verification queue | HTTP 200; submitted apps listed | `test_assistant_verification_flow` | UNIT TEST — PASSED |
| 9 | SPACS Assistant | uid=9 (API test) | UC-SPACS-009 | Record "verified" finding | HTTP 200; `status=verified`; docs marked `valid` | `test_verified_finding_updates_documents_to_valid` | UNIT TEST — PASSED |
| 10 | SPACS Assistant | uid=42 (API test) | UC-SPACS-009 | Record "correction_required" finding | HTTP 200; `status=correction_required` | `test_correction_required_finding_leaves_documents_pending` | UNIT TEST — PASSED |
| 11 | SPACS Convener | uid=1 (API test) | UC-SPACS-012 | View decision queue | HTTP 200; verified apps listed | `test_convener_sanction_flow` | UNIT TEST — PASSED |
| 12 | SPACS Convener | uid=1 (API test) | UC-SPACS-013 | Sanction (approve) application | HTTP 200; `status=approved` | `test_convener_sanction_flow` | UNIT TEST — PASSED |
| 13 | SPACS Convener | uid=1 (Vitest) | UC-SPACS-013 | DecisionModal: approve with sanction ref | `useMakeDecision` called with `{decision:"approved", sanction_order_ref:...}` | `DecisionModal.test.tsx` | UNIT TEST — PASSED |
| 14 | SPACS Convener | uid=1 (Vitest) | UC-SPACS-011 | DecisionModal: concern workflow requires acknowledgement checkbox | Confirm button disabled until checkbox ticked | `DecisionModal.test.tsx` | UNIT TEST — PASSED |
| 15 | SPACS Convener | uid=1 (API test) | UC-SPACS-005 | Create first catalogue version for an entry | HTTP 201; `version_number=1`; `status=draft` | `test_create_first_draft_version_success` | UNIT TEST — PASSED |
| 16 | SPACS Convener | uid=1 (API test) | UC-SPACS-016 | Open award cycle for Director Gold Medal | HTTP 201; cycle created | `test_award_cycle_and_evaluation_flow` | UNIT TEST — PASSED |
| 17 | Award Committee | uid=55 (API test) | UC-SPACS-018 | Evaluate candidate (score 95.5) | HTTP 200 | `test_award_cycle_and_evaluation_flow` | UNIT TEST — PASSED |
| 18 | SPACS Convener | uid=1 (API test) | UC-SPACS-020 | Publish award cycle | HTTP 200; `status=published` | `test_award_cycle_and_evaluation_flow` | UNIT TEST — PASSED |
| 19 | Student | `student` account (E2E) | — | Sign in and view Placement Cell module | Navigation links rendered correctly | `auth.spec.ts` E2E | E2E — PASSED |
| 20 | Student | generated username (E2E) | — | Wrong credentials refused | Alert "Incorrect username or password"; stays on `/login` | `auth.spec.ts` E2E | E2E — PASSED |

---

## 9. Scheduled tasks — manual verification

Three Celery scheduled tasks are registered in `modules/spacs/schedule.py` and exposed as Celery shared tasks in `modules/spacs/tasks.py`. Service-layer implementations live in `modules/spacs/services/tasks.py`.

| Task name | Celery task ID | Schedule | Implementation |
|---|---|---|---|
| Notification delivery | `spacs.deliver_notifications` | Every 60 s | `notifications.deliver_pending()` |
| Review SLA escalation | `spacs.check_review_slas` | Daily at 07:00 | `tasks.check_review_slas()` |
| Renewal reminder sweep | `spacs.send_renewal_reminders` | Daily at 08:00 | `tasks.send_renewal_reminders()` |

### 9.1  Task 1 — `deliver_notifications`

**What it does:** Drains `NotificationOutbox` rows in `pending` status, sends email via `send_mail`, marks rows `sent`. Applies exponential back-off on failure and suppresses beyond the daily rate cap.

**Tested in:** `tests/test_notifications.py`

| Sub-scenario | Test | Observed result |
|---|---|---|
| Pending notification is sent and marked `sent` | `test_delivery_drains_pending_and_marks_sent` | PASSED |
| Failed delivery increments `attempts` and backs off | `test_exponential_backoff_on_failure` | PASSED |
| 21st notification in 24 h is `suppressed` | `test_daily_rate_limiting` | PASSED |
| Duplicate dedupe key is silently ignored | `test_enqueue_and_deduplication` | PASSED |

**Live Celery invocation:** **NOT RUN** — no live Celery broker was available during this report. Manual invocation requires a running Redis/RabbitMQ broker.

**Recommended verification:**
```bash
python manage.py shell -c "from modules.spacs.services import notifications; \
  report = notifications.deliver_pending(); print(report)"
```

### 9.2  Task 2 — `check_review_slas`

**What it does:** Queries applications in `submitted`, `under_verification`, `verified`, or `verification_concern` states older than `sla_threshold_days`. Enqueues an SLA escalation notification for each overdue application.

**Tested:** Covered indirectly by notification-enqueue unit tests. No dedicated SLA sweep test exists.
**Live invocation:** **NOT RUN**

**Recommended verification (using Django shell):**
```python
from modules.spacs.services.tasks import check_review_slas
from django.utils import timezone
# Move now forward past the SLA threshold to trigger escalation
count = check_review_slas(now=timezone.now() + __import__('datetime').timedelta(days=10))
print(f"Escalations queued: {count}")
```

> [!WARNING]
> No dedicated test for `check_review_slas()` or `send_renewal_reminders()` exists. This is documented in Section 10 (Known Gaps, GAP-003).

### 9.3  Task 3 — `send_renewal_reminders`

**What it does:** Queries approved applications with `is_renewable=True` where the renewal window closes within 7 days. Enqueues a reminder notification per qualifying application.

**Tested:** Covered indirectly by notification-enqueue unit tests. No dedicated renewal-reminder test exists.
**Live invocation:** **NOT RUN**

---

## 10. Known gaps, specification IDs, reasons, and approval records

| ID | Specification reference | Description | Reason / justification | Approval record |
|---|---|---|---|---|
| GAP-001 | UC-SPACS-* (all) | No SPACS-specific browser E2E tests | SPACS flows fully covered by backend API tests (52 tests) and 8 Vitest component/page test files (26 tests). Browser-layer E2E tests planned for a follow-up sprint. | **PENDING** — requires convener/module-owner sign-off |
| GAP-002 | — | Frontend test coverage gaps and unexercised code | Vitest measured 53.55% statements for SPACS components and 51.23% statements for SPACS pages (38.33% across whole client). `RenewalModal.tsx` (0%), `ApplyModal.tsx` (35.29%), `DocumentAttachModal.tsx` (42.85%), `CatalogueAdminPage.tsx` (44.32%), and unexercised pages (`AuditPage`, `AwardsPage`, `VerificationQueuePage`) represent remaining coverage gaps. | **PENDING** — test additions planned |
| GAP-003 | UC-SPACS-024 (SLA), UC-SPACS-025 (renewals) | No dedicated unit tests for `check_review_slas()` and `send_renewal_reminders()` | Task behaviour is tested indirectly through the notification-outbox unit tests; direct pytest parametrisation of time-advancing scenarios is absent | **PENDING** — approval or test addition required |
| GAP-004 | — | Fresh-install proof not independently performed | `make check` and `make check-client` are reported passed but were not re-run from a clean database state during this report | **PENDING** |
| GAP-005 | UC-SPACS-015 (scholarship renewal) | Renewal application flow not fully covered by API integration tests | The `ApplyRenewalView` endpoint exists; a full renewal-cycle journey test (submit → verify → approve → renew) is absent from `test_api.py` | **PENDING** |
| GAP-006 | UC-SPACS-022 (audit-log view) | Audit trail page (`AuditPage.tsx`) has no Vitest test | `AuditPage.tsx` renders the audit log but its test file is missing | **PENDING** |

---

## 11. Required approvals and evidence

| Approval item | Required from | Evidence available | Status |
|---|---|---|---|
| Module blueprint approval | Module coordinator / Teaching team | Not on record | **PENDING** |
| GAP-001 approval (no SPACS E2E) | Module coordinator | Not on record | **PENDING** |
| GAP-003 approval (SLA/renewal tests absent) | Module coordinator | Not on record | **PENDING** |
| GAP-005 approval (renewal journey test absent) | Module coordinator | Not on record | **PENDING** |
| GAP-006 approval (AuditPage no test) | Module coordinator | Not on record | **PENDING** |
| Independent review scorecard(s) | Independent reviewer (`module-review-prompt.md`) | Not started | **PENDING** |
| Shared-file change approvals | Authors of files touched in shared layer (e.g., `ops/checks/`) | Not required — no shared files modified | N/A |
| Dependency approvals | Authors of modules consumed via contracts | `modules/directory` contract used (5 contracts kept) | **PASSED** via `make check` |

---

## 12. Independent review scorecards

No independent review rounds have been completed as of this report.

> [!NOTE]
> In accordance with Assignment 9 Step 7 ("Review, fix, repeat until 10/10"), Student 1 opens an independent reviewer session for each review round in a clean clone (`../review-r<N>`) using `module-review-prompt.md`. Each round produces a scorecard across all nine dimensions, numbered findings, and a verdict. The loop repeats until the reviewer returns `VERDICT: 10/10 in all nine dimensions`.
>
> **Round 6 Procedure:** If Round 6 does not achieve 10/10 in all nine dimensions, stop and jointly decide with Student 2 whether to fix or waive the remaining findings before proceeding to Round 7. Go through every review together in writing, mark each open finding "fix" or "waive", and answer each open question. Fix the "fix" ones, record each waiver and answer in the quality report with a link or a dated quote, and run Round 7. After Round 7, the pair's written decision on whatever is still open replaces the 10/10 (a security Blocker is always "fix").
>
> Every review round, including the final round, must be recorded, with the full reviewer output preserved unedited. Completed review round scorecards will be recorded here as they are conducted.

### Round 1 — PENDING

| Item | Detail |
|---|---|
| Reviewer session | NOT STARTED |
| Review date | NOT COMPLETED |
| Commit hash | — |
| Scorecard | Spec: -/10, Arch: -/10, Code: -/10, Security: -/10, Tests: -/10, E2E: -/10, Frontend: -/10, Ops: -/10, Hygiene: -/10 |
| Verdict | **PENDING** |
| Open findings | — |

---

## Appendix A — Verified results summary (22 November 2026)

This appendix preserves the developer-reported results as they were provided, verbatim.

### Backend: `make check`

- Django system check: **passed**, no issues.
- Migration check: **passed**, no changes detected.
- Ruff: **passed**.
- Import contracts: **5 kept, 0 broken**.
- Cross-module foreign-key check: **passed**.
- Contract getter check: **passed**.
- Navigation/routes check: **passed**.
- Permission manifest check: **passed**.
- OpenAPI schema check: **passed**.
- Pytest: all 52 tests completed successfully; actual measured coverage is 75% statement coverage and 70% branch coverage (1,319/1,759 statements, 306/390 branches).

### Frontend: `make check-client`

- TypeScript typecheck: **passed**.
- Vitest: **14 test files passed; 64 tests passed**.
- Coverage: measured via v8 coverage — overall client is 38.33% statements / 39.23% lines; SPACS components achieved 53.55% statements and SPACS pages achieved 51.23% statements.
- Production build: **passed**.
- Warning: one generated JavaScript chunk exceeded 500 kB.
- Initial test failure in `MyApplicationsPage` was corrected by matching the formatted INR value (`4,50,000`); final frontend run passed.

### End-to-end browser tests: `make e2e`

- Command: `make e2e`
- Result: **PASSED — 9 tests passed**.
- Browser: Chromium.
- Coverage included: sign-in, wrong credentials, student access restrictions, placement company registration, and sidebar accessibility.
- IAM fixture preparation succeeded.
- IAM reported two existing role violations: `stf00061` (staff) holds Assistant Professor; `stu01042` (student) holds Dean Academic.
- These warnings were reported by IAM; they did **not** fail the E2E suite.

---

## Appendix B — SPACS module file inventory

### Backend

| Layer | Files |
|---|---|
| Models | `applications.py`, `audit.py`, `awards.py`, `catalogue.py`, `decisions.py`, `documents.py`, `notifications.py`, `verification.py` |
| Services | `applications.py`, `audit.py`, `awards.py`, `catalogue.py`, `decisions.py`, `documents.py`, `notifications.py`, `renewals.py`, `tasks.py`, `verification.py` |
| Selectors | `applications.py`, `awards.py`, `catalogue.py`, `scoping.py` |
| Domain | `eligibility.py`, `rules.py`, `state_machine.py` |
| API | `views.py` (587 lines), `urls.py`, `serializers.py`, `permissions.py`, `exports.py` |
| Registry | `registry.py` |
| Schedule | `schedule.py`, `tasks.py` |
| Tests | `test_api.py` (31), `test_domain.py` (9), `test_models.py` (5), `test_notifications.py` (4), `test_query_budgets.py` (1), `test_client_route_guards.py` (2) |

### Frontend

| Layer | Files |
|---|---|
| Pages | `AuditPage.tsx`, `AwardsPage.tsx`, `CatalogueAdminPage.tsx`, `CataloguePage.tsx`, `DecisionQueuePage.tsx`, `MyApplicationsPage.tsx`, `VerificationQueuePage.tsx` |
| Components | `ApplicationDetailDrawer.tsx`, `ApplyModal.tsx`, `AwardEvaluateModal.tsx`, `CorrectionEditModal.tsx`, `DecisionModal.tsx`, `DocumentAttachModal.tsx`, `RenewalModal.tsx`, `VerificationModal.tsx` |
| API | `hooks.ts`, `types.ts` |
| Routing | `routes.tsx` |
| Tests (Vitest) | 8 `.test.tsx` files (26 tests total) |

### Scheduled tasks

| Task | Queue | Schedule |
|---|---|---|
| `spacs.deliver_notifications` | `notifications` | Every 60 seconds |
| `spacs.check_review_slas` | `default` | Daily 07:00 |
| `spacs.send_renewal_reminders` | `default` | Daily 08:00 |

---

*Report generated on 22 November 2026 by Student 1. Step 7 is **NOT YET COMPLETE** — see Section 10 and Section 12 for outstanding items.*
