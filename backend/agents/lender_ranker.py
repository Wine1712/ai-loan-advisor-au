from __future__ import annotations

from typing import List, Dict, Any, Tuple
from pathlib import Path
import json

from .calculator import monthly_payment


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_lenders_home() -> Dict[str, Any]:
    path = DATA_DIR / "lenders_home.json"
    if not path.exists():
        return {"last_updated": None, "lenders": []}
    return json.loads(path.read_text(encoding="utf-8"))


def load_lenders_car() -> Dict[str, Any]:
    path = DATA_DIR / "lenders_car.json"
    if not path.exists():
        return {"last_updated": None, "lenders": []}
    return json.loads(path.read_text(encoding="utf-8"))


def score_offer(
    rate_pct: float,
    upfront_fees: float,
    ongoing_fees_per_year: float,
    features: List[str],
    profile_flags: Dict[str, Any],
) -> Tuple[float, List[str]]:
    """
    Simple transparent scoring:
    - Lower rate -> better
    - Lower fees -> better
    - Features add small boosts based on user needs
    """
    reasons: List[str] = []

    # Base score starts from 100 and subtract penalties
    score = 100.0

    # Rate penalty (scaled)
    score -= max(rate_pct - 4.0, 0.0) * 8.0
    reasons.append(f"Rate impact: {rate_pct:.2f}%")

    # Fees penalty
    score -= min(upfront_fees / 50.0, 10.0)
    score -= min(ongoing_fees_per_year / 50.0, 10.0)
    if upfront_fees > 0:
        reasons.append(f"Upfront fees: ${upfront_fees:,.0f}")
    if ongoing_fees_per_year > 0:
        reasons.append(f"Ongoing fees: ${ongoing_fees_per_year:,.0f}/yr")

    # Feature boosts
    fset = {f.lower() for f in features}
    if profile_flags.get("wants_offset", False) and "offset" in fset:
        score += 4.0
        reasons.append("Has offset (matches your preference).")
    if profile_flags.get("wants_redraw", True) and "redraw" in fset:
        score += 2.0
        reasons.append("Has redraw flexibility.")

    # Employment caution (small penalty if lender “strict”)
    if profile_flags.get("employment_type") in ("Casual", "Self-employed") and "flexible_income" in fset:
        score += 2.0
        reasons.append("Marked as flexible for variable income.")
    elif profile_flags.get("employment_type") in ("Casual", "Self-employed") and "strict_income" in fset:
        score -= 3.0
        reasons.append("May be stricter for variable income.")

    return max(score, 0.0), reasons


def build_home_offers(
    borrowing_power_aud: float,
    term_years: int,
    lenders_payload: Dict[str, Any],
    profile_flags: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], str | None]:
    lenders = lenders_payload.get("lenders", [])
    last_updated = lenders_payload.get("last_updated")

    offers: List[Dict[str, Any]] = []
    for item in lenders:
        rate = float(item.get("rate_pct", 0.0))
        product = item.get("product", "Home loan")
        upfront = float(item.get("upfront_fees_aud", 0.0))
        ongoing = float(item.get("ongoing_fees_aud_per_year", 0.0))
        features = list(item.get("features", []))
        sources = list(item.get("source_urls", []))
        comp = item.get("comparison_rate_pct")
        comp = float(comp) if comp is not None else None

        repay = monthly_payment(borrowing_power_aud, rate, term_years)
        score, reasons = score_offer(rate, upfront, ongoing, features, profile_flags)

        offers.append({
            "lender": item.get("lender", "Unknown"),
            "product": product,
            "rate_pct": rate,
            "comparison_rate_pct": comp,
            "monthly_repayment_aud": float(repay),
            "upfront_fees_aud": upfront,
            "ongoing_fees_aud_per_year": ongoing,
            "features": features,
            "score": float(score),
            "reasons": reasons,
            "source_urls": sources,
        })

    offers.sort(key=lambda x: (-x["score"], x["monthly_repayment_aud"]))
    return offers, last_updated