from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class DocumentSession(Base):
    """
    One row per uploaded PDF.
    session_id is a UUID generated at upload time.
    """
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)   # UUID
    filename = Column(String, nullable=False)
    pages_extracted = Column(Integer, nullable=False)
    chunks_created = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    """
    One row per chat message (user or assistant).
    Linked to a DocumentSession via session_id.
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)       # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("DocumentSession", back_populates="messages")