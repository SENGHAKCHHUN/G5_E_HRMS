"""Frontend tests import the app the way it runs: with frontend/ on sys.path."""
import sys
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
if str(FRONTEND) not in sys.path:
    sys.path.insert(0, str(FRONTEND))


@pytest.fixture(autouse=True)
def english():
    """Every test starts (and ends) in English with no signed-in user."""
    from core import i18n
    from core.state import state
    i18n.set_language("en")
    state.language = "en"
    yield
    i18n.set_language("en")
    state.language = "en"
