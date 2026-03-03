from __future__ import annotations

import streamlit as st
import requests
import pandas as pd

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Loan Advisor AU", page_icon="🏦", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
.kpi-card {
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 16px;
  padding: 16px 18px;
  background: rgba(255,255,255,0.7);
}
.small-muted {color: rgba(0,0,0,0.55); font-size: 0.9rem;}
</style>
""", unsafe_allow_html=True)

st.title("🏦 AI Loan Advisor (Australia)")
st.caption("Runs locally with Ollama + FastAPI. Educational estimates only — not financial advice.")

# Sidebar inputs
with st.sidebar:
    st.header("Your Profile")

    mode = st.radio("Input mode", ["Manual", "Chat → Extract (Ollama)"], horizontal=False)

    if mode == "Chat → Extract (Ollama)":
        msg = st.text_area(
            "Describe your situation (income, debts, dependants, expenses).",
            height=140,
            placeholder="Example: I earn 95k, casual, 1 dependant, credit card limit 10k, car loan 400/month, HECS yes..."
        )
        model = st.text_input("Ollama model", value="llama3.1:8b")
        if st.button("Extract profile with Ollama"):
            if not msg.strip():
                st.warning("Please enter a message.")
            else:
                r = requests.post(f"{API_BASE}/profile/extract", json={"message": msg, "model": model}, timeout=90)
                if r.ok:
                    st.session_state["profile"] = r.json()
                    st.success("Profile extracted.")
                else:
                    st.error(r.text)

    profile = st.session_state.get("profile", {})

    income = st.number_input("Annual income (AUD)", min_value=0, value=int(profile.get("income_annual_aud", 90000)), step=1000)
    employment = st.selectbox("Employment type", ["Full-time", "Part-time", "Casual", "Self-employed"],
                             index=["Full-time","Part-time","Casual","Self-employed"].index(profile.get("employment_type","Full-time")))

    dependants = st.number_input("Dependants", min_value=0, value=int(profile.get("dependants", 0)), step=1)

    st.divider()
    st.subheader("Debts")
    debts = profile.get("debts", {}) if isinstance(profile.get("debts", {}), dict) else {}
    cc_limit = st.number_input("Credit card limit total (AUD)", min_value=0, value=int(debts.get("credit_card_limit_aud", 5000)), step=500)
    personal_monthly = st.number_input("Personal loan monthly repayment (AUD)", min_value=0, value=int(debts.get("personal_loan_monthly_aud", 0)), step=50)
    car_monthly = st.number_input("Car loan monthly repayment (AUD)", min_value=0, value=int(debts.get("car_loan_monthly_aud", 0)), step=50)
    hecs = st.toggle("HECS/HELP debt", value=bool(debts.get("hecs_help_debt", False)))

    st.divider()
    st.subheader("Living expenses")
    expense_mode = st.radio("Expense assumption", ["Basic", "Typical", "High"],
                            index=["Basic","Typical","High"].index(profile.get("expense_mode","Typical")),
                            horizontal=True)
    override = st.toggle("Manually set monthly expenses", value=profile.get("monthly_expenses_aud") is not None)
    monthly_expenses = None
    if override:
        monthly_expenses = st.slider("Monthly expenses (AUD)", 1000, 10000, int(profile.get("monthly_expenses_aud", 3500)), 100)

    st.divider()
    st.subheader("Home loan settings")
    term_years = st.slider("Term (years)", 5, 35, 30, 1)
    rate_pct = st.slider("Rate assumption (%)", 3.0, 10.0, 6.5, 0.1)

# Build request payload
payload = {
    "profile": {
        "income_annual_aud": income,
        "employment_type": employment,
        "dependants": dependants,
        "expense_mode": expense_mode,
        "monthly_expenses_aud": monthly_expenses,
        "debts": {
            "credit_card_limit_aud": cc_limit,
            "personal_loan_monthly_aud": personal_monthly,
            "car_loan_monthly_aud": car_monthly,
            "hecs_help_debt": hecs,
        }
    },
    "scenario_home": {
        "interest_rate_pct": rate_pct,
        "term_years": term_years,
        "owner_occupier": True,
        "principal_and_interest": True,
        "deposit_aud": 0.0,
        "property_price_aud": None,
    }
}

tabs = st.tabs(["🏠 Estimate", "📊 Compare lenders", "🧠 Explanation"])

with tabs[0]:
    st.subheader("Home loan estimate")

    if st.button("Run estimate"):
        r = requests.post(f"{API_BASE}/estimate/home", json=payload, timeout=60)
        if r.ok:
            est = r.json()
            st.session_state["estimate"] = est
        else:
            st.error(r.text)

    est = st.session_state.get("estimate")
    if est:
        col1, col2 = st.columns(2, gap="large")
        with col1:
            st.markdown(f"""
            <div class="kpi-card">
              <div class="small-muted">Estimated borrowing power</div>
              <div style="font-size: 2.1rem; font-weight: 800;">${est["borrowing_power_aud"]:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="kpi-card">
              <div class="small-muted">Estimated monthly repayment</div>
              <div style="font-size: 2.1rem; font-weight: 800;">${est["monthly_repayment_aud"]:,.0f}</div>
              <div class="small-muted">{term_years} years @ {rate_pct:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

        if est.get("warnings"):
            st.divider()
            st.subheader("Notes")
            for w in est["warnings"]:
                st.info(w)

        with st.expander("Show assumptions used"):
            st.json(est.get("assumptions", {}))
    else:
        st.info("Click **Run estimate** to calculate borrowing power.")

with tabs[1]:
    st.subheader("Compare lenders (demo data from `data/lenders_home.json`)")

    if st.button("Run comparison"):
        r = requests.post(f"{API_BASE}/compare/home", json=payload, timeout=60)
        if r.ok:
            st.session_state["compare"] = r.json()
        else:
            st.error(r.text)

    comp = st.session_state.get("compare")
    if comp:
        est = comp["estimate"]
        st.write(f"Sources last updated: **{comp.get('sources_last_updated')}**")

        offers = comp["offers"]
        df = pd.DataFrame([{
            "Lender": o["lender"],
            "Product": o["product"],
            "Rate %": o["rate_pct"],
            "Comparison %": o.get("comparison_rate_pct"),
            "Monthly repayment": o["monthly_repayment_aud"],
            "Upfront fees": o["upfront_fees_aud"],
            "Ongoing fees/yr": o["ongoing_fees_aud_per_year"],
            "Score": o["score"],
            "Features": ", ".join(o.get("features", []))
        } for o in offers])

        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Top 3 (cards)")
        cols = st.columns(3)
        for i in range(min(3, len(offers))):
            o = offers[i]
            with cols[i]:
                st.markdown(f"""
                <div class="kpi-card">
                  <div style="font-weight:800; font-size: 1.1rem;">{o["lender"]}</div>
                  <div class="small-muted">{o["product"]}</div>
                  <hr/>
                  <div><b>Rate:</b> {o["rate_pct"]:.2f}%</div>
                  <div><b>Repayment:</b> ${o["monthly_repayment_aud"]:,.0f}/mo</div>
                  <div><b>Score:</b> {o["score"]:.1f}</div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander("Why this scored well"):
                    for r_ in o.get("reasons", []):
                        st.write("- " + r_)
                    if o.get("source_urls"):
                        st.write("Sources:")
                        for s in o["source_urls"]:
                            st.write("- " + s)
    else:
        st.info("Click **Run comparison** to view lender ranking.")

with tabs[2]:
    st.subheader("AI explanation (Ollama)")

    model = st.text_input("Ollama model for explanation", value="llama3.1:8b", key="explain_model")
    question = st.text_input("Optional: Ask a question", value="How can I improve my borrowing power?")

    if st.button("Generate explanation"):
        comp = st.session_state.get("compare")
        est = st.session_state.get("estimate")

        if not est:
            st.warning("Run an estimate first.")
        else:
            top_offers = (comp["offers"][:3] if comp else [])
            req = {
                "model": model,
                "profile": payload["profile"],
                "estimate": est,
                "top_offers": top_offers,
                "user_question": question.strip() or None,
            }
            r = requests.post(f"{API_BASE}/explain", json=req, timeout=90)
            if r.ok:
                st.session_state["explain"] = r.json()
            else:
                st.error(r.text)

    ex = st.session_state.get("explain")
    if ex:
        st.markdown(ex["explanation"])
    else:
        st.info("Generate an explanation after running estimate/compare.")