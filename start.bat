@echo off
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
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
echo    Python found!

REM Check if Node.js is installed
echo [2/6] Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)
echo    Node.js found!

REM Check if npm is installed
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: npm is not installed
    echo Please reinstall Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Install Python dependencies
echo.
echo [3/6] Installing Python dependencies...
echo    This may take a few minutes on first run...

pip install -r requirements.txt --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)

pip install -r server/requirements.txt --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo ERROR: Failed to install server dependencies
    pause
    exit /b 1
)
echo    Python dependencies installed!

REM Install Node.js dependencies
echo.
echo [4/6] Installing Node.js dependencies...
echo    This may take a few minutes on first run...

cd frontend
if not exist node_modules (
    echo    Installing frontend dependencies...
    call npm install --silent
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install Node.js dependencies
        cd ..
        pause
        exit /b 1
    )
) else (
    echo    Dependencies already installed, skipping...
)
cd ..
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
    echo   - DATALAB_API_KEY
    echo   - ANTHROPIC_API_KEY
    echo.
    echo Press any key to open .env in notepad...
    pause >nul
    notepad .env
    echo.
    echo After adding your API keys, press any key to continue...
    pause >nul
)
echo    Configuration OK!

REM Start the servers
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
start "SlideRefactor Backend" cmd /k "cd server && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

REM Wait for backend to start
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

REM Start frontend server in new window
start "SlideRefactor Frontend" cmd /k "cd frontend && npm run dev"

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
