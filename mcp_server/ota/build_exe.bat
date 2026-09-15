@echo off
REM ============================================================
REM  build_exe.bat - build relay / http / feishu exe files
REM  Location: repo root (the folder that contains mcp_server)
REM  All commands are single-line ASCII only (no for loop, no caret
REM  continuation, no non-ASCII text) to avoid cmd parsing issues.
REM ============================================================
setlocal
cd /d %~dp0
set REPO_ROOT=%CD%
echo [BUILD] repo root: %REPO_ROOT%

if exist dist rmdir /s /q dist
mkdir dist
if exist build rmdir /s /q build
mkdir build

python -c "import PyInstaller" 2>nul
if errorlevel 1 python -m pip install pyinstaller

echo.
echo [BUILD] === relay ===
cd /d "%REPO_ROOT%\mcp_server\relay_nlp_http\relay"
if not exist "relay_multi.py" goto :nosrc
python -m PyInstaller --clean --onefile --noconsole --name relay_multi --hidden-import websockets --distpath "%REPO_ROOT%\dist" --workpath "%REPO_ROOT%\build\relay" --specpath "%REPO_ROOT%\build" relay_multi.py
if errorlevel 1 goto :fail

echo.
echo [BUILD] === http ===
cd /d "%REPO_ROOT%\mcp_server\relay_nlp_http\http"
if not exist "kz_mcp_http.py" goto :nosrc
python -m PyInstaller --onefile --noconsole --name kz_mcp_http --hidden-import websockets --distpath "%REPO_ROOT%\dist" --workpath "%REPO_ROOT%\build\http" --specpath "%REPO_ROOT%\build" kz_mcp_http.py
if errorlevel 1 goto :fail

echo.
echo [BUILD] === feishu ===
cd /d "%REPO_ROOT%\mcp_server\relay_nlp_http\feishu"
if not exist "feishu_bridge.py" goto :nosrc
python -m PyInstaller --clean --onefile --noconsole --name feishu_bridge --hidden-import websockets --hidden-import lark_oapi --distpath "%REPO_ROOT%\dist" --workpath "%REPO_ROOT%\build\feishu" --specpath "%REPO_ROOT%\build" feishu_bridge.py
if errorlevel 1 goto :fail

cd /d "%REPO_ROOT%"
echo.
echo [BUILD] output files:
dir /b dist\*.exe
echo [BUILD] OK
exit /b 0

:nosrc
cd /d "%REPO_ROOT%"
echo.
echo [BUILD][ERROR] source file not found. Is this bat in the repo root?
echo Expected: %REPO_ROOT%\mcp_server\relay_nlp_http\...
exit /b 1

:fail
cd /d "%REPO_ROOT%"
echo.
echo [BUILD][ERROR] packaging failed. See PyInstaller output above.
exit /b 1
