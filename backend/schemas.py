from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DebtProfile(BaseModel):
    credit_card_limit_aud: float = 0.0
    personal_loan_monthly_aud: float = 0.0
    car_loan_monthly_aud: float = 0.0
    hecs_help_debt: bool = False


class BorrowerProfile(BaseModel):
    income_annual_aud: float = Field(..., ge=0)
    employment_type: str = Field(
        default="Full-time",
        description="Full-time, Part-time, Casual, Self-employed",
    )
    dependants: int = Field(default=0, ge=0)

    # Expenses
    expense_mode: str = Field(default="Typical", description="Basic, Typical, High")
    monthly_expenses_aud: Optional[float] = Field(default=None, ge=0)

    debts: DebtProfile = Field(default_factory=DebtProfile)


class HomeLoanScenario(BaseModel):
    interest_rate_pct: float = Field(default=6.5, ge=0.0)
    term_years: int = Field(default=30, ge=1, le=40)
    owner_occupier: bool = True
    principal_and_interest: bool = True

    deposit_aud: float = Field(default=0.0, ge=0.0)
    property_price_aud: Optional[float] = Field(default=None, ge=0.0)


class CarLoanScenario(BaseModel):
    interest_rate_pct: float = Field(default=9.5, ge=0.0)
    term_years: int = Field(default=5, ge=1, le=10)
    amount_aud: float = Field(default=20000.0, ge=0.0)
    secured: bool = True


class EstimateRequest(BaseModel):
    profile: BorrowerProfile
    scenario_home: Optional[HomeLoanScenario] = None
    scenario_car: Optional[CarLoanScenario] = None


class BorrowingEstimate(BaseModel):
    borrowing_power_aud: float
    monthly_repayment_aud: float
    assumptions: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)


class LenderOffer(BaseModel):
    lender: str
    product: str
    rate_pct: float
    comparison_rate_pct: Optional[float] = None
    monthly_repayment_aud: float
    upfront_fees_aud: float = 0.0
    ongoing_fees_aud_per_year: float = 0.0
    features: List[str] = Field(default_factory=list)

    score: float = 0.0
    reasons: List[str] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)


class CompareResponse(BaseModel):
    estimate: BorrowingEstimate
    offers: List[LenderOffer]
    sources_last_updated: Optional[str] = None


class ProfileExtractRequest(BaseModel):
    message: str
    model: str = "llama3.1:8b"


class ExplainRequest(BaseModel):
    model: str = "llama3.1:8b"
    profile: BorrowerProfile
    estimate: BorrowingEstimate
    top_offers: List[LenderOffer]
    user_question: Optional[str] = None


class ExplainResponse(BaseModel):
    explanation: str
    model: str