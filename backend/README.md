# Pocket Professor - Backend

FastAPI backend with Azure Cognitive Search, LangGraph agents, and intelligent three-mode chat system.

## 🎯 Overview

Production-ready AI tutoring backend featuring:
- **Three-mode chat system** with adaptive response times
- **Azure Cognitive Search** for scalable RAG
- **LangGraph agents** for intent classification and reasoning
- **Canvas analysis** with session management
- **PDF processing** with smart chunking and embeddings

## 🏗️ Architecture

### System Design

```
┌─────────────────────────────────────────────────┐
│              FastAPI Routers                    │
│  /chat  /upload  /regions  /canvas  /documents │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│              Service Layer                      │
│  • AIService (OpenAI wrapper)                   │
│  • CourseRAGService (PDF processing)            │
│  • SessionManager (Canvas sessions)             │
│  • VisionService (Image analysis)               │
│  • AzureSearchService (Index management)        │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│            LangGraph Agents                     │
│  • classify_intent → retrieve_context           │
│  • reason → respond                             │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│         External Services                       │
│  • Azure Cognitive Search                       │
│  • OpenAI GPT-4o / text-embedding-3-small       │
└─────────────────────────────────────────────────┘
```

### Three-Mode Chat System

**1. Simple Chat (2-3s)**
- Direct GPT-4o conversation
- No RAG, no reasoning
- Best for: General questions, greetings

**2. Fast RAG (3-5s)**
- Direct retrieval from Azure Search
- Skips reasoning step
- Best for: Quick factual lookups

**3. Full Analysis (10-15s)**
- Complete LangGraph pipeline
- Intent classification → Context retrieval → Reasoning → Response
- Best for: Complex problems, tutoring

### Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **AI/ML**: OpenAI GPT-4o, text-embedding-3-small
- **Search**: Azure Cognitive Search with HNSW vector search
- **Agents**: LangGraph for workflow orchestration
- **Image Processing**: pdfplumber, PIL/Pillow
- **Validation**: Pydantic v2

## 🚀 Features

### Current Capabilities

✅ **Intelligent Chat System**
- Three response modes with adaptive latency
- Intent classification (problem_solving, conceptual, canvas_review, etc.)
- Confidence scoring
- Follow-up suggestions

✅ **Azure Cognitive Search Integration**
- `course-materials` index for PDFs
- `canvas-sessions` index for student work
- Hybrid vector + keyword search
- HNSW algorithm for fast vector search

✅ **PDF Processing Pipeline**
- pdfplumber text extraction
- Smart paragraph splitting with LaTeX preservation
- Chunking with overlap (500 tokens, 50 overlap)
- Automatic embedding generation
- Batch upload to Azure Search

✅ **Canvas Analysis**
- Handwritten math recognition
- LangGraph workflow for analysis
- Session storage in Azure Search
- Dual-layer caching (memory + Azure)

✅ **Session Management**
- Recent session cache (30 min TTL)
- Historical session search
- Student-specific context retrieval

## 💡 Key Technical Decisions

### 1. Three-Mode Chat Architecture

**Challenge**: Full LangGraph pipeline too slow for simple queries

**Solution**: Three modes with different latency/depth tradeoffs

**Result**: 2-3s for simple chat, 10-15s only when needed

### 2. Azure Search vs ChromaDB

**Why Azure Search**:
- Production-ready, managed service
- Hybrid search (vector + keyword)
- Scalable to millions of documents
- Built-in security and monitoring

**Migration**: Replaced ChromaDB with Azure Search for both course materials and canvas sessions

### 3. LangGraph Agent Design

**Nodes**: classify_intent → retrieve_context → reason → respond

**Benefit**: Modular, testable, easy to extend with new capabilities

## 📊 System Performance

- **Simple Chat**: 2-3s response time
- **Fast RAG**: 3-5s with context retrieval
- **Full Analysis**: 10-15s with reasoning
- **PDF Upload**: ~2s per page for chunking + embedding
- **Scalability**: Async architecture supports 100+ concurrent requests

## 🛠️ Development Setup

### Prerequisites

- Python 3.11+
- Azure Cognitive Search resource
- OpenAI API key

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

### Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Azure Cognitive Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-admin-key

# Optional
LOG_LEVEL=INFO
```

### Run Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at `http://localhost:8000`

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Upload PDF
curl -X POST http://localhost:8000/upload \
  -F "file=@textbook.pdf"

# Chat (Simple mode)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"student_id": "test123", "message": "Hello", "use_rag": false}'

# Chat (Fast RAG mode)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"student_id": "test123", "message": "Explain derivatives", "use_rag": true, "fast_mode": true}'

# Chat (Full Analysis mode)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"student_id": "test123", "message": "Help with quadratics", "use_rag": true, "fast_mode": false}'
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── agents/
│   │   ├── chat_graph.py          # LangGraph workflow
│   │   ├── chat_nodes.py          # Agent nodes
│   │   ├── nodes.py               # Canvas analysis nodes
│   │   └── schemas.py             # Pydantic models
│   ├── services/
│   │   ├── ai_service.py          # OpenAI wrapper
│   │   ├── azure_search_service.py # Azure Search client
│   │   ├── course_rag_service.py  # PDF processing
│   │   ├── session_manager.py     # Canvas sessions
│   │   └── vision.py              # Image analysis
│   ├── routers/
│   │   ├── chat.py                # Three-mode chat endpoint
│   │   ├── upload.py              # PDF/image upload
│   │   ├── regions.py             # Canvas analysis
│   │   ├── canvas.py              # Canvas endpoints
│   │   └── get_documents.py       # Document listing
│   ├── core/
│   │   ├── config.py              # Settings
│   │   ├── logger.py              # Logging
│   │   └── logging_context.py     # Request ID tracking
│   └── main.py                    # FastAPI app
├── tests/
│   └── test_azure_blob.py         # CourseRAGService tests
└── requirements.txt
```

## 🎓 Skills Demonstrated

- **API Design**: RESTful endpoints, multipart form data, three-mode routing
- **AI/ML Engineering**: RAG pipelines, vector embeddings, hybrid search
- **Agent Systems**: LangGraph workflows, intent classification, reasoning
- **Cloud Services**: Azure Cognitive Search integration, index management
- **Software Architecture**: Layered services, separation of concerns, async-first design
- **Type Safety**: Pydantic v2 schemas, Python type hints throughout
- **Performance Optimization**: Adaptive latency, caching strategies, parallel execution
- **Document Processing**: PDF parsing, smart chunking, LaTeX preservation
- **DevOps**: Environment management, structured logging, request tracing

## 📝 License

Proprietary - All rights reserved

---

*Built with FastAPI, Azure Cognitive Search, LangGraph, and OpenAI*