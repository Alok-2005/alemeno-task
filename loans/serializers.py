from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from .models import Customer, Loan


class RegisterCustomerRequestSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    age = serializers.IntegerField()
    monthly_income = serializers.IntegerField()
    phone_number = serializers.CharField(max_length=20)


class CustomerResponseSerializer(serializers.ModelSerializer):
    customer_id = serializers.IntegerField(source="id")
    name = serializers.SerializerMethodField()
    monthly_income = serializers.IntegerField(source="monthly_salary")

    class Meta:
        model = Customer
        fields = [
            "customer_id",
            "name",
            "age",
            "monthly_income",
            "approved_limit",
            "phone_number",
        ]

    def get_name(self, obj: Customer) -> str:
        return f"{obj.first_name} {obj.last_name}"


class CheckEligibilityRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tenure = serializers.IntegerField()


class CheckEligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    corrected_interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tenure = serializers.IntegerField()
    monthly_installment = serializers.DecimalField(max_digits=14, decimal_places=2)


class CreateLoanRequestSerializer(CheckEligibilityRequestSerializer):
    pass


class CreateLoanResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField()
    monthly_installment = serializers.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )


class CustomerEmbeddedSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")

    class Meta:
        model = Customer
        fields = ["id", "first_name", "last_name", "phone_number", "age"]


class ViewLoanResponseSerializer(serializers.ModelSerializer):
    loan_id = serializers.IntegerField(source="id")
    customer = CustomerEmbeddedSerializer()

    class Meta:
        model = Loan
        fields = [
            "loan_id",
            "customer",
            "loan_amount",
            "interest_rate",
            "monthly_installment",
            "tenure",
        ]


class ViewLoansByCustomerItemSerializer(serializers.ModelSerializer):
    loan_id = serializers.IntegerField(source="id")
    repayments_left = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            "loan_id",
            "loan_amount",
            "interest_rate",
            "monthly_installment",
            "repayments_left",
        ]

    def get_repayments_left(self, obj: Loan) -> int:
        return max(obj.tenure - obj.emis_paid_on_time, 0)

