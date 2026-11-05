import cv2
import mediapipe as mp
import numpy as np
from pathlib import Path

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


BASE_DIR = Path(__file__).resolve().parent

HOLISTIC_PATH = BASE_DIR / "holistic_landmarker.task"
DATA_DIR = BASE_DIR / "training_data"

SEQUENCE_LENGTH = 40
SEQUENCES_PER_SIGN = 40

ACTIONS = [
    "HELLO",
    "THANKYOU",
    "PLEASE",
    "YES",
    "NO",
]

SELECTED_FACE_LANDMARKS = [
    0,13,14,17,37,39,40,61,78,80,81,82,87,88,
    91,95,146,178,181,185,191,267,269,270,291,
    308,310,311,312,317,318,321,324,375,402,405,
    33,46,52,53,55,65,66,70,105,107,
    133,145,159,160,161,263,276,282,283,
    285,295,296,300,334,336,362,374,386,387,388,
    1,2,4,5,6,98,327
]


def extract_keypoints(results):
    pose = np.zeros(33 * 3, dtype=np.float32)
    lh = np.zeros(21 * 3, dtype=np.float32)
    rh = np.zeros(21 * 3, dtype=np.float32)

    face = np.zeros(
        len(SELECTED_FACE_LANDMARKS) * 3,
        dtype=np.float32
    )

    if results.pose_landmarks:
        pose = np.array(
            [[lm.x, lm.y, lm.z] for lm in results.pose_landmarks[:33]],
            dtype=np.float32
        ).flatten()

    if results.left_hand_landmarks:
        lh = np.array(
            [[lm.x, lm.y, lm.z] for lm in results.left_hand_landmarks[:21]],
            dtype=np.float32
        ).flatten()

    if results.right_hand_landmarks:
        rh = np.array(
            [[lm.x, lm.y, lm.z] for lm in results.right_hand_landmarks[:21]],
            dtype=np.float32
        ).flatten()

    if results.face_landmarks:
        values = []

        for idx in SELECTED_FACE_LANDMARKS:
            if idx < len(results.face_landmarks):
                lm = results.face_landmarks[idx]
                values.extend([lm.x, lm.y, lm.z])
            else:
                values.extend([0.0, 0.0, 0.0])

        face = np.array(values, dtype=np.float32)

    keypoints = np.concatenate(
        [pose, lh, rh, face]
    ).astype(np.float32)

    return np.nan_to_num(
        keypoints,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )


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

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise SystemExit("Could not open webcam.")


print()
print("==============================================")
print("CO-SL ASL DATA COLLECTOR")
print("==============================================")
print("Each sign: 40 sequences")
print("Each sequence: 40 frames")
print()
print("Signs:")
for i, action in enumerate(ACTIONS, 1):
    print(f"{i}. {action}")
print()
print("Press Q at any time to quit.")
print()

for action_index, action in enumerate(ACTIONS, 1):

    action_dir = DATA_DIR / action
    action_dir.mkdir(parents=True, exist_ok=True)

    existing = sorted(action_dir.glob("*.npy"))

    start_sequence = len(existing) + 1

    print()
    print("----------------------------------------------")
    print(f"ACTION {action_index}/{len(ACTIONS)}: {action}")
    print(f"Existing sequences: {len(existing)}")
    print(f"Starting from: {start_sequence}")
    print("----------------------------------------------")
    print()

    for sequence_number in range(
        start_sequence,
        SEQUENCES_PER_SIGN + 1
    ):

        print(
            f"{action}: sequence "
            f"{sequence_number}/{SEQUENCES_PER_SIGN}"
        )

        print("Get ready...")

        for countdown in [3, 2, 1]:
            ret, frame = cap.read()

            if not ret:
                cap.release()
                raise SystemExit("Camera frame failed.")

            frame = cv2.flip(frame, 1)

            cv2.putText(
                frame,
                f"{action}  |  GET READY: {countdown}",
                (25, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 255),
                2
            )

            cv2.imshow("CO-SL ASL Collector", frame)

            if cv2.waitKey(700) & 0xFF == ord("q"):
                cap.release()
                cv2.destroyAllWindows()
                raise SystemExit("Collection stopped.")

        sequence = []

        for frame_index in range(SEQUENCE_LENGTH):

            ret, frame = cap.read()

            if not ret:
                cap.release()
                cv2.destroyAllWindows()
                raise SystemExit("Camera frame failed.")

            frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb
            )

            timestamp_ms = (
                (sequence_number - 1) * SEQUENCE_LENGTH
                + frame_index
            ) * 33

            results = landmarker.detect_for_video(
                mp_image,
                timestamp_ms
            )

            keypoints = extract_keypoints(results)

            sequence.append(keypoints)

            cv2.rectangle(
                frame,
                (10, 10),
                (630, 75),
                (0, 0, 0),
                -1
            )

            cv2.putText(
                frame,
                f"{action}  |  "
                f"Sequence {sequence_number}/{SEQUENCES_PER_SIGN}  |  "
                f"Frame {frame_index + 1}/{SEQUENCE_LENGTH}",
                (20, 52),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2
            )

            cv2.imshow(
                "CO-SL ASL Collector",
                frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                cap.release()
                cv2.destroyAllWindows()
                raise SystemExit("Collection stopped.")

        output_path = action_dir / f"{sequence_number:03d}.npy"

        np.save(
            output_path,
            np.array(sequence, dtype=np.float32)
        )

        print(f"Saved: {output_path}")

        # Small pause between sequences
        cv2.waitKey(300)

cap.release()
cv2.destroyAllWindows()

print()
print("==============================================")
print("COLLECTION COMPLETE")
print("==============================================")
print(f"Saved under: {DATA_DIR}")
