"""Tests for pagination, login lockout, password-hash upgrade, secret encryption, proxy IPs,
the health check, response schemas and Alembic migrations of an old database.

Run from the project root:  pytest
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_TMP = tempfile.mkdtemp()
os.environ.setdefault("HRMS_DATABASE_URL", f"sqlite:///{os.path.join(_TMP, 'test.db')}")
os.environ.setdefault("HRMS_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")
os.environ.setdefault("HRMS_DEMO_PASSWORD_CHANGE", "false")  # sign in with the demo accounts as they are

import bcrypt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.core.config import config  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models import Setting, User  # noqa: E402
from backend.services.settings_service import get_settings  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def client(ip=("127.0.0.1", 50000)):
    return TestClient(app, client=ip, base_url="http://testserver/api/v1")


def login(c, username, password):
    r = c.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return r.json()


class StandardsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ctx = client()
        cls._ctx.__enter__()
        cls.admin = client(); login(cls.admin, "admin", "admin123")
        cls.hr = client(); login(cls.hr, "hr", "hr123")

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    def new_user(self, email):
        r = self.admin.post("/employees", json={
            "first_name": "Std", "last_name": "Test", "email": email, "hire_date": "2026-01-05",
            "position": "Accountant", "salary": 4500, "department_id": 1, "status": "Active"})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    # ----------------------------------------------------------- pagination
    def test_pagination(self):
        r = self.hr.get("/employees", params={"limit": 3, "offset": 2})
        self.assertEqual(len(r.json()), 3)
        total = int(r.headers["X-Total-Count"])
        self.assertGreaterEqual(total, 7)  # the demo company has 7 employees
        self.assertEqual(r.json()[0]["id"], self.hr.get("/employees").json()[2]["id"])
        self.assertEqual(len(self.hr.get("/employees").json()), total)  # no limit = everything
        self.assertEqual(self.hr.get("/employees", params={"limit": 0}).status_code, 422)
        audit = self.admin.get("/settings/audit", params={"limit": 3})
        self.assertEqual(len(audit.json()), 3)
        self.assertIn("X-Total-Count", audit.headers)

    # -------------------------------------------------------- login lockout
    def test_lockout_after_repeated_failures(self):
        created = self.new_user("lock.out@workflow.io")
        c = client()
        for _ in range(config.login_max_failures):
            self.assertEqual(c.post("/auth/login", data={"username": created["username"],
                                                         "password": "wrong"}).status_code, 401)
        r = c.post("/auth/login", data={"username": created["username"], "password": created["initial_password"]})
        self.assertEqual(r.status_code, 429)  # locked even with the right password
        self.assertIn("Too many failed sign-in attempts", r.json()["detail"])
        # an admin password reset lifts the lock
        uid = next(u["id"] for u in self.admin.get("/users").json() if u["username"] == created["username"])
        temp = self.admin.post(f"/users/{uid}/reset-password").json()["temporary_password"]
        self.assertEqual(c.post("/auth/login", data={"username": created["username"],
                                                     "password": temp}).status_code, 200)

    # ------------------------------------------------ password hash upgrade
    def test_old_bcrypt_hash_is_upgraded_to_argon2(self):
        created = self.new_user("old.hash@workflow.io")
        with SessionLocal() as db:
            user = db.query(User).filter(User.username == created["username"]).one()
            user.password_hash = bcrypt.hashpw(b"OldPass123", bcrypt.gensalt()).decode()
            user.must_change_password = False
            db.commit()
        login(client(), created["username"], "OldPass123")
        with SessionLocal() as db:
            user = db.query(User).filter(User.username == created["username"]).one()
            self.assertTrue(user.password_hash.startswith("$argon2id$"))

    # ---------------------------------------------------- secret encryption
    def test_smtp_password_is_encrypted_at_rest(self):
        self.admin.put("/settings", json={"smtp_password": "s3cret-mail-pass"})
        with SessionLocal() as db:
            raw = db.get(Setting, "smtp_password").value
            self.assertNotIn("s3cret-mail-pass", raw)
            self.assertIn("enc:", raw)
            self.assertEqual(get_settings(db)["smtp_password"], "s3cret-mail-pass")
        self.assertNotIn("smtp_password", self.admin.get("/settings").json())

    # ------------------------------------------------------- proxy client IP
    def test_forwarded_ip_only_trusted_from_configured_proxy(self):
        user = client(("10.9.9.9", 1)); login(user, "employee", "emp123")
        headers = {"X-Forwarded-For": "192.168.7.7"}
        self.assertEqual(user.get("/attendance/policy", headers=headers).json()["ip"], "10.9.9.9")  # ignored
        with mock.patch.object(config, "trusted_proxies", ["10.9.9.9"]):
            self.assertEqual(user.get("/attendance/policy", headers=headers).json()["ip"], "192.168.7.7")

    # ---------------------------------------------------- health & schemas
    def test_health_reports_database(self):
        r = TestClient(app).get("/")
        self.assertEqual(r.json()["database"], "ok")
        self.assertEqual(r.json()["status"], "ok")

    def test_openapi_documents_responses(self):
        spec = TestClient(app).get("/openapi.json").json()
        for name in ("EmployeeOut", "AttendanceOut", "PayrollOut", "LeaveOut", "SessionUser", "SettingsOut"):
            self.assertIn(name, spec["components"]["schemas"])
        employees = spec["paths"]["/api/v1/employees"]["get"]["responses"]["200"]["content"]["application/json"]
        self.assertIn("EmployeeOut", str(employees["schema"]))

    # ------------------------------------------------------------- Alembic
    def test_legacy_database_is_migrated(self):
        """A database made by an older version (create_all, no alembic_version) gets upgraded."""
        db_path = Path(_TMP) / "legacy.db"
        script = (  # noqa: UP031 - a script template
            "import sqlite3\n"
            "from backend.core.database import engine\n"
            "from backend import models\n"
            "models.Base.metadata.create_all(engine)\n"
            "con = sqlite3.connect(r'%s')\n"
            "con.execute('ALTER TABLE users DROP COLUMN totp_enabled')\n"
            "con.execute('DROP TABLE login_attempts'); con.commit(); con.close()\n"
            "from backend.core.migrations import upgrade_database\n"
            "upgrade_database()\n"
            "con = sqlite3.connect(r'%s')\n"
            "cols = [r[1] for r in con.execute('PRAGMA table_info(users)')]\n"
            "tables = [r[0] for r in con.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")]\n"
            "ver = con.execute('SELECT version_num FROM alembic_version').fetchone()[0]\n"
            "print('totp_enabled' in cols, 'login_attempts' in tables, ver)\n"
        ) % (db_path, db_path)
        env = dict(os.environ, HRMS_DATABASE_URL=f"sqlite:///{db_path}", HRMS_LOG_LEVEL="WARNING")
        out = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        head = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini"))).get_current_head()
        self.assertEqual(out.stdout.split()[-3:], ["True", "True", head])


if __name__ == "__main__":
    unittest.main()
