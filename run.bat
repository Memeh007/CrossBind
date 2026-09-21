@echo off
cd /d "%~dp0"
title CrossBind
echo.
echo  CrossBind — local molecular docking
echo  ===================================
echo.

set "PY=python"
where python >nul 2>&1 || set "PY=py -3"

if not exist "venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PY% -m venv venv
  if errorlevel 1 (
    echo FAILED to create venv. Install Python 3.11+ from python.org and retry.
    pause
    exit /b 1
  )
)

echo Installing / updating packages...
"venv\Scripts\python.exe" -m pip install -q --upgrade pip
"venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo FAILED to install requirements.
  echo Tip: if RDKit fails, try: conda install -c conda-forge rdkit
  pause
  exit /b 1
)

REM Optional: set VINA_BIN to your vina.exe full path, e.g.
REM set VINA_BIN=C:\Users\alexc\Desktop\CrossBind\bin\vina.exe
if exist "bin\vina.exe" if not defined VINA_BIN set "VINA_BIN=%~dp0bin\vina.exe"
if exist "bin\vina_1.2.7_win.exe" if not defined VINA_BIN set "VINA_BIN=%~dp0bin\vina_1.2.7_win.exe"

set PORT=8787
echo.
echo Starting CrossBind on http://127.0.0.1:%PORT%
echo Leave this window open. Press Ctrl+C to stop.
echo.
start "" "http://127.0.0.1:%PORT%/"
"venv\Scripts\python.exe" -m uvicorn crossbind.app:app --host 127.0.0.1 --port %PORT%
if errorlevel 1 (
  echo.
  echo Server exited with an error.
  pause
)
