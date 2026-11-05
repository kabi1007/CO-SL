"""
Mock recognizer for development / demo mode.

This is used ONLY when explicitly enabled (COSL_MOCK_MODE=true or no real
model files are present) and the WebSocket response always carries
"demo_mode": true so the frontend can display a clear "Demo mode" indicator.
It must never be silently substituted for real inference.
"""

from __future__ import annotations

import random
import time

from backend.recognizers.base import BaseSignRecognizer, RecognitionResult

_ASL_CYCLE = ["hello", "thankyou", "yes", "no"]
_ISL_CYCLE = ["Hello", "Thank_you", "Good", "How_are_you"]


class MockRecognizer(BaseSignRecognizer):
    def __init__(self, sign_language: str) -> None:
        self.sign_language = sign_language.upper()
        self._loaded = False
        self._frame_count = 0
        self._cycle = _ASL_CYCLE if self.sign_language == "ASL" else _ISL_CYCLE
        self._last_emit = 0.0

    def load(self) -> None:
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def close(self) -> None:
        self._loaded = False

    def reset(self) -> None:
        self._frame_count = 0

    def process_frame(self, frame_bgr) -> RecognitionResult:
        self._frame_count += 1
        now = time.time()

        # Simulate a confirmed prediction roughly every ~2.5 seconds of frames.
        if now - self._last_emit > 2.5 and self._frame_count % 20 == 0:
            self._last_emit = now
            label = random.choice(self._cycle)
            return RecognitionResult(
                label=label,
                confidence=round(random.uniform(0.85, 0.99), 2),
                stable=True,
                ready_frames=self._frame_count,
                required_frames=1,
            )

        return RecognitionResult(ready_frames=self._frame_count, required_frames=1)
