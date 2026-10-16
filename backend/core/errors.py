"""Domain errors raised by the service layer.

Services know nothing about HTTP; main.py turns these into responses with the
matching status code and {"detail": message} body. Messages are English templates
that are translated into the caller's language when the response is built:

    raise Conflict("Overlaps with existing request LV-{id}", id=42)
"""
from .i18n import t


class DomainError(Exception):
    status_code = 400

    def __init__(self, template: str, **params):
        super().__init__(template.format(**params) if params else template)
        self.template = template
        self.params = params

    @property
    def message(self) -> str:
        """The message in the current request's language."""
        return t(self.template, **self.params)


class BadRequest(DomainError):
    status_code = 400


class Unauthorized(DomainError):
    status_code = 401


class Forbidden(DomainError):
    status_code = 403


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    status_code = 409


class TooManyRequests(DomainError):
    """E.g. too many failed logins: the account is temporarily locked."""
    status_code = 429


class ExternalServiceError(DomainError):
    """A system we depend on (e.g. the SMTP server) failed."""
    status_code = 502
