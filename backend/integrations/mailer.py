"""Sending email through the SMTP server configured in Settings > Email (SMTP)."""
import smtplib
from email.message import EmailMessage


class EmailNotConfigured(Exception):
    pass


def is_configured(settings: dict) -> bool:
    return bool(settings.get("smtp_host") and settings.get("smtp_from"))


def send(settings: dict, to: str, subject: str, body: str,
         attachments: list[tuple[str, bytes, str]] | None = None) -> None:
    """attachments: [(filename, data, mime type 'application/pdf')]. Raises on failure."""
    if not is_configured(settings):
        raise EmailNotConfigured("Email is not configured. Set up SMTP in Settings > Email (SMTP).")
    msg = EmailMessage()
    msg["From"] = settings["smtp_from"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    for filename, data, mime in attachments or []:
        maintype, subtype = mime.split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

    port = int(settings.get("smtp_port") or 587)
    if port == 465:
        server = smtplib.SMTP_SSL(settings["smtp_host"], port, timeout=15)
    else:
        server = smtplib.SMTP(settings["smtp_host"], port, timeout=15)
    with server:
        if port != 465 and settings.get("smtp_tls", True):
            server.starttls()
        if settings.get("smtp_user"):
            server.login(settings["smtp_user"], settings.get("smtp_password", ""))
        server.send_message(msg)
