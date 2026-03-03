from __future__ import annotations

from typing import Any, Dict, List, Optional
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"


def build_explanation(
    model: str,
    profile: Dict[str, Any],
    estimate: Dict[str, Any],
    top_offers: List[Dict[str, Any]],
    user_question: Optional[str] = None,
    timeout_s: int = 60,
) -> str:
    prompt = {
        "profile": profile,
        "estimate": estimate,
        "top_offers": top_offers[:3],
        "user_question": user_question,
    }

    system = """You are a helpful Australian loan comparison assistant.
Write a short, professional explanation (6-10 sentences) that:
- explains the borrowing estimate is an educational estimate (not financial advice),
- highlights the biggest factors affecting borrowing power (income, expenses, debts, credit card limits),
- explains why the top 3 offers scored well (rate/fees/features),
- suggests what to change to improve borrowing power,
- encourages verifying details on official lender pages.
No bullet spam. Keep it clear and practical.
"""

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": str(prompt)},
        ],
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=timeout_s)
    r.raise_for_status()
    return r.json()["message"]["content"].strip()