import { useState } from "react";
import { deleteSession } from "../api/api";

export default function Sidebar({
  sessions,
  activeId,
  onSelect,
  onUploadClick,
  onDeleted,
}) {
  const [deletingId, setDeletingId] = useState(null);

  async function handleDelete(e, id) {
    e.stopPropagation();
    if (!window.confirm("Delete this document and its chat history?")) return;
    setDeletingId(id);
    try {
      await deleteSession(id);
      onDeleted(id);
    } catch {
      alert("Failed to delete session.");
    } finally {
      setDeletingId(null);
    }
  }

  function formatDate(iso) {
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-logo">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14,2 14,8 20,8" />
          </svg>
          DocReader
        </span>
      </div>

      <button className="upload-btn" onClick={onUploadClick}>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
        >
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        Upload PDF
      </button>

      <div className="sessions-label">Documents</div>

      <div className="sessions-list">
        {sessions.length === 0 && (
          <p className="no-sessions">
            No documents yet. Upload a PDF to start.
          </p>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`session-item ${s.id === activeId ? "active" : ""}`}
            onClick={() => onSelect(s)}
          >
            <div className="session-name" title={s.filename}>
              {s.filename}
            </div>
            <div className="session-meta">
              {s.pages_extracted}p · {s.chunks_created} chunks ·{" "}
              {formatDate(s.uploaded_at)}
            </div>
            <button
              className="delete-btn"
              onClick={(e) => handleDelete(e, s.id)}
              disabled={deletingId === s.id}
              title="Delete document"
            >
              {deletingId === s.id ? "…" : "✕"}
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
