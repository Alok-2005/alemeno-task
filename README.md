## Credit Approval System – Backend Assignment

This is my backend assignment for a **credit approval system**.  
I have built it in **Django + Django REST Framework**, with **PostgreSQL**, **Celery**, **Redis**, and everything is run using **Docker Compose**.

### What this project does

- Reads two Excel files:
  - `customer_data.xlsx`
  - `loan_data.xlsx`
- A Celery background worker loads this data into Postgres.
- Exposes REST APIs to:
  - register customers,
  - check loan eligibility,
  - create a loan,
  - and view loans.

### Tech stack (short)

- **Backend**: Django 4, Django REST Framework  
- **DB**: PostgreSQL  
- **Async / background**: Celery + Redis  
- **Container**: Docker & Docker Compose  

### Project structure (main folders/files)

- `credit_approval/` – Django project (settings, URLs, Celery config)
- `loans/` – Main app (models, services, Celery tasks, API views)
- `manage.py` – Django entrypoint
- `requirements.txt` – Python dependencies
- `Dockerfile` – Image for Django app + Celery worker
- `docker-compose.yml` – Runs web, worker, Postgres, Redis
- `data/` – Folder where the Excel files go:
  - `data/customer_data.xlsx`
  - `data/loan_data.xlsx`

### How to run (with Docker)

1. Make sure **Docker** and **Docker Compose** are installed.
2. In the project root, create a `data` folder and copy:
   - `customer_data.xlsx` → `data/customer_data.xlsx`
   - `loan_data.xlsx` → `data/loan_data.xlsx`
3. Build and start everything:

```bash
docker-compose up --build
```

4. In another terminal, run migrations inside the `web` container:

```bash
docker-compose exec web python manage.py migrate
```

5. Load the initial Excel data (Celery worker will process it):

```bash
docker-compose exec web python -c "from loans.tasks import ingest_initial_data; ingest_initial_data.delay()"
```

After this, the worker reads from `/data` (mapped from `./data`) and fills the `Customer` and `Loan` tables.

### APIs I have implemented

Base URL (default when running with Docker): `http://localhost:8000/api/`

- **`POST /api/register`**  
  - Registers a new customer.  
  - Request:
    - `first_name`, `last_name`, `age`, `monthly_income`, `phone_number`  
  - Logic:
    - Calculates `approved_limit = 36 * monthly_income` and rounds to nearest lakh.  
  - Response:
    - Basic customer details + `approved_limit`.

- **`POST /api/check-eligibility`**  
  - Checks if a loan is eligible for a given customer.  
  - Request:
    - `customer_id`, `loan_amount`, `interest_rate`, `tenure` (months)  
  - Logic (high level):
    - Builds a **credit score (0–100)** from past loan data:
      - on-time EMI history,
      - number of past loans,
      - current-year loan activity,
      - approved loan volume vs income,
      - if sum of current loans goes beyond approved limit, marks credit score as 0.  
    - Applies rules:
      - If score > 50 → approve with given (or higher) rate.
      - If 50 ≥ score > 30 → approve only if rate ≥ 12%.
      - If 30 ≥ score > 10 → approve only if rate ≥ 16%.
      - If score ≤ 10 → reject.
      - If total EMIs of all current loans > 50% of monthly salary → reject.  
    - If requested rate is lower than allowed slab, returns a `corrected_interest_rate`.  
    - EMI is calculated using the standard EMI formula.
  - Response:
    - `customer_id`, `approval`, `interest_rate`, `corrected_interest_rate`, `tenure`, `monthly_installment`.

- **`POST /api/create-loan`**  
  - Creates a loan for the customer (reuses same eligibility rules).  
  - Request:
    - `customer_id`, `loan_amount`, `interest_rate`, `tenure` (months).  
  - Behavior:
    - Re-checks credit score and rules.
    - If not eligible:
      - `loan_id = null`, `loan_approved = false` with a message.  
    - If eligible:
      - Creates a `Loan` record with:
        - (Possibly) corrected interest rate,
        - EMI using the EMI formula,
        - `start_date = today`,
        - `end_date = today + tenure * 30 days`.  
  - Response:
    - `loan_id`, `customer_id`, `loan_approved`, `message`, `monthly_installment`.

- **`GET /api/view-loan/<loan_id>`**  
  - Returns full details of one loan and its customer.  
  - Response includes:
    - `loan_id`,
    - customer basic info,
    - `loan_amount`, `interest_rate`, `monthly_installment`, `tenure`.

- **`GET /api/view-loans/<customer_id>`**  
  - Returns all **current loans** for a customer.  
  - Each list item has:
    - `loan_id`, `loan_amount`, `interest_rate`, `monthly_installment`, `repayments_left`.

### Short notes

- `customer_id` is the primary key of the `Customer` model.
- `approved_limit` is calculated as `36 * monthly_salary` and then rounded to nearest lakh (as per assignment).
- Credit scoring combines multiple factors into a score out of 100 (details are in `loans/services.py`).
- Initial Excel ingestion is handled by a Celery task: `loans.tasks.ingest_initial_data`.

