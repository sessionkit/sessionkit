"""Suite-wide hooks."""

from __future__ import annotations

import _scanlist
import pytest


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    """The loud half of the private-word guards' skip: counted, and naming the
    variable to set, whenever the private scan list is not set
    (tests/_scanlist.py). A guard that cannot run says so; it never passes
    quietly. A bare `pytest -q` shows it without -rs."""
    _scanlist.summary(terminalreporter)
