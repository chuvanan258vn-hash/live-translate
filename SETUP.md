# Hướng dẫn cài đặt & chạy — Live EN → VI Translator

Ứng dụng dịch **thời gian thực** mọi âm thanh tiếng Anh phát ra trên máy (meeting, video call, YouTube...) sang **tiếng Việt**, hiển thị song ngữ. **Chạy 100% trên máy bạn** (sau khi đã tải model về) — không cần API key, không gửi dữ liệu ra ngoài.

> ⚠️ **Đọc trước:** Mạng công ty thường chặn việc tải model. Cách chắc ăn nhất:
> **(1) Cài + tải model ở MÁY NHÀ** (mạng thoáng) → **(2) Copy cache model sang máy công ty** → **(3) Chạy offline ở công ty.**
> Chi tiết ở [Phần 6](#6-mang-cong-ty-chan--tai-o-nha-roi-mang-vao).

---

## 0. Tổng quan hệ thống

```
[Âm thanh hệ thống]
   │  Trình duyệt: getDisplayMedia (chia sẻ màn hình + system audio)
   │  → chuyển thành PCM 16kHz, gửi qua WebSocket
   ▼
[Backend Python (chạy local, localhost:8000)]
   • faster-whisper (small.en)   → nhận diện giọng nói tiếng Anh → text English
   • opus-mt-en-vi               → dịch sang tiếng Việt
   │  → trả text song ngữ qua WebSocket
   ▼
[Trình duyệt hiển thị 2 dòng]:  🇬🇧 English   +   🇻🇳 Tiếng Việt
```

Backend phục vụ luôn frontend → chỉ **1 process duy nhất**, mở `http://localhost:8000`.

### Cấu trúc thư mục
```
live-translate/
├── SETUP.md              ← file này
├── README.md            ← hướng dẫn ngắn
├── run.bat              ← double-click để chạy (tự setup lần đầu + mở trình duyệt)
├── backend/
│   ├── server.py            ← server chính (Whisper + dịch + WebSocket)
│   ├── download_models.py   ← tải model thủ công (dùng khi mạng chặn bộ tải của HF)
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── app.js
    └── audio-processor.js
```

---

## 1. Yêu cầu

| Thành phần | Yêu cầu |
|---|---|
| **Python** | 3.9 – 3.12 (đã test 3.11). Tải tại python.org, **tick "Add Python to PATH"** khi cài. |
| **Trình duyệt** | **Chrome** hoặc **Edge** (chỉ 2 trình duyệt này chia sẻ *system audio* tốt trên Windows). |
| **Dung lượng đĩa** | ~3–4 GB (torch + 2 model). |
| **RAM** | ≥ 8 GB. |

Kiểm tra Python:
```powershell
python --version
```

---

## 2. Cài đặt (làm ở MÁY NHÀ, mạng thoáng)

Mở **PowerShell**, chạy lần lượt:

```powershell
cd D:\myProject\live-translate\backend

# Tạo môi trường ảo
python -m venv venv

# Kích hoạt
.\venv\Scripts\Activate.ps1
# (Nếu báo lỗi execution policy, chạy 1 lần:)
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Cập nhật pip & cài thư viện
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` gồm:
```
fastapi
uvicorn[standard]
faster-whisper
transformers
torch
sentencepiece
sacremoses
numpy
```

> 💡 Nên cài thêm gói này để tránh lỗi SSL trên mạng công ty (xem Phần 5):
> ```powershell
> pip install pip-system-certs
> ```

---

## 3. Tải model về (làm ở MÁY NHÀ)

Có **2 model** cần tải. Khi mạng thoáng, chỉ cần **chạy server lần đầu là nó tự tải**:

```powershell
cd D:\myProject\live-translate\backend
.\venv\Scripts\Activate.ps1
python server.py
```

Lần đầu sẽ tải về và lưu vào **cache HuggingFace**. Đợi tới khi thấy dòng:
```
[*] Models loaded. Mo http://localhost:8000
```

### Model dùng & dung lượng

| Model | Repo (HuggingFace) | Dung lượng | Vai trò |
|---|---|---|---|
| Speech-to-Text | `Systran/faster-whisper-small.en` | ~480 MB | Nghe tiếng Anh → text |
| Dịch | `Helsinki-NLP/opus-mt-en-vi` | ~300 MB | English → Tiếng Việt |

### Nơi lưu cache (QUAN TRỌNG — để copy sang máy khác)
```
C:\Users\<TÊN_USER>\.cache\huggingface\hub\
   ├── models--Systran--faster-whisper-small.en\
   └── models--Helsinki-NLP--opus-mt-en-vi\
```

### Nếu bộ tải tự động bị lỗi → dùng script tải thủ công
Script `download_models.py` tải model dịch bằng cách thường (có retry), tránh giao thức Xet:
```powershell
python download_models.py
```
Nó lưu vào `backend\models\opus-mt-en-vi\`. Nếu dùng cách này, sửa `server.py`:
```python
MT_MODEL = "models/opus-mt-en-vi"   # trỏ tới thư mục local thay vì repo HF
```

---

## 4. Chạy ứng dụng

### Cách 1 — Double-click `run.bat` (dễ nhất)
- Lần đầu: tự tạo venv + cài thư viện.
- Các lần sau: khởi động server và **tự mở trình duyệt** khi sẵn sàng.
- Tắt app: đóng cửa sổ `live-translate-server`.

### Cách 2 — Chạy tay
```powershell
cd D:\myProject\live-translate\backend
.\venv\Scripts\Activate.ps1
python server.py
```
Rồi mở trình duyệt: **http://localhost:8000**

### Cách dùng
1. Bấm **Bắt đầu** → chọn tab/màn hình muốn nghe.
2. **QUAN TRỌNG:** tick **"Share tab audio" / "Share system audio"** trong hộp thoại.
3. Mọi tiếng Anh phát ra sẽ hiện **English + Tiếng Việt**, cuộn liên tục.
4. Bấm **Dừng** (hoặc đóng tab) để kết thúc.

---

## 5. Các lỗi mạng công ty & cách đã xử lý

Những lỗi này **đã được fix sẵn** trong code/cài đặt. Ghi lại để bạn hiểu và xử nếu gặp lại trên máy khác.

### 5.1. Lỗi SSL: `CERTIFICATE_VERIFY_FAILED`
**Nguyên nhân:** mạng công ty thay chứng chỉ gốc bằng CA nội bộ; Python không tin.
**Fix:**
```powershell
pip install pip-system-certs
```
(Cho Python dùng kho chứng chỉ của Windows — vốn đã có CA công ty.)

### 5.2. Lỗi `WinError 1314 — A required privilege is not held` (symlink)
**Nguyên nhân:** Windows không cho tạo symlink nếu không bật Developer Mode/admin.
**Fix:** đã thêm sẵn vào đầu `server.py`:
```python
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
```

### 5.3. Tải file lớn bị **treo ở vài MB** (giao thức Xet)
**Nguyên nhân:** HuggingFace mới tải file lớn qua giao thức **Xet** (endpoint riêng) → proxy chặn → treo.
**Fix:** đã thêm sẵn vào `server.py`:
```python
os.environ["HF_HUB_DISABLE_XET"] = "1"
```

### 5.4. Lỗi `WinError 10054 — connection forcibly closed`
**Nguyên nhân:** firewall công ty **reset** kết nối tải file lớn.
**Fix:** không tải ở công ty. Tải ở nhà rồi copy cache sang (Phần 6), hoặc dùng `download_models.py`.

---

## 6. Mạng công ty chặn — tải ở nhà rồi mang vào

Đây là cách **được khuyên dùng** cho máy công ty.

### Bước 1 — Ở MÁY NHÀ
Làm xong Phần 2 + 3 (cài + tải model thành công, chạy thử OK).

### Bước 2 — Copy 2 thứ sang máy công ty
1. **Toàn bộ thư mục project** `live-translate\` (gồm cả `backend\venv\` nếu cùng phiên bản Python & Windows — nếu khác thì bỏ `venv`, cài lại bằng `pip install` ở công ty với file `.whl` mang theo, hoặc dùng `pip download` ở nhà).
2. **Thư mục cache model** từ nhà:
   ```
   C:\Users\<USER_NHA>\.cache\huggingface\hub\
   ```
   → chép sang máy công ty vào đúng:
   ```
   C:\Users\<USER_CTY>\.cache\huggingface\hub\
   ```

   Hoặc gọn hơn — đặt cache **ngay trong project** để khỏi phụ thuộc đường dẫn user:
   - Ở nhà, copy 2 thư mục `models--...` vào `live-translate\hf-cache\hub\`.
   - Trên cả 2 máy, đặt biến môi trường trước khi chạy:
     ```powershell
     $env:HF_HOME = "D:\myProject\live-translate\hf-cache"
     ```
     (Hoặc thêm `os.environ["HF_HOME"] = r"...\hf-cache"` vào đầu `server.py`.)

### Bước 3 — Chạy offline ở công ty
Sau khi đã có sẵn model trong cache, ép chạy offline để khỏi gọi mạng:
```powershell
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
python server.py
```
Hoặc thêm 2 dòng này vào đầu `server.py` (sau các `os.environ` khác):
```python
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
```
→ App chạy hoàn toàn offline, **không gọi mạng**, không bị firewall chặn.

> 💡 Vấn đề `venv`: môi trường ảo Python **không nên copy nguyên** giữa 2 máy khác cấu hình. An toàn nhất:
> - Ở nhà: `pip download -r requirements.txt -d wheels` → mang thư mục `wheels\` vào công ty.
> - Ở công ty: `pip install --no-index --find-links wheels -r requirements.txt`.

---

## 7. Tinh chỉnh (sửa trong `backend/server.py`)

| Mục tiêu | Sửa |
|---|---|
| Nhanh hơn (CPU yếu) | `WHISPER_MODEL = "base.en"` |
| Nghe chính xác hơn | `WHISPER_MODEL = "medium.en"` (nặng hơn nhiều) |
| Dịch tự nhiên hơn | `MT_MODEL = "vinai/vinai-translate-en2vi"` (nặng hơn) |
| Phản hồi sớm hơn | giảm `CHUNK_SECONDS` (vd `2.5`) — đổi lại câu dễ bị cắt giữa chừng |
| Trễ ít, câu dài đủ ý | tăng `CHUNK_SECONDS` (vd `5`) |

---

## 8. Khắc phục sự cố nhanh

| Hiện tượng | Cách xử |
|---|---|
| `python` không nhận | Cài lại Python, tick "Add to PATH", mở PowerShell mới. |
| `Activate.ps1` báo execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Không có dòng caption nào | Chưa tick "Share system/tab audio" khi chọn màn hình; hoặc nguồn không phát tiếng Anh. |
| Có English nhưng không có tiếng Việt | Model dịch chưa load xong / lỗi tải — xem log cửa sổ server. |
| Trễ quá lâu | Dùng `base.en` + giảm `CHUNK_SECONDS`. Đóng app nặng khác. |
| Lỗi tải model ở công ty | Làm theo Phần 6 (tải ở nhà → copy cache → chạy offline). |
| SmartScreen chặn `run.bat` | More info → Run anyway. |

---

## 9. Ghi chú độ trễ

- Máy chỉ có **CPU**: độ trễ cảm nhận ~**2–4 giây** mỗi câu. Đủ để nắm ý và phản hồi khách.
- Có **GPU NVIDIA**: sửa trong `server.py` `device="cuda"` để nhanh hơn nhiều (cần cài `torch` bản CUDA).
- Đây là bản **v1**: xử lý theo khối thời gian cố định nên đôi khi câu bị cắt ở ranh giới khối. Có thể nâng cấp cắt câu theo khoảng lặng (VAD) sau.
```
