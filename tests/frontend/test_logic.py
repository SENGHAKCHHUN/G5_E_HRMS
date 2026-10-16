"""Unit tests for the frontend logic modules (no window needed)."""
from datetime import date, datetime

from core import i18n
from core.state import state
from logic import attendance as A
from logic import formatting as F
from logic import forms, labels
from logic import leave as L


def test_money_uses_currency_and_sign():
    assert F.money(6130.5, symbol="$") == "$6,130.50"
    assert F.money(-20, symbol="$") == "-$20.00"
    assert F.money(5, sign=True, symbol="$") == "+$5.00"
    state.settings = {"currency": "KHR"}
    try:
        assert F.money(1000).endswith("1,000.00")
        assert not F.money(1000).startswith("$")
    finally:
        state.settings = {}


def test_duration_in_both_languages():
    assert F.duration(8 * 3600 + 7 * 60) == "8h 07m"
    assert F.duration(-5) == "0h 00m"
    i18n.set_language("km")
    assert F.duration(3600) == "1ម៉ោង 00នាទី"


def test_recent_months_cross_year():
    assert F.recent_months(3, date(2026, 2, 10)) == ["2026-02", "2026-01", "2025-12"]


def test_month_and_date_labels():
    assert F.month_label("2026-10") == "October 2026"
    assert i18n.format_date("2026-10-05") == "Oct 05, 2026"
    assert i18n.format_time("13:05:00") == "01:05 PM"
    i18n.set_language("km")
    assert F.month_label("2026-10") == "តុលា 2026"
    assert i18n.format_time("09:30:00") == "09:30 ព្រឹក"


def test_long_khmer_text_gets_invisible_split_points():
    text = "ការកំណត់ក្រុមហ៊ុន គោលការណ៍សុវត្ថិភាព អ៊ីមែល និងមូលដ្ឋានទិន្នន័យក្នុងម៉ាស៊ីន"
    safe = i18n.safe_khmer(text)
    assert safe != text and i18n.plain(safe) == text
    assert "្﻿" not in safe          # never between a consonant and its subscript
    assert i18n.safe_khmer(safe) == safe        # applied once only
    assert i18n.safe_khmer("ផ្ទាំងគ្រប់គ្រង") == "ផ្ទាំងគ្រប់គ្រង"  # short text unchanged
    assert i18n.safe_khmer("A long English sentence without any Khmer letters in it") == \
        "A long English sentence without any Khmer letters in it"
    i18n.set_language("km")
    template = i18n._("Company preferences, security policy, email and the local database")
    assert "﻿" in template
    assert i18n._("{hours:g} scheduled hours per week").format(hours=45).startswith("45 ")  # placeholders intact


def test_worked_and_overtime_seconds():
    rec = {"date": "2026-10-01", "check_in": "09:00:00", "check_out": "18:30:00", "status": "On Time"}
    assert A.worked_seconds(rec) == 9.5 * 3600
    assert A.overtime_seconds(rec, "18:00") == 30 * 60
    assert A.overtime_seconds({**rec, "status": "Half Day"}) == 0
    open_today = {"date": "2026-10-05", "check_in": "09:00:00", "check_out": None}
    assert A.worked_seconds(open_today, datetime(2026, 10, 5, 10, 0)) == 3600
    assert A.worked_seconds({**open_today, "date": "2026-10-04"}, datetime(2026, 10, 5, 10, 0)) == 0


def test_status_label_and_punctuality():
    late = {"status": "Late", "check_in": "09:22:00"}
    assert A.status_label(late, "09:00") == "Late (22m)"
    assert A.punctuality({"worked_days": 4, "on_time": 3}) == 75
    assert A.punctuality({"worked_days": 0}) == 0
    i18n.set_language("km")
    assert A.translate_status("On Time") == "ទាន់ពេល"


def test_leave_validation():
    balance = {"Annual": {"remaining": 2}}
    assert L.validate_request("2026-10-06", "2026-10-07", "Annual", balance) == (2, None)
    days, error = L.validate_request("2026-10-06", "2026-10-08", "Annual", balance)
    assert days == 3 and "2" in error
    assert L.validate_request("2026-10-08", "2026-10-06", "Sick", {})[1]
    assert L.validate_request("bad", "2026-10-06", "Sick", {})[1]


def test_employee_form():
    values = {"first_name": "Dara", "last_name": "Sok", "email": "dara@example.com", "phone": "",
              "gender": "Male", "hire_date": "2026-01-05", "salary": "1200", "position": "Engineer",
              "status": "Active", "employment": "Full-time", "work_mode": "Remote", "role": "Employee"}
    data, error = forms.employee(values, 3)
    assert error is None and data["salary"] == 1200 and data["shift"] == "Remote Shift"
    assert forms.employee({**values, "email": "nope"}, 3)[1]
    assert forms.employee({**values, "salary": "-1"}, 3)[1]


def test_position_and_department_forms():
    assert forms.position({"title": "Dev", "grade": "E-2", "min_salary": "900", "max_salary": "500"}, 1)[1]
    data, error = forms.position({"title": "Dev", "grade": "E-2", "min_salary": "500", "max_salary": "900"}, 1)
    assert error is None and data["department_id"] == 1
    assert forms.department({"name": ""})[1]
    assert forms.department({"name": "Ops", "budget": "x"})[1]


def test_manual_attendance_form():
    ok = {"date": "2026-10-01", "check_in": "09:00", "check_out": "17:00", "status": "On Time"}
    data, error = forms.manual_attendance(ok, 7)
    assert error is None and data["check_in"] == "09:00:00"
    assert forms.manual_attendance(ok, None)[1]
    assert forms.manual_attendance({**ok, "check_out": "08:00"}, 7)[1]
    absent, _ = forms.manual_attendance({**ok, "status": "Absent"}, 7)
    assert absent["check_in"] is None and absent["check_out"] is None


def test_password_rules():
    assert forms.password_change("abc12345", "abc12345") is None
    assert forms.password_change("abc12345", "different1")
    assert forms.password_change("short1", "short1")
    assert forms.password_change("12345678", "12345678")


def test_labels_translate_but_keep_values():
    i18n.set_language("km")
    assert labels.show(labels.EMPLOYEE_STATUS, "Active") != "Active"
    assert labels.show(labels.EMPLOYEE_STATUS, "Unknown") == "Unknown"
    assert set(labels.choices(labels.ROLE)) == {"Admin", "HR Manager", "Employee"}
