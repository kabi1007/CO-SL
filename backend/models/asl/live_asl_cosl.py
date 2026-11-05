import cv2
import mediapipe as mp
import json
import numpy as np
import tensorflow as tf
from pathlib import Path

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# =========================
# PATHS
# =========================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "cosl_asl_5words_baseline.keras"
LABELS_PATH = BASE_DIR / "cosl_asl_5words_labels.json"
MEAN_PATH = BASE_DIR / "model" / "mean.npy"
STD_PATH = BASE_DIR / "model" / "std.npy"
HOLISTIC_PATH = BASE_DIR / "model" / "holistic_landmarker.task"


# =========================
# SETTINGS
# =========================

SEQUENCE_LENGTH = 40

SELECTED_FACE_LANDMARKS = [
    0,13,14,17,37,39,40,61,78,80,81,82,87,88,
    91,95,146,178,181,185,191,267,269,270,291,
    308,310,311,312,317,318,321,324,375,402,405,
    33,46,52,53,55,65,66,70,105,107,
    133,145,159,160,161,263,276,282,283,
    285,295,296,300,334,336,362,374,386,387,388,
    1,2,4,5,6,98,327
]


# =========================
# LOAD MODEL
# =========================

model = tf.keras.models.load_model(
    MODEL_PATH,
    compile=False
)

with open(LABELS_PATH, "r") as f:
    labels = json.load(f)

mean = np.load(MEAN_PATH).squeeze()
std = np.load(STD_PATH).squeeze()

std = np.where(std == 0, 1.0, std)

print("Model loaded")
print("Labels:", labels)
print("Input:", model.input_shape)


# =========================
# MEDIAPIPE
# =========================

base_options = python.BaseOptions(
    model_asset_path=str(HOLISTIC_PATH)
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

landmarker = vision.HolisticLandmarker.create_from_options(options)


# =========================
# FEATURE EXTRACTION
# =========================

def extract_keypoints(results):

    pose = np.zeros(33 * 3, dtype=np.float32)
    lh = np.zeros(21 * 3, dtype=np.float32)
    rh = np.zeros(21 * 3, dtype=np.float32)

    face = np.zeros(
        len(SELECTED_FACE_LANDMARKS) * 3,
        dtype=np.float32
    )

    if results.pose_landmarks:
        pose_landmarks = results.pose_landmarks[:33]

        pose = np.array(
            [[lm.x, lm.y, lm.z] for lm in pose_landmarks],
            dtype=np.float32
        ).flatten()

    if results.left_hand_landmarks:
        left_hand_landmarks = results.left_hand_landmarks[:21]

        lh = np.array(
            [[lm.x, lm.y, lm.z] for lm in left_hand_landmarks],
            dtype=np.float32
        ).flatten()

    if results.right_hand_landmarks:
        right_hand_landmarks = results.right_hand_landmarks[:21]

        rh = np.array(
            [[lm.x, lm.y, lm.z] for lm in right_hand_landmarks],
            dtype=np.float32
        ).flatten()

    if results.face_landmarks:
        selected_face_values = []

        for idx in SELECTED_FACE_LANDMARKS:

            if idx < len(results.face_landmarks):
                lm = results.face_landmarks[idx]

                selected_face_values.extend(
                    [lm.x, lm.y, lm.z]
                )

            else:
                selected_face_values.extend(
                    [0.0, 0.0, 0.0]
                )

        face = np.array(
            selected_face_values,
            dtype=np.float32
        )

    keypoints = np.concatenate(
        [pose, lh, rh, face]
    ).astype(np.float32)

    return np.nan_to_num(
        keypoints,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )


# =========================
# CAMERA
# =========================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Could not open webcam.")
    raise SystemExit


sequence = []
frame_count = 0
prediction = ""
confidence = 0.0

print()
print("================================")
print("LIVE ASL TEST")
print("================================")
print()
print("Show one sign for about 1-2 seconds.")
print("Press Q to quit.")
print()


# =========================
# LIVE LOOP
# =========================

while cap.isOpened():

    ret, frame = cap.read()

    if not ret:
        print("❌ Failed to read webcam frame.")
        break

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    # Correct MediaPipe image creation
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    timestamp_ms = frame_count * 33

    results = landmarker.detect_for_video(
        mp_image,
        timestamp_ms
    )

    keypoints = extract_keypoints(results)

    sequence.append(keypoints)

    if len(sequence) > SEQUENCE_LENGTH:
        sequence = sequence[-SEQUENCE_LENGTH:]

    # Predict after collecting 40 frames
    if len(sequence) == SEQUENCE_LENGTH:

        input_sequence = np.array(
            sequence,
            dtype=np.float32
        )

        # Normalize exactly like training
        input_sequence = (
            input_sequence - mean
        ) / std

        input_sequence = np.expand_dims(
            input_sequence,
            axis=0
        )

        probs = model.predict(
            input_sequence,
            verbose=0
        )[0]

        idx = int(np.argmax(probs))

        prediction = labels[idx]
        confidence = float(probs[idx]) * 100

    # =========================
    # DISPLAY
    # =========================

    text = f"{prediction}  {confidence:.1f}%"

    cv2.rectangle(
        frame,
        (10, 10),
        (500, 70),
        (0, 0, 0),
        -1
    )

    cv2.putText(
        frame,
        text,
        (25, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        "Press Q to quit",
        (25, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    cv2.imshow(
        "CO-SL - ASL Recognition",
        frame
    )

    frame_count += 1

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# =========================
# CLEANUP
# =========================

cap.release()
cv2.destroyAllWindows()
landmarker.close()

print()
print("Live test ended.")
