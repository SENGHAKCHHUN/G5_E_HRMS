"""Tests for accounts (passwords, 2FA), PDFs, email, backup, requisitions and settings.

Run from the project root:  python -m unittest discover tests -v
"""
import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest import mock

_TMP = tempfile.mkdtemp()
os.environ.setdefault("HRMS_DATABASE_URL", f"sqlite:///{os.path.join(_TMP, 'test.db')}")
os.environ.setdefault("HRMS_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")
os.environ.setdefault("HRMS_DEMO_PASSWORD_CHANGE", "false")  # sign in with the demo accounts as they are

from fastapi.testclient import TestClient  # noqa: E402

from backend.core import totp  # noqa: E402
from backend.main import app  # noqa: E402

IP = ("127.0.0.1", 50000)


def client():
    return TestClient(app, client=IP, base_url="http://testserver/api/v1")


def login(c, username, password, otp=None):
    data = {"username": username, "password": password}
    if otp:
        data["otp"] = otp
    r = c.post("/auth/login", data=data)
    assert r.status_code == 200, r.text
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return r.json()["user"]


class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ctx = client()
        cls._ctx.__enter__()
        cls.admin = client(); login(cls.admin, "admin", "admin123")
        cls.hr = client(); login(cls.hr, "hr", "hr123")
        cls.emp = client(); cls.emp_user = login(cls.emp, "employee", "emp123")

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    def new_employee(self, email, role="Employee"):
        r = self.admin.post("/employees", json={
            "first_name": "Temp", "last_name": "Person", "email": email, "hire_date": "2026-01-05",
            "position": "Accountant", "salary": 4500, "department_id": 1, "status": "Active", "role": role})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def user_id(self, username):
        return next(u["id"] for u in self.admin.get("/users").json() if u["username"] == username)

    # ---------------------------------------------------------- passwords
    def test_change_password_signs_out_old_sessions(self):
        created = self.new_employee("pw.change@workflow.io")
        c = client()
        user = login(c, created["username"], created["initial_password"])
        self.assertEqual(user["pending_action"], "password_change_required")
        self.assertEqual(c.get("/employees").status_code, 403)  # blocked until changed
        bad = c.post("/auth/change-password", json={"current_password": "wrong", "new_password": "Abcdef123"})
        self.assertEqual(bad.status_code, 400)
        weak = c.post("/auth/change-password", json={"current_password": created["initial_password"],
                                                     "new_password": "12345678"})
        self.assertEqual(weak.status_code, 422)
        r = c.post("/auth/change-password", json={"current_password": created["initial_password"],
                                                  "new_password": "Abcdef123"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIsNone(r.json()["user"]["pending_action"])
        self.assertEqual(c.get("/employees").status_code, 401)  # old token no longer valid
        c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        self.assertEqual(c.get("/employees").status_code, 200)

    def test_admin_password_reset(self):
        created = self.new_employee("pw.reset@workflow.io")
        uid = self.user_id(created["username"])
        self.assertEqual(self.hr.post(f"/users/{uid}/reset-password").status_code, 403)  # admin only
        r = self.admin.post(f"/users/{uid}/reset-password")
        self.assertEqual(r.status_code, 200, r.text)
        temp = r.json()["temporary_password"]
        c = client()
        self.assertEqual(login(c, created["username"], temp)["pending_action"], "password_change_required")

    def test_demo_password_must_be_changed(self):
        from backend.core.config import config
        from backend.core.database import SessionLocal
        from backend.repositories import user_repo
        with mock.patch.object(config, "demo_password_change", True):
            c = client()
            self.assertEqual(login(c, "employee", "emp123")["pending_action"], "password_change_required")
            self.assertEqual(c.get("/attendance/today").status_code, 403)  # blocked until changed
        with SessionLocal() as db:  # undo, so the other tests can keep using the demo account
            user_repo.get_by_username(db, "employee").must_change_password = False
            db.commit()

    # ---------------------------------------------------------------- 2FA
    def test_two_factor_login(self):
        created = self.new_employee("two.factor@workflow.io")
        c = client()
        login(c, created["username"], created["initial_password"])
        r = c.post("/auth/change-password", json={"current_password": created["initial_password"],
                                                  "new_password": "Secret123"})
        c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        secret = c.post("/auth/2fa/setup").json()["secret"]
        self.assertEqual(c.post("/auth/2fa/enable", json={"code": "000000"}).status_code, 400)
        r = c.post("/auth/2fa/enable", json={"code": totp.current_code(secret)})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["totp_enabled"])

        c2 = client()
        r = c2.post("/auth/login", data={"username": created["username"], "password": "Secret123"})
        self.assertEqual((r.status_code, r.json()["detail"]), (401, "otp_required"))
        r = c2.post("/auth/login", data={"username": created["username"], "password": "Secret123",
                                         "otp": "123456" if totp.current_code(secret) != "123456" else "654321"})
        self.assertEqual(r.json()["detail"], "Invalid authentication code")
        login(c2, created["username"], "Secret123", otp=totp.current_code(secret))

        # admin can reset 2FA for a user who lost their phone
        self.admin.post(f"/users/{self.user_id(created['username'])}/reset-2fa")
        login(client(), created["username"], "Secret123")

    def test_enforced_mfa_blocks_staff_until_setup(self):
        # an admin without 2FA cannot switch enforcement on (would lock themselves out)
        r = self.admin.put("/settings", json={"enforce_mfa": True})
        self.assertEqual(r.status_code, 400)
        self.assertIn("your own account first", r.json()["detail"])

        from backend.core.database import SessionLocal
        from backend.repositories import setting_repo

        def set_enforce(value):
            with SessionLocal() as db:
                setting_repo.save(db, "enforce_mfa", value)
                db.commit()

        set_enforce(True)
        try:
            c = client()
            user = login(c, "hr", "hr123")
            self.assertEqual(user["pending_action"], "mfa_setup_required")
            self.assertEqual(c.get("/employees").json()["detail"], "mfa_setup_required")
            e = client()  # employees are not affected
            self.assertIsNone(login(e, "employee", "emp123")["pending_action"])
        finally:
            set_enforce(False)

    # ---------------------------------------------------------------- PDF
    def test_payslip_and_summary_pdf(self):
        mine = self.emp.get("/payroll").json()[0]
        r = self.emp.get(f"/payroll/{mine['id']}/pdf")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF"))
        other = next(p for p in self.hr.get("/payroll").json() if p["employee_id"] != mine["employee_id"])
        self.assertEqual(self.emp.get(f"/payroll/{other['id']}/pdf").status_code, 403)
        r = self.hr.get("/dashboard/summary.pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.assertEqual(self.emp.get("/dashboard/summary.pdf").status_code, 403)

    # -------------------------------------------------------------- email
    def test_email_requires_configuration(self):
        self.admin.put("/settings", json={"smtp_host": "", "smtp_from": ""})
        p = self.hr.get("/payroll").json()[0]
        r = self.hr.post(f"/payroll/{p['id']}/email")
        self.assertEqual(r.status_code, 400)
        self.assertIn("not configured", r.json()["detail"])

    def test_payslip_email_and_leave_notification(self):
        self.admin.put("/settings", json={"smtp_host": "smtp.example.com", "smtp_port": 587,
                                          "smtp_from": "hr@workflow.io", "smtp_password": "s3cret",
                                          "email_notifications": True})
        settings = self.admin.get("/settings").json()
        self.assertNotIn("smtp_password", settings)  # never sent back
        self.assertTrue(settings["smtp_password_set"])
        try:
            with mock.patch("backend.integrations.mailer.smtplib.SMTP") as smtp:
                p = self.hr.get("/payroll").json()[0]
                r = self.hr.post(f"/payroll/{p['id']}/email")
                self.assertEqual(r.status_code, 200, r.text)
                server = smtp.return_value  # emailer calls methods on the SMTP object itself
                server.login.assert_not_called()  # no smtp_user configured
                msg = server.send_message.call_args[0][0]
                self.assertEqual(msg["To"], p["email"])
                self.assertEqual(len(list(msg.iter_attachments())), 1)

                start = date.today() + timedelta(days=200)
                start += timedelta(days=(7 - start.weekday()) % 7)  # a Monday: leave counts working days
                lv = self.emp.post("/leaves", json={"type": "Casual", "start_date": start.isoformat(),
                                                    "end_date": start.isoformat()}).json()
                r = self.hr.put(f"/leaves/{lv['id']}/approve", json={"note": "OK"})
                self.assertTrue(r.json().get("email_queued"))
                sent = server.send_message.call_args[0][0]
                self.assertIn(f"LV-{lv['id']} approved", sent["Subject"])
        finally:
            self.admin.put("/settings", json={"smtp_host": "", "smtp_from": ""})

    # ------------------------------------------------------------- backup
    def test_backup(self):
        self.assertEqual(self.hr.get("/settings/backup").status_code, 403)
        r = self.admin.get("/settings/backup")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"SQLite format 3"))

    # ------------------------------------------------------- requisitions
    def test_requisitions(self):
        pos = self.hr.get("/positions", params={"department_id": 1}).json()[0]
        r = self.hr.post("/requisitions", json={"department_id": 1, "position_id": pos["id"],
                                                "title": pos["title"], "openings": 2})
        self.assertEqual(r.status_code, 201, r.text)
        req = r.json()
        self.assertEqual(self.hr.post("/requisitions", json={"department_id": 2, "position_id": pos["id"],
                                                             "title": "x"}).status_code, 400)
        self.assertIn(req["id"], [x["id"] for x in self.hr.get("/requisitions",
                                                               params={"department_id": 1}).json()])
        self.assertEqual(self.hr.put(f"/requisitions/{req['id']}", json={"status": "Filled"}).json()["status"],
                         "Filled")
        self.assertEqual(self.hr.put(f"/requisitions/{req['id']}", json={"status": "Cancelled"}).status_code, 409)
        self.assertEqual(self.emp.get("/requisitions").status_code, 403)

    # ----------------------------------------------------------- settings
    def test_non_working_day_blocks_checkin(self):
        policy = self.emp.get("/attendance/policy").json()
        today = date.fromisoformat(policy["server_time"][:10]).strftime("%a")
        days = [d for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] if d != today]
        self.admin.put("/settings", json={"work_week": days, "checkin_open": "00:00", "checkin_close": "23:59",
                                          "restrict_network": False})
        try:
            self.hr.post("/attendance", json={"employee_id": self.emp_user["employee_id"],
                                              "date": policy["server_time"][:10], "status": "Absent"})
            r = self.emp.post("/attendance/check-in")
            self.assertEqual(r.status_code, 403)
            self.assertIn("not a working day", r.json()["detail"])
        finally:
            self.admin.put("/settings", json={"work_week": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                                              "restrict_network": True})

    def test_settings_validation(self):
        self.assertEqual(self.admin.put("/settings", json={"work_week": []}).status_code, 422)
        self.assertEqual(self.admin.put("/settings", json={"currency": "BTC"}).status_code, 422)
        r = self.admin.put("/settings", json={"checkin_open": "13:00", "checkin_close": "12:00"})
        self.assertEqual(r.status_code, 400)

    def test_timezone_label_parsing(self):
        from backend.core.clock import tz_from_label
        self.assertEqual(tz_from_label("(UTC+07:00) Bangkok").utcoffset(None), timedelta(hours=7))
        self.assertEqual(tz_from_label("(UTC-05:30) X").utcoffset(None), -timedelta(hours=5, minutes=30))
        self.assertIsNone(tz_from_label("Local time"))


if __name__ == "__main__":
    unittest.main()
