from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os
from sqlalchemy.orm import Session

# Import models - assumes SQLAlchemy models are defined in app.db.models
try:
    from app.db.models import AuditLog, Document
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

class AuditLogger:
    """
    Service for audit logging
    
    This service provides methods for logging document operations
    for security and compliance purposes.
    """
    
    LOG_DIR = "logs"
    
    @staticmethod
    def ensure_log_dir():
        """Ensure log directory exists"""
        os.makedirs(AuditLogger.LOG_DIR, exist_ok=True)
    
    @staticmethod
    def log_event(event_type: str, document_id: Optional[str] = None, 
                  user_id: Optional[str] = None, 
                  details: Optional[Dict[str, Any]] = None,
                  db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Log an audit event
        
        Args:
            event_type: Type of event (upload, process, redact, etc.)
            document_id: ID of the document (if applicable)
            user_id: ID of the user (if applicable)
            details: Additional event details
            db: Database session (if available)
            
        Returns:
            Dictionary with logged event information
        """
        # Ensure log directory exists
        AuditLogger.ensure_log_dir()
        
        # Create log entry
        timestamp = datetime.utcnow()
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "event_type": event_type,
            "document_id": document_id,
            "user_id": user_id,
            "details": details or {}
        }
        
        # Write to log file
        log_file = os.path.join(AuditLogger.LOG_DIR, f"audit_{timestamp.strftime('%Y%m%d')}.log")
        
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        # Store in database if available
        if DB_AVAILABLE and db is not None:
            try:
                # Create database audit log entry
                audit_log = AuditLog(
                    document_id=int(document_id) if document_id and document_id.isdigit() else None,
                    timestamp=timestamp,
                    action=event_type,
                    user_id=user_id,
                    details=json.dumps(details) if details else None
                )
                
                db.add(audit_log)
                db.commit()
                
                # Update log entry with database ID
                log_entry["db_id"] = audit_log.id
                
            except Exception as e:
                # Log error but continue with file-based logging
                print(f"Error storing audit log in database: {str(e)}")
                db.rollback()
        
        return log_entry
    
    @staticmethod
    def log_document_upload(filename: str, content_type: str, 
                            user_id: Optional[str] = None,
                            db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Log document upload event
        
        Args:
            filename: Name of the uploaded file
            content_type: Content type of the file
            user_id: ID of the user (if applicable)
            db: Database session (if available)
            
        Returns:
            Dictionary with logged event information
        """
        return AuditLogger.log_event(
            event_type="document_upload",
            user_id=user_id,
            details={
                "filename": filename,
                "content_type": content_type
            },
            db=db
        )
    
    @staticmethod
    def log_document_process(document_id: str, process_type: str, 
                             status: str, user_id: Optional[str] = None,
                             details: Optional[Dict[str, Any]] = None,
                             db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Log document processing event
        
        Args:
            document_id: ID of the document
            process_type: Type of processing (OCR, PII detection, etc.)
            status: Status of the processing (success, error)
            user_id: ID of the user (if applicable)
            details: Additional processing details
            db: Database session (if available)
            
        Returns:
            Dictionary with logged event information
        """
        return AuditLogger.log_event(
            event_type=f"document_{process_type}",
            document_id=document_id,
            user_id=user_id,
            details={
                "status": status,
                **(details or {})
            },
            db=db
        )
