from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
from celery import shared_task
from django.conf import settings
from django.db import transaction

from .models import Customer, Loan
from .services import calculate_emi


@shared_task
def ingest_initial_data() -> None:
    data_dir = Path(settings.INITIAL_DATA_DIR)
    customer_path = data_dir / "customer_data.xlsx"
    loan_path = data_dir / "loan_data.xlsx"

    if not customer_path.exists() or not loan_path.exists():
        return

    with transaction.atomic():
        customers_df = pd.read_excel(customer_path)
        for _, row in customers_df.iterrows():
            customer_id = int(row["customer_id"])
            monthly_salary = Decimal(str(row["monthly_salary"]))
            approved_limit = Decimal(str(row["approved_limit"]))
            current_debt = Decimal(str(row.get("current_debt", 0)))

            Customer.objects.update_or_create(
                id=customer_id,
                defaults={
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "phone_number": str(row["phone_number"]),
                    "monthly_salary": monthly_salary,
                    "approved_limit": approved_limit,
                    "current_debt": current_debt,
                },
            )

        loans_df = pd.read_excel(loan_path)
        for _, row in loans_df.iterrows():
            customer_id = int(row["customer id"])
            tenure = int(row["tenure"])
            loan_amount = Decimal(str(row["loan amount"]))
            interest_rate = Decimal(str(row["interest rate"]))
            start_date = pd.to_datetime(row["start date"]).date()
            end_date = pd.to_datetime(row["end date"]).date()

            customer = Customer.objects.get(id=customer_id)

            monthly_repayment = Decimal(str(row.get("monthly repayment (emi)", 0))) or calculate_emi(
                loan_amount, interest_rate, tenure
            )

            Loan.objects.update_or_create(
                id=int(row["loan id"]),
                defaults={
                    "customer": customer,
                    "loan_amount": loan_amount,
                    "tenure": tenure,
                    "interest_rate": interest_rate,
                    "monthly_installment": monthly_repayment,
                    "emis_paid_on_time": int(row.get("EMIs paid on time", 0)),
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )

