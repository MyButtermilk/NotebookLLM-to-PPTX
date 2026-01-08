# SlideRefactor Quick Start Guide

Get up and running with SlideRefactor in 5 minutes.

## 🚀 Quick Start

### 🪟 Windows: One-Click Launch

**The easiest way:**

1. **Download** the repository
2. **Double-click** `start.bat` (or run `start.ps1`)
3. **Add API keys** when prompted
4. **Use SlideRefactor!**

Everything is automatic! See [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for details.

---

### 🐧 Mac/Linux: Python Launcher

**One command:**

```bash
python launcher.py
```

The launcher will:
- Check prerequisites
- Install dependencies
- Start both servers
- Open your browser

---

### ⚙️ Manual Setup (All Platforms)

#### 1. Set Up API Keys

```bash
# Copy environment file
cp .env.example .env

# Edit .env and add your keys:
DATALAB_API_KEY=your_datalab_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

#### 2. Install Dependencies

```bash
# Backend (Python)
pip install -r requirements.txt
pip install -r server/requirements.txt

# Frontend (Node.js)
cd frontend
npm install
cd ..
```

#### 3. Start the Backend Server

```bash
# From project root
cd server
python -m uvicorn main:app --reload --port 8000
```

The backend API will be available at `http://localhost:8000`.

#### 4. Start the Frontend

```bash
# In a new terminal, from project root
cd frontend
npm run dev
```

The web interface will be available at `http://localhost:3001`.

---

### 5. Convert Your First PDF

1. Open `http://localhost:3001` in your browser
2. Drag and drop a PDF file
3. Configure settings (or use defaults)
4. Click "Start Conversion"
5. Watch real-time progress
6. Download your PPTX!

## 🎯 What You Get

- **deck.pptx** - Editable PowerPoint presentation
- **deck.audit.html** - Interactive QA report
- **deck.slidegraph.json** - Intermediate format (optional)

## 🔧 Common Commands

```bash
# CLI conversion (without web interface)
sliderefactor input.pdf

# With custom output directory
sliderefactor input.pdf --output ./my_output

# Use PaddleOCR instead of Datalab
sliderefactor input.pdf --extractor paddleocr
```

## 📊 Architecture Overview

```
┌──────────────┐
│   Frontend   │  Next.js + React (localhost:3001)
│   (Web UI)   │  Neumorphic design, drag-drop upload
└──────┬───────┘
       │ HTTP + WebSocket
       v
┌──────────────┐
│   Backend    │  FastAPI server (localhost:8000)
│   (API)      │  Job management, real-time updates
└──────┬───────┘
       │
       v
┌──────────────┐
│ SlideRefactor│  Python pipeline
│   Pipeline   │  Datalab → LLM → PPTX
└──────────────┘
```

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check Python version (need 3.9+)
python --version

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Frontend won't connect

```bash
# Check backend is running
curl http://localhost:8000

# Check WebSocket connection
# Open browser console and look for WebSocket errors
```

### API keys not working

```bash
# Verify keys are set
echo $DATALAB_API_KEY
echo $ANTHROPIC_API_KEY

# Test connection via Settings page
# Or test via CLI
sliderefactor --help
```

### Database issues

```bash
# Delete and recreate database
rm server/sliderefactor.db
# Backend will auto-create on next start
```

## 🎨 Features Overview

### Web Interface

- **Convert** - Upload and convert PDFs
- **History** - View past conversions, download results
- **Settings** - Configure API keys and defaults

### Conversion Options

- **Extractor**: Datalab (SOTA) or PaddleOCR (open-source)
- **Preprocessing**: OpenCV enhancements (deskew, denoise)
- **Audit**: Interactive HTML report with bounding boxes
- **SlideGraph**: Save intermediate JSON for re-processing

## 📚 Next Steps

- Read the [full README](README.md) for detailed documentation
- Check out [examples](examples/README.md) for Python API usage
- Review the [Frontend README](frontend/README.md) for UI customization
- See the [original PRD](docs/prd.md) for product requirements

## 🆘 Need Help?

- **Issues**: https://github.com/yourusername/NotebookLLM-to-PPTX/issues
- **Discussions**: https://github.com/yourusername/NotebookLLM-to-PPTX/discussions

## 📄 License

MIT - see [LICENSE](LICENSE) file.
