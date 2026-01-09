# SlideRefactor - PowerShell Launcher
# Right-click and "Run with PowerShell" to start

# Set color scheme
$host.UI.RawUI.BackgroundColor = "Black"
$host.UI.RawUI.ForegroundColor = "White"
Clear-Host

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SlideRefactor - One-Click Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if command exists
function Test-Command($command) {
    try {
        if (Get-Command $command -ErrorAction Stop) {
            return $true
        }
    }
    catch {
        return $false
    }
}

# Check Python
Write-Host "[1/6] Checking Python installation..." -ForegroundColor Yellow
if (-not (Test-Command "python")) {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.9+ from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
$pythonVersion = python --version
Write-Host "   $pythonVersion found!" -ForegroundColor Green

# Check Node.js
Write-Host "[2/6] Checking Node.js installation..." -ForegroundColor Yellow
if (-not (Test-Command "node")) {
    Write-Host "ERROR: Node.js is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Node.js 18+ from https://nodejs.org/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
$nodeVersion = node --version
Write-Host "   Node.js $nodeVersion found!" -ForegroundColor Green

# Check npm
if (-not (Test-Command "npm")) {
    Write-Host "ERROR: npm is not installed" -ForegroundColor Red
    Write-Host "Please reinstall Node.js from https://nodejs.org/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Install Python dependencies
Write-Host ""
Write-Host "[3/6] Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "   This may take a few minutes on first run..." -ForegroundColor Gray

try {
    pip install -r requirements.txt --quiet --disable-pip-version-check 2>&1 | Out-Null
    pip install -r server/requirements.txt --quiet --disable-pip-version-check 2>&1 | Out-Null
    Write-Host "   Python dependencies installed!" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Failed to install Python dependencies" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Install Node.js dependencies
Write-Host ""
Write-Host "[4/6] Installing Node.js dependencies..." -ForegroundColor Yellow
Write-Host "   This may take a few minutes on first run..." -ForegroundColor Gray

Push-Location frontend
if (-not (Test-Path "node_modules")) {
    Write-Host "   Installing frontend dependencies..." -ForegroundColor Gray
    try {
        npm install --silent 2>&1 | Out-Null
        Write-Host "   Node.js dependencies installed!" -ForegroundColor Green
    }
    catch {
        Write-Host "ERROR: Failed to install Node.js dependencies" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        Pop-Location
        Read-Host "Press Enter to exit"
        exit 1
    }
}
else {
    Write-Host "   Dependencies already installed, skipping..." -ForegroundColor Gray
}
Pop-Location

# Check .env file
Write-Host ""
Write-Host "[5/6] Checking configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "Creating .env from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host ""
    Write-Host "IMPORTANT: Please edit .env and add your API keys:" -ForegroundColor Cyan
    Write-Host "  - DATALAB_API_KEY (for PDF extraction)" -ForegroundColor Cyan
    Write-Host "  - GEMINI_API_KEY (for AI processing)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Opening .env in notepad..." -ForegroundColor Yellow
    Start-Process notepad ".env" -Wait
    Write-Host ""
    Write-Host "After adding your API keys, press Enter to continue..." -ForegroundColor Yellow
    Read-Host
}
Write-Host "   Configuration OK!" -ForegroundColor Green

# Clean up old instances if they are still running
Write-Host "Checking for old instances..." -ForegroundColor Gray
$backendProcess = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1
if ($backendProcess) {
    Write-Host "Closing old backend process $backendProcess..." -ForegroundColor Yellow
    Stop-Process -Id $backendProcess -Force -ErrorAction SilentlyContinue
}
$frontendProcess = Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1
if ($frontendProcess) {
    Write-Host "Closing old frontend process $frontendProcess..." -ForegroundColor Yellow
    Stop-Process -Id $frontendProcess -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "[6/6] Starting SlideRefactor..." -ForegroundColor Yellow
Write-Host ""
Write-Host "   Backend server: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   Frontend UI:    http://localhost:3001" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Press Ctrl+C to stop both servers" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start backend
$backendJob = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python -m uvicorn server.main:app --host 0.0.0.0 --port 8000" -PassThru -WindowStyle Normal

Write-Host "Waiting for backend to start..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Start frontend
$frontendJob = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD/frontend'; npm run dev" -PassThru -WindowStyle Normal

Write-Host "Waiting for frontend to start..." -ForegroundColor Gray
Start-Sleep -Seconds 8

# Open browser
Write-Host "Opening browser..." -ForegroundColor Gray
Start-Process "http://localhost:3001"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SlideRefactor is now running!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3001" -ForegroundColor Cyan
Write-Host ""
Write-Host "Two PowerShell windows have opened:" -ForegroundColor White
Write-Host "  - SlideRefactor Backend (FastAPI)" -ForegroundColor White
Write-Host "  - SlideRefactor Frontend (Next.js)" -ForegroundColor White
Write-Host ""
Write-Host "Close those windows to stop the servers." -ForegroundColor Yellow
Write-Host "You can close this window now." -ForegroundColor Gray
Write-Host ""

# Keep window open
Read-Host "Press Enter to close this window"
