from __future__ import annotations

from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Customer, Loan
from .serializers import (
    RegisterCustomerRequestSerializer,
    CustomerResponseSerializer,
    CheckEligibilityRequestSerializer,
    CheckEligibilityResponseSerializer,
    CreateLoanRequestSerializer,
    CreateLoanResponseSerializer,
    ViewLoanResponseSerializer,
    ViewLoansByCustomerItemSerializer,
)
from .services import round_to_nearest_lakh, calculate_emi, assess_creditworthiness


@api_view(["POST"])
def register(request):
    serializer = RegisterCustomerRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    monthly_income = Decimal(data["monthly_income"])
    approved_limit = round_to_nearest_lakh(monthly_income * Decimal("36"))

    next_id = (Customer.objects.order_by("-id").first().id + 1) if Customer.objects.exists() else 1

    customer = Customer.objects.create(
        id=next_id,
        first_name=data["first_name"],
        last_name=data["last_name"],
        age=data["age"],
        monthly_salary=monthly_income,
        approved_limit=approved_limit,
        phone_number=data["phone_number"],
    )

    response_serializer = CustomerResponseSerializer(customer)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def check_eligibility(request):
    serializer = CheckEligibilityRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    customer = get_object_or_404(Customer, pk=data["customer_id"])
    loan_amount = Decimal(data["loan_amount"])
    interest_rate = Decimal(data["interest_rate"])
    tenure = int(data["tenure"])

    assessment = assess_creditworthiness(
        customer=customer,
        requested_amount=loan_amount,
        requested_interest_rate=interest_rate,
        tenure_months=tenure,
    )

    corrected_interest_rate = interest_rate
    if assessment.min_allowed_interest_rate > interest_rate:
        corrected_interest_rate = assessment.min_allowed_interest_rate

    emi = calculate_emi(loan_amount, corrected_interest_rate, tenure)

    response = {
        "customer_id": customer.id,
        "approval": assessment.eligible,
        "interest_rate": float(interest_rate),
        "corrected_interest_rate": float(corrected_interest_rate),
        "tenure": tenure,
        "monthly_installment": float(emi),
    }
    response_serializer = CheckEligibilityResponseSerializer(response)
    return Response(response_serializer.data)


@api_view(["POST"])
def create_loan(request):
    serializer = CreateLoanRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    customer = get_object_or_404(Customer, pk=data["customer_id"])
    loan_amount = Decimal(data["loan_amount"])
    interest_rate = Decimal(data["interest_rate"])
    tenure = int(data["tenure"])

    assessment = assess_creditworthiness(
        customer=customer,
        requested_amount=loan_amount,
        requested_interest_rate=interest_rate,
        tenure_months=tenure,
    )

    corrected_interest_rate = interest_rate
    if assessment.min_allowed_interest_rate > interest_rate:
        corrected_interest_rate = assessment.min_allowed_interest_rate

    if not assessment.eligible:
        emi = calculate_emi(loan_amount, corrected_interest_rate, tenure)
        response = {
            "loan_id": None,
            "customer_id": customer.id,
            "loan_approved": False,
            "message": assessment.rejection_reason or "Loan not approved",
            "monthly_installment": float(emi),
        }
        response_serializer = CreateLoanResponseSerializer(response)
        return Response(response_serializer.data, status=status.HTTP_400_BAD_REQUEST)

    emi = calculate_emi(loan_amount, corrected_interest_rate, tenure)

    from datetime import date, timedelta

    start_date = date.today()
    end_date = start_date + timedelta(days=30 * tenure)

    loan = Loan.objects.create(
        customer=customer,
        loan_amount=loan_amount,
        tenure=tenure,
        interest_rate=corrected_interest_rate,
        monthly_installment=emi,
        emis_paid_on_time=0,
        start_date=start_date,
        end_date=end_date,
    )

    response = {
        "loan_id": loan.id,
        "customer_id": customer.id,
        "loan_approved": True,
        "message": "Loan approved",
        "monthly_installment": float(emi),
    }
    response_serializer = CreateLoanResponseSerializer(response)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def view_loan(request, loan_id: int):
    loan = get_object_or_404(Loan.objects.select_related("customer"), pk=loan_id)
    serializer = ViewLoanResponseSerializer(loan)
    return Response(serializer.data)


@api_view(["GET"])
def view_loans_by_customer(request, customer_id: int):
    loans = Loan.objects.filter(customer_id=customer_id)
    serializer = ViewLoansByCustomerItemSerializer(loans, many=True)
    return Response(serializer.data)

