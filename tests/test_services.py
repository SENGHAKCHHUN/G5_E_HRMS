"""Unit tests for business rules (no HTTP, no database) and checks that the layers stay separate.

Run from the project root:  python -m unittest discover tests -v
"""
import ast
import os
import unittest
from datetime import date, datetime, time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("HRMS_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")

from backend.services import attendance_service, payroll_service  # noqa: E402
from backend.services.settings_service import DEFAULTS  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent / "backend"


def settings(**overrides):
    values = dict(DEFAULTS)
    values.update(overrides)
    return values


class AttendanceRuleTests(unittest.TestCase):
    MONDAY_9AM = datetime(2026, 10, 5, 9, 0)

    def test_office_network_matching(self):
        nets = "127.0.0.1/32, 192.168.0.0/16"
        self.assertTrue(attendance_service.on_office_network("192.168.4.20", nets))
        self.assertFalse(attendance_service.on_office_network("203.0.113.5", nets))
        self.assertFalse(attendance_service.on_office_network("not-an-ip", nets))

    def test_policy_blocks_outside_network_unless_remote(self):
        office = SimpleNamespace(work_mode="HQ Onsite")
        remote = SimpleNamespace(work_mode="Remote")
        s = settings(office_networks="10.0.0.0/8")
        self.assertFalse(attendance_service.evaluate_policy(office, "203.0.113.5", s, self.MONDAY_9AM)["network_ok"])
        self.assertTrue(attendance_service.evaluate_policy(remote, "203.0.113.5", s, self.MONDAY_9AM)["network_ok"])
        s_no_exempt = settings(office_networks="10.0.0.0/8", remote_exempt=False)
        self.assertFalse(attendance_service.evaluate_policy(remote, "203.0.113.5", s_no_exempt,
                                                            self.MONDAY_9AM)["network_ok"])

    def test_policy_window_and_work_day(self):
        s = settings(checkin_open="06:00", checkin_close="12:00")
        p = attendance_service.evaluate_policy(None, "127.0.0.1", s, self.MONDAY_9AM)
        self.assertTrue(p["window_open"] and p["work_day"])
        afternoon = attendance_service.evaluate_policy(None, "127.0.0.1", s, datetime(2026, 10, 5, 13, 0))
        self.assertFalse(afternoon["window_open"])
        sunday = attendance_service.evaluate_policy(None, "127.0.0.1", s, datetime(2026, 10, 4, 9, 0))
        self.assertFalse(sunday["work_day"])

    def test_late_after_shift_start_plus_grace(self):
        s = settings(shift_start="09:00", grace_minutes=15)
        self.assertEqual(attendance_service.punch_status(datetime(2026, 10, 5, 9, 15), s), "On Time")
        self.assertEqual(attendance_service.punch_status(datetime(2026, 10, 5, 9, 16), s), "Late")


