@echo off
setlocal
cd /d "%~dp0"

set "COPILOT_HOME=%~dp0.copilot-data"
set "COPILOT_RUNTIME=%~dp0_internal\runtime\copilot.exe"

if not exist "%COPILOT_RUNTIME%" (
  echo ERROR: Bundled Copilot Runtime not found:
  echo   %COPILOT_RUNTIME%
  echo Re-extract the complete portable folder and try again.
  pause
  exit /b 2
)

"%COPILOT_RUNTIME%" login
set "LOGIN_EXIT_CODE=%ERRORLEVEL%"

if "%LOGIN_EXIT_CODE%"=="0" (
  echo.
  echo Login succeeded. Credentials are stored under:
  echo   %COPILOT_HOME%
  echo Next step: run run.cmd
) else (
  echo.
  echo Login failed with exit code %LOGIN_EXIT_CODE%.
  echo Check the network and browser authorization, then try again.
)

pause
exit /b %LOGIN_EXIT_CODE%
