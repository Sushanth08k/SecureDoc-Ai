from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Document(Base):
    """
    Database model for document metadata
    """
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="uploaded")
    
    # Relationships
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="document", cascade="all, delete-orphan")
    pii_findings = relationship("PIIFinding", back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base):
    """
    Database model for document pages
    """
    __tablename__ = "document_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_path = Column(String(255), nullable=True)
    redacted_image_path = Column(String(255), nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="pages")


class PIIFinding(Base):
    """
    Database model for PII findings
    """
    __tablename__ = "pii_findings"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    pii_type = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    start_pos = Column(Integer, nullable=True)
    end_pos = Column(Integer, nullable=True)
    redacted = Column(Boolean, default=False)
    
    # Relationships
    document = relationship("Document", back_populates="pii_findings")


class AuditLog(Base):
    """
    Database model for audit logging
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String(100), nullable=False)
    user_id = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="audit_logs")
