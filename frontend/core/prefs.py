"""Per-computer preferences (remembered username, language, theme, accent colour, UI scaling).

Stored as JSON in the user's home folder. Passwords are never stored.
"""
import json
from pathlib import Path

PATH = Path.home() / ".workflow_hrms.json"
DEFAULTS = {"username": "", "remember": False, "language": "en", "theme": "dark", "accent": "Blue",
            "scaling": 1.0}


def load() -> dict:
    data = dict(DEFAULTS)
    try:
        data.update(json.loads(PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return data


def save(**changes) -> None:
    data = load()
    data.update(changes)
    try:
        PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # preferences are a convenience; never fail the app over them
