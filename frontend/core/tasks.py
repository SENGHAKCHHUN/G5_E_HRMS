"""Run server calls in the background so the window never freezes.

Tkinter widgets may only be touched from the main thread, so the work runs in a
thread pool and the result is handed back on the main thread via `widget.after`.

    run(self, api.get_employees, on_done=self.render)

Errors go to `on_error` if given, otherwise to the app-wide handler (toast message,
or back to the login screen when the session has expired).
"""
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from tkinter import Misc

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="hrms-api")
_hooks: dict[str, Callable] = {}
_pending = {"count": 0}
POLL_MS = 25


def set_error_handler(handler: Callable[[Exception], None]) -> None:
    _hooks["error"] = handler


def set_busy_listener(listener: Callable[[bool], None]) -> None:
    """Called with True when background work starts and False when all of it has finished."""
    _hooks["busy"] = listener


def pending() -> int:
    return _pending["count"]


def _change_pending(delta: int):
    before = _pending["count"]
    _pending["count"] += delta
    if "busy" in _hooks and (before == 0) != (_pending["count"] == 0):
        try:
            _hooks["busy"](_pending["count"] > 0)
        except Exception:  # noqa: BLE001 - the indicator must never break the work itself
            pass


def run(widget: Misc, fn: Callable, *args, on_done: Callable | None = None,
        on_error: Callable[[Exception], None] | None = None, **kwargs) -> Future:
    """Run fn(*args, **kwargs) in the background; call on_done(result) on the main thread."""
    future = _executor.submit(fn, *args, **kwargs)
    _change_pending(+1)
    # poll on the root window: a destroyed widget drops its pending `after` callbacks,
    # which would leave this call counted as running forever
    root = widget._root()

    def poll():
        if not future.done():
            _schedule()
            return
        _change_pending(-1)
        try:
            alive = bool(widget.winfo_exists())
        except Exception:  # noqa: BLE001 - window already destroyed
            alive = False
        if not alive:
            return  # the screen was closed meanwhile; drop the result
        error = future.exception()
        if error is not None:
            (on_error or _hooks.get("error") or _raise)(error)
        elif on_done is not None:
            on_done(future.result())

    def _schedule():
        try:
            root.after(POLL_MS, poll)
        except Exception:  # noqa: BLE001 - app closed before the work finished
            _change_pending(-1)

    _schedule()
    return future


def _raise(error: Exception):
    raise error
