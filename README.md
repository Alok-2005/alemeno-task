## Credit Approval System (Backend Internship Assignment)

**Stack**: Django 4, Django REST Framework, PostgreSQL, Celery, Redis, Docker & Docker Compose.

### Project overview

- Implements a **credit approval system** using:
  - `customer_data.xlsx` and `loan_data.xlsx` ingested by a **Celery background worker**
  - A PostgreSQL database (via Docker)
  - REST APIs with Django REST Framework
- All services (web app, worker, DB, Redis) are **dockerized** and run via a single `docker-compose up` command.

### Folder layout (important files)

- `manage.py` – Django entrypoint
- `credit_approval/` – Django project (settings, URLs, Celery config)
- `loans/` – Main app (models, services, tasks, API views)
- `requirements.txt` – Python dependencies
- `Dockerfile` – Image for Django app and Celery worker
- `docker-compose.yml` – Orchestrates web, worker, Postgres, Redis
- `data/` – **Place your Excel files here**:
  - `data/customer_data.xlsx`
  - `data/loan_data.xlsx`

### Running locally with Docker

1. **Ensure Docker & Docker Compose are installed.**
2. Create a `data` folder next to `docker-compose.yml` and copy:
   - `customer_data.xlsx` → `data/customer_data.xlsx`
   - `loan_data.xlsx` → `data/loan_data.xlsx`
3. Build and start all services:

```bash
docker-compose up --build
```

4. Apply migrations in another terminal (inside the `web` container):

```bash
docker-compose exec web python manage.py migrate
```

5. Trigger initial data ingestion (runs via Celery worker):

```bash
docker-compose exec web python -c "from loans.tasks import ingest_initial_data; ingest_initial_data.delay()"
```

The worker reads the Excel files from `/data` (mapped from `./data`) and populates `Customer` and `Loan` tables.

### Available API endpoints (all under `/api/`)

Base URL (Docker default): `http://localhost:8000/api/`

- **`POST /api/register`**
  - Registers a new customer.
  - Request body:
    - `first_name` (string)
    - `last_name` (string)
    - `age` (int)
    - `monthly_income` (int)
    - `phone_number` (string or int)
  - Logic:
    - `approved_limit = 36 * monthly_income` rounded to **nearest lakh**.
  - Response body:
    - `customer_id` (int)
    - `name` (string)
    - `age` (int)
    - `monthly_income` (int)
    - `approved_limit` (int)
    - `phone_number` (string)

- **`POST /api/check-eligibility`**
  - Checks if a loan is eligible for a given customer.
  - Request body:
    - `customer_id` (int)
    - `loan_amount` (float/decimal)
    - `interest_rate` (float/decimal; requested)
    - `tenure` (int, in months)
  - Internal logic:
    - Builds a **credit score (0–100)** from historical `loan_data`:
      - Past EMIs paid on time
      - Number of past loans
      - Loan activity in current year
      - Approved loan volume vs annual income
      - If **sum of current loans > approved limit** → credit score = 0 and ineligible.
    - Applies rules:
      - If `score > 50` → approve with given rate (or higher).
      - If `50 >= score > 30` → approve only if rate ≥ 12%.
      - If `30 >= score > 10` → approve only if rate ≥ 16%.
      - If `score <= 10` → reject.
      - If `sum of all current EMIs > 50% of monthly salary` → reject.
    - If requested rate is *below* slab minimum, returns a **`corrected_interest_rate`**.
    - EMI is calculated using **compound interest EMI formula**.
  - Response body:
    - `customer_id` (int)
    - `approval` (bool)
    - `interest_rate` (float; as requested)
    - `corrected_interest_rate` (float; may be higher than requested)
    - `tenure` (int)
    - `monthly_installment` (float)

- **`POST /api/create-loan`**
  - Creates a loan if eligible (using same eligibility rules as `/check-eligibility`).
  - Request body:
    - `customer_id` (int)
    - `loan_amount` (float/decimal)
    - `interest_rate` (float/decimal; requested)
    - `tenure` (int, months)
  - Behavior:
    - Re-assesses creditworthiness.
    - If **not eligible**:
      - Returns `loan_id = null`, `loan_approved = false`, reason in `message`.
    - If **eligible**:
      - Creates a `Loan` record with:
        - Corrected interest rate (if required by slab)
        - EMI using compound interest formula
        - `start_date = today`
        - `end_date = today + tenure * 30 days`
  - Response body:
    - `loan_id` (int or null)
    - `customer_id` (int)
    - `loan_approved` (bool)
    - `message` (string)
    - `monthly_installment` (float)

- **`GET /api/view-loan/<loan_id>`**
  - Returns full loan and customer details.
  - Response body:
    - `loan_id` (int)
    - `customer` (JSON):
      - `id`
      - `first_name`
      - `last_name`
      - `phone_number`
      - `age`
    - `loan_amount` (float)
    - `interest_rate` (float)
    - `monthly_installment` (float)
    - `tenure` (int)

- **`GET /api/view-loans/<customer_id>`**
  - Returns a list of **current loans** for the customer.
  - Each item:
    - `loan_id` (int)
    - `loan_amount` (float)
    - `interest_rate` (float)
    - `monthly_installment` (float)
    - `repayments_left` (int, tenure − EMIs paid on time, min 0)

### Notes & assumptions

- `customer_id` is stored as the **primary key** of `Customer`.
- `approved_limit` is handled as per assignment: `36 * monthly_salary` rounded to nearest lakh.
- Credit scoring combines the described factors into a 0–100 score with sensible weights; exact formula is documented in code (`loans/services.py`).
- Initial Excel ingestion is done via a **Celery background task** (`loans.tasks.ingest_initial_data`), satisfying the background-worker requirement.

