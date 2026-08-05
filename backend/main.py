import os
import uuid
import logging
import shutil
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import engine, get_db, Base
from models import DocumentSession, Message
from ingest import ingest_pdf, UPLOAD_DIR
from rag import query_document

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Document Reader",
    description="Upload PDFs and ask questions using RAG + Groq LLM",
    version="1.0.0"
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to frontend URL in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Create DB tables on startup ───────────────────────────────────────────────
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified")


# ── Pydantic Schemas ──────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    session_id: str
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    low_confidence: bool

class MessageOut(BaseModel):
    role: str
    content: str
    timestamp: datetime

class SessionOut(BaseModel):
    id: str
    filename: str
    pages_extracted: int
    chunks_created: int
    uploaded_at: datetime


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "AI Document Reader is running"}


@app.post("/upload", tags=["Document"])
def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF document.
    - Saves file to /uploads
    - Extracts text (OCR fallback for scanned PDFs)
    - Chunks + embeds with Mistral
    - Stores in ChromaDB
    - Creates a session in SQLite
    Returns session_id and extracted text preview.
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    session_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{session_id}.pdf")

    # Save uploaded file
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        logger.info(f"Saved uploaded file: {file_path}")
    except Exception as e:
        logger.error(f"File save failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    # Run ingest pipeline
    try:
        result = ingest_pdf(file_path, session_id)
    except ValueError as e:
        os.remove(file_path)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        os.remove(file_path)
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process PDF.")

    # Save session to DB
    session = DocumentSession(
        id=session_id,
        filename=file.filename,
        pages_extracted=result["pages_extracted"],
        chunks_created=result["chunks_created"]
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(f"Session created: {session_id} for file: {file.filename}")

    return {
        "session_id": session_id,
        "filename": file.filename,
        "pages_extracted": result["pages_extracted"],
        "chunks_created": result["chunks_created"],
        "full_text": result["full_text"]
    }


@app.post("/query", response_model=QueryResponse, tags=["Chat"])
def query(
    body: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Ask a question about the uploaded document.
    - Retrieves relevant chunks from ChromaDB
    - Passes chat history for context-aware answers
    - Returns answer + source pages + confidence flag
    """
    # Verify session exists
    session = db.query(DocumentSession).filter(DocumentSession.id == body.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Please upload a document first.")

    # Fetch chat history for this session
    history = db.query(Message).filter(
        Message.session_id == body.session_id
    ).order_by(Message.timestamp).all()

    history_dicts = [{"role": m.role, "content": m.content} for m in history]

    # Run RAG
    try:
        result = query_document(body.session_id, body.question, history_dicts)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate answer.")

    # Save user message + assistant response to DB
    db.add(Message(session_id=body.session_id, role="user", content=body.question))
    db.add(Message(session_id=body.session_id, role="assistant", content=result["answer"]))
    db.commit()

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        low_confidence=result["low_confidence"]
    )


@app.get("/history/{session_id}", response_model=list[MessageOut], tags=["Chat"])
def get_history(session_id: str, db: Session = Depends(get_db)):
    """
    Fetch full chat history for a session.
    """
    session = db.query(DocumentSession).filter(DocumentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.timestamp).all()

    return messages


@app.get("/sessions", response_model=list[SessionOut], tags=["Document"])
def list_sessions(db: Session = Depends(get_db)):
    """
    List all document sessions (for switching between uploaded docs).
    """
    sessions = db.query(DocumentSession).order_by(DocumentSession.uploaded_at.desc()).all()
    return sessions


@app.delete("/sessions/{session_id}", tags=["Document"])
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """
    Delete a session and all its chat history.
    """
    session = db.query(DocumentSession).filter(DocumentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    db.delete(session)
    db.commit()
    logger.info(f"Deleted session: {session_id}")
    return {"message": f"Session {session_id} deleted successfully."}