"""
Launcher cho Live EN -> VI Translator.

Khoi dong backend (server.py - phuc vu luon frontend), cho toi khi
http://localhost:8000 san sang (HTTP 200) roi tu mo tab trinh duyet.
Dong cua so nay -> server tat theo.

Dong goi thanh .exe:
    pip install pyinstaller
    pyinstaller --onefile --name LiveTranslate launcher.py
.exe phai dat CUNG THU MUC voi folder backend (vd: thu muc goc project).
"""
import os
import sys
import time
import socket
import subprocess
import urllib.request
import webbrowser

PORT = 8000
URL = f"http://localhost:{PORT}"
STARTUP_TIMEOUT = 600  # giay - lan dau load model co the lau


def base_dir() -> str:
    """Thu muc chua .exe (khi da dong goi) hoac chua file .py (khi chay truc tiep)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_python(backend: str) -> str:
    """Uu tien python trong venv cua project; neu khong co thi dung python he thong."""
    venv_py = os.path.join(backend, "venv", "Scripts", "python.exe")
    if os.path.isfile(venv_py):
        return venv_py
    return sys.executable if not getattr(sys, "frozen", False) else "python"


def port_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def http_ready() -> bool:
    try:
        with urllib.request.urlopen(URL, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def main() -> int:
    base = base_dir()
    backend = os.path.join(base, "backend")
    server = os.path.join(backend, "server.py")

    if not os.path.isfile(server):
        print(f"[!] Khong tim thay {server}")
        print("    Dat file .exe cung thu muc voi folder 'backend'.")
        input("Nhan Enter de thoat...")
        return 1

    python = find_python(backend)

    print("=" * 50)
    print("   Live EN -> VI Translator")
    print("=" * 50)
    print(f"[*] Khoi dong server... ({python})")
    print("    (Lan dau load model co the mat 1-2 phut)")

    # Neu da co server chay san o 8000 thi khoi dong lai luon trinh duyet.
    if http_ready():
        print("[*] Server da chay san. Mo trinh duyet...")
        webbrowser.open(URL)
        input("Nhan Enter de thoat...")
        return 0

    proc = subprocess.Popen([python, "-u", "server.py"], cwd=backend)

    opened = False
    start = time.time()
    try:
        while True:
            if proc.poll() is not None:
                print(f"\n[!] Server da dung (ma loi {proc.returncode}). Xem log o tren.")
                input("Nhan Enter de thoat...")
                return proc.returncode or 1

            if not opened and port_open() and http_ready():
                print(f"\n[+] San sang! Mo trinh duyet: {URL}")
                webbrowser.open(URL)
                opened = True
                print("[*] Dang chay. Dong cua so nay de tat server.")

            if not opened and time.time() - start > STARTUP_TIMEOUT:
                print("\n[!] Qua thoi gian cho server san sang.")
                proc.terminate()
                input("Nhan Enter de thoat...")
                return 1

            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Dang tat server...")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
