# Pocket Professor - Frontend

React-based web interface with three-mode chat system, file upload, and modern UI.

## 🎯 Overview

Modern React frontend featuring:
- **Three-mode chat selector** (Simple, Fast RAG, Full Analysis)
- **Real-time messaging** with AI tutor
- **File upload** for PDFs and images
- **Metadata display** showing intent, confidence, and context counts
- **Responsive design** with gradient backgrounds and smooth animations

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│           App.js                    │
│  • Mode state management            │
│  • Component orchestration          │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│        Components                   │
│  • ChatInterface                    │
│  • ModeSelector                     │
│  • MessageList                      │
│  • FileUpload                       │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│      API Service (api.js)           │
│  • sendMessage(message, speedMode)  │
│  • uploadFile(file)                 │
│  • getDocuments()                   │
└─────────────────────────────────────┘
            ↓
    FastAPI Backend (localhost:8000)
```

## ✨ Features

### Three-Mode Chat System

**💬 Simple Chat (2-3s)**
- Blue theme
- No RAG, direct conversation
- Best for greetings and general questions

**⚡ Fast RAG (3-5s)**
- Orange theme
- Quick retrieval from course materials
- Best for factual lookups

**🧠 Full Analysis (10-15s)**
- Purple theme
- Complete reasoning with metadata
- Shows intent, confidence, context counts
- Best for complex tutoring

### UI Components

**ChatInterface**
- Message history with auto-scroll
- User/AI/System message types
- Loading states
- Enter to send

**ModeSelector**
- Visual mode buttons with icons
- Response time estimates
- Active state highlighting
- Mode descriptions

**FileUpload**
- Drag-and-drop support
- PDF and image upload
- Upload status feedback
- Success/error notifications

**MessageList**
- Animated message appearance
- Icon-based message types
- Metadata display for Full mode
- Responsive layout

## 🚀 Quick Start

### Installation

```bash
npm install
```

### Development

```bash
npm start
```

Opens at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

Creates optimized build in `build/` folder

### Environment Variables

Create `.env` file:

```bash
REACT_APP_API_URL=http://localhost:8000
```

## 📁 Project Structure

```
frontend/src/
├── components/
│   ├── ChatInterface.jsx      # Main chat UI
│   ├── ModeSelector.jsx       # Three-mode selector
│   ├── MessageList.jsx        # Message display
│   └── FileUpload.jsx         # PDF/image upload
├── services/
│   └── api.js                 # API client
├── App.js                     # Main app component
├── App.css                    # Global styles
└── index.js                   # Entry point
```

## 🎨 Design System

### Colors

- **Primary Blue**: `#3498db` (Simple mode, user messages)
- **Orange**: `#f39c12` (Fast mode, accents)
- **Purple**: `#9b59b6` (Full mode, AI messages)
- **Dark**: `#2c3e50` (Header)
- **Background**: Linear gradient `#1e3c72` → `#2a5298`

### Typography

- **Font**: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto
- **Headers**: 2.5em bold
- **Body**: 1em regular
- **Metadata**: 0.8em

### Animations

- **Message fade-in**: 0.3s ease
- **Button hover**: transform + shadow
- **Mode transition**: border-color 0.3s

## 🛠️ Tech Stack

- **React 18** - UI framework
- **Axios** - HTTP client
- **Lucide React** - Icon library
- **CSS3** - Styling with gradients and animations
- **Create React App** - Build tooling

## 🎓 Skills Demonstrated

- **React Hooks**: useState, useRef, useEffect
- **Component Architecture**: Modular, reusable components
- **State Management**: Props drilling, lifting state
- **API Integration**: Axios, async/await, error handling
- **Responsive Design**: CSS Grid, Flexbox, media queries
- **UX Design**: Loading states, animations, feedback
- **Modern CSS**: Gradients, transitions, custom properties

## 📝 Available Scripts

### `npm start`
Runs development server at `http://localhost:3000`

### `npm test`
Launches test runner

### `npm run build`
Builds production-ready app

### `npm run eject`
Ejects from Create React App (one-way operation)

## 🚀 Deployment

Ready to deploy to:
- **Azure Static Web Apps**
- **Vercel**
- **Netlify**
- **GitHub Pages**

## 📝 License

Proprietary - All rights reserved

---

*Built with React, Axios, and Lucide Icons*
