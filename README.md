# AI-Powered Document Reader

An intelligent document reader that lets you upload PDFs and have contextual conversations about their content using RAG (Retrieval-Augmented Generation).

---

## Live Demo

| | URL |
|---|---|
| Frontend | https://ai-document-reader-30gz67wc4-gawadearyan2-gmailcoms-projects.vercel.app |
| API Docs (Swagger) | https://amaze-recycling-suffocate.ngrok-free.dev/docs |
| GitHub | https://github.com/Aryan1347/ai-document-reader |

---

## Features

- **PDF Upload** — upload any PDF and extract text instantly
- **OCR Fallback** — scanned PDFs handled automatically via pytesseract
- **AI Chat** — ask questions about the document, get cited answers
- **Source Attribution** — every answer cites the exact page it came from
- **Chat History** — full conversation history persisted per document session
- **Multi-document Sessions** — switch between multiple uploaded documents
- **Confidence Signal** — low retrieval confidence flagged honestly rather than hallucinating
- **API Docs** — Swagger UI available at `/docs`

---

## Screenshots

> Add screenshots or a short demo video here.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Tailwind CSS |
| Backend | FastAPI (Python) |
| PDF Extraction | PyMuPDF |
| OCR Fallback | pytesseract + tesseract-ocr |
| Chunking | LangChain RecursiveCharacterTextSplitter |
| Embeddings | Mistral AI (`mistral-embed`) via LangChain |
| Vector Store | ChromaDB (persistent) |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Chat History | SQLite via SQLAlchemy |
| Backend Deploy | AWS EC2 (t3.micro, Ubuntu, nginx reverse proxy, ngrok HTTPS) |
| Frontend Deploy | Vercel |

---

## Architecture

```
User
 │
 ▼
React Frontend (Vercel)
 │  POST /upload       POST /query
 ▼
FastAPI Backend (AWS EC2 — t3.micro, us-east-1)
 │
 ├── ingest.py
 │    ├── PyMuPDF → extract text page by page
 │    ├── pytesseract → OCR fallback for scanned pages
 │    ├── LangChain splitter → 500 char chunks, 50 overlap
 │    └── Mistral embed → ChromaDB (persisted to disk)
 │
 └── rag.py
      ├── Mistral embed → embed user question
      ├── ChromaDB → similarity search (top 5 chunks)
      ├── Groq LLM → answer with page citations
      └── SQLite → save chat history
```

---

## Deployment

### Backend — AWS EC2

The backend is deployed on an AWS EC2 t3.micro instance (Ubuntu 24.04, us-east-1) with the following setup:

- **Security group** — inbound rules for SSH (22), HTTP (80), and custom TCP (8000)
- **nginx** configured as a reverse proxy, forwarding port 80 → uvicorn on port 8000
- **uvicorn** running via `nohup` for persistence across SSH sessions
- **ngrok** providing a stable HTTPS tunnel (required because EC2 public IPs are HTTP-only without a domain + SSL certificate)
- **tesseract-ocr** installed at system level for OCR fallback

AWS EC2 was chosen over Vercel serverless for the backend because:
- ChromaDB requires persistent local disk storage
- pytesseract requires a system-level binary (`tesseract-ocr`)
- File uploads need temporary disk space
- Long-running Python processes aren't supported on serverless platforms

Steps to reproduce:

