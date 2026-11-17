@echo off
rem Start the official Kanzi Monitor Web UI against the instrument over serial.
rem   usage: start_webui.cmd [COM_PORT] [BAUD] [LISTEN_PORT]
rem   default COM3 115200 47002
setlocal
cd /d "%~dp0.."
set COM=%1
if "%COM%"=="" set COM=COM3
set BAUD=%2
if "%BAUD%"=="" set BAUD=115200
set LPORT=%3
if "%LPORT%"=="" set LPORT=47002

echo [1/2] starting serial adapter on %COM% @ %BAUD% (listen 127.0.0.1:%LPORT%)
start "webui-adapter" /min cmd /c python monitor_tools\webui_bridge.py --com %COM% --baud %BAUD% --listen %LPORT% ^& pause
timeout /t 6 >nul

echo [2/2] starting monitor-web-ui
start "" monitor_tools\monitor-web-ui\monitor-web-ui-win64.exe --monitor-host 127.0.0.1 --monitor-port %LPORT% --command-timeout 120

echo.
echo Web UI: http://127.0.0.1:8765
echo Stop : close both windows (web-ui window + "webui-adapter" window)
endlocal
