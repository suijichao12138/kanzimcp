@echo off
setlocal
cd /d "%~dp0"

if not exist "config.yaml" (
  copy "config.example.yaml" "config.yaml" >nul
  echo Created config.yaml. Edit it before production use.
)
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env. Replace placeholder credentials before production use.
)

"%~dp0nlp_worker.exe" --config "%~dp0config.yaml" %*
if errorlevel 1 pause
endlocal
