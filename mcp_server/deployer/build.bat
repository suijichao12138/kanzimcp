@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo  kanzi-deployer build
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
echo   OK

echo [2/4] Clean old build ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist kanzi-deployer.spec del /q kanzi-deployer.spec
echo   OK

echo [3/4] Building (about 1-2 minutes) ...
python -m PyInstaller --clean --onefile --noconsole --name kanzi-deployer --add-data "%~dp0web\static;web\static" --hidden-import core --hidden-import web --paths "%~dp0." "%~dp0deployer.py"

if errorlevel 1 (
    echo.
    echo   [FAILED] build error, see log above
    pause
    exit /b 1
)

echo [4/4] Verify output ...
if not exist "dist\kanzi-deployer.exe" (
    echo   [FAILED] dist\kanzi-deployer.exe not generated
    pause
    exit /b 1
)
echo   OK

if exist build rmdir /s /q build
if exist kanzi-deployer.spec del /q kanzi-deployer.spec

echo.
echo ============================================================
echo  BUILD DONE
echo ============================================================
echo  Output: %CD%\dist\kanzi-deployer.exe
echo.
echo  Deploy steps:
echo    1. mkdir an install dir, e.g. D:\kanziMCP_deployer\
echo    2. copy kanzi-deployer.exe into it
echo    3. run it - deployer_config.json is created automatically
echo    4. open http://^<this-machine-IP^>:9100 in browser
echo.
echo  Notes:
echo    - No password is set on first run: set one in Settings page ASAP
echo    - Building the 3 components requires python + pyinstaller on this machine
echo ============================================================
echo.

pause
endlocal
