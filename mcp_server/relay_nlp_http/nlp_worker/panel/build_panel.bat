@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo  nlp-worker-panel build  (PySide6 edition)
echo ============================================================
echo  Work dir: %CD%
echo.

echo [1/4] Check dependencies ...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] python not found in PATH
    pause
    exit /b 1
)
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] PyInstaller not found. Run: pip install pyinstaller
    pause
    exit /b 1
)
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] PySide6 not found. Run:
    echo           pip install -i https://pypi.tuna.tsinghua.edu.cn/simple PySide6
    pause
    exit /b 1
)
echo   OK

echo [2/4] Clean old build ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist nlp-worker-panel.spec del /q nlp-worker-panel.spec
echo   OK

echo [3/4] Building (PySide6 is big, about 2-4 minutes) ...
python -m PyInstaller --clean --noconfirm --onefile --windowed ^
    --name nlp-worker-panel ^
    --hidden-import yaml ^
    --hidden-import dotenv_io ^
    --hidden-import form ^
    --hidden-import validate ^
    --hidden-import widgets ^
    --hidden-import runner ^
    --hidden-import yaml_io ^
    --hidden-import schema ^
    --exclude-module PySide6.QtWebEngineCore ^
    --exclude-module PySide6.QtWebEngineWidgets ^
    --exclude-module PySide6.Qt3DCore ^
    --exclude-module PySide6.QtMultimedia ^
    --exclude-module PySide6.QtCharts ^
    --exclude-module PySide6.QtQuick ^
    --exclude-module PySide6.QtQml ^
    --exclude-module tkinter ^
    --paths "%~dp0." "%~dp0panel_qt.py"

if errorlevel 1 (
    echo.
    echo   [FAILED] build error, see log above
    pause
    exit /b 1
)

echo [4/4] Verify output ...
if not exist "dist\nlp-worker-panel.exe" (
    echo   [FAILED] dist\nlp-worker-panel.exe not generated
    pause
    exit /b 1
)
echo   OK

if exist build rmdir /s /q build
if exist nlp-worker-panel.spec del /q nlp-worker-panel.spec

echo.
echo ============================================================
echo  BUILD DONE
echo ============================================================
echo  Output: %CD%\dist\nlp-worker-panel.exe
echo.
echo  Deploy steps:
echo    1. put nlp-worker-panel.exe beside nlp_worker.exe
echo       (same folder - the panel looks for it there)
echo    2. double-click nlp-worker-panel.exe
echo    3. pick your config.yaml, fill in the Basic tab
echo    4. fill in the .env tab for any ${VAR} keys
echo    5. click Validate, then Save, then Start
echo.
echo  Notes:
echo    - Panel reads config.yaml + .env in the same folder
echo    - To add a new config item, edit schema.py only
echo    - Excludes QtWebEngine/QtMultimedia etc. to keep size down
echo ============================================================
echo.

pause
endlocal
