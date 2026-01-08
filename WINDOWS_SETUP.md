# SlideRefactor - Windows Setup Guide

Get SlideRefactor running on Windows with **one double-click**! 🚀

## 🎯 Quick Start (3 Steps)

### 1. Install Prerequisites

You only need to install these **once**:

#### **Python 3.9+**
1. Download from: https://www.python.org/downloads/
2. ⚠️ **IMPORTANT**: Check ✅ **"Add Python to PATH"** during installation
3. Click "Install Now"

#### **Node.js 18+**
1. Download from: https://nodejs.org/
2. Use the "LTS" (Long Term Support) version
3. Click through the installer (default options are fine)

### 2. Get Your API Keys

SlideRefactor needs two API keys:

#### **Datalab API Key**
- Get it here: https://datalab.to
- Used for PDF extraction

#### **Anthropic API Key**
- Get it here: https://console.anthropic.com
- Used for AI-powered layout reconstruction

### 3. Launch SlideRefactor

**Option A: Batch File (Easiest)**
1. Double-click `start.bat`
2. The first time, it will:
   - Install all dependencies automatically
   - Open `.env` in Notepad for you to add API keys
   - Start both servers
   - Open your browser

**Option B: PowerShell (Recommended)**
1. Right-click `start.ps1`
2. Select **"Run with PowerShell"**
3. Follow the on-screen instructions

**Option C: Python Launcher (Cross-platform)**
1. Open Command Prompt or PowerShell
2. Run: `python launcher.py`

That's it! SlideRefactor will open at `http://localhost:3001` 🎉

---

## 📝 Detailed Instructions

### First Time Setup

#### Step 1: Run the Launcher

**Method 1: Batch File**
- Locate `start.bat` in the project folder
- Double-click it
- A command window will open

**Method 2: PowerShell**
- Locate `start.ps1` in the project folder
- Right-click → "Run with PowerShell"
- You may need to allow execution (see Troubleshooting)

#### Step 2: Automatic Installation

The launcher will automatically:

```
[1/6] Checking Python installation...
   ✓ Python found!

[2/6] Checking Node.js installation...
   ✓ Node.js found!

[3/6] Installing Python dependencies...
   This may take a few minutes on first run...
   ✓ Python dependencies installed!

[4/6] Installing Node.js dependencies...
   This may take a few minutes on first run...
   ✓ Node.js dependencies installed!
```

⏱️ **First run takes 5-10 minutes** to install everything. Subsequent runs are instant!

#### Step 3: Configure API Keys

If `.env` doesn't exist, the launcher will:
1. Create it from `.env.example`
2. Open it in Notepad
3. Wait for you to add your keys

**Add your API keys like this:**
```bash
DATALAB_API_KEY=your_actual_datalab_key_here
ANTHROPIC_API_KEY=your_actual_anthropic_key_here
```

Save and close Notepad, then press Enter in the launcher window.

#### Step 4: Servers Start

The launcher will:
1. Start the backend server (port 8000)
2. Start the frontend server (port 3001)
3. Open your browser automatically

You'll see two new command windows open:
- **SlideRefactor Backend** (FastAPI)
- **SlideRefactor Frontend** (Next.js)

**⚠️ Don't close these windows!** They keep the servers running.

---

## 🎮 Using SlideRefactor

### 1. Upload Your PDF
- Drag and drop a PDF onto the upload zone
- Or click to browse and select a file

### 2. Configure Settings (Optional)
- Choose extractor: **Datalab** (recommended) or **PaddleOCR**
- Enable preprocessing for scanned PDFs
- Choose output options

### 3. Start Conversion
- Click **"Start Conversion"**
- Watch real-time progress (4 phases)
- Download your PPTX when complete!

### 4. View History
- Click **"History"** in the navigation
- Download past conversions
- Delete old jobs

### 5. Manage Settings
- Click **"Settings"** in the navigation
- Update API keys
- Test connections
- Change defaults

