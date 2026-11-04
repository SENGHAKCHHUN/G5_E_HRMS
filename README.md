# HR Management System

A desktop Human Resources Management System built with Python. A **CustomTkinter** desktop app
talks to a **FastAPI** backend over a REST API. Data is stored with **SQLAlchemy** in **SQLite**
by default, and PostgreSQL or MySQL can be used by changing one connection string.

The whole app is available in **English and Khmer (ខ្មែរ)**: screens, server messages, dates and PDFs.

---

## Features

1. **Authentication & Roles** – Login with Argon2-hashed passwords, JWT tokens and optional 2FA. Three roles: Admin, HR Manager, Employee.
2. **Employee Management** – Add, view, edit and delete employees; search and filter by department.
3. **Departments & Positions** – Manage departments, job roles and hiring requests (requisitions).
4. **Attendance** – Self check-in/check-out with server-enforced rules, and monthly reports.
5. **Leave Management** – Employees request leave; HR approves or rejects; balances are tracked.
6. **Payroll** – Monthly payroll with bonuses and deductions, PDF payslips and email delivery.
7. **Dashboard** – Company KPIs and charts for staff; a personal overview for employees.

Admins also have a **Settings** screen for company rules, user accounts, email, the audit log and backups.

### Role Permissions

| Module                                | Admin |     HR Manager     |     Employee     |
| ------------------------------------- | :---: | :-----------------: | :---------------: |
| Dashboard                             |  ✅  |         ✅         | Personal overview |
| Employees                             |  ✅  |         ✅         | Own profile only |
| Departments, Positions & Requisitions |  ✅  |         ✅         |        ❌        |
| Attendance                            |  ✅  |         ✅         | Own records only |
| Leave                                 |  ✅  | ✅ (approve/reject) | Own requests only |
| Payroll                               |  ✅  |         ✅         | Own payslips only |
| Settings & User accounts              |  ✅  |         ❌         |        ❌        |

---

## Tech Stack

| Layer        | Technology                                        |
| ------------ | ------------------------------------------------- |
| Frontend     | CustomTkinter, ttk.Treeview, Matplotlib, requests |
| Backend      | FastAPI, Uvicorn, Pydantic                        |
| Database     | SQLAlchemy 2.0, Alembic, SQLite                   |
| Security     | PyJWT, Argon2 (pwdlib), TOTP 2FA                  |
| Documents    | ReportLab, uharfbuzz (Khmer shaping)              |
| Translations | gettext + Babel                                   |
| Tests / lint | pytest, ruff                                      |

---

## Quick Start

**Requirements:** Python 3.11+ and Tkinter (on Linux: `sudo apt install python3-tk`).

```bash
git clone <your-repository-url>
cd G5_E_HRMS
python -m venv venv
venv\Scripts\activate          # macOS / Linux: source venv/bin/activate
pip install -r requirements.txt
```

Start everything with one command. `app.py` starts the backend, waits until it is ready, opens the
desktop app, and stops the backend when you close the window:

```bash
python app.py
```

| Command | What it starts |
|---|---|
| `python app.py` | Backend, then the desktop app |
| `python app.py --backend` | Backend only: API at http://127.0.0.1:8000/api/v1, docs at `/docs` |
| `python app.py --frontend` | Desktop app only (the backend must already be running) |

Options: `--host`, `--port`, and `--reload` (backend auto-reload while developing).

You can still run the two parts yourself in two terminals, backend first:

```bash
uvicorn backend.main:app --reload    # Terminal 1
python frontend/main.py              # Terminal 2
```

On first start the backend creates `hr_system.db` with a small demo company: one department
(*Head Office*) with 7 positions and 7 employees, two months of attendance, a few leave requests and
last month's payroll (paid).
Delete that file to start over.

### Default Login

| Role       | Username | Password |
| ---------- | -------- | -------- |
| Admin      | admin    | admin123 |
| HR Manager | hr       | hr123    |
| Employee   | employee | emp123   |

> These passwords are public, so the first sign-in with each one asks for a new password before
> anything else opens. New employees get their own username and one-time password when they are added
> (see [User Guide](docs/user-guide.md#accounts--security)).

---

## Documentation

| Document                                               | Contents                                                            |
| ------------------------------------------------------ | ------------------------------------------------------------------- |
| [Architecture](docs/architecture.md)                    | Project structure, backend layers, frontend design, database tables |
| [User Guide](docs/user-guide.md)                        | Check-in rules, accounts & security, PDFs, email, backups           |
| [Configuration & Deployment](docs/configuration.md) | Environment variables, other databases, HTTPS, network setup        |
| [Development](docs/development.md)                      | Tests, linting, database migrations, translations                   |
| [API Reference](docs/api.md)                            | All REST endpoints                                                  |

---

## Future Improvements

- Export reports to Excel
- Employee profile photos
- Performance review module
- Recruitment and job applicant tracking

---

## Author

- **Name:** _Your Name_
- **Course:** _Course Name_
- **Instructor:** _Instructor Name_
- **Date:** _Submission Date_
