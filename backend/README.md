# Interactive AI Tutor — Backend

FastAPI backend with streaming chat, on-demand canvas vision analysis, and smart conversation context.

## Overview

The backend handles:
- **Streaming chat** via SSE (Server-Sent Events)
- **Intent classification** to determine what the student needs
- **On-demand canvas analysis** using GPT-4o vision
- **Conversation persistence** with history tracking
- **Canvas image storage** from iPad uploads

## Architecture

```
Routers
  /chat/stream  →  SSE streaming chat
  /chat         →  Non-streaming chat (fallback)
  /steps        →  iPad canvas image uploads
  /upload       →  PDF upload
        ↓
Chat Agents (app/agents/chat/)
  IntentAgent   →  Classify intent + decide if canvas needed
  ResponseAgent →  Generate tutoring response (streaming)
        ↓
Services
  AIService        →  OpenAI GPT-4o wrapper (streaming + non-streaming)
  CanvasStorage    →  In-memory canvas image + analysis cache
  ConversationMgr  →  Message history per conversation
  VisionAgent      →  Canvas image analysis via GPT-4o vision
```

## Chat Workflow

1. **Intent Classification** — Determines intent (`canvas_review_request`, `question`, `hint_request`, `clarification`, `general`) and whether canvas is needed
2. **Canvas Analysis** (if needed) — Runs GPT-4o vision on the student's canvas image, caches results
3. **Response Streaming** — Streams the AI response word-by-word via SSE

SSE event types: `meta`, `status`, `canvas_image`, `chunk`, `done`

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

```bash
OPENAI_API_KEY=sk-...
```

### Run

```bash
uvicorn app.main:app --reload
```

Server at `http://localhost:8000`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat/stream` | Streaming chat (SSE) |
| POST | `/chat` | Non-streaming chat |
| POST | `/steps` | iPad canvas upload (multipart) |
| GET | `/conversations/{student_id}` | List conversations |
| GET | `/conversation/{id}` | Get conversation history |
| DELETE | `/conversation/{id}` | Delete conversation |
| POST | `/upload` | PDF upload |
| GET | `/health` | Health check |

## Project Structure

```
backend/
├── app/
│   ├── agents/
│   │   ├── chat/
│   │   │   ├── intent_agent.py    # Intent classification
│   │   │   ├── response_agent.py  # Response generation (streaming)
│   │   │   ├── workflow.py        # Chat workflow orchestration
│   │   │   └── schema.py         # ChatState dataclass
│   │   └── canvas/
│   │       ├── vision_agent.py    # GPT-4o vision analysis
│   │       └── schema.py         # CanvasState
│   ├── services/
│   │   ├── ai_service.py          # OpenAI wrapper (stream + non-stream)
│   │   ├── canvas_storage.py      # Canvas image + analysis cache
│   │   └── conversation_manager.py # Conversation history
│   ├── routers/
│   │   ├── chat.py                # Chat endpoints (stream + non-stream)
│   │   └── steps.py               # iPad canvas upload
│   ├── core/
│   │   ├── config.py              # Settings
│   │   ├── logger.py              # Structured logging
│   │   └── logging_context.py     # Request ID tracking
│   └── main.py                    # FastAPI app + static file mount
└── requirements.txt
```