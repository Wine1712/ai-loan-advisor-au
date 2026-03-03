from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import (
    EstimateRequest,
    BorrowingEstimate,
    CompareResponse,
    ProfileExtractRequest,
    ExplainRequest,
    ExplainResponse,
    BorrowerProfile,
    HomeLoanScenario,
    LenderOffer,
)
from backend.agents.calculator import CalcInputs, estimate_borrowing_power
from backend.agents.lender_ranker import load_lenders_home, build_home_offers
from backend.agents.profile_agent import extract_profile
from backend.agents.explain_agent import build_explanation


app = FastAPI(title="AI Loan Advisor AU", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


def _to_calc_inputs(req: EstimateRequest) -> CalcInputs:
    prof = req.profile
    home = req.scenario_home or HomeLoanScenario()

    return CalcInputs(
        income_annual_aud=prof.income_annual_aud,
        employment_type=prof.employment_type,
        dependants=prof.dependants,
        expense_mode=prof.expense_mode,
        monthly_expenses_aud=prof.monthly_expenses_aud,
        credit_card_limit_aud=prof.debts.credit_card_limit_aud,
        personal_loan_monthly_aud=prof.debts.personal_loan_monthly_aud,
        car_loan_monthly_aud=prof.debts.car_loan_monthly_aud,
        hecs_help_debt=prof.debts.hecs_help_debt,
        interest_rate_pct=home.interest_rate_pct,
        term_years=home.term_years,
    )


@app.post("/profile/extract", response_model=BorrowerProfile)
def api_extract_profile(req: ProfileExtractRequest):
    try:
        data = extract_profile(req.message, model=req.model)
        # Validate through Pydantic
        return BorrowerProfile(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Profile extraction failed: {e}")


@app.post("/estimate/home", response_model=BorrowingEstimate)
def estimate_home(req: EstimateRequest):
    try:
        inp = _to_calc_inputs(req)
        borrowing, repayment, assumptions, warnings = estimate_borrowing_power(inp)
        return BorrowingEstimate(
            borrowing_power_aud=borrowing,
            monthly_repayment_aud=repayment,
            assumptions=assumptions,
            warnings=warnings,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Estimate failed: {e}")


@app.post("/compare/home", response_model=CompareResponse)
def compare_home(req: EstimateRequest):
    # 1) Estimate
    inp = _to_calc_inputs(req)
    borrowing, repayment, assumptions, warnings = estimate_borrowing_power(inp)
    estimate = BorrowingEstimate(
        borrowing_power_aud=borrowing,
        monthly_repayment_aud=repayment,
        assumptions=assumptions,
        warnings=warnings,
    )

    # 2) Offers
    lenders_payload = load_lenders_home()
    profile_flags = {
        "employment_type": req.profile.employment_type,
        "wants_offset": True,     # you can wire this to UI later
        "wants_redraw": True,
    }
    offers_raw, last_updated = build_home_offers(
        borrowing_power_aud=estimate.borrowing_power_aud,
        term_years=(req.scenario_home.term_years if req.scenario_home else 30),
        lenders_payload=lenders_payload,
        profile_flags=profile_flags,
    )
    offers = [LenderOffer(**o) for o in offers_raw]

    return CompareResponse(
        estimate=estimate,
        offers=offers[:10],
        sources_last_updated=last_updated,
    )


@app.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest):
    try:
        explanation = build_explanation(
            model=req.model,
            profile=req.profile.model_dump(),
            estimate=req.estimate.model_dump(),
            top_offers=[o.model_dump() for o in req.top_offers],
            user_question=req.user_question,
        )
        return ExplainResponse(explanation=explanation, model=req.model)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Explanation failed: {e}")