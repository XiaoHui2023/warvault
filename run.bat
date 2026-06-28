@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)

".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 exit /b 1

set "BUILD_FRONTEND=0"
if exist "frontend\package.json" (
  if not exist "frontend\dist\index.html" (
    set "BUILD_FRONTEND=1"
  ) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$dist = Get-Item 'frontend\dist\index.html'; $inputs = @('frontend\index.html','frontend\package.json','frontend\package-lock.json','frontend\vite.config.js'); $latest = Get-ChildItem -Path 'frontend\src' -Recurse -File; foreach ($item in $inputs) { if (Test-Path $item) { $latest += Get-Item $item } }; if (($latest | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime -gt $dist.LastWriteTime) { exit 1 } else { exit 0 }"
    if errorlevel 1 set "BUILD_FRONTEND=1"
  )
)

if "%BUILD_FRONTEND%"=="1" (
  echo Frontend build output is missing or stale. Building...
  pushd frontend
  if not exist "node_modules" npm install
  if errorlevel 1 exit /b 1
  npm run build
  if errorlevel 1 exit /b 1
  popd
)

".venv\Scripts\python.exe" -m app_main --config config.yaml %*
