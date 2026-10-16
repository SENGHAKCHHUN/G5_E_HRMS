"""Server messages follow the Accept-Language header; machine codes and PDFs keep working in Khmer.

Run from the project root:  pytest
"""
import os
import tempfile
import unittest

_TMP = tempfile.mkdtemp()
os.environ.setdefault("HRMS_DATABASE_URL", f"sqlite:///{os.path.join(_TMP, 'test.db')}")
os.environ.setdefault("HRMS_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")

from fastapi.testclient import TestClient  # noqa: E402

from backend.core import i18n  # noqa: E402
from backend.integrations import pdf  # noqa: E402
from backend.main import app  # noqa: E402


def client():
    return TestClient(app, client=("10.1.2.3", 50000), base_url="http://testserver/api/v1")


class I18nTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ctx = client()
        cls._ctx.__enter__()
        cls.hr = client()
        r = cls.hr.post("/auth/login", data={"username": "hr", "password": "hr123"})
        cls.hr.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    def test_parse_accept_language(self):
        self.assertEqual(i18n.parse_accept_language("km-KH,km;q=0.9,en;q=0.8"), "km")
        self.assertEqual(i18n.parse_accept_language("fr-FR,en;q=0.5"), "en")
        self.assertEqual(i18n.parse_accept_language(None), "en")

    def test_errors_follow_the_request_language(self):
        bad = {"username": "hr", "password": "wrong-password"}
        english = client().post("/auth/login", data=bad).json()["detail"]
        khmer = client().post("/auth/login", data=bad, headers={"Accept-Language": "km"}).json()["detail"]
        self.assertEqual(english, "Invalid username or password")
        self.assertNotEqual(khmer, english)
        self.assertRegex(khmer, "[ក-៿]")  # Khmer script

    def test_not_found_in_khmer(self):
        r = self.hr.get("/employees/999999", headers={"Accept-Language": "km"})
        self.assertEqual(r.status_code, 404)
        self.assertRegex(r.json()["detail"], "[ក-៿]")

    def test_machine_codes_are_never_translated(self):
        i18n.set_language("km")
        try:
            self.assertEqual(i18n.gettext_("otp_required"), "otp_required")
        finally:
            i18n.set_language("en")

    def test_khmer_dates(self):
        from datetime import datetime
        i18n.set_language("km")
        try:
            self.assertEqual(i18n.month_name(10), "តុលា")
            self.assertEqual(i18n.day_name(datetime(2026, 10, 5)), "ច័ន្ទ")
            self.assertEqual(i18n.format_time(datetime(2026, 10, 5, 14, 30)), "02:30 ល្ងាច")
        finally:
            i18n.set_language("en")

    def test_payslip_pdf_in_khmer(self):
        rows = self.hr.get("/payroll", params={"limit": 1}).json()
        if not rows:
            self.skipTest("no payroll rows in the demo data")
        r = self.hr.get(f"/payroll/{rows[0]['id']}/pdf", headers={"Accept-Language": "km"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.content.startswith(b"%PDF"))
        if pdf._khmer_fonts() is not None:
            self.assertIn(b"Khmer", r.content)  # the Khmer font is embedded


if __name__ == "__main__":
    unittest.main()
