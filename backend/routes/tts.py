
import os
from io import BytesIO

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sarvamai import SarvamAI

load_dotenv()

router = APIRouter(prefix="/api/tts", tags=["tts"])

LANGUAGE_CONFIG = {
    "ta": {"language_code": "ta-IN", "speaker": "ratan"},
    "te": {"language_code": "te-IN", "speaker": "neha"},
    "kn": {"language_code": "kn-IN", "speaker": "neha"},
    "ml": {"language_code": "ml-IN", "speaker": "shubh"},
    "hi": {"language_code": "hi-IN", "speaker": "priya"},
}

class TTSRequest(BaseModel):
    text: str
    language: str

@router.post("")
def generate_speech(request: TTSRequest):
    text = request.text.strip()
    language = request.language.lower().strip()

    if not text:
        raise HTTPException(status_code=400, detail="Text is required.")

    config = LANGUAGE_CONFIG.get(language)
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported TTS language: {language}"
        )

    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="SARVAM_API_KEY is not configured."
        )

    try:
        client = SarvamAI(api_subscription_key=api_key)

        audio = client.text_to_speech.convert(
            text=text,
            model="bulbul:v3",
            language_code=config["language_code"],
            speaker=config["speaker"],
            pace=0.9,
        )

        audio_bytes = BytesIO()

        # Sarvam SDK response exposes the generated audio as base64.
        import base64
        encoded = audio.audios[0]
        audio_bytes.write(base64.b64decode(encoded))

        return Response(
            content=audio_bytes.getvalue(),
            media_type="audio/wav",
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Sarvam TTS failed: {exc}"
        )
