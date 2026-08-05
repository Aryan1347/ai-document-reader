import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import Upload from "./components/Upload";
import Chat from "./components/Chat";
import { getSessions } from "./api/api";

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [showUpload, setShowUpload] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(true);

  useEffect(() => {
    getSessions()
      .then((data) => {
        setSessions(data);
        if (data.length > 0) setActiveSession(data[0]);
      })
      .catch(console.error)
      .finally(() => setLoadingSessions(false));
  }, []);

  function handleUploaded(result) {
    const newSession = {
      id: result.session_id,
      filename: result.filename,
      pages_extracted: result.pages_extracted,
      chunks_created: result.chunks_created,
      uploaded_at: new Date().toISOString(),
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSession(newSession);
    setShowUpload(false);
  }

  function handleSelectSession(session) {
    setActiveSession(session);
    setShowUpload(false);
  }

  function handleDeleted(id) {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeSession?.id === id) {
      const remaining = sessions.filter((s) => s.id !== id);
      setActiveSession(remaining.length > 0 ? remaining[0] : null);
      if (remaining.length === 0) setShowUpload(false);
    }
  }

  const showChat = activeSession && !showUpload;
  const showUploadPage = showUpload || (!activeSession && !loadingSessions);

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        activeId={activeSession?.id}
        onSelect={handleSelectSession}
        onUploadClick={() => setShowUpload(true)}
        onDeleted={handleDeleted}
      />
      <main className="main">
        {loadingSessions ? (
          <div className="center-spinner">
            <div className="spinner large" />
          </div>
        ) : showUploadPage ? (
          <Upload onUploaded={handleUploaded} />
        ) : showChat ? (
          <Chat session={activeSession} />
        ) : null}
      </main>
    </div>
  );
}
