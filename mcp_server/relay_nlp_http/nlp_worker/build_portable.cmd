@echo off
setlocal
cd /d "%~dp0"

set "PYTHON="
if exist "%CD%\.venv\Scripts\python.exe" set "PYTHON=%CD%\.venv\Scripts\python.exe"
if not defined PYTHON for /f "delims=" %%I in ('where python') do if not defined PYTHON set "PYTHON=%%I"
if not defined PYTHON (
  echo Python was not found. Install Windows x64 Python on the build machine.
  exit /b 1
)

echo [1/6] Checking Windows x64 build environment...
"%PYTHON%" -c "import platform,sys; assert sys.platform == 'win32' and platform.machine().lower() in ('amd64','x86_64'), 'Windows x64 Python is required'"
if errorlevel 1 exit /b 1

echo [2/6] Installing build dependencies...
"%PYTHON%" -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1

echo [3/6] Locating the Copilot Runtime...
if not exist "build" mkdir "build"
if not defined COPILOT_RUNTIME_SOURCE if defined COPILOT_CLI_PATH set "COPILOT_RUNTIME_SOURCE=%COPILOT_CLI_PATH%"
if defined COPILOT_RUNTIME_SOURCE goto runtime_ready
if not defined COPILOT_RUNTIME_SOURCE (
  "%PYTHON%" -c "from copilot._cli_download import get_cached_cli_path; print(get_cached_cli_path() or '')" > "build\runtime-path.txt"
  set /p COPILOT_RUNTIME_SOURCE=<"build\runtime-path.txt"
)
if defined COPILOT_RUNTIME_SOURCE goto runtime_ready
echo No SDK-pinned runtime is cached; downloading with a 300-second timeout...
set "COPILOT_CLI_EXTRACT_DIR=%CD%\build\copilot-runtime"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Start-Process -FilePath $env:PYTHON -ArgumentList @('-m','copilot','download-runtime') -NoNewWindow -PassThru; if (-not $p.WaitForExit(300000)) { Stop-Process -Id $p.Id; Write-Error 'Copilot Runtime download timed out after 300 seconds.'; exit 124 }; exit $p.ExitCode"
if errorlevel 1 (
  echo Set COPILOT_RUNTIME_SOURCE or COPILOT_CLI_PATH to a compatible copilot.exe and retry.
  exit /b 1
)
set "COPILOT_RUNTIME_SOURCE=%COPILOT_CLI_EXTRACT_DIR%\copilot.exe"

:runtime_ready
if not exist "%COPILOT_RUNTIME_SOURCE%" (
  echo Copilot Runtime was not found at "%COPILOT_RUNTIME_SOURCE%".
  exit /b 1
)
for %%I in ("%COPILOT_RUNTIME_SOURCE%") do if %%~zI LSS 1048576 (
  echo Copilot Runtime is unexpectedly small: "%COPILOT_RUNTIME_SOURCE%".
  exit /b 1
)
"%COPILOT_RUNTIME_SOURCE%" --version > "build\runtime-version.txt"
if errorlevel 1 (
  echo Copilot Runtime failed its version check.
  exit /b 1
)
type "build\runtime-version.txt"

echo [4/6] Building PyInstaller onedir package...
"%PYTHON%" -m PyInstaller --noconfirm --clean nlp_worker.spec
if errorlevel 1 exit /b 1

echo [5/6] Adding external configuration templates...
copy /Y "config.example.yaml" "dist\nlp-worker-portable\config.example.yaml" >nul
copy /Y ".env.example" "dist\nlp-worker-portable\.env.example" >nul
copy /Y "README.md" "dist\nlp-worker-portable\README.md" >nul
copy /Y "run.cmd" "dist\nlp-worker-portable\run.cmd" >nul
copy /Y "login_copilot.cmd" "dist\nlp-worker-portable\login_copilot.cmd" >nul
copy /Y "build\runtime-version.txt" "dist\nlp-worker-portable\COPILOT_RUNTIME_VERSION.txt" >nul
if exist "skills" xcopy "skills" "dist\nlp-worker-portable\skills\" /E /I /Y >nul

echo [6/6] Validating package and creating zip...
set "GITHUB_TOKEN=portable-build-validation"
set "COPILOT_SKIP_CLI_DOWNLOAD=1"
"dist\nlp-worker-portable\nlp_worker.exe" --help >nul
if errorlevel 1 exit /b 1
"dist\nlp-worker-portable\nlp_worker.exe" --validate-config --config "dist\nlp-worker-portable\config.example.yaml"
if errorlevel 1 exit /b 1
powershell -NoProfile -Command "Compress-Archive -Path 'dist\nlp-worker-portable\*' -DestinationPath 'dist\nlp-worker-portable-win-x64.zip' -Force"
if errorlevel 1 exit /b 1

echo Portable package: dist\nlp-worker-portable
echo Zip package:      dist\nlp-worker-portable-win-x64.zip
endlocal
