from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple

from django.db.models import Sum, Q, QuerySet

from .models import Customer, Loan


def round_to_nearest_lakh(amount: Decimal) -> Decimal:
    lakh = Decimal("100000")
    return (amount / lakh).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * lakh


def calculate_emi(
    principal: Decimal, annual_interest_rate_pct: Decimal, tenure_months: int
) -> Decimal:
    if tenure_months <= 0:
        return Decimal("0.00")
    monthly_rate = (annual_interest_rate_pct / Decimal("100")) / Decimal("12")
    if monthly_rate == 0:
        emi = principal / Decimal(tenure_months)
    else:
        one_plus_r_pow_n = (Decimal("1") + monthly_rate) ** tenure_months
        emi = principal * monthly_rate * one_plus_r_pow_n / (one_plus_r_pow_n - 1)
    return emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_active_loans(customer: Customer) -> QuerySet[Loan]:
    today = date.today()
    return customer.loans.filter(Q(end_date__gte=today))


def current_monthly_emi_burden(customer: Customer) -> Decimal:
    result = (
        get_active_loans(customer).aggregate(total=Sum("monthly_installment")).get("total")
        or Decimal("0.00")
    )
    return result


@dataclass
class CreditAssessment:
    credit_score: int
    eligible: bool
    min_allowed_interest_rate: Decimal
    rejection_reason: str | None = None


def assess_creditworthiness(
    customer: Customer,
    requested_amount: Decimal,
    requested_interest_rate: Decimal,
    tenure_months: int,
) -> CreditAssessment:
    loans = Loan.objects.filter(customer=customer)

    if not loans.exists():
        base_score = 50
    else:
        base_score = 0

        on_time_scores = []
        for loan in loans:
            if loan.tenure > 0:
                ratio = Decimal(loan.emis_paid_on_time) / Decimal(loan.tenure)
                on_time_scores.append(max(min(ratio, Decimal("1.0")), Decimal("0.0")))
        if on_time_scores:
            on_time_component = sum(on_time_scores) / Decimal(len(on_time_scores))
            base_score += int(on_time_component * 40)

        loan_count = loans.count()
        if loan_count <= 2:
            base_score += 20
        elif loan_count <= 5:
            base_score += 10
        else:
            base_score += 0

        current_year = date.today().year
        current_year_loans = loans.filter(start_date__year=current_year).count()
        if current_year_loans == 0:
            base_score += 10
        elif current_year_loans <= 2:
            base_score += 5

        total_volume = (
            loans.aggregate(total=Sum("loan_amount")).get("total") or Decimal("0.00")
        )
        income = customer.monthly_salary * Decimal("12")
        if income > 0:
            ratio = total_volume / income
            if ratio <= Decimal("0.5"):
                base_score += 20
            elif ratio <= Decimal("1.0"):
                base_score += 10

    current_active_loans = get_active_loans(customer)
    current_principal_sum = (
        current_active_loans.aggregate(total=Sum("loan_amount")).get("total")
        or Decimal("0.00")
    )
    if current_principal_sum > customer.approved_limit:
        return CreditAssessment(
            credit_score=0,
            eligible=False,
            min_allowed_interest_rate=Decimal("0.00"),
            rejection_reason="Current active loans exceed approved limit",
        )

    score = max(min(base_score, 100), 0)

    if score > 50:
        min_rate = Decimal("0.00")
        eligible = True
    elif 30 < score <= 50:
        min_rate = Decimal("12.00")
        eligible = True
    elif 10 < score <= 30:
        min_rate = Decimal("16.00")
        eligible = True
    else:
        min_rate = Decimal("0.00")
        eligible = False

    emi_burden = current_monthly_emi_burden(customer)
    prospective_emi = calculate_emi(requested_amount, max(requested_interest_rate, min_rate), tenure_months)
    total_emi_after_loan = emi_burden + prospective_emi
    if customer.monthly_salary > 0 and total_emi_after_loan > customer.monthly_salary * Decimal("0.5"):
        return CreditAssessment(
            credit_score=score,
            eligible=False,
            min_allowed_interest_rate=min_rate,
            rejection_reason="Total EMIs would exceed 50% of monthly salary",
        )

    return CreditAssessment(
        credit_score=score,
        eligible=eligible,
        min_allowed_interest_rate=min_rate,
        rejection_reason=None,
    )

