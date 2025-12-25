# Interactive AI Tutor - Backend

AI-powered educational platform that analyzes handwritten math work in real-time, providing intelligent tutoring feedback through computer vision and natural language processing.

## 🎯 Problem Statement

Students learning math often get stuck and need immediate feedback, but tutors aren't always available. This system bridges that gap by:
- Analyzing handwritten work in real-time
- Understanding mathematical reasoning and common mistakes
- Providing Socratic guidance without giving away answers
- Adapting to different problem types (algebra, geometry, calculus, etc.)

## 🏗️ Technical Overview

### Architecture

Built with a **layered service architecture** for scalability and maintainability:

```
iOS Canvas App (SwiftUI)
        ↓
   FastAPI Backend
        ↓
  OpenAI Vision API
```

**Key Design Principles:**
- **Separation of concerns**: Infrastructure, business logic, and presentation layers
- **Type safety**: Pydantic schemas throughout
- **Async-first**: Non-blocking I/O for concurrent request handling
- **Client-side intelligence**: iOS app tracks strokes and calculates bounding boxes for accuracy

### Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **AI/ML**: OpenAI GPT-4.1 mini Vision API
- **Image Processing**: PIL/Pillow
- **Validation**: Pydantic v2
- **Development**: uvicorn, ngrok for tunneling

## 🚀 Features

### Current Capabilities

✅ **Real-time Canvas Analysis**
- Receives handwritten math from iOS app
- Processes stroke-level bounding boxes
- Validates and visualizes regions for debugging

✅ **Coordinate System Management**
- Normalized coordinates (0-1) for device independence
- Automatic conversion between coordinate systems
- Handles different screen sizes and aspect ratios

✅ **Robust Error Handling**
- Comprehensive logging at all layers
- Graceful degradation on API failures
- Detailed error messages for debugging

### In Development

🚧 **Multi-Stroke Symbol Recognition**
- Clustering algorithm to merge strokes (e.g., "+" sign = 2 strokes)
- Adaptive distance thresholds
- Overlap detection

### Roadmap

📋 **Planned Features**
1. Region classification (math expression vs text vs diagram)
2. Mathematical notation extraction (OCR + LaTeX conversion)
3. Step-by-step work analysis
4. Problem type inference (algebra, geometry, etc.)
5. Intelligent feedback generation
6. Multi-language support

## 💡 Key Technical Challenges Solved

### 1. Client-Side vs Server-Side Region Detection

**Initial approach**: Use AI to detect bounding boxes from image

**Problem**: Inaccurate, expensive, slow

**Solution**: iOS app tracks strokes and calculates precise bounding boxes

**Result**: 3x faster, more accurate, lower API costs

### 2. Coordinate System Design

**Challenge**: Different devices, screen sizes, image compressions

**Solution**: Normalized coordinates (0-1) with client-provided dimensions

**Benefit**: Device-independent, scales automatically, easier debugging

### 3. Layered Service Architecture

**Vision Service**: Generic OpenAI wrapper (reusable)

**Perception Service**: Canvas-specific logic (domain knowledge)

**Routers**: HTTP handling (thin presentation layer)

**Benefit**: Testable, maintainable, easy to swap implementations

## 📊 System Performance

- **Latency**: < 2s end-to-end (iOS → Backend → OpenAI → Response)
- **Accuracy**: High precision with client-side bounding boxes
- **Scalability**: Async architecture supports concurrent requests
- **Cost**: Optimized API usage through intelligent caching and batching

## 🛠️ Development Setup

### Prerequisites

- Python 3.11+
- OpenAI API key
- ngrok (for iOS testing)

### Quick Start

```bash
# Clone and setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# Run
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal (for iOS testing)
ngrok http 8000
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── services/          # Business logic layer
│   ├── routers/           # API endpoints
│   ├── mcp_servers/       # MCP integration (planned)
│   └── orchestrator/      # Workflow coordination
├── tests/
├── prompts/               # AI prompt engineering
└── requirements.txt
```

## 🎓 Skills Demonstrated

- **API Design**: RESTful endpoints, multipart form data handling
- **Computer Vision**: Image processing, coordinate systems, region detection
- **AI Integration**: Prompt engineering, OpenAI Vision API
- **Software Architecture**: Layered services, separation of concerns
- **Type Safety**: Pydantic schemas, Python type hints
- **Async Programming**: FastAPI, concurrent request handling
- **DevOps**: Environment management, logging, debugging tools
- **iOS Integration**: Client-server communication, real-time data sync

## 📝 License

Proprietary - All rights reserved

---

*This is an active development project. For collaboration inquiries, please reach out.*