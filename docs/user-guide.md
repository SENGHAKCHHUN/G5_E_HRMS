# User Guide

[← Back to README](../README.md)

## Check-in / Check-out Rules

Employees clock in and out on the **Attendance & Time** screen. The backend enforces these rules,
which an Admin can change in **Settings → Attendance & Policies**:

1. **Server time:** times come from the server clock, so changing the computer's clock has no effect.
2. **Check-in window:** accepted between 06:00 and 12:00 by default.
3. **Office network only:** clocking in/out only works from office networks (by default this
   computer and private LAN ranges such as `192.168.0.0/16`). Everything else works from anywhere.
4. **Remote staff exempt:** employees with work mode *Remote* may clock in from anywhere.
5. **Once a day:** one check-in and one check-out. Arriving after 09:00 + 15 min grace is **Late**.
6. **Work week:** check-in is refused on non-working days (Settings → General).
7. **Shifts past midnight:** a check-out after midnight and before 04:00 (*Late Check-out Until*)
   ends the previous day's shift. If *Check-in Opens* is earlier, that time ends the grace instead.
8. **Half Day:** working less than 4 hours (*Half Day Below*, 0 = off) is recorded as **Half Day**.

When a day is over, the server closes it (Settings → Attendance & Policies → *Closing the Day*):

- **Mark no-shows Absent:** once check-in has closed on a working day, every employee without a
  record, approved leave or *On Leave* status gets an **Absent** record. Employees hired later and
  terminated employees are skipped. This starts on the day the rule is first applied; older days are
  not filled in.
- **Close forgotten check-outs:** a check-out still missing after the day (and the after-midnight
  grace) is over is set to *Shift End*, and the Half Day rule is applied.

Records made by these rules have source **auto**. HR or Admin can fix any record with **Manual Log Entry**.

## Accounts & Security

- **New employees** get a login automatically: the username is the part of their email before `@`,
  and HR is shown a one-time temporary password (with a *Copy* button; it is not shown again). The employee
  picks their own password at first sign-in.
- **Demo accounts** (`admin`, `hr`, `employee`) must also choose a new password at their first sign-in,
  because their passwords are public.
- **Change password:** user menu → *Change Password*. This signs out the account's other sessions.
- **Forgot password:** an Admin uses *Settings → Authentication & Users → User Accounts → Reset Password*.
- **Two-factor authentication:** user menu → *Two-Factor Authentication* (Google / Microsoft
  Authenticator). Admins can require 2FA for staff accounts, and *Reset 2FA* helps a user who lost their phone.
- **Login lockout:** 5 failed sign-ins within 15 minutes lock the account for 15 minutes.
  An Admin password reset lifts the lock.
- **Secret key:** `backend/.secret_key` signs tokens and encrypts stored secrets. Keep it private,
  and keep it when moving the database.

## Leave

- Employees request leave on **Leave Management**; an HR Manager or Admin approves or rejects it
  (with a reason). Nobody can review their own request.
- **Leave days are working days:** only days in the work week (Settings → General) count. A
  Thursday–Monday request is 3 days with a Monday–Friday week, and a request with no working days is
  refused. Allowances per year: Annual 20, Sick 10, Casual 5 days.
- Annual, Sick, Casual and Maternity/Paternity leave are paid; **Unpaid** leave is deducted in payroll.

## Payroll

Payroll is run in two steps on **Payroll & Payslips** (HR Manager or Admin):

1. **Calculate Payroll** creates a line for everyone employed in the month and recalculates every
   line that is not paid yet, using the current salaries, tax and pension rates and employment dates.
   Run it again as often as needed: bonuses, adjustments and notes are kept.
2. Review the lines. Open a payslip and press **Edit** to set a bonus, an adjustment (positive for
   an extra payment, negative for a deduction such as a salary advance) and a note.
3. **Mark as Paid** locks the calculated lines. Paid lines never change.

Rules:

- **Gross** = base salary + overtime + bonus + adjustment.
  **Net pay** = gross − (unpaid days + income tax + pension + health insurance).
- **Unpaid days** (Settings → Payroll → *Deduct unpaid days*): each **Absent** day and each working
  day of approved **Unpaid** leave deducts one daily rate; a **Half Day** deducts half of one.
  Daily rate = monthly salary ÷ working days in the month (the work week in Settings → General).
  Annual, Sick, Casual and Maternity/Paternity leave are paid and deduct nothing.
- **Overtime** (*Overtime Pay Rate*, default 1.5, 0 = not paid): time after *Overtime Counted
  After* (18:00) is paid at hourly rate × 1.5. Hourly rate = daily rate ÷ shift hours
  (*Shift Start* to *Shift End*). Half Days never count as overtime.
- **Income tax:** a flat *Income Tax Rate*, or **progressive brackets** written as
  `from:rate`, for example `0:0, 1500000:5, 2000000:10, 8500000:15, 12500000:20` for monthly pay in
  KHR (check the current rates with your accountant). Each rate applies only to the part of pay
  above its amount. With *Tax bonus and overtime* on (default), bonus and overtime are taxed too.
  The adjustment is never taxed.
- **Pension** is taken from the base salary earned (after unpaid days).
- **Health insurance** is a fixed monthly amount (85), or a higher one (120) from a base salary of
  6,000. All three numbers are in Settings → Payroll.
- **Who is paid:** people hired on or before the last day of the month and not terminated before its
  first day.
- **Joining or leaving month:** base salary × days employed ÷ days in the month. The payslip shows
  the paid days (e.g. *15 of 31*).
- **Leavers:** edit the employee, set the status to *Terminated* and enter the **Last Working Day**
  (empty = today). Use this instead of deleting the employee, which also deletes their payslips.

## Documents, Email & Backups

- **PDF:** payslips (*Payroll → Payslip → Save PDF*) and the dashboard summary
  (*Dashboard → Export PDF Summary*) are generated in the app's language. Khmer PDFs need a Khmer
  font (*Khmer UI* on Windows, Khmer OS on Linux); without one the PDF is made in English.
- **Email:** set up SMTP in *Settings → Email (SMTP)*. HR can then email payslips, and employees are
  emailed when their leave is approved or rejected.
- **Backup:** *Settings → Backend & Database → Download Backup* saves a copy of the SQLite database,
  even while the server is running.

## Language

Switch between English and Khmer on the login screen, at the bottom of the sidebar, or in the user menu.
The choice is saved per computer.
