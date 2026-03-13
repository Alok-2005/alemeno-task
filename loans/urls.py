from django.urls import path

from . import views

urlpatterns = [
    path("register", views.register, name="register"),
    path("check-eligibility", views.check_eligibility, name="check-eligibility"),
    path("create-loan", views.create_loan, name="create-loan"),
    path("view-loan/<int:loan_id>", views.view_loan, name="view-loan"),
    path("view-loans/<int:customer_id>", views.view_loans_by_customer, name="view-loans-by-customer"),
]

