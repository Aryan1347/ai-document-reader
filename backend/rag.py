import os
import logging
from groq import Groq
from ingest import get_vectorstore

# ── Logging ───────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
TOP_K = 5
LOW_CONFIDENCE_THRESHOLD = 0.4

# ── Client ────────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])


# ── Retrieve Relevant Chunks ──────────────────────────────────────────────────
def retrieve_chunks(session_id: str, question: str) -> list[dict]:
    """
    Load vectorstore for this session and retrieve top-K relevant chunks.
    LangChain handles embedding the query + similarity search internally.
    """
    try:
        vectorstore = get_vectorstore(session_id)
    except Exception:
        raise ValueError(f"No document found for session {session_id}. Please upload a PDF first.")

    results = vectorstore.similarity_search_with_relevance_scores(question, k=TOP_K)

    chunks = []
    for doc, score in results:
        chunks.append({
            "text": doc.page_content,
            "page": doc.metadata.get("page", "?"),
            "relevance_score": round(score, 3)
        })

    logger.info(f"Retrieved {len(chunks)} chunks for session {session_id}")
    return chunks


# ── Build System Prompt ───────────────────────────────────────────────────────
def build_system_prompt(chunks: list[dict]) -> str:
    context_parts = [f"[Page {c['page']}]\n{c['text']}" for c in chunks]
    context = "\n\n---\n\n".join(context_parts)

    return f"""You are a precise document assistant. Answer the user's question using ONLY the context provided below.

Rules:
- Always cite the page number(s) you used, e.g. "(Page 3)" at the end of relevant sentences.
- If the answer spans multiple pages, cite all relevant pages.
- If the context does not contain enough information to answer, say: "I couldn't find a confident answer in the document."
- Do not make up information outside the provided context.
- Be concise and direct.

Context from document:
{context}"""


# ── Format Chat History ───────────────────────────────────────────────────────
def format_history(chat_history: list[dict]) -> list[dict]:
    recent = chat_history[-6:] if len(chat_history) > 6 else chat_history
    return [{"role": msg["role"], "content": msg["content"]} for msg in recent]


# ── Main Query Function ───────────────────────────────────────────────────────
def query_document(session_id: str, question: str, chat_history: list[dict]) -> dict:
    """
    Full RAG pipeline:
    1. Retrieve relevant chunks via LangChain similarity search
    2. Check confidence
    3. Build prompt with context + history
    4. Call Groq LLM
    5. Return answer + sources + confidence flag
    """
    logger.info(f"Query for session {session_id}: {question[:80]}")

    # 1. Retrieve
    chunks = retrieve_chunks(session_id, question)

    # 2. Confidence check
    avg_score = sum(c["relevance_score"] for c in chunks) / len(chunks)
    low_confidence = avg_score < LOW_CONFIDENCE_THRESHOLD
    if low_confidence:
        logger.warning(f"Low confidence retrieval — avg score: {avg_score:.3f}")

    # 3. Build prompt
    system_prompt = build_system_prompt(chunks)

    # 4. Format history + question
    messages = format_history(chat_history)
    messages.append({"role": "user", "content": question})

    # 5. Call Groq
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            *messages
        ],
        temperature=0.2,
        max_tokens=1024
    )

    answer = response.choices[0].message.content

    sources = [
        {"page": c["page"], "relevance_score": c["relevance_score"]}
        for c in chunks
    ]

    logger.info(f"Answer generated | low_confidence={low_confidence}")

    return {
        "answer": answer,
        "sources": sources,
        "low_confidence": low_confidence
    }