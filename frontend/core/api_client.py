"""All data access for the desktop frontend: talks to the FastAPI backend.

Set HRMS_API_URL to point at a backend on another machine (default
http://127.0.0.1:8000). The views only ever call `api.<method>()`, and they do it
through core.tasks.run(...) so the window stays responsive.
"""
import os
from dataclasses import dataclass
from typing import Any

import requests

from .i18n import _, safe_khmer
from .state import state

BASE_URL = os.environ.get("HRMS_API_URL", "http://127.0.0.1:8000")
API_PREFIX = os.environ.get("HRMS_API_PREFIX", "/api/v1")  # versioned API routes

Json = dict[str, Any]
Rows = list[Json]


class ApiError(Exception):
    """A request failed; the message is ready to show to the user (in their language)."""


class SessionExpired(ApiError):
    """The login token is no longer valid: the app returns to the login screen."""


@dataclass
class Page:
    rows: Rows
    total: int


class HttpApiClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.http = requests.Session()
        self.token: str | None = None

    # ------------------------------------------------------------- helpers
    def _headers(self) -> dict:
        headers = {"Accept-Language": state.language}  # server messages come back in this language
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _send(self, method: str, path: str, params: dict | None = None, json: Any = None, data: dict | None = None,
              timeout: float = 15) -> requests.Response:
        try:
            r = self.http.request(method, self.base_url + API_PREFIX + path, params=params, json=json,
                                  data=data, headers=self._headers(), timeout=timeout)
        except requests.ConnectionError:
            raise ApiError(_("Cannot reach the HRMS server at {url}. Is the backend running?").format(
                url=self.base_url))
        except requests.Timeout:
            raise ApiError(_("The HRMS server took too long to respond"))
        if r.status_code == 401 and self.token and not path.startswith("/auth/login"):
            self.token = None
            raise SessionExpired(_("Your session has expired. Please sign in again."))
        if r.status_code >= 400:
            raise ApiError(self._error_message(r))
        return r

    def _request(self, method: str, path: str, params: dict | None = None, json: Any = None,
                 data: dict | None = None, timeout: float = 15, raw: bool = False) -> Any:
        r = self._send(method, path, params, json, data, timeout)
        if raw:
            return r.content
        return r.json() if r.content else None

    @staticmethod
    def _error_message(r: requests.Response) -> str:
        try:
            detail = r.json().get("detail")
        except ValueError:
            return _("Server error ({code})").format(code=r.status_code)
        if isinstance(detail, list) and detail:  # pydantic validation errors
            first = detail[0]
            field = ".".join(str(x) for x in first.get("loc", [])[1:])
            msg = first.get("msg", "Invalid value").replace("Value error, ", "")
            return safe_khmer(f"{field}: {msg}" if field else msg)
        return safe_khmer(str(detail or _("Server error ({code})").format(code=r.status_code)))

    @staticmethod
    def _clean(params: dict) -> dict:
        return {k: v for k, v in params.items() if v not in (None, "")}

    def _get(self, path: str, **params: Any) -> Any:
        return self._request("GET", path, params=self._clean(params))

    def _page(self, path: str, **params: Any) -> Page:
        """A list endpoint with ?limit=&offset=: rows plus the total from X-Total-Count."""
        r = self._send("GET", path, params=self._clean(params))
        rows = r.json()
        return Page(rows, int(r.headers.get("X-Total-Count", len(rows))))

    def _post(self, path: str, payload: Json | None = None, **params: Any) -> Any:
        return self._request("POST", path, params=params or None, json=payload)

    def _put(self, path: str, payload: Json | None = None) -> Any:
        return self._request("PUT", path, json=payload)

    def _delete(self, path: str) -> None:
        return self._request("DELETE", path)

    # -------------------------------------------------------------- health
    def health(self) -> tuple[bool, str]:
        try:
            info = self.http.get(self.base_url + "/", timeout=2).json()  # health check (not versioned)
        except (requests.RequestException, ValueError):
            return False, _("Backend offline at {url}").format(url=self.base_url)
        if info.get("database") != "ok":
            return False, _("Server at {url} cannot reach its database").format(url=self.base_url)
        return True, _("Connected to {url} (v{version})").format(url=self.base_url,
                                                                   version=info.get("version", "?"))

    # ---------------------------------------------------------------- auth
    def login(self, username: str, password: str, otp: str | None = None) -> dict:
        """Raises ApiError('otp_required') when the account has 2FA and no code was given."""
        form = {"username": username.strip(), "password": password}
        if otp:
            form["otp"] = otp.strip()
        return self._start_session(self._request("POST", "/auth/login", data=form))

    def _start_session(self, res: Json) -> dict:
        self.token = res["access_token"]
        return dict(res["user"])

    def logout(self) -> None:
        self.token = None

    # ------------------------------------------------------------ account
    def change_password(self, current_password: str, new_password: str) -> dict:
        res = self._post("/auth/change-password", {"current_password": current_password,
                                                    "new_password": new_password})
        return self._start_session(res)  # the server issues a new token

    def setup_2fa(self) -> Json:
        return self._post("/auth/2fa/setup")

    def enable_2fa(self, code: str) -> Json:
        return self._post("/auth/2fa/enable", {"code": code})

    def disable_2fa(self, password: str) -> Json:
        return self._post("/auth/2fa/disable", {"password": password})

    # ----------------------------------------------------------- employees
    def employees_page(self, search: str | None = None, department_id: int | None = None,
                       position: str | None = None, status: str | None = None, limit: int | None = None,
                       offset: int = 0) -> Page:
        return self._page("/employees", search=search, department_id=department_id, position=position,
                          status=status, limit=limit, offset=offset)

    def get_employees(self) -> Rows:
        return self._get("/employees")

    def employee_summary(self) -> Json:
        return self._get("/employees/summary")

    def get_employee(self, emp_id: int) -> Json:
        return self._get(f"/employees/{emp_id}")

    def create_employee(self, data: Json) -> Json:
        return self._post("/employees", data)

    def update_employee(self, emp_id: int, data: Json) -> Json:
        return self._put(f"/employees/{emp_id}", data)

    def delete_employee(self, emp_id: int) -> None:
        self._delete(f"/employees/{emp_id}")

    # --------------------------------------------------------- departments
    def get_departments(self) -> Rows:
        return self._get("/departments")

    def create_department(self, data: Json) -> Json:
        return self._post("/departments", data)

    def update_department(self, dept_id: int, data: Json) -> Json:
        return self._put(f"/departments/{dept_id}", data)

    def get_positions(self, department_id: int | None = None) -> Rows:
        return self._get("/positions", department_id=department_id)

    def create_position(self, data: Json) -> Json:
        return self._post("/positions", data)

    def update_position(self, pos_id: int, data: Json) -> Json:
        return self._put(f"/positions/{pos_id}", data)

    def delete_position(self, pos_id: int) -> None:
        self._delete(f"/positions/{pos_id}")

    # ---------------------------------------------------------- attendance
    def attendance_page(self, month: str | None = None, employee_id: int | None = None, status: str | None = None,
                        search: str | None = None, department_id: int | None = None, limit: int | None = None,
                        offset: int = 0) -> Page:
        return self._page("/attendance", month=month, employee_id=employee_id, status=status, search=search,
                          department_id=department_id, limit=limit, offset=offset)

    def attendance_summary(self, month: str | None = None, employee_id: int | None = None) -> Json:
        return self._get("/attendance/summary", month=month, employee_id=employee_id)

    def today_record(self) -> Json | None:
        return self._get("/attendance/today")

    def get_policy(self) -> Json:
        return self._get("/attendance/policy")

    def check_in(self) -> Json:
        return self._post("/attendance/check-in")

    def check_out(self) -> Json:
        return self._post("/attendance/check-out")

    def add_attendance(self, data: Json) -> Json:
        return self._post("/attendance", data)

    # --------------------------------------------------------------- leave
    def leaves_page(self, employee_id: int | None = None, status: str | None = None, limit: int | None = None,
                    offset: int = 0) -> Page:
        return self._page("/leaves", employee_id=employee_id, status=status, limit=limit, offset=offset)

    def submit_leave(self, data: Json) -> Json:
        return self._post("/leaves", data)

    def approve_leave(self, leave_id: int, note: str = "") -> Json:
        return self._put(f"/leaves/{leave_id}/approve", {"note": note})

    def reject_leave(self, leave_id: int, note: str = "") -> Json:
        return self._put(f"/leaves/{leave_id}/reject", {"note": note})

    def get_leave_balance(self, employee_id: int | None = None) -> Json:
        return self._get("/leaves/balance", employee_id=employee_id)

    # ------------------------------------------------------------- payroll
    def payroll_page(self, month: str | None = None, employee_id: int | None = None, status: str | None = None,
                     search: str | None = None, department_id: int | None = None, limit: int | None = None,
                     offset: int = 0) -> Page:
        return self._page("/payroll", month=month, employee_id=employee_id, status=status, search=search,
                          department_id=department_id, limit=limit, offset=offset)

    def payroll_summary(self, month: str | None = None, employee_id: int | None = None) -> Json:
        return self._get("/payroll/summary", month=month, employee_id=employee_id)

    def generate_payroll(self, month: str) -> Json:
        """{created, calculated, removed}: unpaid lines are recalculated each time."""
        return self._post("/payroll/generate", month=month)

    def update_payroll_line(self, payroll_id: int, data: Json) -> Json:
        return self._request("PATCH", f"/payroll/{payroll_id}", json=data)

    def mark_paid(self, month: str) -> int:
        return self._post("/payroll/pay", month=month)["paid"]

    # ----------------------------------------------------------- dashboard
    def get_dashboard_stats(self) -> Json:
        return self._get("/dashboard/stats")

    def recent_checkins(self, limit: int = 5) -> Rows:
        return self._get("/dashboard/checkins", limit=limit)

    def get_notifications(self) -> list[str]:
        return [safe_khmer(note) for note in self._get("/dashboard/notifications")]

    # ------------------------------------------------------------ settings
    def get_settings(self) -> Json:
        return self._get("/settings")

    def save_settings(self, data: Json) -> Json:
        return self._put("/settings", data)

    def audit_page(self, limit: int = 50, offset: int = 0) -> Page:
        return self._page("/settings/audit", limit=limit, offset=offset)

    def get_users(self) -> Rows:
        return self._get("/users")

    def reset_password(self, user_id: int) -> Json:
        return self._post(f"/users/{user_id}/reset-password")

    def reset_2fa(self, user_id: int) -> Json:
        return self._post(f"/users/{user_id}/reset-2fa")

    def send_test_email(self, to: str) -> Json:
        return self._post("/settings/test-email", {"to": to})

    def database_info(self) -> Json:
        return self._get("/settings/database")

    def download_backup(self) -> bytes:
        return self._request("GET", "/settings/backup", raw=True, timeout=120)

    # ------------------------------------------------------ documents / email
    def payslip_pdf(self, payroll_id: int) -> bytes:
        return self._request("GET", f"/payroll/{payroll_id}/pdf", raw=True, timeout=60)

    def email_payslip(self, payroll_id: int) -> Json:
        return self._request("POST", f"/payroll/{payroll_id}/email", timeout=60)

    def summary_pdf(self) -> bytes:
        return self._request("GET", "/dashboard/summary.pdf", raw=True, timeout=60)

    # -------------------------------------------------------- requisitions
    def get_requisitions(self, department_id: int | None = None, status: str | None = None) -> Rows:
        return self._get("/requisitions", department_id=department_id, status=status)

    def create_requisition(self, data: Json) -> Json:
        return self._post("/requisitions", data)

    def update_requisition(self, req_id: int, status: str) -> Json:
        return self._put(f"/requisitions/{req_id}", {"status": status})


api = HttpApiClient()
