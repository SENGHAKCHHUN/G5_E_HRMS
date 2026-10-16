"""Smoke test: sign in as each role and open every screen, in English and Khmer.

The frontend talks to the real FastAPI app in-process (a throw-away database), so this
checks the screens, the API client and the backend together. Needs a display (Tk).
"""
import os
import tempfile
import time

import pytest

_TMP = tempfile.mkdtemp()
os.environ.setdefault("HRMS_DATABASE_URL", f"sqlite:///{os.path.join(_TMP, 'screens.db')}")
os.environ.setdefault("HRMS_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")

tk = pytest.importorskip("tkinter")
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app as backend_app  # noqa: E402


class _InProcessHttp:
    """Gives the frontend's requests-style calls to FastAPI's TestClient."""

    def __init__(self, client):
        self.client = client

    def request(self, method, url, params=None, json=None, data=None, headers=None, timeout=None):
        return self.client.request(method, url, params=params, json=json, data=data, headers=headers)

    def get(self, url, timeout=None):
        return self.client.get(url)


@pytest.fixture(scope="module")
def backend():
    with TestClient(backend_app, client=("10.1.2.3", 50000)) as client:  # runs migrations + seed
        yield client


@pytest.fixture(scope="module")
def window(backend, tmp_path_factory):
    """One Tk root for the whole module (icons are cached per root, so it is never recreated)."""
    from core import prefs
    from core.api_client import api
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(prefs, "PATH", tmp_path_factory.mktemp("prefs") / "prefs.json")  # never the real file
        mp.setattr(api, "http", _InProcessHttp(backend))
        mp.setattr(api, "base_url", "http://testserver")
        try:
            from app import HRMSApp
            root = HRMSApp()
        except tk.TclError as exc:
            pytest.skip(f"no display: {exc}")
        root.withdraw()
        yield root
        api.logout()
        root.destroy()


@pytest.fixture
def gui(window):
    from core import tasks
    from core.state import state
    errors: list[BaseException] = []
    window.report_callback_exception = lambda _t, exc, _tb: errors.append(exc)
    tasks.set_error_handler(errors.append)
    state.set_language("en")
    window.show_login()
    _settle(window)
    yield window, errors
    tasks.set_error_handler(window.handle_error)


def _settle(window, seconds: float = 30):
    """Process events until every background call has finished and been rendered."""
    from core import tasks
    deadline = time.monotonic() + seconds
    quiet = 0
    while time.monotonic() < deadline:
        window.update()
        quiet = quiet + 1 if tasks.pending() == 0 else 0
        if quiet > 5:
            return
        time.sleep(0.02)
    raise AssertionError("background calls did not finish")


def _open_every_screen(window, errors):
    from app import Shell
    shell = window.current
    assert isinstance(shell, Shell)
    for key, *_rest in shell.nav:
        shell.navigate(key)
        _settle(window)
        assert not errors, f"{key}: {errors!r}"
    return shell


@pytest.mark.parametrize("username,password,screens", [
    ("admin", "admin123", 7),
    ("hr", "hr123", 6),
    ("employee", "emp123", 4),
])
def test_every_screen_opens_in_both_languages(gui, username, password, screens):
    from core.api_client import api
    from core.i18n import _
    window, errors = gui
    window.after_login(api.login(username, password))
    _settle(window)
    shell = _open_every_screen(window, errors)
    assert len(shell.nav) == screens

    shell.change_language("km")  # rebuilds the window in Khmer
    _settle(window)
    assert _("Dashboard") == "ផ្ទាំងគ្រប់គ្រង"
    _open_every_screen(window, errors)


def test_expired_session_returns_to_login(gui):
    from core.api_client import api
    from views.login_view import LoginView
    window, errors = gui
    window.after_login(api.login("hr", "hr123"))
    _settle(window)
    api.token = "not-a-valid-token"
    from core import tasks
    tasks.set_error_handler(window.handle_error)  # use the app's real handler for this one
    window.current.navigate("employees")
    _settle(window)
    assert isinstance(window.current, LoginView)
    assert not errors
