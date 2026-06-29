@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0backend"

echo ============================================
echo   Live EN -^> VI Translator
echo ============================================

REM --- Lan dau: tao venv + cai dependencies ---
if not exist "venv\Scripts\python.exe" (
    echo [*] Lan dau chay - tao moi truong ao va cai dependencies...
    echo     ^(buoc nay tai torch + model, co the lau vai phut^)
    python -m venv venv
    if errorlevel 1 (
        echo [!] Khong tao duoc venv. Kiem tra Python da cai chua.
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [!] Cai dependencies that bai.
        pause
        exit /b 1
    )
) else (
    call venv\Scripts\activate.bat
)

REM --- Khoi dong server trong cua so rieng (BE + FE) ---
echo [*] Khoi dong server... ^(cho log "Models loaded" trong cua so moi^)
start "live-translate-server" cmd /k python server.py

REM --- Doi server mo cong 8000 roi tu mo trinh duyet ---
echo [*] Dang doi server san sang...
powershell -NoProfile -Command "$ok=$false; while(-not $ok){ try{ $c=New-Object Net.Sockets.TcpClient; $c.Connect('localhost',8000); $c.Close(); $ok=$true } catch { Start-Sleep -Seconds 2 } }; Start-Process 'http://localhost:8000'"

echo [*] Da mo trinh duyet: http://localhost:8000
echo     ^(Dong cua so server de tat ung dung^)
endlocal
