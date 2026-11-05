"""
WebSocket streaming endpoint: /ws/sign/{sign_language}

Protocol:
- Client connects to /ws/sign/ASL or /ws/sign/ISL, optionally with
  ?output_language=en|ta|hi as a query param (defaults to "en").
- Client sends binary WebSocket frames containing a single JPEG-encoded
  camera frame each.
- Client may send text (JSON) control messages:
    {"type": "set_language", "language": "ta"}
    {"type": "reset"}
- Server sends JSON text messages back:
    {"type": "status", ...}                 -- buffering / recognition status
    {"type": "prediction", ...}              -- raw per-frame model output
    {"type": "message", ...}                 -- confirmed, translated message
    {"type": "error", "code": ..., "message": ...}

All ML details (MediaPipe, Keras, frame counts, normalization) stay fully
inside the recognizer classes; this route only orchestrates I/O.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend import config
from backend.recognizers.asl_recognizer import ASLRecognizer
from backend.recognizers.isl_recognizer import ISLRecognizer
from backend.recognizers.mock_recognizer import MockRecognizer
from backend.services import meaning_mapper, translation

logger = logging.getLogger("cosl.ws")

router = APIRouter()

# One recognizer instance is created per active WebSocket connection (per
# spec section 35: models are loaded once and reused, not per-frame; here
# "once" is once per connection/session rather than a single global
# instance, so concurrent ASL and ISL sessions don't share mutable
# sequence-buffer state).


def _files_available(sign_language: str) -> bool:
    if sign_language == "ASL":
        return all(
            p.exists()
            for p in [
                config.ASL_MODEL_PATH,
                config.ASL_LABELS_PATH,
                config.ASL_MEAN_PATH,
                config.ASL_STD_PATH,
                config.ASL_HOLISTIC_TASK_PATH,
            ]
        )
    if sign_language == "ISL":
        task_ok = (
            config.ISL_HOLISTIC_TASK_PATH_OVERRIDE.exists()
            or config.ISL_HOLISTIC_TASK_PATH_FALLBACK.exists()
        )
        return task_ok and all(
            p.exists() for p in [config.ISL_MODEL_PATH, config.ISL_LABELS_PATH]
        )
    return False


@router.websocket("/ws/sign/{sign_language}")
async def sign_stream(websocket: WebSocket, sign_language: str):
    sign_language = sign_language.upper()

    if sign_language not in config.SUPPORTED_SIGN_LANGUAGES:
        await websocket.accept()
        await websocket.send_json(
            {"type": "error", "code": "invalid_sign_language", "message": f"Unsupported sign language: {sign_language}"}
        )
        await websocket.close()
        return

    initial_lang = websocket.query_params.get("output_language", "en")
    if not translation.is_supported_language(initial_lang):
        initial_lang = "en"
    # Mutable single-element holder so the control-message handler can
    # update the active output language without needing `nonlocal`.
    output_language_box = [initial_lang]

    await websocket.accept()

    demo_mode = False
    if _files_available(sign_language):
        recognizer = ASLRecognizer() if sign_language == "ASL" else ISLRecognizer()
    elif config.MOCK_MODE:
        recognizer = MockRecognizer(sign_language)
        demo_mode = True
    else:
        await websocket.send_json(
            {
                "type": "error",
                "code": "model_missing",
                "message": (
                    f"{sign_language} model files were not found on the server. "
                    "Place the required files under backend/models/ or enable "
                    "COSL_MOCK_MODE=true for a demo."
                ),
            }
        )
        await websocket.close()
        return

    try:
        recognizer.load()
    except FileNotFoundError as e:
        await websocket.send_json({"type": "error", "code": "model_missing", "message": str(e)})
        await websocket.close()
        return
    except Exception as e:  # noqa: BLE001 - surface as a clean client-facing error
        logger.exception("Failed to load %s recognizer", sign_language)
        await websocket.send_json(
            {"type": "error", "code": "model_load_failed", "message": "The recognition model failed to load. Check server logs."}
        )
        await websocket.close()
        return

    await websocket.send_json(
        {"type": "status", "state": "ready", "sign_language": sign_language, "demo_mode": demo_mode}
    )

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            text = message.get("text")
            data = message.get("bytes")

            if text is not None:
                await _handle_control_message(websocket, recognizer, text, output_language_box)
                continue

            if data is None:
                continue

            frame = _decode_jpeg(data)
            if frame is None:
                await websocket.send_json(
                    {"type": "error", "code": "invalid_frame", "message": "Received an unreadable video frame."}
                )
                continue

            try:
                result = recognizer.process_frame(frame)
            except Exception:  # noqa: BLE001
                logger.exception("Inference error for %s", sign_language)
                await websocket.send_json(
                    {"type": "error", "code": "inference_failed", "message": "Recognition failed on this frame."}
                )
                continue
            if result.label is None:
                # Lightweight status only, so the UI can show "buffering" /
                # "listening" without flooding the client every frame.
                if result.ready_frames % 5 == 0:
                    await websocket.send_json(
                        {
                            "type": "status",
                            "state": "listening",
                            "ready_frames": result.ready_frames,
                            "required_frames": result.required_frames,
                        }
                    )
                continue

            meaning_key = meaning_mapper.to_meaning_key(sign_language, result.label)

            await websocket.send_json(
                {
                    "type": "prediction",
                    "sign_language": sign_language,
                    "label": result.label,
                    "meaning_key": meaning_key,
                    "confidence": round(result.confidence, 4),
                    "stable": result.stable,
                }
            )

            if result.stable and meaning_key is not None:
                text_out = translation.translate(meaning_key, output_language_box[0])
                if text_out is not None:
                    await websocket.send_json(
                        {
                            "type": "message",
                            "speaker": "signer",
                            "meaning_key": meaning_key,
                            "language": output_language_box[0],
                            "text": text_out,
                            "speak": True,
                        }
                    )

    except WebSocketDisconnect:
        pass
    finally:
        recognizer.close()


async def _handle_control_message(websocket, recognizer, text: str, output_language_box: list) -> None:
    import json

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return

    msg_type = payload.get("type")

    if msg_type == "reset":
        recognizer.reset()
        await websocket.send_json({"type": "status", "state": "reset"})

    elif msg_type == "set_language":
        lang = payload.get("language")
        if translation.is_supported_language(lang):
            output_language_box[0] = lang
            await websocket.send_json({"type": "status", "state": "language_ack", "language": lang})
        else:
            await websocket.send_json(
                {"type": "error", "code": "invalid_language", "message": f"Unsupported language: {lang}"}
            )


def _decode_jpeg(data: bytes) -> np.ndarray | None:
    try:
        arr = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return frame
    except Exception:  # noqa: BLE001
        return None