1. Launch EC2 t3.micro (Ubuntu 24.04), open ports 22, 80, 8000
2. SSH in and run:
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git nginx tesseract-ocr
git clone https://github.com/Aryan1347/ai-document-reader
cd ai-document-reader/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```
3. Set environment variables:
```bash
export MISTRAL_API_KEY=your_key
export GROQ_API_KEY=your_key
```
4. Start backend:
```bash
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &
```
5. Configure nginx reverse proxy on port 80
6. Install and run ngrok for HTTPS:
```bash
sudo snap install ngrok
ngrok config add-authtoken YOUR_TOKEN
ngrok http 8000
```

### Frontend — Vercel

1. Push frontend to GitHub
2. Import repo in [Vercel](https://vercel.com), set Root Directory to `frontend`
3. Add environment variable: `VITE_API_URL=your_ngrok_https_url`
4. Deploy

---

## Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Mistral API key](https://console.mistral.ai/)
- [Groq API key](https://console.groq.com/)
- tesseract installed:
  - Windows: [tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki)
  - Mac: `brew install tesseract`
  - Linux: `sudo apt install tesseract-ocr`

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create `.env` in `backend/`:

```
MISTRAL_API_KEY=your_mistral_key_here
GROQ_API_KEY=your_groq_key_here
```

Run:

```bash
uvicorn main:app --reload
```

Backend at `http://localhost:8000` — Swagger at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
```

Create `.env` in `frontend/`:

```
VITE_API_URL=http://localhost:8000
```

Run:

```bash
npm run dev
```

Frontend at `http://localhost:5173`

---

## API Reference

Full interactive docs: [https://amaze-recycling-suffocate.ngrok-free.dev/docs](https://amaze-recycling-suffocate.ngrok-free.dev/docs)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/upload` | Upload a PDF document |
| POST | `/query` | Ask a question about the document |
| GET | `/history/{session_id}` | Get chat history for a session |
| GET | `/sessions` | List all uploaded documents |
| DELETE | `/sessions/{session_id}` | Delete a session and its history |

### POST `/upload`

**Request:** `multipart/form-data` with `file` field (PDF only)

**Response:**
```json
{
  "session_id": "uuid",
  "filename": "document.pdf",
  "pages_extracted": 5,
  "chunks_created": 42,
  "full_text": "[Page 1]\n..."
}
```

### POST `/query`

**Request:**
```json
{
  "session_id": "uuid",
  "question": "What are the main conclusions?"
}
```

**Response:**
```json
{
  "answer": "The main conclusions are... (Page 3)",
  "sources": [
    { "page": 3, "relevance_score": 0.91 },
    { "page": 4, "relevance_score": 0.87 }
  ],
  "low_confidence": false
}
```

---

## Sample Documents

Sample PDFs for testing are in the `sample_docs/` folder.

---

## Design Decisions

**AWS EC2 over fully serverless** — The RAG backend requires ChromaDB (persistent disk storage), tesseract-ocr (system binary), and file handling — none of which are supported on serverless platforms like Vercel. EC2 gives a full Linux environment with complete control over installed dependencies.

**Mistral over Gemini** — Gemini introduced a 250 RPD hard cap post-Dec 2025. Mistral provides 1B tokens/month with no daily ceiling — more reliable for demos.

**Groq over OpenAI** — Groq offers the fastest inference available on llama-3.3-70b, free tier sufficient for this use case.

**ChromaDB persistent client** — vectors saved to disk, survive server restarts. Each document gets an isolated collection (`session_{uuid}`) so multiple documents don't mix.

**SQLite over PostgreSQL** — single-user demo with no concurrent writes. One environment variable change (`DATABASE_URL`) migrates to Postgres for production.

**PyMuPDF over pypdf** — 10x faster extraction, better handling of complex layouts, actively maintained.

---

## Project Structure

```
ai-document-reader/
├── backend/
│   ├── main.py          # FastAPI app, all routes
│   ├── ingest.py        # PDF extraction, chunking, embedding, ChromaDB storage
│   ├── rag.py           # retrieval, prompt building, Groq LLM call
│   ├── models.py        # SQLAlchemy ORM models
│   ├── database.py      # DB engine, session factory, get_db dependency
│   ├── requirements.txt
│   └── .gitignore
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── Upload.jsx
│       │   └── Chat.jsx
│       └── api/
│           └── api.js
├── sample_docs/
│   └── sample.pdf
└── README.md
```