class PayrollRuleTests(unittest.TestCase):
    def test_net_salary(self):
        line = SimpleNamespace(bonus=300.0)
        payroll_service.calculate(line, 5000, settings(tax_rate=10, pension_rate=2, tax_bonus=False))
        self.assertEqual((line.tax, line.pension, line.insurance), (500.0, 100.0, 85.0))
        self.assertEqual(line.net_salary, 5000 + 300 - (500 + 100 + 85))
        line.adjustment = -50.0  # never taxed
        payroll_service.calculate(line, 5000, settings(tax_rate=10, pension_rate=2))
        self.assertEqual(line.tax, 530.0)  # the bonus is taxed by default
        self.assertEqual(line.net_salary, 5000 + 300 - 50 - (530 + 100 + 85))

    def test_unpaid_days_and_overtime_in_net(self):
        line = SimpleNamespace(bonus=0.0, adjustment=0.0, unpaid_deduction=200.0, overtime_pay=60.0)
        payroll_service.calculate(line, 2000, settings(tax_rate=10, pension_rate=2, insurance_amount=50))
        self.assertEqual(line.tax, (2000 - 200 + 60) * 0.10)
        self.assertEqual(line.pension, (2000 - 200) * 0.02)
        self.assertEqual(line.deductions, 200 + 186 + 36 + 50)
        self.assertEqual(line.net_salary, 2000 + 60 - line.deductions)
        self.assertEqual(payroll_service.calculate(line, 7000, settings()) or line.insurance, 120.0)

    def test_progressive_tax(self):
        s = settings(tax_brackets="0:0, 1500000:5, 2000000:10, 8500000:15, 12500000:20")
        tax = payroll_service.income_tax
        self.assertEqual(tax(1_500_000, s), 0)
        self.assertEqual(tax(2_000_000, s), 25_000)  # 5% of the 500,000 above 1.5 million
        self.assertEqual(tax(3_000_000, s), 25_000 + 100_000)
        self.assertEqual(tax(15_000_000, s), 25_000 + 650_000 + 600_000 + 500_000)
        self.assertEqual(tax(1000, settings(tax_rate=11)), 110)

    def test_attendance_pay(self):
        emp = SimpleNamespace(hire_date=date(2020, 1, 1), termination_date=None, salary=2100)
        rec = lambda day, status, cin=None, cout=None: SimpleNamespace(  # noqa: E731
            date=date(2026, 6, day), status=status, check_in=cin and time.fromisoformat(cin),
            check_out=cout and time.fromisoformat(cout))
        records = [rec(1, "Absent"), rec(2, "Half Day", "09:00", "12:00"), rec(6, "Absent"),  # 6th: Saturday
                   rec(3, "On Time", "09:00", "20:30"), rec(4, "Late", "10:00", "01:00")]  # 2.5 h, 7 h (overnight)
        leave = [SimpleNamespace(start_date=date(2026, 6, 5), end_date=date(2026, 6, 8))]  # Fri-Mon: 2 working days
        out = payroll_service.attendance_pay(emp, "2026-06", records, leave, settings())
        daily = 2100 / 22  # June 2026 has 22 working days (Mon-Fri)
        self.assertEqual(out["unpaid_days"], 3.5)
        self.assertEqual(out["unpaid_deduction"], round(daily * 3.5, 2))
        self.assertEqual(out["overtime_hours"], 9.5)
        self.assertEqual(out["overtime_pay"], round(daily / 9 * 9.5 * 1.5, 2))
        off = payroll_service.attendance_pay(emp, "2026-06", records, leave, settings(deduct_unpaid=False,
                                                                                      overtime_rate=0))
        self.assertEqual((off["unpaid_deduction"], off["overtime_pay"]), (0, 0))

    def test_employed_days(self):
        emp = lambda hired, status="Active", left=None: SimpleNamespace(  # noqa: E731
            hire_date=date.fromisoformat(hired), status=status, termination_date=left and date.fromisoformat(left))
        days = payroll_service.employed_days
        self.assertEqual(days(emp("2020-01-01"), "2026-02"), (28, 28))
        self.assertEqual(days(emp("2026-02-15"), "2026-02"), (14, 28))
        self.assertEqual(days(emp("2026-03-01"), "2026-02"), (0, 28))  # not hired yet
        self.assertEqual(days(emp("2020-01-01", "Terminated", "2026-02-10"), "2026-02"), (10, 28))
        self.assertEqual(days(emp("2020-01-01", "Terminated", "2026-01-31"), "2026-02"), (0, 28))
        self.assertEqual(days(emp("2020-01-01", "Terminated"), "2026-02"), (0, 28))  # no last day known


class LayerTests(unittest.TestCase):
    """Keep the structure clean: each layer only uses the layer below it."""

    def imports_of(self, folder):
        for path in (BACKEND / folder).glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    yield path.name, (node.module or ""), [a.name for a in node.names]
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        yield path.name, alias.name, []

    def test_routers_do_not_touch_the_database(self):
        for name, module, _ in self.imports_of("routers"):
            self.assertNotIn("repositories", module, f"routers/{name} imports a repository")
            self.assertFalse(module.startswith("sqlalchemy") and module != "sqlalchemy.orm",
                             f"routers/{name} builds queries")

    def test_services_know_nothing_about_http(self):
        for name, module, _ in self.imports_of("services"):
            self.assertFalse(module.startswith(("fastapi", "starlette")), f"services/{name} imports {module}")

    def test_repositories_contain_no_business_rules(self):
        for name, module, _names in self.imports_of("repositories"):
            self.assertNotIn("services", module, f"repositories/{name} imports a service")
            self.assertFalse(module.startswith("fastapi"), f"repositories/{name} imports fastapi")


if __name__ == "__main__":
    unittest.main()
