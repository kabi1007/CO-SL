# CO-SL — Connecting signs, languages and people

CO-SL is a real-time, two-way communication bridge between a sign-language
user and a listener who doesn't know sign language. It combines your
existing trained ASL and ISL computer-vision models with a multilingual
text/speech layer (English, Tamil, Hindi) so a signer's message is
recognized live from a webcam and shown/spoken to the listener, who can
reply with text or speech.

This is not a generic "AI demo" landing page — the interface itself is the
product: a live camera feed, a recognized-message panel, and a conversation
history, built around your models exactly as they already work.

## Architecture

```
Browser (React)
  → webcam frames (JPEG, ~6-7 fps) over WebSocket
  → FastAPI backend
      → MediaPipe HolisticLandmarker (per-language config)
      → ASL/ISL preprocessing (ported 1:1 from live_asl_cosl.py / live_cosl.py)
      → Keras model (.keras, loaded once, never retrained/modified)
      → common meaning-key layer (normalizes ASL/ISL label differences)
      → translation dictionary (en / ta / hi)
  → WebSocket messages: status / prediction / message / error
  → React renders recognized text, speaks it (Web Speech API), and logs it
    to the on-screen conversation (no database, no server-side storage)
```

The frontend never touches `.keras`, `.npy`, or `.task` files — all ML
details are owned by the backend.

## Folder structure

```
cosl/
├── backend/
│   ├── main.py                 FastAPI app
│   ├── config.py                All paths/constants (OS-independent)
│   ├── requirements.txt
│   ├── models/
│   │   ├── asl/                 ← place your ASL model files here
│   │   └── isl/                 ← place your ISL model files here
│   ├── recognizers/
│   │   ├── base.py              Shared interface
│   │   ├── asl_recognizer.py    Ported from live_asl_cosl.py
│   │   ├── isl_recognizer.py    Ported from live_cosl.py
│   │   └── mock_recognizer.py   Demo-mode only, clearly flagged
│   ├── services/
│   │   ├── meaning_mapper.py    ASL/ISL label → common meaning key
│   │   ├── translation.py       meaning key → en/ta/hi text
│   │   └── session.py
│   ├── routes/
│   │   ├── health.py
│   │   ├── models.py
│   │   └── websocket.py         /ws/sign/{ASL|ISL} streaming endpoint
│   └── tests/
└── frontend/
    └── src/
        ├── components/          CameraPanel, Conversation, etc.
        ├── hooks/                useCamera, useSignWebSocket, useSpeech
        ├── services/             api.ts, speech.ts
        ├── types/
        └── App.tsx
```

## Where to place your model files

Copy your existing files into these exact paths (do not rename them):

```
backend/models/asl/cosl_asl_5words_baseline.keras
backend/models/asl/cosl_asl_5words_labels.json
backend/models/asl/mean.npy
backend/models/asl/std.npy
backend/models/asl/holistic_landmarker.task

backend/models/isl/cosl_isl_5words_baseline.keras
backend/models/isl/cosl_isl_5words_labels.json
```

**Note on the ISL `.task` file:** `live_cosl.py` loads its MediaPipe asset
from `mediapipe_models/holistic_landmarker.task`, but no ISL-specific
`.task` file path was given in the integration file list you provided. The
`.task` file is a generic MediaPipe landmarker asset (not trained on your
sign vocabulary), so the ISL recognizer defaults to reusing
`backend/models/asl/holistic_landmarker.task`. If you actually have a
separate ISL-specific `.task` file, place it at
`backend/models/isl/holistic_landmarker.task` and it will be preferred
automatically — no code changes needed.

## Install & run — backend

Requires Python 3.10+ (TensorFlow/MediaPipe compatibility).

```bash
cd cosl/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Place your model files as described above, then from the `cosl/` project
root (not inside `backend/`, so the `backend.*` imports resolve):

```bash
cd cosl
uvicorn backend.main:app --reload --port 8000
```

Health check: `http://localhost:8000/health` → `{"status": "ok"}`

## Install & run — frontend

Requires Node 18+.

