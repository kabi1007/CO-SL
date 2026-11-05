import cv2
import json
import time
import numpy as np
import mediapipe as mp
import tensorflow as tf
from collections import deque
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

MODEL_PATH = "cosl_isl_5words_baseline.keras"
LABELS_PATH = "cosl_isl_5words_labels.json"

MAX_FRAMES = 30
PREDICT_EVERY = 3

CONFIDENCE_THRESHOLD = 0.50
VOTE_WINDOW_SIZE = 7
VOTE_THRESHOLD = 4

# ============================================================
# LOAD MODEL + LABELS
# ============================================================

print("Loading model...")

model = tf.keras.models.load_model(MODEL_PATH)

with open(LABELS_PATH, "r") as f:
    labels = json.load(f)

print("Labels:", labels)
print("Model loaded.")

# ============================================================
# MEDIAPIPE
# ============================================================

BaseOptions = mp.tasks.BaseOptions
VisionRunningMode = mp.tasks.vision.RunningMode

HolisticLandmarker = mp.tasks.vision.HolisticLandmarker
HolisticLandmarkerOptions = mp.tasks.vision.HolisticLandmarkerOptions

options = HolisticLandmarkerOptions(
    base_options = BaseOptions(
    model_asset_path="/Users/kabinayasrim/Desktop/cosl/backend/models/isl/holistic_landmarker.task"
),
    running_mode=VisionRunningMode.IMAGE,
    min_face_detection_confidence=0.5,
    min_face_landmarks_confidence=0.5,
    min_pose_detection_confidence=0.5,
    min_pose_landmarks_confidence=0.5,
    min_hand_landmarks_confidence=0.5,
)

holistic = HolisticLandmarker.create_from_options(options)

# ============================================================
# EXACT REPO FEATURE CONFIGURATION
# ============================================================

FACE_KEY_INDICES = [
    70, 63, 105, 66, 107, 55, 65, 52,
    300, 293, 334, 296, 336, 285, 295, 282,
    33, 133, 159, 145, 362, 263, 386, 374,
    61, 37, 0, 267, 291, 321, 314, 17,
    78, 81, 13, 311, 308, 317, 14, 87
]


def wrist_relative(hand):
    """Make hand coordinates relative to the wrist."""
    if hand is None:
        return np.zeros(63, dtype=np.float32)

    arr = np.array(
        [[lm.x, lm.y, lm.z] for lm in hand],
        dtype=np.float32
    )

    wrist = arr[0]

    return (arr - wrist).flatten()


def extract_keypoints(result):
    """Extract the exact 378 features used by the pretrained model."""

    # --------------------------------------------------------
    # Pose: 33 landmarks × 4 values = 132
    # --------------------------------------------------------

    if result.pose_landmarks:
        pose = np.array(
            [
                [lm.x, lm.y, lm.z, lm.visibility]
                for lm in result.pose_landmarks
            ],
            dtype=np.float32
        ).flatten()
    else:
        pose = np.zeros(132, dtype=np.float32)

    # --------------------------------------------------------
    # Face: 40 selected landmarks × 3 = 120
    # --------------------------------------------------------

    if result.face_landmarks:
        face = result.face_landmarks

        nose = np.array(
            [face[1].x, face[1].y, face[1].z],
            dtype=np.float32
        )

        face_features = []

        for idx in FACE_KEY_INDICES:
            point = np.array(
                [face[idx].x, face[idx].y, face[idx].z],
                dtype=np.float32
            )

            face_features.extend(point - nose)

        face_features = np.array(
            face_features,
            dtype=np.float32
        )

    else:
        face_features = np.zeros(120, dtype=np.float32)

    # --------------------------------------------------------
    # Hands: 63 + 63
    # --------------------------------------------------------

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

    left_features = wrist_relative(left_hand)
    right_features = wrist_relative(right_hand)

    # --------------------------------------------------------
    # Total = 132 + 120 + 63 + 63 = 378
    # --------------------------------------------------------

    keypoints = np.concatenate(
        [
            pose,
            face_features,
            left_features,
            right_features
        ]
    )

    return keypoints.astype(np.float32)


# ============================================================
# CAMERA
# ============================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("Could not open webcam.")

sequence = deque(maxlen=MAX_FRAMES)
vote_window = deque(maxlen=VOTE_WINDOW_SIZE)

frame_count = 0
last_prediction = "Waiting..."
last_confidence = 0.0

print("\nCamera started.")
print("Show one sign clearly for about 1–2 seconds.")
print("Press Q to quit.\n")

# ============================================================
# LIVE LOOP
# ============================================================

try:

    while True:

        ret, frame = cap.read()

        if not ret:
            print("Could not read camera frame.")
            break

        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        result = holistic.detect(mp_image)

        hands_present = bool(
            result.left_hand_landmarks
            or result.right_hand_landmarks
        )

        if hands_present:

            features = extract_keypoints(result)

            if features.shape == (378,):

                sequence.append(features)

        else:

            # Clear old sequence if hands disappear
            if len(sequence) > 0:
                sequence.clear()
                vote_window.clear()

        # ----------------------------------------------------
        # PREDICT
        # ----------------------------------------------------

        frame_count += 1

        if (
            len(sequence) == MAX_FRAMES
            and frame_count % PREDICT_EVERY == 0
        ):

            X = np.expand_dims(
                np.array(sequence, dtype=np.float32),
                axis=0
            )

            probs = model.predict(
                X,
                verbose=0
            )[0]

            top_index = int(np.argmax(probs))

            confidence = float(
                probs[top_index]
            )

            word = labels[top_index]

            if confidence >= CONFIDENCE_THRESHOLD:

                vote_window.append(word)

                # Majority vote
                counts = {}

                for item in vote_window:
                    counts[item] = counts.get(item, 0) + 1

                best_word = max(
                    counts,
                    key=counts.get
                )

                best_count = counts[best_word]

                if best_count >= VOTE_THRESHOLD:

                    last_prediction = best_word
                    last_confidence = confidence

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        cv2.rectangle(
            frame,
            (10, 10),
            (600, 100),
            (0, 0, 0),
            -1
        )

        cv2.putText(
            frame,
            f"CO-SL: {last_prediction}",
            (25, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"Confidence: {last_confidence * 100:.1f}%",
            (25, 82),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Frames: {len(sequence)}/{MAX_FRAMES}",
            (10, frame.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        cv2.imshow(
            "CO-SL | ISL Live Recognition",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

finally:

    cap.release()
    holistic.close()
    cv2.destroyAllWindows()

    print("\nCamera closed.")
