from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend import config
from backend.services.session import session_store

router = APIRouter()


def _asl_files_present() -> bool:
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


def _isl_files_present() -> bool:
    task_ok = (
        config.ISL_HOLISTIC_TASK_PATH_OVERRIDE.exists()
        or config.ISL_HOLISTIC_TASK_PATH_FALLBACK.exists()
    )
    return task_ok and all(
        p.exists() for p in [config.ISL_MODEL_PATH, config.ISL_LABELS_PATH]
    )


@router.get("/api/models")
def list_models():
    return {
        "models": [
            {
                "id": "ASL",
                "name": "American Sign Language",
                "available": _asl_files_present() or config.MOCK_MODE,
                "demo_mode": not _asl_files_present() and config.MOCK_MODE,
            },
            {
                "id": "ISL",
                "name": "Indian Sign Language",
                "available": _isl_files_present() or config.MOCK_MODE,
                "demo_mode": not _isl_files_present() and config.MOCK_MODE,
            },
        ]
    }


class SessionRequest(BaseModel):
    sign_language: str
    output_language: str


@router.post("/api/session")
def create_session(payload: SessionRequest):
    try:
        cfg = session_store.create(payload.sign_language, payload.output_language)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "sign_language": cfg.sign_language,
        "output_language": cfg.output_language,
    }
