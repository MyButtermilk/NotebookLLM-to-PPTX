# SlideRefactor Frontend

Modern web interface for converting NotebookLLM PDFs to editable PowerPoint presentations.

## Features

- 🎨 **Neumorphic Design** - Beautiful, premium UI with soft shadows and depth
- 📤 **Drag & Drop Upload** - Intuitive PDF upload experience
- 🔄 **Real-time Progress** - WebSocket-powered live updates
- ⚙️ **Configurable Settings** - Control extraction engines, preprocessing, and API keys
- 📊 **Conversion History** - Track and manage past conversions
- ✨ **Smooth Animations** - Framer Motion for delightful interactions

## Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Animation library
- **Zustand** - State management
- **Axios** - HTTP client
- **React Dropzone** - File upload handling

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend server running on `localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3001`.

### Configuration

The frontend expects the backend API at `http://localhost:8000`. Update `next.config.js` if your backend runs on a different port.

## Project Structure

```
frontend/
├── app/                    # Next.js app router pages
│   ├── page.tsx           # Convert page (home)
│   ├── history/           # History page
│   ├── settings/          # Settings page
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── Navigation.tsx     # Navigation bar
│   ├── UploadZone.tsx     # File upload dropzone
│   ├── ConversionSettings.tsx  # Settings panel
│   ├── ProgressView.tsx   # Real-time progress
│   └── ResultsView.tsx    # Completion screen
├── lib/                   # Utilities
│   ├── store.ts          # Zustand state management
│   └── useWebSocket.ts   # WebSocket hook
└── public/               # Static assets
```

## Design System

### Neumorphism

The UI uses a neumorphic design system with:

- **Raised surfaces** - Buttons and interactive elements (`.neu-button`)
- **Recessed surfaces** - Input fields and wells (`.neu-pressed`, `.neu-input`)
- **Flat surfaces** - Cards and panels (`.neu-card`, `.neu-surface`)

### Colors

- **Base**: `#e8ecf1` - Background
- **Primary**: Blue shades for actions
- **Success**: `#10b981` - Completed states
- **Warning**: `#f59e0b` - In-progress states
- **Error**: `#ef4444` - Failed states

### Typography

- **Sans**: Inter for UI text
- **Display**: Manrope for headings

## Available Scripts

```bash
# Development server
npm run dev

# Production build
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## License

MIT
