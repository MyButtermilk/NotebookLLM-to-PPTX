@echo off
setlocal enabledelayedexpansion
REM SlideRefactor - Windows Launcher
REM Double-click this file to start the application

title SlideRefactor - Starting...

echo.
echo ========================================
echo   SlideRefactor - One-Click Launcher
echo ========================================
echo.

REM Check if Python is installed
echo [1/6] Checking Python installation...
where python >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
echo    Python found!

REM Check if Node.js is installed
echo [2/6] Checking Node.js installation...
where node >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)
echo    Node.js found!

REM Check if npm is installed
echo    Checking npm...
where npm >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: npm is not installed
    echo Please reinstall Node.js from https://nodejs.org/
    pause
    exit /b 1
)
echo    npm found!

REM Install Python dependencies
echo.
echo [3/6] Installing Python dependencies...
echo    This may take a few minutes on first run...

call pip install -r requirements.txt --quiet --disable-pip-version-check
if !errorlevel! neq 0 (
    echo ERROR: Failed to install Python dependencies
    echo    Try running: pip install -r requirements.txt
    pause
    exit /b 1
)

call pip install -r server/requirements.txt --quiet --disable-pip-version-check
if !errorlevel! neq 0 (
    echo ERROR: Failed to install server dependencies
    echo    Try running: pip install -r server/requirements.txt
    pause
    exit /b 1
)
echo    Python dependencies installed!

REM Install Node.js dependencies
echo.
echo [4/6] Installing Node.js dependencies...
echo    This may take a few minutes on first run...

pushd frontend
if not exist node_modules (
    echo    Installing frontend dependencies...
    call npm install
    if !errorlevel! neq 0 (
        echo ERROR: Failed to install Node.js dependencies
        popd
        pause
        exit /b 1
    )
) else (
    echo    Dependencies already installed, skipping...
)
popd
echo    Node.js dependencies installed!

REM Check if .env file exists
echo.
echo [5/6] Checking configuration...
if not exist .env (
    echo WARNING: .env file not found!
    echo Creating .env from template...
    copy .env.example .env >nul
    echo.
    echo IMPORTANT: Please edit .env and add your API keys:
    echo   - DATALAB_API_KEY (for PDF extraction)
    echo   - GEMINI_API_KEY (for AI processing)
    echo.
    echo Press any key to open .env in notepad...
    pause >nul
    notepad .env
    echo.
    echo After adding your API keys, press any key to continue...
    pause >nul
)
echo    Configuration OK!

REM Clean up old instances if they are still running
echo Checking for old instances...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /r ":8000 *0.0.0.0:"') do (
    if NOT "%%a"=="" (
        echo Closing old backend process %%a...
        taskkill /F /PID %%a >nul 2>&1
    )
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /r ":3001 *0.0.0.0:"') do (
    if NOT "%%a"=="" (
        echo Closing old frontend process %%a...
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo.
echo [6/6] Starting SlideRefactor...
echo.
echo    Backend server: http://localhost:8000
echo    Frontend UI:    http://localhost:3001
echo.
echo    Press Ctrl+C to stop both servers
echo.
echo ========================================
echo.

REM Start backend server in new window
start "SlideRefactor Backend" cmd /k "cd /d %~dp0 && python -m uvicorn server.main:app --host 0.0.0.0 --port 8000"

REM Wait for backend to start
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

REM Start frontend server in new window
start "SlideRefactor Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

REM Wait for frontend to start
echo Waiting for frontend to start...
timeout /t 8 /nobreak >nul

REM Open browser
echo Opening browser...
start http://localhost:3001

echo.
echo ========================================
echo   SlideRefactor is now running!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3001
echo.
echo Two command windows have opened:
echo   - SlideRefactor Backend (FastAPI)
echo   - SlideRefactor Frontend (Next.js)
echo.
echo Close those windows to stop the servers.
echo You can close this window now.
echo.
pause
