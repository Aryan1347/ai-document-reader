import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 60000, // 60s — ingest can be slow
});

// ── Document ──────────────────────────────────────────────────────────────────

/**
 * Upload a PDF. Returns { session_id, filename, pages_extracted, chunks_created, full_text }
 */
export async function uploadPDF(file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await client.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    },
  });
  return res.data;
}

/**
 * List all sessions. Returns [{ id, filename, pages_extracted, chunks_created, uploaded_at }]
 */
export async function getSessions() {
  const res = await client.get("/sessions");
  return res.data;
}

/**
 * Delete a session by id.
 */
export async function deleteSession(sessionId) {
  const res = await client.delete(`/sessions/${sessionId}`);
  return res.data;
}

// ── Chat ──────────────────────────────────────────────────────────────────────

/**
 * Ask a question. Returns { answer, sources, low_confidence }
 */
export async function queryDocument(sessionId, question) {
  const res = await client.post("/query", {
    session_id: sessionId,
    question,
  });
  return res.data;
}

/**
 * Fetch chat history for a session. Returns [{ role, content, timestamp }]
 */
export async function getHistory(sessionId) {
  const res = await client.get(`/history/${sessionId}`);
  return res.data;
}
