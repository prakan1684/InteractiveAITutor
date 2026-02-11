# Interactive AI Tutor

AI-powered tutoring platform with streaming chat, on-demand canvas analysis, and smart conversation context.

## Overview

An interactive AI tutor where students work on problems on an iPad canvas and get real-time feedback through a web chat interface. The system uses vision analysis to read handwritten work and provides guided tutoring responses.

## Architecture

```
iPad App (PocketProfessor)          React Frontend (localhost:3000)
   │  canvas strokes/images              │  streaming chat
   └──────────┐                          │
              ↓                          ↓
         FastAPI Backend (localhost:8000)
              │
    ┌─────────┴─────────┐
    │   Chat Agents      │   Canvas Storage
    │  Intent → Vision   │   (in-memory)
    │  → Response        │
    └─────────┬─────────┘
              ↓
       OpenAI APIs (GPT-4o)
```

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure .env with OPENAI_API_KEY
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## Key Features

- **Streaming Chat** — AI responses stream word-by-word via SSE
- **Canvas Analysis** — On-demand vision analysis of student handwriting
- **Inline Canvas Display** — Canvas images shown in chat when AI reviews work
- **Smart Context** — AI tracks conversation flow, understands retries and corrections
- **Conversation Management** — Persistent conversations with sidebar navigation
- **Intent Classification** — Automatic detection of what the student needs

## Tech Stack

**Backend:** FastAPI, OpenAI GPT-4o, Python 3.11+
**Frontend:** React 18, Lucide icons, KaTeX for math rendering
**iOS App:** Swift (PocketProfessor)

## Documentation

- **[Backend](./backend/README.md)**
- **[Frontend](./frontend/README.md)**
