# Tài liệu hệ thống — Live EN → VI Translator

> Tài liệu thiết kế tổng thể: **mục tiêu, các quyết định kỹ thuật, kiến trúc, luồng dữ liệu, lựa chọn công nghệ, đánh đổi và lộ trình nâng cấp.**
> Hướng dẫn cài đặt/chạy nằm ở [SETUP.md](SETUP.md). Hướng dẫn ngắn ở [README.md](README.md).

---

## 1. Mục tiêu & bối cảnh

### Vấn đề
Trong các cuộc họp / call có người nói **tiếng Anh**, cần một công cụ **dịch thời gian thực sang tiếng Việt** để thu hẹp rào cản ngôn ngữ và **phản hồi nhanh** cho khách hàng.

### Yêu cầu cốt lõi
| # | Yêu cầu | Ghi chú |
|---|---|---|
| 1 | Bắt **mọi âm thanh tiếng Anh** phát ra trên máy (meeting, video, call...) | Không chỉ mic, mà cả âm thanh hệ thống |
| 2 | Hiển thị **song ngữ**: text tiếng Anh + tiếng Việt | Để vừa nghe vừa đối chiếu |
| 3 | **Chạy trên máy người dùng** ("local") | Không cần deploy server riêng |
| 4 | **Không cần quá nhanh**, nhưng không được quá chậm | Đủ để reply khách |
| 5 | Ưu tiên **chi phí thấp & riêng tư** | Không tốn phí API, dữ liệu không bắt buộc rời máy |

---

## 2. Các quyết định kiến trúc (và lý do)

