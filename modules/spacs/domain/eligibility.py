"""Machine-checkable eligibility evaluation for SPACS schemes (BR-SPACS-001)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class EligibilityResult:
    is_eligible: bool
    reasons: tuple[str, ...]

    @classmethod
    def passed(cls) -> EligibilityResult:
        return cls(is_eligible=True, reasons=())

    @classmethod
    def failed(cls, reasons: list[str]) -> EligibilityResult:
        return cls(is_eligible=False, reasons=tuple(reasons))


def _check_cpi_and_backlogs(criteria: dict, student: dict) -> list[str]:
    failures: list[str] = []
    min_cpi = criteria.get("min_cpi")
    if min_cpi is not None:
        student_cpi = student.get("cpi")
        if student_cpi is None:
            failures.append("Academic standing or CPI has not been declared.")
        else:
            try:
                if Decimal(str(student_cpi)) < Decimal(str(min_cpi)):
                    failures.append(f"CPI {student_cpi} is below the minimum required {min_cpi}.")
            except (ValueError, TypeError, ArithmeticError):
                failures.append("Invalid CPI value.")

    max_backlogs = criteria.get("max_backlogs")
    if max_backlogs is not None:
        backlogs = student.get("active_backlogs", 0)
        if backlogs is not None and int(backlogs) > int(max_backlogs):
            failures.append(
                f"Active backlogs ({backlogs}) exceed maximum allowed ({max_backlogs})."
            )
    return failures


def _check_income(criteria: dict, student: dict) -> list[str]:
    failures: list[str] = []
    income_ceiling = criteria.get("income_ceiling")
    if income_ceiling is not None:
        student_income = student.get("annual_income")
        if student_income is None:
            failures.append("Annual family income has not been declared.")
        else:
            try:
                if Decimal(str(student_income)) > Decimal(str(income_ceiling)):
                    msg = (
                        f"Declared annual income ₹{student_income} "
                        f"exceeds scheme ceiling ₹{income_ceiling}."
                    )
                    failures.append(msg)
            except (ValueError, TypeError, ArithmeticError):
                failures.append("Invalid income value.")
    return failures


def _check_cohort(criteria: dict, student: dict) -> list[str]:
    failures: list[str] = []
    programmes = criteria.get("allowed_programmes")
    if programmes:
        student_prog = (student.get("programme") or "").strip().lower()
        allowed = {p.strip().lower() for p in programmes}
        if student_prog not in allowed:
            failures.append(
                f"Programme {student.get('programme')!r} is not eligible for this scheme."
            )

    disciplines = criteria.get("allowed_disciplines")
    if disciplines:
        student_disc = (student.get("discipline") or "").strip().lower()
        allowed = {d.strip().lower() for d in disciplines}
        if student_disc not in allowed:
            failures.append(
                f"Discipline {student.get('discipline')!r} is not eligible for this scheme."
            )

    batches = criteria.get("allowed_batches")
    if batches:
        student_batch = student.get("batch_year")
        if student_batch is None or int(student_batch) not in {int(b) for b in batches}:
            failures.append(f"Batch year {student_batch} is not eligible for this scheme.")

    categories = criteria.get("allowed_categories")
    if categories:
        student_cat = (student.get("category") or "").strip().upper()
        allowed = {c.strip().upper() for c in categories}
        if student_cat not in allowed:
            failures.append(
                f"Category {student.get('category')!r} is not eligible for this scheme."
            )
    return failures


def evaluate_eligibility(criteria: dict, student: dict) -> EligibilityResult:
    """Evaluate machine-checkable eligibility rules against scheme criteria and student data."""
    failures: list[str] = []
    failures.extend(_check_cpi_and_backlogs(criteria, student))
    failures.extend(_check_income(criteria, student))
    failures.extend(_check_cohort(criteria, student))

    if failures:
        return EligibilityResult.failed(failures)
    return EligibilityResult.passed()
