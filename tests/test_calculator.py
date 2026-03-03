from backend.agents.calculator import monthly_payment, implied_principal_from_payment


def test_monthly_payment_zero_rate():
    p = 120000
    pay = monthly_payment(p, 0.0, 10)
    assert abs(pay - (p / (10 * 12))) < 1e-6


def test_inverse_payment_principal_roundtrip():
    principal = 500000
    rate = 6.5
    years = 30

    pay = monthly_payment(principal, rate, years)
    principal2 = implied_principal_from_payment(pay, rate, years)

    # allow small numerical error
    assert abs(principal2 - principal) / principal < 1e-6