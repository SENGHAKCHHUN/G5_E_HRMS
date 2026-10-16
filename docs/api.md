# API Reference

[← Back to README](../README.md)

All endpoints are under **`/api/v1`** (e.g. `POST /api/v1/auth/login`). Full request and response
formats are in the interactive docs at `http://127.0.0.1:8000/docs`. `GET /` is a health check.

- **Pagination:** list endpoints accept `?limit=&offset=` and return the total in the `X-Total-Count` header.
- **Language:** send `Accept-Language: km` for Khmer messages. Codes such as `otp_required` are never translated.

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Log in and receive a JWT (form: `username`, `password`, optional `otp`) |
| GET | `/auth/me` | Current user profile |
| POST | `/auth/change-password` | Change your own password |
| POST | `/auth/2fa/setup` | Start 2FA setup (returns a setup key) |
| POST | `/auth/2fa/enable` | Confirm setup with a 6-digit code |
| POST | `/auth/2fa/disable` | Turn 2FA off (password required) |

### Employees
| Method | Endpoint | Description |
|---|---|---|
| GET | `/employees?search=&department_id=&position=&status=` | List employees (paged) |
| GET | `/employees/summary` | Headcount totals by status |
| POST | `/employees` | Add an employee |
| GET | `/employees/{id}` | Get one employee |
| PUT | `/employees/{id}` | Update an employee |
| DELETE | `/employees/{id}` | Delete an employee |

### Departments & Positions
| Method | Endpoint | Description |
|---|---|---|
| GET | `/departments` | List departments |
| POST | `/departments` | Add a department |
| PUT | `/departments/{id}` | Update a department |
| GET | `/positions?department_id=` | List job roles |
| POST | `/positions` | Add a job role |
| PUT | `/positions/{id}` | Update a job role |
| DELETE | `/positions/{id}` | Delete an unused job role |

### Requisitions
| Method | Endpoint | Description |
|---|---|---|
| GET | `/requisitions?department_id=&status=` | List hiring requests |
| POST | `/requisitions` | Open a requisition |
| PUT | `/requisitions/{id}` | Mark filled or cancelled |

### Attendance
| Method | Endpoint | Description |
|---|---|---|
| POST | `/attendance/check-in` | Check in (server time, rules apply) |
| POST | `/attendance/check-out` | Check out (server time, rules apply) |
| GET | `/attendance?employee_id=&month=&status=&search=&department_id=` | Attendance records (paged) |
| GET | `/attendance/summary?employee_id=&month=` | Month totals |
| GET | `/attendance/today` | Signed-in user's record for today |
| GET | `/attendance/policy` | Whether this device may clock in now |
| POST | `/attendance` | Manual log entry (HR / Admin) |

### Leave
| Method | Endpoint | Description |
|---|---|---|
| GET | `/leaves?employee_id=&status=` | List leave requests (paged) |
| GET | `/leaves/balance?employee_id=` | Leave balances |
| POST | `/leaves` | Submit a request |
| PUT | `/leaves/{id}/approve` | Approve |
| PUT | `/leaves/{id}/reject` | Reject (note required) |

### Payroll
| Method | Endpoint | Description |
|---|---|---|
| POST | `/payroll/generate?month=` | Generate payroll for a month |
| POST | `/payroll/pay?month=` | Mark calculated payroll as paid |
| GET | `/payroll?month=&employee_id=&status=&search=&department_id=` | Payroll records (paged) |
| GET | `/payroll/summary?month=&employee_id=` | Month totals |
| GET | `/payroll/{id}/pdf` | Payslip PDF |
| POST | `/payroll/{id}/email` | Email the payslip to the employee |

### Dashboard
| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboard/stats` | Summary statistics |
| GET | `/dashboard/checkins` | Today's latest check-ins |
| GET | `/dashboard/notifications` | Bell-menu alerts |
| GET | `/dashboard/summary.pdf` | Dashboard summary PDF |

### Settings & Users (Admin)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/settings` | Read settings (any signed-in user) |
| PUT | `/settings` | Update settings |
| GET | `/settings/audit` | Audit log (paged) |
| GET | `/settings/database` | Database size and row counts |
| GET | `/settings/backup` | Download a SQLite backup |
| POST | `/settings/test-email` | Send a test email |
| GET | `/users` | User accounts |
| POST | `/users/{id}/reset-password` | Issue a one-time temporary password |
| POST | `/users/{id}/reset-2fa` | Turn off a user's 2FA |
