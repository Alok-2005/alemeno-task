from __future__ import annotations

from decimal import Decimal

from django.db import models


class Customer(models.Model):
    id = models.IntegerField(primary_key=True)  # maps to customer_id from Excel / API
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, unique=True)
    age = models.IntegerField(null=True, blank=True)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2)
    approved_limit = models.DecimalField(max_digits=12, decimal_places=2)
    current_debt = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )

    class Meta:
        db_table = "customer"

    def __str__(self) -> str:
        return f"{self.id} - {self.first_name} {self.last_name}"


class Loan(models.Model):
    id = models.AutoField(primary_key=True)  # loan_id
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="loans")
    loan_amount = models.DecimalField(max_digits=14, decimal_places=2)
    tenure = models.IntegerField(help_text="Tenure in months")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Annual interest rate in percent")
    monthly_installment = models.DecimalField(max_digits=14, decimal_places=2)
    emis_paid_on_time = models.IntegerField(default=0)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        db_table = "loan"

    def __str__(self) -> str:
        return f"Loan {self.id} for customer {self.customer_id}"

