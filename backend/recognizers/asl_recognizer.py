"""
ASL recognizer.

This is a direct, faithful port of the preprocessing and inference logic in
live_asl_cosl.py, adapted from an OpenCV live-loop script into a streaming
per-frame recognizer usable from a WebSocket handler. The feature extraction,
feature ORDER (pose, left hand, right hand, face - not face-first), face
landmark selection, sequence length (40), and normalization
((x - mean) / std, zero-std guarded to 1.0) are all reproduced exactly as in
the source file. Nothing about the model's input contract has been changed.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from typing import Optional

import cv2
import numpy as np

from backend import config
from backend.recognizers.base import BaseSignRecognizer, RecognitionResult

logger = logging.getLogger("cosl.asl")

# Exact face landmark subset from live_asl_cosl.py (73 landmarks)
SELECTED_FACE_LANDMARKS = [
    0, 13, 14, 17, 37, 39, 40, 61, 78, 80, 81, 82, 87, 88,
    91, 95, 146, 178, 181, 185, 191, 267, 269, 270, 291,
    308, 310, 311, 312, 317, 318, 321, 324, 375, 402, 405,
    33, 46, 52, 53, 55, 65, 66, 70, 105, 107,
    133, 145, 159, 160, 161, 263, 276, 282, 283,
    285, 295, 296, 300, 334, 336, 362, 374, 386, 387, 388,
    1, 2, 4, 5, 6, 98, 327,
]


class ASLRecognizer(BaseSignRecognizer):
    sign_language = "ASL"

    def __init__(self) -> None:
        self._model = None
        self._labels: list[str] = []
        self._mean: Optional[np.ndarray] = None
        self._std: Optional[np.ndarray] = None
        self._landmarker = None
        self._loaded = False

        self._sequence: deque = deque(maxlen=config.ASL_SEQUENCE_LENGTH)
        self._frame_count = 0

        # stability tracking
        self._last_label: Optional[str] = None
        self._consecutive = 0
        self._confirmed_label: Optional[str] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self) -> None:
        if self._loaded:
            return

        missing = [
            p for p in [
                config.ASL_MODEL_PATH,
                config.ASL_LABELS_PATH,
                config.ASL_MEAN_PATH,
                config.ASL_STD_PATH,
                config.ASL_HOLISTIC_TASK_PATH,
            ]
            if not p.exists()
        ]
        if missing:
            raise FileNotFoundError(
                "Missing required ASL model file(s): "
                + ", ".join(str(p) for p in missing)
            )

        # Imported lazily so the rest of the backend (health check, model
        # listing, etc.) can run even before TensorFlow/MediaPipe are needed.
        import tensorflow as tf
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        self._mp = mp

        self._model = tf.keras.models.load_model(
            config.ASL_MODEL_PATH, compile=False
        )

        with open(config.ASL_LABELS_PATH, "r") as f:
            self._labels = json.load(f)

        self._mean = np.load(config.ASL_MEAN_PATH).squeeze()
        std = np.load(config.ASL_STD_PATH).squeeze()
        self._std = np.where(std == 0, 1.0, std)

        base_options = python.BaseOptions(
            model_asset_path=str(config.ASL_HOLISTIC_TASK_PATH)
        )
        options = vision.HolisticLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            min_face_detection_confidence=0.5,
            min_face_suppression_threshold=0.5,
            min_pose_detection_confidence=0.5,
            min_pose_suppression_threshold=0.5,
            min_hand_landmarks_confidence=0.5,
        )
        self._landmarker = vision.HolisticLandmarker.create_from_options(options)

        self._loaded = True
        logger.info("ASL recognizer loaded. Labels: %s", self._labels)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def close(self) -> None:
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None
        self._loaded = False

    def reset(self) -> None:
        self._sequence.clear()
        self._frame_count = 0
        self._last_label = None
        self._consecutive = 0
        self._confirmed_label = None

    # ------------------------------------------------------------------
    # Feature extraction (exact port of extract_keypoints in live_asl_cosl.py)
    # ------------------------------------------------------------------

    def _extract_keypoints(self, results) -> np.ndarray:
        pose = np.zeros(33 * 3, dtype=np.float32)
        lh = np.zeros(21 * 3, dtype=np.float32)
        rh = np.zeros(21 * 3, dtype=np.float32)
        face = np.zeros(len(SELECTED_FACE_LANDMARKS) * 3, dtype=np.float32)

        if results.pose_landmarks:
            pose_landmarks = results.pose_landmarks[:33]
            pose = np.array(
                [[lm.x, lm.y, lm.z] for lm in pose_landmarks], dtype=np.float32
            ).flatten()

        if results.left_hand_landmarks:
            left_hand_landmarks = results.left_hand_landmarks[:21]
            lh = np.array(
                [[lm.x, lm.y, lm.z] for lm in left_hand_landmarks], dtype=np.float32
            ).flatten()

        if results.right_hand_landmarks:
            right_hand_landmarks = results.right_hand_landmarks[:21]
            rh = np.array(
                [[lm.x, lm.y, lm.z] for lm in right_hand_landmarks], dtype=np.float32
            ).flatten()

        if results.face_landmarks:
            selected_face_values = []
            for idx in SELECTED_FACE_LANDMARKS:
                if idx < len(results.face_landmarks):
                    lm = results.face_landmarks[idx]
                    selected_face_values.extend([lm.x, lm.y, lm.z])
                else:
                    selected_face_values.extend([0.0, 0.0, 0.0])
            face = np.array(selected_face_values, dtype=np.float32)

        # NOTE: order is [pose, lh, rh, face] - matches live_asl_cosl.py exactly.
        keypoints = np.concatenate([pose, lh, rh, face]).astype(np.float32)
        return np.nan_to_num(keypoints, nan=0.0, posinf=0.0, neginf=0.0)

    # ------------------------------------------------------------------
    # Per-frame processing
    # ------------------------------------------------------------------

    def process_frame(self, frame_bgr: np.ndarray) -> RecognitionResult:
        if not self._loaded:
            raise RuntimeError("ASLRecognizer.load() must be called before use")

        # live_asl_cosl.py flips the webcam frame before extraction (selfie view).
        frame = cv2.flip(frame_bgr, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)

        timestamp_ms = self._frame_count * 33
        import time

        t0 = time.perf_counter()
        results = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        mp_time = (time.perf_counter() - t0) * 1000
        self._frame_count += 1

        if self._frame_count % 10 == 0:
            logger.info("ASL TIMING: MediaPipe %.1f ms/frame", mp_time)

        keypoints = self._extract_keypoints(results)
        self._sequence.append(keypoints)

        result = RecognitionResult(
            ready_frames=len(self._sequence),
            required_frames=config.ASL_SEQUENCE_LENGTH,
        )

        if len(self._sequence) < config.ASL_SEQUENCE_LENGTH:
            return result

        input_sequence = np.array(self._sequence, dtype=np.float32)
        input_sequence = (input_sequence - self._mean) / self._std
        input_sequence = np.expand_dims(input_sequence, axis=0)

        import time

        t_pred = time.perf_counter()
        probs = self._model.predict(input_sequence, verbose=0)[0]
        pred_time = (time.perf_counter() - t_pred) * 1000

        if self._frame_count % 10 == 0:
            logger.info("ASL TIMING: TensorFlow prediction %.1f ms", pred_time)

        idx = int(np.argmax(probs))
        label = self._labels[idx]
        confidence = float(probs[idx])

        result.label = label
        result.confidence = confidence

        # Stability: require N consecutive matching, sufficiently-confident
        # predictions before confirming a message (generic stabilizer layered
        # on top of the raw per-frame model output - live_asl_cosl.py itself
        # has no such debouncing since it only prints to an OpenCV window).
        if confidence >= config.ASL_MIN_CONFIDENCE and label == self._last_label:
            self._consecutive += 1
        else:
            self._consecutive = 1
            self._last_label = label

        if (
            self._consecutive >= config.ASL_STABLE_CONSECUTIVE_FRAMES
            and confidence >= config.ASL_MIN_CONFIDENCE
            and self._confirmed_label != label
        ):
            result.stable = True
            self._confirmed_label = label
        elif label != self._confirmed_label:
            # signer moved on to a new/unclear sign; allow re-confirmation later
            pass

        return result
