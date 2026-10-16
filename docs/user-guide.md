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

HR or Admin can fix missed entries with **Manual Log Entry**.

## Accounts & Security

- **New employees** get a login automatically: the username is the part of their email before `@`,
  and HR is shown a one-time temporary password. The employee picks their own password at first sign-in.
- **Change password:** user menu → *Change Password*. This signs out the account's other sessions.
- **Forgot password:** an Admin uses *Settings → Authentication & Users → User Accounts → Reset Password*.
- **Two-factor authentication:** user menu → *Two-Factor Authentication* (Google / Microsoft
  Authenticator). Admins can require 2FA for staff accounts, and *Reset 2FA* helps a user who lost their phone.
- **Login lockout:** 5 failed sign-ins within 15 minutes lock the account for 15 minutes.
  An Admin password reset lifts the lock.
- **Secret key:** `backend/.secret_key` signs tokens and encrypts stored secrets. Keep it private,
  and keep it when moving the database.

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
