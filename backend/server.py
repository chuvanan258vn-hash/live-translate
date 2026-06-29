"""
Live EN -> VI translator (100% local, CPU).

Luong xu ly:
  Browser bat audio he thong (getDisplayMedia) -> gui PCM 16kHz int16 qua WebSocket
  -> faster-whisper (speech-to-text English)
  -> opus-mt-en-vi (dich sang tieng Viet)
  -> tra ve text song ngu de hien thi.

Chay:  python server.py   (lan dau se tu tai model ve, can mang)
Mo:    http://localhost:8000
"""

import os

# Windows khong cho tao symlink neu khong bat Developer Mode / chay admin.
# Bao Hugging Face dung copy thay vi symlink (phai set TRUOC khi import HF libs).
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
# Proxy cong ty thuong chan giao thuc Xet (tai file lon) -> treo.
# Ep huggingface_hub dung HTTPS thuong de tai.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import asyncio
import json
import sys

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from faster_whisper import WhisperModel
from transformers import MarianMTModel, MarianTokenizer

# ----------------------------------------------------------------------------
# Cau hinh - chinh o day neu muon doi do nhanh/chinh xac
# ----------------------------------------------------------------------------
WHISPER_MODEL = "small.en"        # nhanh hon: "base.en" | chinh xac hon: "medium.en"
WHISPER_COMPUTE = "int8"          # toi uu cho CPU
MT_MODEL = "Helsinki-NLP/opus-mt-en-vi"   # nhe & nhanh; chat luong hon: "vinai/vinai-translate-en2vi"

SAMPLE_RATE = 16000
CHUNK_SECONDS = 4.0               # gom bao nhieu giay audio moi lan transcribe
MIN_SAMPLES = int(SAMPLE_RATE * CHUNK_SECONDS)
PORT = 8000

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

# ----------------------------------------------------------------------------
# Tai model (1 lan luc khoi dong)
# ----------------------------------------------------------------------------
print(f"[*] Loading Whisper model '{WHISPER_MODEL}' (compute={WHISPER_COMPUTE}) ...", flush=True)
whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type=WHISPER_COMPUTE)

print(f"[*] Loading translation model '{MT_MODEL}' ...", flush=True)
mt_tokenizer = MarianTokenizer.from_pretrained(MT_MODEL)
mt_model = MarianMTModel.from_pretrained(MT_MODEL)
print("[*] Models loaded. Mo http://localhost:%d" % PORT, flush=True)


def translate_en_vi(text: str) -> str:
    batch = mt_tokenizer([text], return_tensors="pt", truncation=True, max_length=512)
    generated = mt_model.generate(**batch, max_length=512, num_beams=2)
    return mt_tokenizer.decode(generated[0], skip_special_tokens=True)


def process_audio(audio: np.ndarray):
    """Chay STT + dich (blocking, goi trong executor)."""
    segments, _info = whisper.transcribe(
        audio,
        language="en",
        vad_filter=True,          # bo qua khoang im lang
        beam_size=1,
    )
    results = []
    for seg in segments:
        en = seg.text.strip()
        if en:
            vi = translate_en_vi(en)
            results.append({"en": en, "vi": vi})
    return results


app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_event_loop()
    buffer = np.zeros(0, dtype=np.float32)
    print("[+] Client connected", flush=True)
    try:
        while True:
            data = await websocket.receive_bytes()
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            buffer = np.concatenate([buffer, samples])

            if len(buffer) >= MIN_SAMPLES:
                audio = buffer
                buffer = np.zeros(0, dtype=np.float32)
                results = await loop.run_in_executor(None, process_audio, audio)
                for item in results:
                    await websocket.send_text(json.dumps(item))
    except WebSocketDisconnect:
        print("[-] Client disconnected", flush=True)
    except Exception as e:  # noqa
        print(f"[!] Error: {e}", file=sys.stderr, flush=True)


# Phuc vu frontend tinh (dat SAU khi da khai bao /ws)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=PORT)
