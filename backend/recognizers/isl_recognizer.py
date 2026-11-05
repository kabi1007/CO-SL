"""
CO-SL ISL recognizer.

Matches the working backend/models/isl/live_cosl.py preprocessing and
inference pipeline, with tolerance for occasional missed hand detections
from browser JPEG frames.
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

logger = logging.getLogger("cosl.isl")

FACE_KEY_INDICES = [
    70, 63, 105, 66, 107, 55, 65, 52,
    300, 293, 334, 296, 336, 285, 295, 282,
    33, 133, 159, 145, 362, 263, 386, 374,
    61, 37, 0, 267, 291, 321, 314, 17,
    78, 81, 13, 311, 308, 317, 14, 87,
]


def _wrist_relative(hand) -> np.ndarray:
    if hand is None:
        return np.zeros(63, dtype=np.float32)

    arr = np.array(
        [[lm.x, lm.y, lm.z] for lm in hand],
        dtype=np.float32,
    )

    wrist = arr[0]
    return (arr - wrist).flatten()


class ISLRecognizer(BaseSignRecognizer):
    sign_language = "ISL"

    def __init__(self) -> None:
        self._model = None
        self._labels: list[str] = []
        self._landmarker = None
        self._loaded = False
        self._mp = None

        self._sequence: deque = deque(maxlen=config.ISL_MAX_FRAMES)
        self._vote_window: deque = deque(
            maxlen=config.ISL_VOTE_WINDOW_SIZE
        )

        self._frame_count = 0
        self._last_confirmed: Optional[str] = None

        # Browser frames can occasionally miss hand detection.
        # Do not immediately destroy the gesture sequence.
        self._missed_hand_frames = 0
        self._max_missed_hand_frames = 4

    def _resolve_task_path(self):
        if config.ISL_HOLISTIC_TASK_PATH_OVERRIDE.exists():
            return config.ISL_HOLISTIC_TASK_PATH_OVERRIDE

        return config.ISL_HOLISTIC_TASK_PATH_FALLBACK

    def load(self) -> None:
        if self._loaded:
            return

        task_path = self._resolve_task_path()

        missing = [
            p
            for p in [
                config.ISL_MODEL_PATH,
                config.ISL_LABELS_PATH,
            ]
            if not p.exists()
        ]

        if not task_path.exists():
            missing.append(task_path)

        if missing:
            raise FileNotFoundError(
                "Missing required ISL model file(s): "
                + ", ".join(str(p) for p in missing)
            )

        import tensorflow as tf
        import mediapipe as mp

        self._mp = mp

        self._model = tf.keras.models.load_model(
            config.ISL_MODEL_PATH
        )

        with open(config.ISL_LABELS_PATH, "r") as f:
            self._labels = json.load(f)

        BaseOptions = mp.tasks.BaseOptions
        VisionRunningMode = mp.tasks.vision.RunningMode
        HolisticLandmarker = mp.tasks.vision.HolisticLandmarker
        HolisticLandmarkerOptions = (
            mp.tasks.vision.HolisticLandmarkerOptions
        )

        options = HolisticLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path=str(task_path)
            ),
            running_mode=VisionRunningMode.IMAGE,
            min_face_detection_confidence=0.5,
            min_face_landmarks_confidence=0.5,
            min_pose_detection_confidence=0.5,
            min_pose_landmarks_confidence=0.5,
            min_hand_landmarks_confidence=0.5,
        )

        self._landmarker = (
            HolisticLandmarker.create_from_options(options)
        )

        self._loaded = True

        logger.info(
            "ISL recognizer loaded. Labels: %s",
            self._labels,
        )

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
        self._vote_window.clear()
        self._frame_count = 0
        self._last_confirmed = None
        self._missed_hand_frames = 0

    def _extract_keypoints(self, result) -> np.ndarray:

        # Pose: 33 × 4 = 132
        if result.pose_landmarks:
            pose = np.array(
                [
                    [
                        lm.x,
                        lm.y,
                        lm.z,
                        lm.visibility,
                    ]
                    for lm in result.pose_landmarks
                ],
                dtype=np.float32,
            ).flatten()
        else:
            pose = np.zeros(132, dtype=np.float32)

        # Face: 40 × 3 = 120
        if result.face_landmarks:
            face = result.face_landmarks

            nose = np.array(
                [
                    face[1].x,
                    face[1].y,
                    face[1].z,
                ],
                dtype=np.float32,
            )

            face_features = []

            for idx in FACE_KEY_INDICES:
                point = np.array(
                    [
                        face[idx].x,
                        face[idx].y,
                        face[idx].z,
                    ],
                    dtype=np.float32,
                )

                face_features.extend(point - nose)

            face_features = np.array(
                face_features,
                dtype=np.float32,
            )
        else:
            face_features = np.zeros(
                120,
                dtype=np.float32,
            )

        # Hands: 63 + 63
        left_hand = (
            result.left_hand_landmarks
            if result.left_hand_landmarks
            else None
        )

        right_hand = (
            result.right_hand_landmarks
            if result.right_hand_landmarks
            else None
        )

        left_features = _wrist_relative(left_hand)
        right_features = _wrist_relative(right_hand)

        keypoints = np.concatenate(
            [
                pose,
                face_features,
                left_features,
                right_features,
            ]
        )

        return keypoints.astype(np.float32)

    def process_frame(
        self,
        frame_bgr: np.ndarray,
    ) -> RecognitionResult:

        if not self._loaded:
            raise RuntimeError(
                "ISLRecognizer.load() must be called before use"
            )

        # Same preprocessing as working live_cosl.py
        frame = cv2.flip(frame_bgr, 1)

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        mp_image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB,
            data=rgb,
        )

        result = self._landmarker.detect(mp_image)

        hands_present = bool(
            result.left_hand_landmarks
            or result.right_hand_landmarks
        )

        if hands_present:

            self._missed_hand_frames = 0

            features = self._extract_keypoints(result)

            if features.shape == (378,):
                self._sequence.append(features)

        else:

            self._missed_hand_frames += 1

            # Allow a few missed browser frames before clearing.
            if (
                self._missed_hand_frames
                > self._max_missed_hand_frames
            ):
                self._sequence.clear()
                self._vote_window.clear()
                self._missed_hand_frames = 0

        self._frame_count += 1

        out = RecognitionResult(
            ready_frames=len(self._sequence),
            required_frames=config.ISL_MAX_FRAMES,
        )

        if not (
            len(self._sequence)
            == config.ISL_MAX_FRAMES
            and self._frame_count
            % config.ISL_PREDICT_EVERY
            == 0
        ):
            return out

        X = np.expand_dims(
            np.array(
                self._sequence,
                dtype=np.float32,
            ),
            axis=0,
        )

        probs = self._model.predict(
            X,
            verbose=0,
        )[0]

        top_index = int(np.argmax(probs))

        confidence = float(
            probs[top_index]
        )

        word = self._labels[top_index]

        out.label = word
        out.confidence = confidence

        if confidence >= config.ISL_CONFIDENCE_THRESHOLD:

            self._vote_window.append(word)

            counts: dict[str, int] = {}

            for item in self._vote_window:
                counts[item] = (
                    counts.get(item, 0) + 1
                )

            best_word = max(
                counts,
                key=counts.get,
            )

            best_count = counts[best_word]

            if (
                best_count
                >= config.ISL_VOTE_THRESHOLD
                and best_word
                != self._last_confirmed
            ):
                out.label = best_word
                out.stable = True
                self._last_confirmed = best_word

        return out
