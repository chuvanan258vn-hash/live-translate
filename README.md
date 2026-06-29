# Live EN → VI Translator (local, CPU)

Dịch thời gian thực mọi âm thanh tiếng Anh phát ra trên máy (meeting, video, call...) sang tiếng Việt.
Hiển thị song ngữ. **Chạy 100% trên máy bạn — không API key, không gửi dữ liệu ra ngoài** (sau khi đã tải model lần đầu).

## Cách hoạt động

```
Browser (getDisplayMedia: share màn hình + system audio)
   → gửi PCM 16kHz qua WebSocket
   → Backend Python:  faster-whisper (STT English)  →  opus-mt-en-vi (dịch VI)
   → trả text song ngữ → hiển thị
```

## Cài đặt (lần đầu)

Cần Python 3.9–3.12.

```powershell
cd D:\myProject\live-translate\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Lần chạy đầu sẽ tự tải model (~480MB Whisper + ~300MB model dịch). Cần mạng lúc này, sau đó offline.

## Chạy

```powershell
cd D:\myProject\live-translate\backend
.\venv\Scripts\Activate.ps1
python server.py
```

Đợi log `Models loaded`, rồi mở trình duyệt: **http://localhost:8000**

1. Bấm **Bắt đầu** → chọn tab/màn hình muốn nghe.
2. **QUAN TRỌNG:** tick **"Share tab audio" / "Share system audio"** trong hộp thoại chia sẻ.
3. Mọi tiếng Anh phát ra sẽ hiện English + Tiếng Việt.

## Tinh chỉnh (sửa trong `backend/server.py`)

| Mục tiêu | Sửa |
|---|---|
| Nhanh hơn | `WHISPER_MODEL = "base.en"` |
| Chính xác hơn (STT) | `WHISPER_MODEL = "medium.en"` (nặng CPU) |
| Dịch tự nhiên hơn | `MT_MODEL = "vinai/vinai-translate-en2vi"` |
| Phản hồi sớm hơn / trễ ít hơn | giảm `CHUNK_SECONDS` (vd 2.5) — đổi lại câu hay bị cắt giữa chừng |

## Lưu ý
- Chỉ Chrome/Edge mới hỗ trợ chia sẻ **system audio** tốt trên Windows.
- Độ trễ ~2–4 giây tùy CPU. Dùng `base.en` + giảm `CHUNK_SECONDS` nếu cần phản hồi nhanh cho khách.
- Đây là bản tối thiểu (v1): xử lý theo từng khối 4s. Có thể nâng cấp dùng VAD theo câu để mượt hơn.
