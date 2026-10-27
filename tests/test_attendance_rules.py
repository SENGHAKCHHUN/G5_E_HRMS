"""Day closing rules (auto Absent, forgotten check-out), Half Day and check-out after midnight.

Uses its own in-memory database, so moving the clock forward does not touch the shared test database.
Run from the project root:  python -m unittest discover tests -v
"""
import os
import unittest
from datetime import date, datetime, time
from types import SimpleNamespace

os.environ.setdefault("HRMS_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.core.database import Base  # noqa: E402
from backend.models import Attendance, Department, Employee, LeaveRequest  # noqa: E402
from backend.repositories import attendance_repo, setting_repo  # noqa: E402
from backend.services import attendance_service as A  # noqa: E402
from backend.services.settings_service import DEFAULTS  # noqa: E402

MON, TUE, SAT = date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 10)


def settings(**overrides):
    return {**DEFAULTS, **overrides}


def at(day: date, hm: str) -> datetime:
    return datetime.combine(day, time.fromisoformat(hm))


class PureRuleTests(unittest.TestCase):
    def test_worked_time_past_midnight(self):
        rec = SimpleNamespace(date=MON, check_in=time(18, 0), check_out=time(1, 30))
        self.assertEqual(A.worked_seconds(rec, None), 7.5 * 3600)
        open_rec = SimpleNamespace(date=MON, check_in=time(18, 0), check_out=None)
        self.assertEqual(A.worked_seconds(open_rec, at(TUE, "01:00")), 7 * 3600)

    def test_half_day(self):
        rec = SimpleNamespace(date=MON, check_in=time(9, 0), check_out=time(12, 59), status="On Time")
        self.assertEqual(A.checkout_status(rec, settings()), "Half Day")
        self.assertEqual(A.checkout_status(rec, settings(half_day_hours=0)), "On Time")
        rec.check_out = time(13, 0)
        self.assertEqual(A.checkout_status(rec, settings()), "On Time")


class DayClosingTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.db = Session(engine)
        self.db.add(Department(id=1, name="Ops"))
        for i, status in enumerate(["Active", "Active", "On Leave", "Terminated", "Active"], start=1):
            self.db.add(Employee(id=i, first_name="E", last_name=str(i), email=f"e{i}@x.test", position="P",
                                 salary=1, department_id=1, status=status,
                                 hire_date=date(2026, 1, 1) if i != 5 else date(2026, 12, 1)))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def rec(self, emp_id, day):
        return attendance_repo.get_for_day(self.db, emp_id, day)

    def test_no_shows_marked_absent_after_checkin_closes(self):
        s = settings()
        self.db.add(Attendance(employee_id=1, date=MON, check_in=time(8, 50), status="On Time"))
        self.db.add(LeaveRequest(employee_id=2, type="Annual", start_date=MON, end_date=MON, reason="",
                                 status="Approved"))
        self.db.commit()
        A.close_days(self.db, s, at(MON, "11:00"))  # check-in still open: nothing yet
        self.assertIsNone(self.rec(1, MON).check_out)
        self.assertEqual(attendance_repo.count(self.db), 1)

        A.close_days(self.db, s, at(MON, "12:01"))
        self.assertEqual(attendance_repo.count(self.db), 1)  # 1 came, 2 on leave, 3 On Leave, 4 left, 5 not hired
        self.db.delete(self.db.get(LeaveRequest, 1))
        self.db.commit()
        A.close_days(self.db, s, at(TUE, "12:01"))
        self.assertEqual(self.rec(2, TUE).status, "Absent")
        self.assertEqual(self.rec(2, TUE).source, "auto")
        self.assertIsNone(self.rec(2, MON))  # Monday was already closed with the leave in place

    def test_first_run_does_not_fill_in_history(self):
        A.close_days(self.db, settings(), at(TUE, "12:01"))
        self.assertIsNone(self.rec(1, MON))
        self.assertEqual(self.rec(1, TUE).status, "Absent")

    def test_non_working_days_and_switch_off(self):
        setting_repo.save(self.db, A.CLOSED_THROUGH, "2026-10-09")
        A.close_days(self.db, settings(), at(SAT, "13:00"))
        self.assertIsNone(self.rec(1, SAT))
        setting_repo.save(self.db, A.CLOSED_THROUGH, MON.isoformat())
        A.close_days(self.db, settings(auto_absent=False), at(TUE, "13:00"))
        self.assertIsNone(self.rec(1, TUE))

    def test_forgotten_checkout_closed_at_shift_end(self):
        self.db.add(Attendance(employee_id=1, date=MON, check_in=time(9, 0), status="On Time"))
        self.db.add(Attendance(employee_id=2, date=MON, check_in=time(16, 0), status="Late"))
        self.db.commit()
        s = settings()
        A.close_days(self.db, s, at(TUE, "03:59"))  # still inside the after-midnight grace
        self.assertIsNone(self.rec(1, MON).check_out)
        A.close_days(self.db, s, at(TUE, "04:00"))
        self.assertEqual((self.rec(1, MON).check_out, self.rec(1, MON).status, self.rec(1, MON).source),
                         (time(18, 0), "On Time", "auto"))
        self.assertEqual(self.rec(2, MON).status, "Half Day")  # 16:00-18:00

    def test_forgotten_checkout_left_open_when_off(self):
        self.db.add(Attendance(employee_id=1, date=MON, check_in=time(9, 0), status="On Time"))
        self.db.commit()
        A.close_days(self.db, settings(auto_checkout=False), at(TUE, "10:00"))
        self.assertIsNone(self.rec(1, MON).check_out)

    def test_checkout_after_midnight_closes_yesterday(self):
        self.db.add(Attendance(employee_id=1, date=MON, check_in=time(17, 0), status="Late"))
        self.db.commit()
        emp = self.db.get(Employee, 1)
        s = settings()
        self.assertIs(A._open_record(self.db, emp, at(TUE, "01:30"), s), self.rec(1, MON))
        self.assertIsNone(A._open_record(self.db, emp, at(TUE, "04:30"), s))


if __name__ == "__main__":
    unittest.main()
