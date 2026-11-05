"""
Lightweight session service.

No database is used (per spec section 46) - conversation history lives in
frontend memory. This service only tracks the current sign_language /
output_language pairing chosen via POST /api/session, so the WebSocket
route can validate incoming connections against a known configuration
if desired. State is process-local and intentionally simple.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend import config


@dataclass
class SessionConfig:
    sign_language: str
    output_language: str


class SessionStore:
    def __init__(self) -> None:
        self._current: SessionConfig | None = None

    def create(self, sign_language: str, output_language: str) -> SessionConfig:
        sign_language = sign_language.upper()
        if sign_language not in config.SUPPORTED_SIGN_LANGUAGES:
            raise ValueError(f"Unsupported sign_language: {sign_language}")
        if output_language not in config.SUPPORTED_OUTPUT_LANGUAGES:
            raise ValueError(f"Unsupported output_language: {output_language}")

        self._current = SessionConfig(
            sign_language=sign_language, output_language=output_language
        )
        return self._current

    @property
    def current(self) -> SessionConfig | None:
        return self._current


session_store = SessionStore()
