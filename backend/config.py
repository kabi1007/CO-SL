"""
Central configuration for CO-SL backend.

All filesystem paths are derived from this file's location using pathlib,
so the application works identically on macOS and Windows. Nothing here
is hard-coded to a specific machine.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

ASL_DIR = MODELS_DIR / "asl"
ISL_DIR = MODELS_DIR / "isl"

# ---------------------------------------------------------------------------
# ASL model assets (must match live_asl_cosl.py exactly)
# ---------------------------------------------------------------------------

ASL_MODEL_PATH = ASL_DIR / "cosl_asl_5words_baseline.keras"
ASL_LABELS_PATH = ASL_DIR / "cosl_asl_5words_labels.json"
ASL_MEAN_PATH = ASL_DIR / "mean.npy"
ASL_STD_PATH = ASL_DIR / "std.npy"
ASL_HOLISTIC_TASK_PATH = ASL_DIR / "holistic_landmarker.task"

ASL_SEQUENCE_LENGTH = 40

# ---------------------------------------------------------------------------
# ISL model assets (must match live_cosl.py exactly)
# ---------------------------------------------------------------------------

ISL_MODEL_PATH = ISL_DIR / "cosl_isl_5words_baseline.keras"
ISL_LABELS_PATH = ISL_DIR / "cosl_isl_5words_labels.json"

# live_cosl.py loads its HolisticLandmarker from "mediapipe_models/holistic_landmarker.task".
# No dedicated ISL .task file was specified in the integration file list, and the .task
# file is a generic MediaPipe landmarker asset (not trained on ISL vocabulary), so by
# default we point ISL at the same file already required for ASL. If you have a
# separate ISL-specific .task file, place it at backend/models/isl/holistic_landmarker.task
# and it will be preferred automatically.
ISL_HOLISTIC_TASK_PATH_OVERRIDE = ISL_DIR / "holistic_landmarker.task"
ISL_HOLISTIC_TASK_PATH_FALLBACK = ASL_HOLISTIC_TASK_PATH

ISL_MAX_FRAMES = 30
ISL_PREDICT_EVERY = 3
ISL_CONFIDENCE_THRESHOLD = 0.50
ISL_VOTE_WINDOW_SIZE = 7
ISL_VOTE_THRESHOLD = 4

# ---------------------------------------------------------------------------
# Supported languages / sign languages
# ---------------------------------------------------------------------------

SUPPORTED_SIGN_LANGUAGES = {"ASL", "ISL"}
SUPPORTED_OUTPUT_LANGUAGES = {"en", "ta", "hi", "te", "ml", "kn"}

# ---------------------------------------------------------------------------
# Stability / debouncing (applies uniformly at the API layer; ISL already
# has its own internal vote-based stabilization from live_cosl.py, ASL does
# not, so we apply a generic confirmation-window stabilizer for ASL here)
# ---------------------------------------------------------------------------

ASL_STABLE_CONSECUTIVE_FRAMES = 4  # consecutive matching predictions to confirm
ASL_MIN_CONFIDENCE = 0.60

# ---------------------------------------------------------------------------
# Server / CORS
# ---------------------------------------------------------------------------

CORS_ALLOW_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# ---------------------------------------------------------------------------
# Mock mode (backend-side flag; can be overridden by env var COSL_MOCK_MODE)
# ---------------------------------------------------------------------------

import os

MOCK_MODE = os.environ.get("COSL_MOCK_MODE", "false").lower() == "true"
