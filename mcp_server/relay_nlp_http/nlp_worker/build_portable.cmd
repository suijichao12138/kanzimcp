@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "EXPECTED_SDK_VERSION=1.0.26"
set "EXPECTED_RUNTIME_VERSION=1.0.103"
set "PYTHON="
if exist "%CD%\.venv\Scripts\python.exe" set "PYTHON=%CD%\.venv\Scripts\python.exe"
if not defined PYTHON for /f "delims=" %%I in ('where python') do if not defined PYTHON set "PYTHON=%%I"
if not defined PYTHON (
  echo Python was not found. Install Windows x64 Python on the build machine.
  exit /b 1
)

echo [1/7] Checking Windows x64 build environment...
"%PYTHON%" -c "import platform,sys; assert sys.platform == 'win32' and platform.machine().lower() in ('amd64','x86_64'), 'Windows x64 Python is required'"
if errorlevel 1 exit /b 1

echo [2/7] Installing locked build dependencies...
"%PYTHON%" -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1
"%PYTHON%" -c "from importlib.metadata import version; from copilot._cli_version import CLI_VERSION; assert version('github-copilot-sdk') == '%EXPECTED_SDK_VERSION%'; assert CLI_VERSION == '%EXPECTED_RUNTIME_VERSION%'; print('SDK', version('github-copilot-sdk'), 'pins Runtime', CLI_VERSION)"
if errorlevel 1 (
  echo The installed SDK or its Runtime pin does not match this release.
  exit /b 1
)

echo [3/7] Selecting the project-local Copilot Runtime cache...
if not exist "build" mkdir "build"
set "COPILOT_CLI_PATH="
set "COPILOT_RUNTIME_SOURCE="
set "COPILOT_RUNTIME_BUNDLE="
"%PYTHON%" build_runtime_cache.py --project-root "%CD%" --env-file "build\runtime-env.cmd" --release-marker "build\runtime-version.txt"
if errorlevel 1 (
  echo Direct SDK download failed; trying authenticated GitHub API fallback...
  where gh >nul 2>nul
  if errorlevel 1 (
    echo GitHub CLI is unavailable. Check GitHub release network access and retry.
    exit /b 1
  )
  set "RUNTIME_RELEASE_DIR=%CD%\build\runtime-release\v%EXPECTED_RUNTIME_VERSION%"
  if not exist "!RUNTIME_RELEASE_DIR!" mkdir "!RUNTIME_RELEASE_DIR!"
  if not exist "!RUNTIME_RELEASE_DIR!\github-copilot-%EXPECTED_RUNTIME_VERSION%-win32-x64.tgz" (
    gh release download v%EXPECTED_RUNTIME_VERSION% -R github/copilot-cli -p "github-copilot-%EXPECTED_RUNTIME_VERSION%-win32-x64.tgz" -D "!RUNTIME_RELEASE_DIR!"
    if errorlevel 1 (
      echo Failed to download the official Runtime release asset through gh.
      exit /b 1
    )
  )
  if not exist "!RUNTIME_RELEASE_DIR!\SHA256SUMS.txt" (
    gh release download v%EXPECTED_RUNTIME_VERSION% -R github/copilot-cli -p "SHA256SUMS.txt" -D "!RUNTIME_RELEASE_DIR!"
    if errorlevel 1 (
      echo Failed to download the official Runtime checksums through gh.
      exit /b 1
    )
  )
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$root = (Get-Location).Path; $server = Start-Process -FilePath $env:PYTHON -ArgumentList @('-m','http.server','18765','--bind','127.0.0.1','--directory',(Join-Path $root 'build\runtime-release')) -PassThru -WindowStyle Hidden; try { Start-Sleep -Seconds 1; $env:COPILOT_CLI_DOWNLOAD_BASE_URL='http://127.0.0.1:18765'; & $env:PYTHON 'build_runtime_cache.py' '--project-root' $root '--env-file' 'build\runtime-env.cmd' '--release-marker' 'build\runtime-version.txt'; exit $LASTEXITCODE } finally { if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id } }"
  if errorlevel 1 (
    echo SDK verification/extraction of the GitHub API asset failed.
    exit /b 1
  )
)

call "build\runtime-env.cmd"
if not exist "%COPILOT_RUNTIME_SOURCE%" (
  echo Copilot Runtime was not found at "%COPILOT_RUNTIME_SOURCE%".
  exit /b 1
)
if not exist "%COPILOT_RUNTIME_BUNDLE%\copilot-runtime.exe" (
  echo Copilot Runtime bundle is incomplete: copilot-runtime.exe is missing.
  exit /b 1
)
if not exist "%COPILOT_RUNTIME_BUNDLE%\runtime.node" (
  echo Copilot Runtime bundle is incomplete: runtime.node is missing.
  exit /b 1
)

echo [4/7] Verifying SDK, Runtime executable, and marker...
"%PYTHON%" -c "from pathlib import Path; from copilot_runtime import CopilotRuntime,validate_runtime_binary; CopilotRuntime.validate_sdk_version(); validate_runtime_binary(Path(r'%COPILOT_RUNTIME_SOURCE%'), marker_path=Path(r'%COPILOT_RUNTIME_BUNDLE%') / 'COPILOT_RUNTIME_VERSION.txt'); print(Path(r'build\runtime-version.txt').read_text(encoding='utf-8'), end='')"
if errorlevel 1 (
  echo Runtime verification failed; refusing to build a mixed-version package.
  exit /b 1
)

echo [5/7] Building PyInstaller onedir package...
"%PYTHON%" -m PyInstaller --noconfirm --clean nlp_worker.spec
if errorlevel 1 exit /b 1

echo [6/7] Adding external configuration templates...
copy /Y "config.example.yaml" "dist\nlp-worker-portable\config.example.yaml" >nul
copy /Y ".env.example" "dist\nlp-worker-portable\.env.example" >nul
copy /Y "README.md" "dist\nlp-worker-portable\README.md" >nul
copy /Y "run.cmd" "dist\nlp-worker-portable\run.cmd" >nul
copy /Y "login_copilot.cmd" "dist\nlp-worker-portable\login_copilot.cmd" >nul
copy /Y "build\runtime-version.txt" "dist\nlp-worker-portable\COPILOT_RUNTIME_VERSION.txt" >nul
if exist "skills" xcopy "skills" "dist\nlp-worker-portable\skills\" /E /I /Y >nul

echo [7/7] Validating package and creating zip...
if not exist "dist\nlp-worker-portable\_internal\runtime\copilot.exe" exit /b 1
if not exist "dist\nlp-worker-portable\_internal\runtime\copilot-runtime.exe" exit /b 1
if not exist "dist\nlp-worker-portable\_internal\runtime\runtime.node" exit /b 1
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
