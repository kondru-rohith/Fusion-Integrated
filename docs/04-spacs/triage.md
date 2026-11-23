# SPACS Specification Test Baseline Triage

## 1. Baseline execution summary

All four specification-based test suites were executed independently on branch `module/spacs`, before test repairs or Student 1 production-code changes.

| Strategy | Designed cases | Executed cases | Passed | Failed | Errors | Exit code |
|---|---:|---:|---:|---:|---:|---:|
| FR | 70 | 70 | 60 | 8 | 2 | 1 |
| UC | 58 | 58 | 56 | 1 | 1 | 1 |
| BR | 33 | 33 | 33 | 2 | 0 | 1 |
| WF | 31 | 31 | 31 | 12 | 0 | 1 |
| **Total** | **192** | **192** | **166** | **23** | **3** | — |

The six documented blocker-only cases are not included in pytest execution: UC-SPACS-050, UC-SPACS-054, BR-SPACS-003, BR-SPACS-005, WF-SPACS-022, and WF-SPACS-027.

## 2. Baseline artifacts

Each strategy has the following outputs under `docs/04-spacs/baseline-results/`:

- `pytest.log`
- `junit.xml`
- `coverage.xml`

The original FR preflight-failure outputs are retained separately under `fr/preflight-failure/`. They are not the final FR baseline run.

## 3. Observed failures and errors

### FR — 8 failed, 2 errors

- FR-SPACS-001 and FR-SPACS-019: missing `published_scholarship` pytest fixture.
- FR-SPACS-003: duplicate-application IntegrityError causes the existing-test helper's savepoint rollback to fail with TransactionManagementError.
- FR-SPACS-014 and FR-SPACS-064: award approval service rejects the observed `awaiting_approval` status because it expects `AWAITING_INSTITUTIONAL_APPROVAL`.
- FR-SPACS-020: expected catalogue entry description is absent from the API response.
- FR-SPACS-024: existing API test expects `mcm-scholarship`, but the available catalogue result contains only `FR-TRACE-SCHEME`.
- FR-SPACS-028: duplicate application is rejected by the database uniqueness constraint despite the test enabling multiple applications.
- FR-SPACS-036: expected additional recipient notification is not observed.
- FR-SPACS-038: mapped existing test function cannot be found.

### UC — 1 failed, 1 error

- UC-SPACS-030: missing `published_scholarship` pytest fixture.
- UC-SPACS-004: duplicate-application IntegrityError causes the existing-test helper's savepoint rollback to fail with TransactionManagementError.

### BR — 2 failed

- BR-SPACS-004: duplicate-application IntegrityError causes the existing-test helper's savepoint rollback to fail with TransactionManagementError.
- BR-SPACS-033: mapped scenario function `_direct_configured_candidate_source_case` is not defined in the test module.

### WF — 12 failed

- WF-SPACS-005, WF-SPACS-008, WF-SPACS-009, WF-SPACS-010, and WF-SPACS-011: failure details require further review.
- WF-SPACS-014, WF-SPACS-018, WF-SPACS-019, WF-SPACS-020, WF-SPACS-021, WF-SPACS-023, and WF-SPACS-024: test helper generates application numbers longer than the database field's 32-character limit, causing DataError.

## 4. Initial triage classification

The following are preliminary classifications and must be confirmed during the permitted test-repair and investigation stages.

| Finding | Initial classification |
|---|---|
| Missing fixtures in FR and UC | Student 2 test setup defect |
| Missing FR-SPACS-038 mapped function | Student 2 test mapping defect |
| BR-SPACS-033 missing scenario function | Student 2 test mapping defect |
| UC-SPACS-004, BR-SPACS-004, FR-SPACS-003 | Shared test helper transaction-handling defect |
| WF application-number length failures | Student 2 test-data generation defect |
| FR-SPACS-024 | Test fixture or seed-data dependency; investigate |
| FR-SPACS-014 and FR-SPACS-064 | Potential production status inconsistency; investigate |
| FR-SPACS-020 | Potential API response/specification mismatch; investigate |
| FR-SPACS-028 | Potential production uniqueness-rule/configuration defect; report to Student 1 |
| FR-SPACS-036 | Potential notification behavior gap; verify against source specification |
| WF-SPACS-005, 008, 009, 010, 011 | Pending detailed investigation |

## 5. Baseline preservation and repair constraints

- Preserve the original baseline logs, JUnit reports, and coverage reports.
- Do not modify production code as Student 2.
- Repair test code and test setup only within the assignment's permitted limits.
- Do not remove, skip, xfail, or weaken designed test cases.
- Preserve test IDs, source IDs, design intent, and case counts.
- Report confirmed production implementation gaps to Student 1 rather than changing production code.
- Record each repair and its rationale in the subsequent triage updates.

## 6. Current status

Baseline execution is complete for FR, UC, BR, and WF. Initial triage is recorded; detailed investigation and permitted test repairs remain pending.