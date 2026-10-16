"""Small helpers shared by the screens."""
from collections.abc import Callable

from core import tasks
from core.api_client import ApiError


def submit(dialog, call: Callable, error_label, on_done: Callable):
    """Run a save in the background; show an ApiError (or a ValueError from local checks) inside the
    dialog instead of a toast."""
    def failed(error: Exception):
        if not isinstance(error, (ApiError, ValueError)):
            raise error
        error_label.configure(text=str(error))
    error_label.configure(text="")
    tasks.run(dialog, call, on_done=on_done, on_error=failed)
