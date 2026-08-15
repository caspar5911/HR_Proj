"""Payroll calculation service.

Computes gross → deductions → net pay for each employee in a payroll run.
"""

import math
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.deduction_rule import DeductionRule
from app.models.employee import Employee
from app.models.payroll_entry import PayrollEntry
from app.models.payroll_run import PayrollRun


async def calculate_payroll_for_run(
    db: AsyncSession,
    payroll_run: PayrollRun,
) -> list[PayrollEntry]:
    """Calculate payroll entries for all active employees in a payroll run.

    For each active employee:
      1. Use salary_base (or 0 if missing) as gross salary.
      2. Apply active deduction rules (fixed or percentage).
      3. Compute net = gross - deductions.
      4. Create PayrollEntry records.

    Returns the list of created PayrollEntry objects.
    """
    # Fetch all active employees
    result = await db.execute(
        select(Employee).where(Employee.status == "active")
    )
    employees = list(result.scalars().all())

    # Fetch all active deduction rules
    result = await db.execute(
        select(DeductionRule).where(
            DeductionRule.active == True  # noqa: E712
        )
    )
    deduction_rules = list(result.scalars().all())

    entries: list[PayrollEntry] = []
    for emp in employees:
        # Use salary_base as gross; default to 0
        gross_salary = float(emp.salary_base) if emp.salary_base else 0.0
        bonuses = 0.0  # TODO: allow bonus input later

        # Calculate deductions
        deductions = _apply_deductions(gross_salary, deduction_rules)

        # Net pay
        net_pay = gross_salary + bonuses - deductions

        entry = PayrollEntry(
            payroll_run_id=payroll_run.id,
            employee_id=emp.id,
            gross_salary=gross_salary,
            bonuses=bonuses,
            deductions=deductions,
            net_pay=net_pay,
        )
        payroll_run.entries.append(entry)
        entries.append(entry)

    await db.commit()
    # Refresh to get IDs
    for entry in entries:
        await db.refresh(entry)

    return entries


def _apply_deductions(gross_salary: float, rules: list[DeductionRule]) -> float:
    """Apply a list of deduction rules to a gross salary.

    Fixed deductions are subtracted directly.
    Percentage deductions are computed as (gross_salary * value / 100).
    """
    total_deductions = 0.0
    for rule in rules:
        if rule.deduction_type == "fixed":
            total_deductions += float(rule.value)
        elif rule.deduction_type == "percentage":
            total_deductions += gross_salary * float(rule.value) / 100.0

    # Deductions cannot exceed gross salary
    return min(total_deductions, gross_salary)


async def calculate_run_totals(db: AsyncSession, payroll_run: PayrollRun) -> dict:
    """Compute summary totals for a payroll run after entries are created."""
    stmt = select(PayrollEntry).where(
        PayrollEntry.payroll_run_id == payroll_run.id
    )
    result = await db.execute(stmt)
    entries = list(result.scalars().all())

    total_gross = sum(e.gross_salary for e in entries)
    total_bonuses = sum(e.bonuses for e in entries)
    total_deductions = sum(e.deductions for e in entries)
    total_net = sum(e.net_pay for e in entries)

    return {
        "total_gross": round(total_gross, 2),
        "total_bonuses": round(total_bonuses, 2),
        "total_deductions": round(total_deductions, 2),
        "total_net": round(total_net, 2),
        "entry_count": len(entries),
        "average_net": round(total_net / len(entries), 2) if entries else 0.0,
    }


async def regenerate_entries(
    db: AsyncSession,
    payroll_run: PayrollRun,
) -> list[PayrollEntry]:
    """Delete existing entries and recalculate the entire payroll run."""
    # Delete existing entries
    for entry in payroll_run.entries:
        await db.delete(entry)

    await db.commit()
    return await calculate_payroll_for_run(db, payroll_run)


async def compute_payroll_for_employee(
    db: AsyncSession,
    employee: Employee,
    deduction_rules: list[DeductionRule],
) -> dict:
    """Compute a single employee's payroll entry (for preview/standalone).

    Returns a dict with gross, deductions, bonuses, net_pay.
    """
    gross_salary = float(employee.salary_base) if employee.salary_base else 0.0
    bonuses = 0.0
    deductions = _apply_deductions(gross_salary, deduction_rules)
    net_pay = gross_salary + bonuses - deductions

    return {
        "gross_salary": round(gross_salary, 2),
        "bonuses": round(bonuses, 2),
        "deductions": round(deductions, 2),
        "net_pay": round(net_pay, 2),
    }