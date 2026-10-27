# Configuration & Deployment

[← Back to README](../README.md)

## Environment Variables

The backend reads `HRMS_*` environment variables, or a `.env` file in the project root:

| Variable | Default | Purpose |
|---|---|---|
| `HRMS_DATABASE_URL` | `sqlite:///./hr_system.db` | Database connection |
| `HRMS_SECRET_KEY` | random key in `backend/.secret_key` | Signs login tokens and encrypts stored secrets |
| `HRMS_SMTP_PASSWORD` | – | SMTP password (instead of storing it in Settings) |
| `HRMS_TRUSTED_PROXIES` | `[]` | Reverse proxies allowed to send `X-Forwarded-For`, e.g. `["127.0.0.1"]` |
| `HRMS_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO` or `WARNING` |
| `HRMS_LOGIN_MAX_FAILURES` / `HRMS_LOGIN_LOCKOUT_MINUTES` | `5` / `15` | Login lockout |
| `HRMS_DEMO_PASSWORD_CHANGE` | `true` | Signing in with a demo account's public password (`admin123` ...) asks for a new one first |

The desktop app reads `HRMS_API_URL` (default `http://127.0.0.1:8000`).

## Running on a Network

Start the backend so other computers can reach it, then point each desktop app at it:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
# on each client:  HRMS_API_URL=http://192.168.1.10:8000
```

## HTTPS

On a network, use HTTPS so passwords and tokens are encrypted:

- **Simple:** give uvicorn a certificate, then set `HRMS_API_URL=https://server-name:8443`:
  ```bash
  uvicorn backend.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile key.pem --ssl-certfile cert.pem
  ```
- **Recommended:** put a reverse proxy (Caddy or nginx) in front of `uvicorn --host 127.0.0.1` and set
  `HRMS_TRUSTED_PROXIES=["127.0.0.1"]`, so the office-network check sees the real client address.

## Switching Databases

Set `HRMS_DATABASE_URL` and install the matching driver. The tables are created on first start.

```bash
HRMS_DATABASE_URL=postgresql://user:password@localhost:5432/hr_system   # pip install psycopg2-binary
HRMS_DATABASE_URL=mysql+pymysql://user:password@localhost:3306/hr_system  # pip install pymysql
```