### 2.1. Cloud vs Local
Ý tưởng ban đầu tham khảo repo **[google-gemini/gemini-live-api-examples](https://github.com/google-gemini/gemini-live-api-examples)** — nhưng **Gemini Live API là dịch vụ cloud**: audio bị gửi lên server Google.

| Phương án | Ưu | Nhược | Kết luận |
|---|---|---|---|
| **A. Gemini Live API (cloud)** | Chất lượng/độ trễ tốt nhất, ít code | Tốn phí, cần API key, audio rời máy, cần mạng | ❌ |
| **B. Model chạy local (đã chọn)** | Miễn phí, offline được, riêng tư | Phụ thuộc CPU/GPU, độ trễ cao hơn | ✅ |

→ Chọn **B**: giữ *cách làm* của repo (capture audio → stream → caption song ngữ) nhưng **thay phần AI bằng model chạy local trên CPU**.

### 2.2. Tại sao tách 2 model (STT riêng, dịch riêng)?
Thay vì một mô hình "nghe + dịch" gộp (như Gemini), bản local tách 2 bước:
1. **Speech-to-Text** (nghe tiếng Anh → chữ tiếng Anh) — yêu cầu #2 cần text English.
2. **Machine Translation** (chữ Anh → chữ Việt).

Lợi ích: mỗi bước dùng model **nhỏ, chuyên dụng, tối ưu cho CPU**; dễ thay/đổi model từng phần; lấy được cả 2 dòng song ngữ tự nhiên.

### 2.3. Tại sao bắt audio ở trình duyệt?
Trình duyệt có sẵn `getDisplayMedia` → cho phép người dùng **chọn màn hình/tab và chia sẻ system audio** mà không cần cài driver/loopback. Đổi lại, người dùng phải tick "Share audio" mỗi lần (đã chấp nhận).

---

## 3. Kiến trúc tổng thể

```
┌─────────────────────────────── TRÌNH DUYỆT (Chrome/Edge) ───────────────────────────────┐
│                                                                                          │
│   getDisplayMedia({audio:true})                                                          │
│        │  (MediaStream: âm thanh hệ thống, 44.1/48 kHz)                                   │
│        ▼                                                                                  │
│   AudioContext(16 kHz)  ──►  AudioWorklet (pcm-processor)                                 │
│        │  trình duyệt tự resample về 16 kHz       │ Float32 → Int16 PCM, gói ~100ms       │
│        │                                          ▼                                       │
│        │                                   WebSocket.send(ArrayBuffer)                    │
│        ▼                                          │                                       │
│   UI hiển thị 2 dòng  ◄────────── JSON {en, vi} ──┘                                       │
│        🇬🇧 English / 🇻🇳 Tiếng Việt                                                        │
└──────────────────────────────────────────│──────────────────────────────────────────────┘
                                            │  ws://localhost:8000/ws  (PCM 16kHz int16)
                                            ▼
┌──────────────────────────── BACKEND PYTHON (FastAPI, localhost:8000) ─────────────────────┐
│                                                                                            │
│   WebSocket endpoint /ws                                                                    │
│        │  gom buffer tới ngưỡng CHUNK_SECONDS (mặc định 4s)                                 │
│        ▼                                                                                    │
│   process_audio()  (chạy trong thread executor để không chặn vòng lặp async)               │
│        │                                                                                    │
│        ├──►  faster-whisper (small.en, int8, vad_filter)  →  segment text tiếng Anh         │
│        │                                                                                    │
│        └──►  opus-mt-en-vi (MarianMT)  →  text tiếng Việt                                   │
│        │                                                                                    │
│        ▼                                                                                    │
│   gửi {en, vi} về client qua WebSocket                                                      │
│                                                                                            │
│   StaticFiles mount "/"  →  phục vụ luôn frontend (1 process duy nhất)                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Các thành phần

### 4.1. Frontend (`frontend/`)
| File | Vai trò |
|---|---|
| `index.html` | Giao diện: nút Bắt đầu/Dừng, vùng transcript cuộn, style tối |
| `app.js` | Xin chia sẻ màn hình, mở WebSocket, dựng AudioContext 16kHz + AudioWorklet, nhận và hiển thị kết quả |
| `audio-processor.js` | Chạy trong AudioWorklet: chuyển Float32 → Int16 PCM, gửi theo gói ~100ms về main thread |

**Điểm kỹ thuật quan trọng:** đặt `new AudioContext({ sampleRate: 16000 })` để **trình duyệt tự resample** audio hệ thống (48kHz) về 16kHz — đúng định dạng Whisper cần, khỏi tự viết resampler.

### 4.2. Backend (`backend/`)
| File | Vai trò |
|---|---|
| `server.py` | FastAPI + WebSocket; load 2 model; vòng lặp gom audio → STT → dịch → trả text; mount frontend |
| `download_models.py` | Tải model dịch thủ công (có retry) khi bộ tải HuggingFace bị mạng chặn |
| `requirements.txt` | Thư viện cần cài |

**Xử lý đồng thời:** inference là tác vụ chặn (blocking) và nặng → chạy trong `run_in_executor` để vòng lặp async vẫn nhận được audio mới trong lúc đang dịch.

---

## 5. Luồng dữ liệu chi tiết

1. Người dùng bấm **Bắt đầu** → `getDisplayMedia` → chọn màn hình + tick share audio.
2. Trình duyệt tạo `MediaStream` (audio hệ thống). Video track bị tắt ngay (không cần).
3. `AudioContext(16kHz)` + `AudioWorkletNode` đọc audio, chuyển sang **Int16 PCM**, gửi từng gói ~100ms qua WebSocket (binary).
4. Backend **gom buffer**. Khi đủ `CHUNK_SECONDS` (4s) → cắt một khối, xử lý:
   - `faster-whisper.transcribe(..., vad_filter=True)` bỏ khoảng lặng, trả các **segment** chữ tiếng Anh.
   - Mỗi segment → `opus-mt-en-vi` dịch sang tiếng Việt.
5. Backend gửi từng `{en, vi}` về client.
6. Frontend chèn thẻ mới (English + Tiếng Việt), tự cuộn xuống.

---

## 6. Lựa chọn model & lý do

| Khâu | Model mặc định | Kích thước | Vì sao chọn |
|---|---|---|---|
| STT | `Systran/faster-whisper-small.en` | ~480 MB | `faster-whisper` (CTranslate2) tối ưu mạnh cho **CPU**; bản `small.en` cân bằng tốc độ/độ chính xác; `int8` để nhẹ |
| Dịch | `Helsinki-NLP/opus-mt-en-vi` | ~300 MB | MarianMT **nhẹ, nhanh trên CPU**, chuyên EN→VI |

### Phương án thay thế (ghi trong `server.py`)
| Mục tiêu | Đổi sang |
|---|---|
| Nhanh hơn | `WHISPER_MODEL = "base.en"` |
| Nghe chính xác hơn | `WHISPER_MODEL = "medium.en"` |
| Dịch tự nhiên hơn | `MT_MODEL = "vinai/vinai-translate-en2vi"` |

---

## 7. Đặc tính độ trễ & hiệu năng

- Xử lý theo **khối cố định** `CHUNK_SECONDS = 4s`: nói xong một câu thì ~1–2s sau hiện text → **độ trễ cảm nhận ~2–4s** trên CPU thường.
- Đánh đổi tham số:
  - `CHUNK_SECONDS` nhỏ → phản hồi sớm hơn nhưng **dễ cắt câu giữa chừng** → dịch kém.
  - `CHUNK_SECONDS` lớn → câu đủ ý, dịch tốt hơn nhưng trễ hơn.
- Có **GPU NVIDIA**: đổi `device="cuda"` (cần `torch` CUDA) → nhanh hơn nhiều, có thể chạy `medium`.

---

## 8. Bảo mật & riêng tư

- Sau khi tải model, app chạy **hoàn toàn offline** (đặt `HF_HUB_OFFLINE=1`).
- Audio **không rời máy** — chỉ đi nội bộ trình duyệt ↔ `localhost`.
- Không API key, không tài khoản, không log ra ngoài.
- WebSocket chỉ bind `127.0.0.1` (localhost) → máy khác trong mạng không truy cập được.

---

## 9. Ràng buộc môi trường (mạng công ty)

Hệ thống đã xử lý sẵn các rào cản hay gặp trên máy doanh nghiệp (chi tiết & cách fix ở [SETUP.md §5–6](SETUP.md)):

| Rào cản | Triệu chứng | Giải pháp đã áp dụng |
|---|---|---|
| SSL inspection (CA nội bộ) | `CERTIFICATE_VERIFY_FAILED` | `pip install pip-system-certs` |
| Chặn tạo symlink | `WinError 1314` | `HF_HUB_DISABLE_SYMLINKS=1` |
| Chặn giao thức Xet (file lớn) | Tải treo ở vài MB | `HF_HUB_DISABLE_XET=1` |
| Firewall reset kết nối tải | `WinError 10054` | Tải ở nhà → copy cache → chạy `HF_HUB_OFFLINE=1` |

---

## 10. Hạn chế hiện tại (v1)

- **Cắt khối theo thời gian cố định** → đôi khi câu bị chia đôi ở ranh giới khối, làm dịch sai ngữ cảnh.
- Không có **VAD theo câu** (chỉ dùng `vad_filter` lọc im lặng trong khối).
- Không lưu lịch sử transcript ra file.
- Chỉ EN→VI một chiều; chưa tự nhận diện ngôn ngữ.
- Mỗi segment dịch độc lập → thiếu ngữ cảnh xuyên câu.

---

## 11. Lộ trình nâng cấp (đề xuất)

| Ưu tiên | Cải tiến | Lợi ích |
|---|---|---|
| Cao | **Cắt câu theo VAD/khoảng lặng** thay vì khối cố định | Hết cảnh câu bị cắt đôi, dịch mượt hơn |
| Cao | **Cửa sổ trượt + ghép câu** (streaming Whisper) | Giảm độ trễ, caption mượt như phụ đề |
| Vừa | **Lưu transcript** ra `.txt/.srt` theo buổi họp | Tra cứu lại sau |
| Vừa | Hiển thị **partial (tạm) → final** | Thấy chữ sớm, sửa dần |
| Thấp | Hỗ trợ **2 chiều / auto-detect ngôn ngữ** | Linh hoạt hơn |
| Thấp | Đóng gói **`.exe`** (PyInstaller) | Đem sang máy không cài Python (file lớn ~2GB) |
| Thấp | Chế độ **overlay nổi** trên màn hình | Xem caption khi đang ở app khác |

---

## 12. Công nghệ sử dụng

| Lớp | Công nghệ |
|---|---|
| Frontend | HTML/CSS/JS thuần, Web Audio API (AudioWorklet), WebSocket |
| Backend | Python, FastAPI, Uvicorn, WebSocket |
| STT | faster-whisper (CTranslate2) |
| Dịch | Hugging Face Transformers (MarianMT) |
| Nền tảng AI | PyTorch (CPU) |
```
