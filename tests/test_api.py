"""API tests. Run from the project root:  python -m unittest discover tests -v

Uses a throw-away SQLite file so the real hr_system.db is never touched.
"""
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta

_TMP = tempfile.mkdtemp()
os.environ.setdefault("HRMS_DATABASE_URL", f"sqlite:///{os.path.join(_TMP, 'test.db')}")
os.environ.setdefault("HRMS_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")
os.environ.setdefault("HRMS_DEMO_PASSWORD_CHANGE", "false")  # sign in with the demo accounts as they are

from fastapi.testclient import TestClient  # noqa: E402

from backend.core.database import SessionLocal  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models import LeaveRequest  # noqa: E402

OFFICE_IP = ("10.1.2.3", 50000)
HOME_IP = ("203.0.113.5", 50000)


def client(ip=OFFICE_IP):
    return TestClient(app, client=ip, base_url="http://testserver/api/v1")


def login(c, username, password):
    r = c.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return r.json()["user"]


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ctx = client()
        cls._ctx.__enter__()  # runs startup: create tables + seed demo data
        cls.admin = client(); login(cls.admin, "admin", "admin123")
        cls.hr = client(); login(cls.hr, "hr", "hr123")
        cls.emp = client(); cls.emp_user = login(cls.emp, "employee", "emp123")
        cls.emp_home = client(HOME_IP); login(cls.emp_home, "employee", "emp123")

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    # -------------------------------------------------------------- helpers
    def set_policy(self, **values):
        base = {"checkin_open": "00:00", "checkin_close": "23:59", "restrict_network": True,
                "office_networks": "10.0.0.0/8", "remote_exempt": True,
                "work_week": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
        base.update(values)
        r = self.admin.put("/settings", json=base)
        self.assertEqual(r.status_code, 200, r.text)

    def reset_today(self, employee_id):
        """HR clears today's punches (manual 'Absent' entry has no check-in)."""
        r = self.hr.post("/attendance", json={"employee_id": employee_id, "date": date.today().isoformat(),
                                              "status": "Absent"})
        self.assertEqual(r.status_code, 201, r.text)

    # ----------------------------------------------------------------- auth
    def test_login_and_me(self):
        c = client()
        self.assertEqual(c.post("/auth/login", data={"username": "hr", "password": "x"}).status_code, 401)
        self.assertEqual(c.get("/employees").status_code, 401)
        user = login(c, "s.lim@workflow.io", "hr123")  # work email also works
        self.assertEqual(user["role"], "HR Manager")
        self.assertEqual(c.get("/auth/me").json()["name"], "Sophea Lim")

    # ----------------------------------------------------------------- RBAC
    def test_employee_sees_only_own_data(self):
        me = self.emp_user["employee_id"]
        rows = self.emp.get("/employees").json()
        self.assertEqual([r["id"] for r in rows], [me])
        self.assertEqual(self.emp.get("/employees/2").status_code, 403)
        self.assertTrue(all(r["employee_id"] == me for r in self.emp.get("/attendance").json()))
        self.assertTrue(all(r["employee_id"] == me for r in self.emp.get("/payroll").json()))
        self.assertEqual(self.emp.get("/dashboard/stats").status_code, 403)
        self.assertEqual(self.emp.post("/payroll/generate", params={"month": "2026-01"}).status_code, 403)
        self.assertEqual(self.hr.put("/settings", json={"jwt_hours": 4}).status_code, 403)

    # ---------------------------------------------------------- check-in rules
    def test_checkin_rejected_outside_office_network(self):
        self.set_policy()
        self.reset_today(self.emp_user["employee_id"])
        r = self.emp_home.post("/attendance/check-in")
        self.assertEqual(r.status_code, 403)
        self.assertIn("office network", r.json()["detail"])
        self.assertFalse(self.emp_home.get("/attendance/policy").json()["network_ok"])

    def test_checkin_and_checkout_use_server_time(self):
        self.set_policy()
        me = self.emp_user["employee_id"]
        self.reset_today(me)
        r = self.emp.post("/attendance/check-in")
        self.assertEqual(r.status_code, 200, r.text)
        rec = r.json()
        server_now = datetime.now()
        punched = datetime.combine(date.today(), datetime.strptime(rec["check_in"], "%H:%M:%S").time())
        self.assertLess(abs((server_now - punched).total_seconds()), 60)
        late_after = datetime.combine(date.today(), datetime.strptime("09:15", "%H:%M").time())
        self.assertEqual(rec["status"], "Late" if server_now > late_after else "On Time")
        self.assertEqual(self.emp.post("/attendance/check-in").status_code, 409)  # once per day
        r = self.emp.post("/attendance/check-out")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIsNotNone(r.json()["check_out"])
        self.assertEqual(self.emp.post("/attendance/check-out").status_code, 409)
        self.assertEqual(self.emp.get("/attendance/today").json()["check_out"], r.json()["check_out"])

    def test_checkin_rejected_outside_time_window(self):
        now = datetime.now()
        start = (now + timedelta(hours=2)).strftime("%H:%M")
        end = (now + timedelta(hours=3)).strftime("%H:%M")
        if end < start:  # window would wrap past midnight - move it to the morning instead
            start, end = "00:00", "00:01"
        self.set_policy(checkin_open=start, checkin_close=end)
        self.reset_today(self.emp_user["employee_id"])
        r = self.emp.post("/attendance/check-in")
        self.assertEqual(r.status_code, 403)
        self.assertIn("only allowed between", r.json()["detail"])
        self.set_policy()

    def test_remote_employee_may_punch_from_anywhere(self):
        self.set_policy()
        r = self.hr.post("/employees", json={
            "first_name": "Rema", "last_name": "Remote", "email": "r.remote@workflow.io",
            "hire_date": date.today().isoformat(), "position": "Full-Stack Engineer", "salary": 5000,
            "department_id": 1, "status": "Active", "work_mode": "Remote"})
        self.assertEqual(r.status_code, 201, r.text)
        created = r.json()
        remote = client(HOME_IP)
        login(remote, created["username"], created["initial_password"])
        # new accounts must change the one-time password before anything else
        self.assertEqual(remote.post("/attendance/check-in").json()["detail"], "password_change_required")
        r = remote.post("/auth/change-password", json={"current_password": created["initial_password"],
                                                        "new_password": "NewPass123"})
        self.assertEqual(r.status_code, 200, r.text)
        remote.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        self.assertEqual(remote.post("/attendance/check-in").status_code, 200)
        # with the exemption switched off, the same person is blocked
        self.set_policy(remote_exempt=False)
        self.assertEqual(remote.post("/attendance/check-out").status_code, 403)
        self.set_policy()
        self.assertEqual(self.hr.delete(f"/employees/{created['id']}").status_code, 204)

    def test_network_rule_can_be_switched_off(self):
        self.set_policy(restrict_network=False)
        self.reset_today(self.emp_user["employee_id"])
        self.assertEqual(self.emp_home.post("/attendance/check-in").status_code, 200)
        self.set_policy()

    def test_manual_entry_is_staff_only(self):
        body = {"employee_id": 5, "date": date.today().isoformat(), "check_in": "09:00",
                "check_out": "18:00", "status": "On Time"}
        self.assertEqual(self.emp.post("/attendance", json=body).status_code, 403)
        r = self.hr.post("/attendance", json=body)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["source"], "manual")

    def test_invalid_office_network_rejected(self):
        r = self.admin.put("/settings", json={"office_networks": "10.0.0.0/8, not-an-ip"})
        self.assertEqual(r.status_code, 422)

    # ---------------------------------------------------------------- leave
    def test_leave_flow(self):
        start = date.today() + timedelta(days=60)
        start += timedelta(days=(7 - start.weekday()) % 7)  # a Monday: a working day in any work week
        body = {"type": "Casual", "start_date": start.isoformat(), "end_date": start.isoformat(),
                "reason": "Test"}
        r = self.emp.post("/leaves", json=body)
        self.assertEqual(r.status_code, 201, r.text)
        leave_id = r.json()["id"]
        self.assertEqual(self.emp.post("/leaves", json=body).status_code, 409)   # overlap
        self.assertEqual(self.emp.put(f"/leaves/{leave_id}/approve").status_code, 403)
        self.assertEqual(self.hr.put(f"/leaves/{leave_id}/reject", json={"note": ""}).status_code, 400)
        r = self.hr.put(f"/leaves/{leave_id}/approve", json={"note": "Enjoy"})
        self.assertEqual(r.json()["status"], "Approved")
        self.assertEqual(self.hr.put(f"/leaves/{leave_id}/approve").status_code, 409)  # already reviewed
        bal = self.emp.get("/leaves/balance").json()["Casual"]
        self.assertEqual(bal["remaining"], bal["allowance"] - bal["used"])

    def test_leave_counts_working_days_only(self):
        self.set_policy(work_week=["Mon", "Tue", "Wed", "Thu", "Fri"])  # other tests use a 7-day week
        thursday = date(date.today().year, 12, 1)
        thursday += timedelta(days=(3 - thursday.weekday()) % 7)
        if thursday + timedelta(days=4) > date(date.today().year, 12, 31):
            self.skipTest("no Thursday-Monday left in December")
        before = self.emp.get("/leaves/balance").json()["Annual"]["used"]
        body = {"type": "Annual", "start_date": thursday.isoformat(),
                "end_date": (thursday + timedelta(days=4)).isoformat(), "reason": "Long weekend"}
        r = self.emp.post("/leaves", json=body)
        self.assertEqual((r.status_code, r.json()["days"]), (201, 3), r.text)  # Thu, Fri, Mon
        self.hr.put(f"/leaves/{r.json()['id']}/approve", json={"note": ""})
        self.assertEqual(self.emp.get("/leaves/balance").json()["Annual"]["used"], before + 3)
        weekend = {**body, "start_date": (thursday + timedelta(days=9)).isoformat(),
                   "end_date": (thursday + timedelta(days=10)).isoformat()}  # Saturday-Sunday
        r = self.emp.post("/leaves", json=weekend)
        self.assertEqual(r.status_code, 400)
        self.assertIn("no working days", r.json()["detail"])

    # -------------------------------------------------------------- payroll
    def test_payroll_generate_and_pay(self):
        month = "2030-01"
        r = self.hr.post("/payroll/generate", params={"month": month})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertGreaterEqual(r.json()["created"], 7)  # everyone in the demo data
        rows = self.hr.get("/payroll", params={"month": month}).json()
        p = rows[0]
        self.assertAlmostEqual(p["net_salary"], p["base_salary"] + p["bonus"] - p["deductions"], places=2)
        self.assertEqual(self.hr.post("/payroll/pay", params={"month": month}).json()["paid"], len(rows))

    def test_payroll_proration_recalculation_and_line_edit(self):
        month = "2031-03"  # 31 days

        def hire(email, hire_date, salary=3100):
            r = self.hr.post("/employees", json={
                "first_name": "Pay", "last_name": "Roll", "email": email, "hire_date": hire_date,
                "position": "Accountant", "salary": salary, "department_id": 1, "status": "Active"})
            self.assertEqual(r.status_code, 201, r.text)
            return r.json()["id"]

        joiner = hire("pay.joiner@workflow.io", "2031-03-22")
        leaver = hire("pay.leaver@workflow.io", "2030-01-01")
        gone = hire("pay.gone@workflow.io", "2030-01-01")
        self.hr.put(f"/employees/{leaver}", json={"status": "Terminated", "termination_date": "2031-03-10"})
        self.hr.put(f"/employees/{gone}", json={"status": "Terminated", "termination_date": "2031-02-28"})
        bad = self.hr.put(f"/employees/{gone}", json={"termination_date": "2029-01-01", "status": "Terminated"})
        self.assertEqual(bad.status_code, 400)  # before the hire date

        self.assertEqual(self.hr.post("/payroll/generate", params={"month": month}).status_code, 200)
        lines = lambda: {p["employee_id"]: p for p in self.hr.get("/payroll", params={"month": month,  # noqa: E731
                                                                                     "limit": 500}).json()}
        rows = lines()
        self.assertNotIn(gone, rows)  # left before the month
        self.assertEqual((rows[joiner]["paid_days"], rows[joiner]["base_salary"]), (10, 1000.0))
        self.assertEqual((rows[leaver]["paid_days"], rows[leaver]["base_salary"]), (10, 1000.0))

        r = self.hr.patch(f"/payroll/{rows[joiner]['id']}", json={"bonus": 200, "adjustment": -50, "note": "advance"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertAlmostEqual(r.json()["net_salary"], 1000 + 200 - 50 - r.json()["deductions"], places=2)
        self.assertEqual(self.emp.patch(f"/payroll/{rows[joiner]['id']}", json={"bonus": 1}).status_code, 403)

        self.hr.put(f"/employees/{joiner}", json={"salary": 6200})  # recalculated, bonus kept
        self.assertGreater(self.hr.post("/payroll/generate", params={"month": month}).json()["calculated"], 0)
        line = lines()[joiner]
        self.assertEqual((line["base_salary"], line["bonus"], line["adjustment"], line["note"]),
                         (2000.0, 200.0, -50.0, "advance"))
        self.hr.put(f"/employees/{joiner}", json={"hire_date": "2031-04-01"})
        self.assertEqual(self.hr.post("/payroll/generate", params={"month": month}).json()["removed"], 1)
        self.assertNotIn(joiner, lines())

        self.hr.post("/payroll/pay", params={"month": month})
        paid = lines()[leaver]
        self.assertEqual(self.hr.patch(f"/payroll/{paid['id']}", json={"bonus": 5}).status_code, 400)
        self.hr.put(f"/employees/{leaver}", json={"salary": 9999})
        self.hr.post("/payroll/generate", params={"month": month})
        self.assertEqual(lines()[leaver]["base_salary"], paid["base_salary"])  # paid lines never change

    def test_payroll_uses_attendance_and_unpaid_leave(self):
        month = "2031-06"  # starts on a Sunday: 21 working days (Mon-Fri)
        self.set_policy(work_week=["Mon", "Tue", "Wed", "Thu", "Fri"])  # other tests use a 7-day week
        r = self.hr.post("/employees", json={
            "first_name": "Att", "last_name": "Pay", "email": "att.pay@workflow.io", "hire_date": "2030-01-01",
            "position": "Accountant", "salary": 2100, "department_id": 1, "status": "Active"})
        emp_id = r.json()["id"]
        for day, status, cin, cout in (("2031-06-02", "Absent", None, None), ("2031-06-03", "Half Day", "09:00", "12:00"),
                                       ("2031-06-04", "On Time", "09:00", "20:00")):
            body = {"employee_id": emp_id, "date": day, "status": status, "check_in": cin, "check_out": cout}
            self.assertEqual(self.hr.post("/attendance", json=body).status_code, 201)
        with SessionLocal() as db:  # approved Unpaid leave Thu 12 - Mon 16 June = 3 working days
            db.add(LeaveRequest(employee_id=emp_id, type="Unpaid", start_date=date(2031, 6, 12),
                                end_date=date(2031, 6, 16), status="Approved"))
            db.commit()
        self.hr.post("/payroll/generate", params={"month": month})
        line = next(p for p in self.hr.get("/payroll", params={"month": month, "limit": 500}).json()
                    if p["employee_id"] == emp_id)
        daily = 2100 / 21
        self.assertEqual(line["unpaid_days"], 4.5)
        self.assertEqual(line["unpaid_deduction"], round(daily * 4.5, 2))
        self.assertEqual(line["overtime_hours"], 2.0)
        self.assertEqual(line["overtime_pay"], round(daily / 9 * 2 * 1.5, 2))
        self.assertAlmostEqual(line["net_salary"], line["base_salary"] + line["overtime_pay"] + line["bonus"]
                               + line["adjustment"] - line["deductions"], places=2)
        pdf = self.hr.get(f"/payroll/{line['id']}/pdf")
        self.assertEqual((pdf.status_code, pdf.content[:4]), (200, b"%PDF"))

    # ----------------------------------------------------------- employees
    def test_employee_validation(self):
        r = self.hr.post("/employees", json={"first_name": "", "last_name": "X", "email": "bad",
                                             "hire_date": "2026-01-01", "position": "X", "salary": -1,
                                             "department_id": 1})
        self.assertEqual(r.status_code, 422)
        r = self.hr.post("/employees", json={"first_name": "Dup", "last_name": "Mail", "email": "s.chea@workflow.io",
                                             "hire_date": "2026-01-01", "position": "X", "salary": 1,
                                             "department_id": 1})
        self.assertEqual(r.status_code, 409)


if __name__ == "__main__":
    unittest.main()
