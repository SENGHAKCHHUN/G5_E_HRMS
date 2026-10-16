# Architecture

[← Back to README](../README.md)

```
┌──────────────────────┐   HTTP / JSON   ┌──────────────────────┐   SQLAlchemy   ┌────────────┐
│  Desktop Frontend    │ ──────────────► │   FastAPI Backend    │ ─────────────► │  Database  │
│  (CustomTkinter)     │ ◄────────────── │   (REST API)         │ ◄───────────── │  (SQLite)  │
└──────────────────────┘                 └──────────────────────┘                └────────────┘
```

## Project Structure

```
G5_E_HRMS/
├── backend/
│   ├── main.py              # FastAPI app: routers, error handling, start-up
│   ├── dependencies.py      # DB session, current user, role checks
│   ├── models.py            # SQLAlchemy table models
│   ├── schemas.py           # Pydantic request models (validation)
│   ├── serializers.py       # ORM objects -> JSON responses
│   ├── seed.py, seed_data.py  # demo data for an empty database
│   ├── migrations/          # Alembic migrations
│   ├── core/                # config, database, security, encryption, logging, errors
│   ├── integrations/        # email (SMTP) and PDF generation
│   ├── locales/             # server message translations
│   ├── routers/             # HTTP layer, one file per module
│   ├── services/            # business rules
│   └── repositories/        # database queries
├── frontend/
│   ├── main.py              # entry point, starts on the login screen
│   ├── app.py               # main window, sidebar, top bar, screen switching
│   ├── assets/fonts/        # Noto Sans Khmer (SIL Open Font License)
│   ├── core/                # API client, background tasks, app state, i18n, preferences
│   ├── logic/               # pure, unit-tested functions (formatting, validation, calculations)
│   ├── ui/                  # theme, reusable widgets, icons
│   ├── views/               # one file per screen
│   └── locales/             # screen translations
├── scripts/                 # fill_translations.py
├── tests/                   # backend and frontend tests
├── alembic.ini, pyproject.toml, pytest.ini, requirements.txt
└── README.md
```

## Backend Layers

Each layer only calls the one below it:

```
Router (HTTP)  →  Service (business rules)  →  Repository (queries)  →  Database
```

- **Routers** read the request, call one service function and return the result.
- **Services** handle permissions, validation and calculations. They raise domain errors
  (`NotFound`, `Conflict`, ...) that `main.py` turns into HTTP status codes.
- **Repositories** hold every database query. They never commit; the service commits once
  the whole operation succeeds.

`tests/test_services.py` enforces these rules (for example, a router importing a repository fails the tests).

## Frontend

- **No frozen screens:** every server call runs in a background thread via `core.tasks.run(...)`,
  and the result is drawn on the Tk main thread.
- **Session expiry:** a 401 response returns the user to the login screen.
- **Server-side paging and filters:** tables load one page at a time (`?limit=&offset=`, total
  from `X-Total-Count`), and KPI cards come from `/summary` endpoints, so totals cover the whole company.
- **Logic separated from screens:** `frontend/logic/` is unit tested without opening a window.

## Database Design

Main fields (full definitions in `backend/models.py`):

| Table | Fields |
|---|---|
| **users** | id, username, password_hash, role, employee_id, must_change_password, totp_secret, totp_enabled |
| **departments** | id, name, description, code, lead, location, budget, target, icon |
| **positions** | id, department_id, title, grade, min_salary, max_salary, skills, planned |
| **employees** | id, first_name, last_name, email, phone, gender, hire_date, position, salary, department_id, status, employment, work_mode, shift |
| **attendance** | id, employee_id, date, check_in, check_out, status, source, ip_address |
| **leave_requests** | id, employee_id, start_date, end_date, type, reason, status, review_note |
| **payroll** | id, employee_id, month, base_salary, bonus, tax, insurance, pension, deductions, net_salary, status |
| **requisitions** | id, department_id, position_id, title, openings, note, status, created_by, created_at |
| **settings** | key, value |
| **audit_log** | id, timestamp, username, action, detail |
| **login_attempts** | id, username, ip_address, attempted_at |

**Relationships**

- One department has many positions, employees and requisitions.
- One employee has at most one user account.
- One employee has many attendance records, leave requests and payroll records.
