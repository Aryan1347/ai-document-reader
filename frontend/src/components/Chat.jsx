import { useState, useEffect, useRef } from "react";
import { queryDocument, getHistory } from "../api/api";

export default function Chat({ session }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!session) return;
    setMessages([]);
    setLoadingHistory(true);
    getHistory(session.id)
      .then((history) => {
        const mapped = history.map((m) => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp,
        }));
        setMessages(mapped);
      })
      .catch(() => setMessages([]))
      .finally(() => setLoadingHistory(false));
  }, [session?.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!loadingHistory) inputRef.current?.focus();
  }, [loadingHistory]);

  async function handleSend() {
    const q = input.trim();
    if (!q || loading) return;

    setInput("");
    setError("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);

    try {
      const result = await queryDocument(session.id, q);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.answer,
          sources: result.sources,
          low_confidence: result.low_confidence,
        },
      ]);
    } catch (err) {
      const msg = err.response?.data?.detail || "Query failed. Try again.";
      setError(msg);
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-title">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14,2 14,8 20,8" />
          </svg>
          {session.filename}
        </div>
        <div className="chat-meta">
          {session.pages_extracted} pages · {session.chunks_created} chunks
          indexed
        </div>
      </div>

      <div className="messages">
        {loadingHistory ? (
          <div className="history-loading">
            <div className="spinner" />
          </div>
        ) : messages.length === 0 ? (
          <div className="empty-chat">
            <svg
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <p>Document indexed. Ask anything about it.</p>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`message ${m.role}`}>
              <div className="message-bubble">
                <pre className="message-text">{m.content}</pre>

                {m.sources && m.sources.length > 0 && (
                  <div className="sources">
                    {m.low_confidence && (
                      <span
                        className="confidence-warn"
                        title="Low relevance — answer may be approximate"
                      >
                        ⚠ Low confidence
                      </span>
                    )}
                    {[
                      ...new Map(m.sources.map((s) => [s.page, s])).values(),
                    ].map((s) => (
                      <span
                        key={s.page}
                        className="source-chip"
                        title={`Relevance: ${s.relevance_score}`}
                      >
                        Page {s.page}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="message assistant">
            <div className="message-bubble typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {error && <div className="error-banner chat-error">{error}</div>}

      <div className="chat-input-area">
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder="Ask a question about this document…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={loading || loadingHistory}
        />
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={!input.trim() || loading || loadingHistory}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22,2 15,22 11,13 2,9" />
          </svg>
        </button>
      </div>
    </div>
  );
}
