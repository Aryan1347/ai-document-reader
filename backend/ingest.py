import os
import logging
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_mistralai import MistralAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
UPLOAD_DIR = "uploads"
CHROMA_DIR = "chroma_store"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Embeddings ────────────────────────────────────────────────────────────────
embeddings = MistralAIEmbeddings(
    model="mistral-embed",
    api_key=os.environ["MISTRAL_API_KEY"]
)


# ── PDF Text Extraction ───────────────────────────────────────────────────────
def extract_text_from_pdf(file_path: str) -> dict[int, str]:
    """
    Extract text page-by-page using PyMuPDF.
    Falls back to OCR (pytesseract) for scanned pages with no selectable text.
    Returns: { page_number: text }
    """
    doc = fitz.open(file_path)
    pages: dict[int, str] = {}

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text().strip()

        if not text:
            logger.info(f"Page {page_num} has no text — attempting OCR fallback")
            text = _ocr_page(page)

        if text:
            pages[page_num] = text
        else:
            logger.warning(f"Page {page_num} yielded no text even after OCR")

    doc.close()

    if not pages:
        raise ValueError("Could not extract any text from this PDF. It may be corrupt or unsupported.")

    logger.info(f"Extracted text from {len(pages)} pages")
    return pages


def _ocr_page(page: fitz.Page) -> str:
    """Render page to image and run pytesseract OCR."""
    try:
        mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR accuracy
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""


# ── Main Ingest Pipeline ──────────────────────────────────────────────────────
def ingest_pdf(file_path: str, session_id: str) -> dict:
    """
    Full ingest pipeline:
    1. Extract text page-by-page (OCR fallback for scanned PDFs)
    2. Chunk using LangChain RecursiveCharacterTextSplitter
    3. Embed + store in ChromaDB using LangChain (Mistral embeddings)

    Returns summary dict for API response.
    """
    logger.info(f"Starting ingest for session {session_id} | file: {file_path}")

    # 1. Extract text
    pages = extract_text_from_pdf(file_path)

    # 2. Build LangChain Documents with page metadata
    raw_docs = [
        Document(page_content=text, metadata={"page": page_num})
        for page_num, text in sorted(pages.items())
    ]

    # 3. Chunk with overlap
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        add_start_index=True
    )
    chunks = splitter.split_documents(raw_docs)

    if not chunks:
        raise ValueError("No content could be chunked from this PDF.")

    logger.info(f"Created {len(chunks)} chunks")

    # 4. Delete existing collection for this session (re-upload scenario)
    try:
        existing = Chroma(
            collection_name=f"session_{session_id}",
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR
        )
        existing.delete_collection()
        logger.info(f"Deleted existing collection for session {session_id}")
    except Exception:
        pass

    # 5. Embed + store in ChromaDB
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=f"session_{session_id}",
        persist_directory=CHROMA_DIR,
        collection_metadata={"hnsw:space": "cosine"}
    )

    logger.info(f"Stored {len(chunks)} chunks in ChromaDB for session {session_id}")

    # 6. Build full text for frontend display
    full_text = "\n\n".join(
        f"[Page {p}]\n{t}" for p, t in sorted(pages.items())
    )

    return {
        "session_id": session_id,
        "pages_extracted": len(pages),
        "chunks_created": len(chunks),
        "full_text": full_text
    }


def get_vectorstore(session_id: str) -> Chroma:
    """
    Load existing ChromaDB collection for a session.
    Used by rag.py for retrieval.
    """
    return Chroma(
        collection_name=f"session_{session_id}",
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )