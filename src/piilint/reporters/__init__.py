"""Reporters: console (Rich), JSON (schema_version 1), SARIF 2.1.0.

Chassis boundary: this package must not import recognizer logic.
"""

from __future__ import annotations

from piilint.reporters.console import render_console
from piilint.reporters.json_ import config_hash, render_json
from piilint.reporters.sarif import render_sarif

__all__ = ["config_hash", "render_console", "render_json", "render_sarif"]
