# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Live EN→VI translator: captures English **system audio** (meetings, video, calls) in the browser, streams it to a local Python backend, and displays bilingual (English + Vietnamese) captions in real time. Runs **100% locally on CPU** — no API keys, audio never leaves the machine once models are cached. Documentation (README.md, SETUP.md, ARCHITECTURE.md) is in Vietnamese.

## Commands

There is no build, lint, or test suite. The backend serves the frontend, so it's a single process.

```powershell
# First-time setup (run from backend/)
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pip-system-certs   # avoids SSL errors behind corporate CA inspection

# Run (downloads ~780MB of models into the HuggingFace cache on first run)
python server.py               # then open http://localhost:8000
```

Or double-click `run.bat` from the repo root — it creates the venv, installs deps on first run, starts the server, and opens the browser when port 8000 is ready.

Requires Python 3.9–3.12 and Chrome or Edge (only these share system audio well on Windows).

## Architecture

The data path crosses three execution contexts; understanding the audio pipeline requires reading all of them together:

1. **Browser main thread** (`frontend/app.js`) — `getDisplayMedia({audio:true})` captures system audio. Crucially, `AudioContext` is constructed with `{ sampleRate: 16000 }` so the **browser itself resamples** the 48kHz system audio down to the 16kHz Whisper expects (no manual resampler). The video track is stopped immediately; the worklet node is intentionally **not** connected to `destination` to avoid an audio feedback loop.

2. **AudioWorklet** (`frontend/audio-processor.js`) — runs off-main-thread, converts Float32 → Int16 PCM, and posts ~100ms binary chunks back to the main thread, which forwards them over the WebSocket.

3. **Python backend** (`backend/server.py`) — single FastAPI process. The `/ws` endpoint accumulates incoming PCM into a buffer and only processes once it reaches `CHUNK_SECONDS` (4s) worth of samples. Inference (`process_audio`) is **blocking and CPU-heavy**, so it runs in `run_in_executor` to keep the async loop free to receive new audio. Two separate models are chained: `faster-whisper` (STT, `vad_filter=True` to drop silence) → `opus-mt-en-vi` MarianMT (translation). Results `{en, vi}` are sent back per segment. The frontend is served via `StaticFiles` mounted at `/` — this mount **must stay declared after** the `/ws` route or it shadows it.

**Two-model design (not one combined model):** STT and translation are deliberately split so each step uses a small, CPU-optimized model and so both English and Vietnamese text are available for the bilingual display. Models are swappable via constants at the top of `server.py` (`WHISPER_MODEL`, `MT_MODEL`, `CHUNK_SECONDS`).

**Latency tradeoff:** the fixed `CHUNK_SECONDS` window is the core limitation — smaller = faster response but sentences get cut mid-boundary (worse translation); larger = better context but more delay. This is the main lever and the documented v1 weakness. The roadmap (ARCHITECTURE.md §11) proposes replacing fixed chunking with VAD-based sentence segmentation.

## Offline / corporate-network model loading

This is the most error-prone area and is heavily addressed in the code and SETUP.md §5–6. Key facts:

- `server.py` sets `HF_HUB_DISABLE_SYMLINKS`, `HF_HUB_DISABLE_XET` env vars **before importing HF libraries** — order matters; new constraints must be set the same way.
- Models load by HuggingFace **repo name** and resolve through the HF cache (`~/.cache/huggingface/hub/`), not from a path in the repo.
- `backend/download_models.py` is a fallback that downloads the translation model via plain `httpx` (with retry, bypassing the Xet protocol) into `backend/models/opus-mt-en-vi/`. **If you use it, you must change `MT_MODEL` in `server.py` to `"models/opus-mt-en-vi"`** for the local path to take effect — otherwise the repo-name default still hits the HF cache.
- For fully offline runs, set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` (env vars or at the top of `server.py`). The recommended deployment is: download models on an unrestricted network → copy the HF cache → run offline.
