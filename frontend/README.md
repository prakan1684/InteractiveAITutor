# Interactive AI Tutor — Frontend

React web interface with streaming chat, inline canvas display, and conversation management.

## Overview

The frontend provides:
- **Streaming chat** — AI responses appear word-by-word
- **Conversation sidebar** — Create, switch, and delete conversations
- **Inline canvas images** — Student's canvas work displayed in the chat thread
- **Markdown + LaTeX** — Math expressions rendered with KaTeX
- **Status indicators** — "Thinking...", "Looking at your canvas..." feedback

## Setup

```bash
npm install
npm start
```

Opens at `http://localhost:3000`

### Environment Variables

```bash
REACT_APP_API_URL=http://localhost:8000
```

## Components

- **`ChatInterface`** — Main chat UI. Consumes SSE stream from `/chat/stream`, manages message state, handles streaming chunks and status events.
- **`MessageList`** — Renders messages (user, AI, system, canvas images). Shows blinking cursor during streaming, status indicators during processing.
- **`ConversationSidebar`** — Lists conversations, create new, switch between, delete.
- **`FileUpload`** — PDF upload to backend.
- **`CanvasGallery`** — Browse uploaded canvas images.

## Streaming Flow

1. User sends message → `sendMessageStream()` opens SSE connection
2. `meta` event → captures conversation ID
3. `status` event → shows "Thinking..." / "Looking at your canvas..."
4. `canvas_image` event → inserts canvas image inline in chat
5. `chunk` events → appends text word-by-word with blinking cursor
6. `done` event → finalizes message with metadata

## Project Structure

```
frontend/src/
├── components/
│   ├── ChatInterface.jsx      # Streaming chat + message management
│   ├── MessageList.jsx        # Message rendering (text, images, status)
│   ├── ConversationSidebar.jsx # Conversation list + navigation
│   ├── FileUpload.jsx         # PDF upload
│   └── CanvasGallery.jsx      # Canvas image browser
├── services/
│   └── api.js                 # API client (axios + fetch for SSE)
├── App.js                     # Layout + state orchestration
├── App.css                    # All styles
└── index.js                   # Entry point
```

## Tech Stack

- **React 18** with hooks
- **Axios** for REST calls, **fetch + ReadableStream** for SSE
- **ReactMarkdown** + **remark-math** + **rehype-katex** for math rendering
- **Lucide React** for icons
- **Create React App** for build tooling