```bash
cd cosl/frontend
npm install
cp .env.example .env   # adjust API/WS URLs if backend isn't on localhost:8000
npm run dev
```

Open `http://localhost:5173`.

## Testing ASL

1. Place the ASL files under `backend/models/asl/` (see above).
2. Start the backend and frontend.
3. In the browser, select **ASL** and any output language, enter the
   workspace, allow camera access.
4. Perform one of: `hello`, `thankyou`, `please`, `yes`, `no`, holding the
   sign steady for ~1–2 seconds.
5. The recognized meaning should appear on the right panel and be spoken.

## Testing ISL

1. Place the ISL files under `backend/models/isl/` (see above).
2. Select **ISL** in the setup screen.
3. Perform one of: `Hello`, `Thank_you`, `Good`, `Good_Morning`,
   `How_are_you`.
4. ISL requires a hand to be visible in frame to accumulate its 30-frame
   buffer — the buffer clears automatically if hands leave the frame.

## Enabling mock/demo mode

If you want to demo the UI without model files present (or before they're
copied in), start the backend with:

```bash
COSL_MOCK_MODE=true uvicorn backend.main:app --reload --port 8000
```

The UI will clearly show **"Demo mode"** next to the recognition status
whenever mock predictions are being used — this is never silently
substituted for real inference. If real model files ARE present, they take
priority over mock mode automatically.

## Running backend tests

```bash
cd cosl
python -m pytest backend/tests/ -v
```

These 12 tests cover the health endpoint, model metadata, session
validation, the meaning-mapping layer, the translation dictionary, and
WebSocket error handling (invalid sign language, missing model files) —
all without requiring the actual `.keras` files, since fabricating model
accuracy tests against files that may not exist would be misleading.

## Frontend type-check / build

```bash
cd cosl/frontend
npm run typecheck   # tsc --noEmit
npm run build        # production build (verified: builds cleanly)
```

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `/api/models` shows `available: false` | Model files aren't at the exact paths listed above |
| WebSocket sends `{"type":"error","code":"model_missing"}` | Same as above, or `COSL_MOCK_MODE` is off with no files present |
| WebSocket sends `{"type":"error","code":"model_load_failed"}` | Check backend logs — usually a TensorFlow/MediaPipe version mismatch |
| "Camera permission required" | Grant camera access in the browser; HTTPS or `localhost` is required by most browsers |
| No speech output | Browser has no voice for the selected language — UI shows "Speech unavailable" instead of failing silently |
| CORS errors in console | Confirm `frontend/.env`'s `VITE_API_BASE_URL`/`VITE_WS_BASE_URL` match where the backend is actually running, and that origin is in `backend/config.py`'s `CORS_ALLOW_ORIGINS` |

## Known limitations (prototype scope)

- Fixed vocabulary only: 5 ASL signs, 5 ISL signs, 8 shared meaning keys.
- Reverse (listener → signer) communication is text-only; no ASL/ISL
  animation generation is implemented, as specified.
- No persistence — conversation history lives in frontend memory only and
  is lost on page reload.
- Listener speech-to-text and TTS voice availability depend entirely on the
  browser (Web Speech API is not universally supported, particularly for
  Tamil/Hindi voices) — the UI degrades gracefully rather than failing.
- ASL stability uses a generic consecutive-frame confirmation layered on
  top of the ported model output (live_asl_cosl.py itself has no such
  debouncing since it only prints to an OpenCV window); ISL uses its
  original majority-vote window, ported as-is.

## Demonstrating to judges

1. Select **ASL** → **English** → enter workspace → allow camera.
2. Perform `hello` → right panel shows **Hello**, spoken aloud.
3. Type/speak a listener reply (e.g. "Hi!") → appears in conversation.
4. Switch listener language to **Tamil** (no need to leave the workspace).
5. Perform `hello` again → right panel shows **வணக்கம்**, spoken in Tamil if
   a Tamil voice is available in the browser.
6. Return to setup, switch to **ISL**, repeat with `Hello` — this
   demonstrates the sign-language selection actually swaps the underlying
   model, not just a UI label.
