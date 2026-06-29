"""
Tai model opus-mt-en-vi ve thu muc local bang httpx (co retry),
de tranh bo tai cua huggingface_hub bi firewall cong ty reset.

Chay 1 lan:  python download_models.py
Sau do server.py se load tu  ./models/opus-mt-en-vi
"""
import os
import time

import httpx

REPO = "Helsinki-NLP/opus-mt-en-vi"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "opus-mt-en-vi")
API = f"https://huggingface.co/api/models/{REPO}"
BASE = f"https://huggingface.co/{REPO}/resolve/main"

os.makedirs(OUT_DIR, exist_ok=True)


def list_files():
    r = httpx.get(API, timeout=30, follow_redirects=True)
    r.raise_for_status()
    return [s["rfilename"] for s in r.json()["siblings"]]


def download(fname, retries=6):
    url = f"{BASE}/{fname}"
    dest = os.path.join(OUT_DIR, fname)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for attempt in range(1, retries + 1):
        try:
            tmp = dest + ".part"
            got = 0
            with httpx.stream("GET", url, timeout=60, follow_redirects=True) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                with open(tmp, "wb") as f:
                    for chunk in r.iter_bytes(1 << 20):
                        f.write(chunk)
                        got += len(chunk)
                        if total:
                            pct = got * 100 // total
                            print(f"\r  {fname}: {pct:3d}%  ({got/1e6:.1f}/{total/1e6:.1f} MB)", end="", flush=True)
            os.replace(tmp, dest)
            print(f"\r  {fname}: done ({got/1e6:.1f} MB)            ")
            return
        except Exception as e:
            print(f"\r  {fname}: loi lan {attempt}/{retries} -> {type(e).__name__}; thu lai...   ")
            time.sleep(2 * attempt)
    raise RuntimeError(f"Tai that bai: {fname}")


def main():
    print(f"[*] Lay danh sach file cua {REPO} ...")
    files = list_files()
    # bo qua cac file khong can (tf/flax/onnx) cho nhe
    skip = (".h5", ".msgpack", ".onnx", "rust_model.ot")
    files = [f for f in files if not f.endswith(skip)]
    print(f"[*] Se tai {len(files)} file vao {OUT_DIR}")
    for f in files:
        download(f)
    print("[*] XONG. Da tai model ve local.")


if __name__ == "__main__":
    main()
