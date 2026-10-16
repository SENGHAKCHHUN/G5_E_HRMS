"""Unit tests for business rules (no HTTP, no database) and checks that the layers stay separate.

Run from the project root:  python -m unittest discover tests -v
"""
import ast
import os
import unittest
from datetime import datetime
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
        payroll_service.calculate(line, 5000, settings(tax_rate=10, pension_rate=2))
        self.assertEqual((line.tax, line.pension, line.insurance), (500.0, 100.0, 85.0))
        self.assertEqual(line.net_salary, 5000 + 300 - (500 + 100 + 85))


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
