@echo off
REM ============================================================
REM  build_exe.bat — 本地打包 relay / http / feishu 三个 exe
REM  由 ota_agent.py 调用（也可手动双击运行）
REM  打包参数以 ota_config.json 的 pyinstaller_args 为准，本脚本按同样参数执行
REM ============================================================
setlocal enabledelayedexpansion

cd /d %~dp0
set REPO_ROOT=%CD%
echo [BUILD] 仓库根目录: %REPO_ROOT%

if exist dist rmdir /s /q dist
mkdir dist

REM ── 依赖检查 ──
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [BUILD] 未安装 PyInstaller，正在安装...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [BUILD][ERROR] PyInstaller 安装失败
        exit /b 1
    )
)

REM ============================================================
REM  [1] relay  —— --clean --onefile --noconsole
REM ============================================================
echo.
echo [BUILD] === 打包 relay ===
cd /d "%REPO_ROOT%\mcp_server\relay_nlp_http\relay"
python -m PyInstaller --clean --onefile --noconsole --name relay_multi ^
    --hidden-import websockets ^
    --distpath "%REPO_ROOT%\dist" ^
    --workpath "%REPO_ROOT%\build\relay" ^
    --specpath "%REPO_ROOT%\build" ^
    relay_multi.py
if errorlevel 1 (
    echo [BUILD][ERROR] relay 打包失败
    cd /d "%REPO_ROOT%"
    exit /b 1
)

REM ============================================================
REM  [2] http  —— --onefile --noconsole
REM ============================================================
echo.
echo [BUILD] === 打包 http ===
cd /d "%REPO_ROOT%\mcp_server\relay_nlp_http\http"
python -m PyInstaller --onefile --noconsole --name kz_mcp_http ^
    --hidden-import websockets ^
    --distpath "%REPO_ROOT%\dist" ^
    --workpath "%REPO_ROOT%\build\http" ^
    --specpath "%REPO_ROOT%\build" ^
    kz_mcp_http.py
if errorlevel 1 (
    echo [BUILD][ERROR] http 打包失败
    cd /d "%REPO_ROOT%"
    exit /b 1
)

REM ============================================================
REM  [3] feishu  —— --clean --onefile --noconsole
REM ============================================================
echo.
echo [BUILD] === 打包 feishu ===
cd /d "%REPO_ROOT%\mcp_server\relay_nlp_http\feishu"
python -m PyInstaller --clean --onefile --noconsole --name feishu_bridge ^
    --hidden-import websockets ^
    --hidden-import lark_oapi ^
    --distpath "%REPO_ROOT%\dist" ^
    --workpath "%REPO_ROOT%\build\feishu" ^
    --specpath "%REPO_ROOT%\build" ^
    feishu_bridge.py
if errorlevel 1 (
    echo [BUILD][ERROR] feishu 打包失败
    cd /d "%REPO_ROOT%"
    exit /b 1
)

cd /d "%REPO_ROOT%"
echo.
echo [BUILD] 全部完成，产物：
dir /b dist\*.exe
echo [BUILD] OK
exit /b 0
