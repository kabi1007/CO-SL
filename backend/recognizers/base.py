"""
Common interface that every sign-language recognizer must implement.

The rest of the application (WebSocket route, session service) only ever
talks to recognizers through this interface. It has no knowledge of
MediaPipe, Keras, frame counts, feature layouts, or normalization -
all of that is owned entirely by each concrete recognizer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class RecognitionResult:
    """Result of feeding one frame into a recognizer."""

    label: Optional[str] = None          # raw model label, e.g. "hello"
    meaning_key: Optional[str] = None    # normalized semantic key, e.g. "HELLO"
    confidence: float = 0.0              # 0..1
    stable: bool = False                 # True only on a newly-confirmed prediction
    ready_frames: int = 0                # frames buffered so far (for UI "warming up")
    required_frames: int = 0             # frames needed before prediction is possible


class BaseSignRecognizer(ABC):
    """Abstract interface implemented by ASLRecognizer and ISLRecognizer."""

    sign_language: str = "BASE"

    @abstractmethod
    def load(self) -> None:
        """Load model weights, labels, normalization stats, and MediaPipe assets.

        Must be safe to call once and cheap to no-op on subsequent calls
        (idempotent), since recognizers are loaded once at startup / first use.
        """
        raise NotImplementedError

    @abstractmethod
    def process_frame(self, frame_bgr: np.ndarray) -> RecognitionResult:
        """Feed a single BGR frame (as decoded from the browser) into the
        recognizer's internal buffer and, once enough frames are collected,
        run prediction and return a RecognitionResult.

        Implementations own their own internal sequence buffering, so this
        is the only method the caller needs per frame.
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Clear internal frame buffers / stability state (e.g. when the
        signer stops, or after a confirmed prediction, or on language switch).
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Release MediaPipe / model resources."""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        raise NotImplementedError
