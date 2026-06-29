@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   Build LiveTranslate.exe
echo ============================================

set PY=backend\venv\Scripts\python.exe
if not exist "%PY%" (
    echo [!] Chua co venv. Chay run.bat mot lan de tao venv truoc.
    pause
    exit /b 1
)

echo [*] Cai PyInstaller (neu chua co)...
"%PY%" -m pip install --quiet pyinstaller

echo [*] Dong goi launcher.py -^> LiveTranslate.exe ...
"%PY%" -m PyInstaller --onefile --name LiveTranslate ^
    --distpath dist --workpath build --specpath build launcher.py
if errorlevel 1 (
    echo [!] Build that bai.
    pause
    exit /b 1
)

copy /y dist\LiveTranslate.exe LiveTranslate.exe >nul
rmdir /s /q build dist 2>nul

echo.
echo [*] XONG. Da tao LiveTranslate.exe o thu muc nay.
echo     Double-click de chay (tu mo server + trinh duyet).
pause
endlocal
