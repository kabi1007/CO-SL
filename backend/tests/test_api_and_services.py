"""
Tests that do NOT require the .keras model files or a camera to run.
Model-loading / inference itself is intentionally not unit-tested here
since it depends on binary files the user places locally (see README) -
fabricating accuracy tests against a model that may not exist would be
misleading.
"""

from fastapi.testclient import TestClient

from backend.main import app
from backend.services import meaning_mapper, translation
from backend.services.session import SessionStore

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_models_schema():
    resp = client.get("/api/models")
    assert resp.status_code == 200
    body = resp.json()
    ids = {m["id"] for m in body["models"]}
    assert ids == {"ASL", "ISL"}
    for m in body["models"]:
        assert "available" in m
        assert "name" in m


def test_create_session_valid():
    resp = client.post(
        "/api/session", json={"sign_language": "ASL", "output_language": "en"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"sign_language": "ASL", "output_language": "en"}


def test_create_session_invalid_sign_language():
    resp = client.post(
        "/api/session", json={"sign_language": "BSL", "output_language": "en"}
    )
    assert resp.status_code == 400


def test_create_session_invalid_output_language():
    resp = client.post(
        "/api/session", json={"sign_language": "ASL", "output_language": "fr"}
    )
    assert resp.status_code == 400


def test_meaning_mapper_asl():
    assert meaning_mapper.to_meaning_key("ASL", "hello") == "HELLO"
    assert meaning_mapper.to_meaning_key("ASL", "thankyou") == "THANK_YOU"
    assert meaning_mapper.to_meaning_key("ASL", "unknown_label") is None


def test_meaning_mapper_isl():
    assert meaning_mapper.to_meaning_key("ISL", "Hello") == "HELLO"
    assert meaning_mapper.to_meaning_key("ISL", "How_are_you") == "HOW_ARE_YOU"
    assert meaning_mapper.to_meaning_key("ISL", "hello") is None  # case-sensitive, different vocab


def test_translation_all_supported_languages():
    for key in ["HELLO", "THANK_YOU", "PLEASE", "YES", "NO", "GOOD", "GOOD_MORNING", "HOW_ARE_YOU"]:
        for lang in ["en", "ta", "hi"]:
            text = translation.translate(key, lang)
            assert text, f"Missing translation for {key}/{lang}"


def test_translation_unknown_key():
    assert translation.translate("NOT_A_KEY", "en") is None


def test_session_store_isolated_instance():
    store = SessionStore()
    cfg = store.create("isl", "ta")
    assert cfg.sign_language == "ISL"
    assert cfg.output_language == "ta"


def test_websocket_invalid_sign_language_closes_with_error():
    with client.websocket_connect("/ws/sign/XYZ") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "invalid_sign_language"


def test_websocket_model_missing_reports_clean_error(monkeypatch):
    # With no model files present and mock mode off, the server must
    # report a clean model_missing error rather than crashing.
    from backend import config as cfg
    monkeypatch.setattr(cfg, "MOCK_MODE", False)
    with client.websocket_connect("/ws/sign/ASL") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "model_missing"
