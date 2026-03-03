from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math


EXPENSE_DEFAULTS = {
    "Basic": 2500.0,
    "Typical": 3500.0,
    "High": 5000.0,
}

EMPLOYMENT_SHADING = {
    "Full-time": 1.00,
    "Part-time": 0.95,
    "Casual": 0.90,
    "Self-employed": 0.88,
}


@dataclass
class CalcInputs:
    income_annual_aud: float
    employment_type: str
    dependants: int

    expense_mode: str
    monthly_expenses_aud: Optional[float]

    credit_card_limit_aud: float
    personal_loan_monthly_aud: float
    car_loan_monthly_aud: float
    hecs_help_debt: bool

    interest_rate_pct: float
    term_years: int


def monthly_payment(principal: float, annual_rate_pct: float, term_years: int) -> float:
    """
    Standard amortising loan payment (P&I).
    """
    if principal <= 0:
        return 0.0
    r = (annual_rate_pct / 100.0) / 12.0
    n = term_years * 12
    if r == 0:
        return principal / n
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def implied_principal_from_payment(payment: float, annual_rate_pct: float, term_years: int) -> float:
    """
    Invert amortisation: given max monthly payment, compute max principal.
    """
    if payment <= 0:
        return 0.0
    r = (annual_rate_pct / 100.0) / 12.0
    n = term_years * 12
    if r == 0:
        return payment * n
    return payment * ((1 + r) ** n - 1) / (r * (1 + r) ** n)


def _default_expenses(mode: str) -> float:
    return EXPENSE_DEFAULTS.get(mode, EXPENSE_DEFAULTS["Typical"])


def _employment_shading(emp: str) -> float:
    return EMPLOYMENT_SHADING.get(emp, 0.90)


def estimate_borrowing_power(
    inp: CalcInputs,
) -> Tuple[float, float, Dict, List[str]]:
    """
    Conservative, explainable estimator (NOT bank credit engine).
    Returns: borrowing_power, monthly_repayment_at_borrowing_power, assumptions, warnings
    """
    warnings: List[str] = []

    # 1) Shade income for employment risk
    shade = _employment_shading(inp.employment_type)
    monthly_gross = (inp.income_annual_aud / 12.0) * shade

    # 2) Expenses
    expenses = inp.monthly_expenses_aud if inp.monthly_expenses_aud is not None else _default_expenses(inp.expense_mode)

    # 3) Dependants: add buffer per dependant
    dependant_buffer = 350.0 * max(inp.dependants, 0)

    # 4) Debt servicing proxy
    # Credit cards are assessed using a % of limit (common industry proxy).
    cc_proxy = max(inp.credit_card_limit_aud, 0.0) * 0.03
    debt_pmts = max(inp.personal_loan_monthly_aud, 0.0) + max(inp.car_loan_monthly_aud, 0.0) + cc_proxy

    # HECS/HELP: reduce usable monthly capacity a little (simple proxy)
    hecs_proxy = 0.0
    if inp.hecs_help_debt:
        hecs_proxy = 0.02 * monthly_gross  # simple conservative haircut
        warnings.append("HECS/HELP included as a conservative income haircut (proxy).")

    # 5) Use only part of leftover cashflow for repayments
    net_capacity = monthly_gross - expenses - dependant_buffer - debt_pmts - hecs_proxy

    if net_capacity <= 0:
        warnings.append("Your inputs leave little to no monthly surplus after expenses and debts.")
        return 0.0, 0.0, _assumptions_dict(inp, expenses, dependant_buffer, cc_proxy, shade, hecs_proxy), warnings

    # Banks include buffers. We apply a conservative buffer by limiting max repayment usage.
    max_repayment = net_capacity * 0.70

    # 6) Compute max principal from max repayment using interest rate/term
    principal = implied_principal_from_payment(max_repayment, inp.interest_rate_pct, inp.term_years)
    repay = monthly_payment(principal, inp.interest_rate_pct, inp.term_years)

    # Basic warning flags
    if inp.credit_card_limit_aud >= 15000:
        warnings.append("High credit card limits can reduce borrowing power even if unused.")
    if expenses >= 5000:
        warnings.append("Higher living expenses materially reduce borrowing power.")
    if inp.employment_type in ("Casual", "Self-employed"):
        warnings.append("Some lenders assess variable income more conservatively.")

    return float(principal), float(repay), _assumptions_dict(inp, expenses, dependant_buffer, cc_proxy, shade, hecs_proxy), warnings


def _assumptions_dict(
    inp: CalcInputs,
    expenses: float,
    dependant_buffer: float,
    cc_proxy: float,
    shade: float,
    hecs_proxy: float,
) -> Dict:
    return {
        "income_annual_aud": inp.income_annual_aud,
        "employment_type": inp.employment_type,
        "income_shading_factor": shade,
        "dependants": inp.dependants,
        "expense_mode": inp.expense_mode,
        "monthly_expenses_used_aud": expenses,
        "dependant_buffer_aud": dependant_buffer,
        "credit_card_limit_aud": inp.credit_card_limit_aud,
        "credit_card_assessed_monthly_aud": cc_proxy,
        "personal_loan_monthly_aud": inp.personal_loan_monthly_aud,
        "car_loan_monthly_aud": inp.car_loan_monthly_aud,
        "hecs_help_debt": inp.hecs_help_debt,
        "hecs_income_haircut_proxy_aud": hecs_proxy,
        "interest_rate_pct": inp.interest_rate_pct,
        "term_years": inp.term_years,
        "repayment_utilisation_ratio": 0.70,
    }