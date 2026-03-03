from __future__ import annotations

from typing import Any, Dict
import json
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"


SYSTEM = """You are a data extraction assistant for an Australian loan comparison app.
Extract the user's message into a STRICT JSON object that matches this schema:

{
  "income_annual_aud": number,
  "employment_type": "Full-time|Part-time|Casual|Self-employed",
  "dependants": integer,
  "expense_mode": "Basic|Typical|High",
  "monthly_expenses_aud": number|null,
  "debts": {
    "credit_card_limit_aud": number,
    "personal_loan_monthly_aud": number,
    "car_loan_monthly_aud": number,
    "hecs_help_debt": boolean
  }
}

Rules:
- If a value is missing, use reasonable defaults:
  employment_type="Full-time", dependants=0, expense_mode="Typical", monthly_expenses_aud=null,
  debts all 0, hecs_help_debt=false.
- Output JSON ONLY (no markdown, no extra text).
"""


def extract_profile(message: str, model: str = "llama3.1:8b", timeout_s: int = 60) -> Dict[str, Any]:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": message},
        ],
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=timeout_s)
    r.raise_for_status()
    content = r.json()["message"]["content"].strip()

    # Robust: try parse JSON even if model adds stray text
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # attempt to extract JSON substring
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start:end+1])
        raise