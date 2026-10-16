"""The app's runtime state in one place (instead of globals scattered over modules).

There is exactly one AppState (`state`). It holds who is signed in, the server
settings, and the look chosen on this computer (language, theme, accent, scaling).
"""
from dataclasses import dataclass, field

from . import i18n, prefs

CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "SGD": "S$", "KHR": "៛"}


@dataclass
class AppState:
    session: dict | None = None            # signed-in user (from /auth/login)
    settings: dict = field(default_factory=dict)   # server settings (company, currency, shift ...)
    language: str = i18n.DEFAULT
    theme: str = "dark"
    accent: str = "Blue"
    scaling: float = 1.0

    # ------------------------------------------------------------ helpers
    @property
    def role(self) -> str | None:
        return self.session["role"] if self.session else None

    @property
    def is_staff(self) -> bool:
        return self.role in ("Admin", "HR Manager")

    @property
    def currency_symbol(self) -> str:
        code = self.settings.get("currency", "USD")
        return CURRENCY_SYMBOLS.get(code, code + " ")

    # -------------------------------------------------------- preferences
    def load_preferences(self) -> None:
        saved = prefs.load()
        self.language = saved["language"]
        self.theme = saved["theme"]
        self.accent = saved["accent"]
        self.scaling = float(saved["scaling"])
        i18n.set_language(self.language)

    def set_language(self, code: str) -> None:
        self.language = code
        i18n.set_language(code)
        prefs.save(language=code)

    def sign_out(self) -> None:
        self.session = None
        self.settings = {}


state = AppState()
