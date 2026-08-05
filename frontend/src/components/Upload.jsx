import { useState, useRef } from "react";
import { uploadPDF } from "../api/api";

export default function Upload({ onUploaded }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  function handleDrop(e) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }

  function handleFileChange(e) {
    const file = e.target.files[0];
    if (file) processFile(file);
  }

  async function processFile(file) {
    if (!file.name.endsWith(".pdf")) {
      setError("Only PDF files are accepted.");
      return;
    }
    setError("");
    setUploading(true);
    setProgress(0);
    try {
      const result = await uploadPDF(file, setProgress);
      onUploaded(result);
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        "Upload failed. Check backend is running.";
      setError(msg);
    } finally {
      setUploading(false);
      setProgress(0);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="upload-page">
      <div className="upload-hero">
        <h1>AI Document Reader</h1>
        <p>Upload a PDF — ask anything about it.</p>
      </div>

      <div
        className={`drop-zone ${dragging ? "dragging" : ""} ${uploading ? "busy" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !uploading && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />

        {uploading ? (
          <div className="upload-progress">
            <div className="spinner" />
            <p>Processing PDF…</p>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="progress-label">{progress}%</span>
          </div>
        ) : (
          <div className="drop-content">
            <svg
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17,8 12,3 7,8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <p>
              Drop PDF here or <span className="link-text">browse</span>
            </p>
            <span className="drop-hint">
              Scanned PDFs supported — OCR enabled
            </span>
          </div>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="feature-pills">
        <span className="pill">Mistral embeddings</span>
        <span className="pill">Groq LLaMA 3.3 70B</span>
        <span className="pill">Source attribution</span>
        <span className="pill">Chat history</span>
        <span className="pill">OCR fallback</span>
      </div>
    </div>
  );
}