---

## 🛑 Stopping the Servers

**To stop SlideRefactor:**

1. Close the two server windows:
   - Close "SlideRefactor Backend"
   - Close "SlideRefactor Frontend"

**Or:**

- Press `Ctrl+C` in either server window
- Type `Y` when asked to terminate

---

## 🐛 Troubleshooting

### "Python is not recognized"

**Problem:** Windows can't find Python

**Solution:**
1. Reinstall Python from https://www.python.org/downloads/
2. ✅ **Check "Add Python to PATH"** during installation
3. Restart your computer
4. Try again

**Or manually add to PATH:**
1. Search for "Environment Variables" in Windows
2. Edit "Path" under "System variables"
3. Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python3XX`
4. Restart Command Prompt

### "Node is not recognized"

**Problem:** Windows can't find Node.js

**Solution:**
1. Reinstall Node.js from https://nodejs.org/
2. Use the LTS version
3. Restart your computer
4. Try again

### "Cannot run PowerShell script"

**Problem:** PowerShell execution policy blocks scripts

**Solution:**
1. Open PowerShell as Administrator
2. Run: `Set-ExecutionPolicy RemoteSigned`
3. Type `Y` to confirm
4. Try running `start.ps1` again

**Or use the batch file instead:**
- Just double-click `start.bat`

### "Port 8000 is already in use"

**Problem:** Another program is using port 8000

**Solution:**
1. Find what's using port 8000:
   ```cmd
   netstat -ano | findstr :8000
   ```
2. Kill that process in Task Manager
3. Or edit `server/main.py` to use a different port

### "npm install fails"

**Problem:** Node.js installation is corrupted

**Solution:**
1. Delete `frontend/node_modules` folder
2. Delete `frontend/package-lock.json`
3. Run the launcher again
4. Or manually: `cd frontend && npm install`

### "API key errors"

**Problem:** API keys not set or invalid

**Solution:**
1. Open `.env` in Notepad
2. Make sure keys are set correctly:
   ```
   DATALAB_API_KEY=your_key_here
   ANTHROPIC_API_KEY=your_key_here
   ```
3. No quotes, no spaces
4. Restart the servers

### "Browser doesn't open automatically"

**Not a problem!** Just manually open:
- http://localhost:3001

---

## 💡 Tips & Tricks

### Running on Startup

**To make SlideRefactor start with Windows:**

1. Press `Win+R`
2. Type: `shell:startup`
3. Create a shortcut to `start.bat` in this folder

### Creating a Desktop Shortcut

1. Right-click `start.bat`
2. Select "Create shortcut"
3. Drag shortcut to Desktop
4. (Optional) Right-click shortcut → Properties → Change Icon

### Faster Subsequent Launches

After the first run:
- Dependencies are already installed
- Servers start in ~10 seconds
- No more waiting!

### Running Without Browser

If you don't want the browser to auto-open:
1. Edit `start.bat` or `start.ps1`
2. Comment out the `start http://localhost:3001` line
3. Manually open browser when ready

---

## 📚 Next Steps

- **[QUICKSTART.md](QUICKSTART.md)** - Overview of features
- **[README.md](README.md)** - Full documentation
- **[Frontend Docs](frontend/README.md)** - Web interface details

---

## 🆘 Still Having Issues?

1. **Check the Prerequisites:**
   - Python 3.9+: `python --version`
   - Node.js 18+: `node --version`
   - npm: `npm --version`

2. **Try Manual Installation:**
   ```cmd
   pip install -r requirements.txt
   pip install -r server/requirements.txt
   cd frontend
   npm install
   ```

3. **Check Error Messages:**
   - Read the error carefully
   - Google the error message
   - Check GitHub Issues

4. **Ask for Help:**
   - GitHub Issues: https://github.com/yourusername/NotebookLLM-to-PPTX/issues
   - Include error messages and Windows version

---

**Made with ❤️ for Windows users**
