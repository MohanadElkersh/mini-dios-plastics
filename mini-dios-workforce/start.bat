@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo ============================================================
echo   Mini-DIOS Plastics - Starting Local Executive Demo
echo ============================================================

rem --- Locate Python virtual environment ---
set "PY_EXE="
if exist "%ROOT%\.venv\Scripts\python.exe" set "PY_EXE=%ROOT%\.venv\Scripts\python.exe"
if not defined PY_EXE if exist "%ROOT%\backend\.venv\Scripts\python.exe" set "PY_EXE=%ROOT%\backend\.venv\Scripts\python.exe"
if not defined PY_EXE if exist "%USERPROFILE%\.venv\Scripts\python.exe" set "PY_EXE=%USERPROFILE%\.venv\Scripts\python.exe"

if not defined PY_EXE (
    echo [ERROR] Python 3.12 virtual environment not found.
    echo         Checked:
    echo           - %ROOT%\.venv\Scripts\python.exe
    echo           - %ROOT%\backend\.venv\Scripts\python.exe
    echo           - %USERPROFILE%\.venv\Scripts\python.exe
    pause
    exit /b 1
)

rem --- Locate Node.js / npm (portable project copy or system PATH) ---
set "NODE_DIR="
if exist "%ROOT%\.tools\node\npm.cmd" set "NODE_DIR=%ROOT%\.tools\node"
if defined NODE_DIR (
    set "PATH=%NODE_DIR%;%PATH%"
)

where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm.cmd not found in %ROOT%\.tools\node or system PATH.
    pause
    exit /b 1
)

echo [1/3] Starting FastAPI + OR-Tools CP-SAT Backend on http://localhost:8000 ...
start "Mini-DIOS Backend (Port 8000)" cmd /k "cd /d "%ROOT%\backend" && "%PY_EXE%" -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/3] Starting Next.js Executive Command Center on http://localhost:3000 ...
start "Mini-DIOS Frontend (Port 3000)" cmd /k "cd /d "%ROOT%\frontend" && set NEXT_TELEMETRY_DISABLED=1 && npm.cmd run dev"

echo [3/3] Waiting 4 seconds before launching http://localhost:3000 ...
timeout /t 4 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo Mini-DIOS Plastics is running:
echo   - Executive UI : http://localhost:3000
echo   - FastAPI Docs : http://localhost:8000/docs
echo.
echo Run stop.bat at any time to cleanly shut down both servers.
endlocal
