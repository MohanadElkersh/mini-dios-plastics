@echo off
setlocal EnableExtensions

echo ============================================================
echo   Mini-DIOS Plastics - Stopping Local Servers
echo ============================================================

rem --- Terminate any process listening on Backend (8000) or Frontend (3000) ---
for %%P in (8000 3000) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr /R /C:":%%P .*LISTENING"') do (
        if not "%%A"=="0" (
            echo Stopping process PID %%A on port %%P ...
            taskkill /PID %%A /T /F >nul 2>&1
        )
    )
)

rem --- Close the Mini-DIOS terminal windows if still open ---
taskkill /FI "WINDOWTITLE eq Mini-DIOS Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Mini-DIOS Frontend*" /T /F >nul 2>&1

echo.
echo All Mini-DIOS Plastics local servers (ports 8000 and 3000) stopped.
timeout /t 2 /nobreak >nul
endlocal
