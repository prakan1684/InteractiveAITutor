# Elara

AI-powered tutoring platform with intelligent RAG, canvas analysis, and multi-mode chat system.

## 🎯 Overview

Elara is an interactive AI tutor that combines:
- **Three-mode chat system** (Simple, Fast RAG, Full Analysis)
- **Azure Cognitive Search** for scalable RAG
- **LangGraph agent** for intelligent reasoning
- **Canvas analysis** for handwritten math work
- **React frontend** with modern UI

## 🏗️ Architecture

```
React Frontend (localhost:3000)
        ↓
   FastAPI Backend (localhost:8000)
        ↓
   ┌────────────────────────────┐
   │  Azure Cognitive Search    │
   │  - course-materials index  │
   │  - canvas-sessions index   │
   └────────────────────────────┘
        ↓
   OpenAI APIs (GPT-4o, Embeddings)
```

## 🚀 Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure .env with:
# - OPENAI_API_KEY
# - AZURE_SEARCH_ENDPOINT
# - AZURE_SEARCH_KEY

uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## 📚 Components

- **[Backend Documentation](./backend/README.md)** - FastAPI + Azure Search + LangGraph
- **[Frontend Documentation](./frontend/README.md)** - React + Three-mode chat UI

## ✨ Key Features

- 🧠 **Intelligent Chat Modes**: Simple (2-3s), Fast RAG (3-5s), Full Analysis (10-15s)
- 📚 **PDF Upload**: Automatic chunking, embedding, and indexing to Azure Search
- 🖼️ **Canvas Analysis**: Handwritten math work recognition and feedback
- 🔍 **Hybrid Search**: Vector + keyword search for optimal retrieval
- 💾 **Session Management**: Canvas sessions stored in Azure Search
- ⚡ **Async Architecture**: Non-blocking I/O for concurrent requests

## 🛠️ Tech Stack

**Backend:**
- FastAPI, Python 3.11+
- Azure Cognitive Search
- LangGraph for agent workflows
- OpenAI GPT-4o & text-embedding-3-small

**Frontend:**
- React 18
- Axios for API calls
- Lucide React icons
- Modern CSS with gradients

## 📝 License

Proprietary - All rights reserved
