import os
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, BackgroundTasks, Form, Path
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
from pathlib import Path as FilePath

# Import services
from ..services.preprocess import PreprocessingService
from ..services.ocr import OCRService
from ..services.pii import PIIDetectionService
from ..services.layout import LayoutAnalysisService
from ..services.redact import RedactionService

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Document Ingestion"])

# Create the upload directories if they don't exist
UPLOAD_DIR = "uploads"
REDACTED_DIR = "redacted"
REPORTS_DIR = "reports"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "pages"), exist_ok=True)
os.makedirs(REDACTED_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# In-memory document cache
document_cache = {}

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    ocr: bool = Query(False, description="Run OCR on the uploaded document"),
    detect_pii: bool = Query(False, description="Detect PII in the document"),
    analyze_layout: bool = Query(False, description="Analyze document layout")
):
    """
    Endpoint to upload a document (PDF or image)
    
    Args:
        file: The file to upload
        ocr: Whether to run OCR on the document
        detect_pii: Whether to detect PII in the document
        analyze_layout: Whether to analyze document layout
        
    Returns:
        JSON with upload status and filename
    """
    # Validate file type
    allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/tiff"]
    content_type = file.content_type
    
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Only PDF and images (JPEG, PNG, TIFF) are supported."
        )
    
    # Create a unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save the file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Error saving uploaded file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while saving the file: {str(e)}"
        )
    finally:
        file.file.close()
    
    response = {
        "status": "uploaded", 
        "filename": filename,
        "content_type": content_type,
        "file_path": file_path,
        "document_id": timestamp
    }
    
    # Preprocess the document
    try:
        preprocessing_result = PreprocessingService.prepare_document(file_path)
        document_cache[timestamp] = {"preprocessing": preprocessing_result}
        
        if preprocessing_result["status"] != "success":
            response["preprocessing"] = {
                "status": "error",
                "message": preprocessing_result.get("message", "Unknown preprocessing error")
            }
            return response
            
        response["preprocessing"] = {
            "status": "success",
            "pages": len(preprocessing_result.get("processed_pages", []))
        }
        
        # Run OCR if requested
        if ocr:
            try:
                logger.info(f"Running OCR on uploaded file: {filename}")
                
                # Process document with OCR
                ocr_results = OCRService.process_document(preprocessing_result)
                document_cache[timestamp]["ocr"] = ocr_results
                
                # Include a preview in the response
                ocr_preview = {
                    "status": ocr_results.get("status"),
                    "pages": ocr_results.get("pages", 0),
                }
                
                # Include text from first page as preview
                if ocr_results.get("status") == "success" and ocr_results.get("results"):
                    first_page = ocr_results.get("results")[0]
                    ocr_preview["text_preview"] = first_page.get("text", "")[:500] + "..."  # First 500 chars
                
                response["ocr"] = ocr_preview
                
                # Process additional analyses if OCR was successful
                if ocr_results.get("status") == "success":
                    # Detect PII if requested
                    if detect_pii:
                        logger.info(f"Detecting PII in document: {filename}")
                        pii_results = PIIDetectionService.process_document(ocr_results)
                        document_cache[timestamp]["pii"] = pii_results
                        
                        # Include summary in response
                        if pii_results.get("status") == "success":
                            response["pii"] = {
                                "status": "success",
                                "sensitivity": pii_results.get("sensitivity", "unknown"),
                                "entity_count": pii_results.get("entity_count", 0),
                                "entity_types": pii_results.get("entity_types", [])
                            }
                        else:
                            response["pii"] = {
                                "status": "error",
                                "message": pii_results.get("message", "Unknown PII detection error")
                            }
                    
                    # Analyze layout if requested
                    if analyze_layout:
                        logger.info(f"Analyzing layout of document: {filename}")
                        layout_results = LayoutAnalysisService.process_document(ocr_results)
                        document_cache[timestamp]["layout"] = layout_results
                        
                        # Include summary in response
                        if layout_results.get("status") == "success":
                            response["layout"] = {
                                "status": "success",
                                "pages": layout_results.get("pages", 0),
                                "summary": layout_results.get("summary", {})
                            }
                        else:
                            response["layout"] = {
                                "status": "error",
                                "message": layout_results.get("message", "Unknown layout analysis error")
                            }
                
            except Exception as e:
                logger.error(f"Error in document processing: {str(e)}", exc_info=True)
                response["processing"] = {
                    "status": "error",
                    "message": f"Processing error: {str(e)}"
                }
    
    except Exception as e:
        logger.error(f"Error in document preprocessing: {str(e)}", exc_info=True)
        response["preprocessing"] = {
            "status": "error",
            "message": f"Preprocessing error: {str(e)}"
        }
    
    return response

@router.get("/document/{document_id}")
async def get_document_info(
    document_id: str = Path(..., description="Document ID from upload response")
):
    """
    Get information about a processed document
    
    Args:
        document_id: The document ID from the upload response
        
    Returns:
        JSON with document processing results
    """
    if document_id not in document_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Document not found. It may have been removed from the cache."
        )
    
    document_info = document_cache[document_id]
    
    # Create a sanitized response without large data
    response = {
        "document_id": document_id,
        "status": "processed"
    }
    
    # Add preprocessing info
    if "preprocessing" in document_info:
        preprocessing = document_info["preprocessing"]
        response["preprocessing"] = {
            "status": preprocessing.get("status"),
            "pages": len(preprocessing.get("processed_pages", []))
        }
    
    # Add OCR info
    if "ocr" in document_info:
        ocr = document_info["ocr"]
        response["ocr"] = {
            "status": ocr.get("status"),
            "pages": ocr.get("pages", 0)
        }
        
        # Include sample text from first page
        if ocr.get("status") == "success" and ocr.get("results"):
            first_page = ocr.get("results")[0]
            response["ocr"]["text_preview"] = first_page.get("text", "")[:500] + "..."  # First 500 chars
    
    # Add PII info
    if "pii" in document_info:
        pii = document_info["pii"]
        response["pii"] = {
            "status": pii.get("status"),
            "sensitivity": pii.get("sensitivity", "unknown"),
            "entity_count": pii.get("entity_count", 0),
            "entity_types": pii.get("entity_types", [])
        }
    
    # Add layout info
    if "layout" in document_info:
        layout = document_info["layout"]
        response["layout"] = {
            "status": layout.get("status"),
            "pages": layout.get("pages", 0),
            "summary": layout.get("summary", {})
        }
    
    # Add redaction info
    if "redaction" in document_info:
        redaction = document_info["redaction"]
        response["redaction"] = {
            "status": redaction.get("status"),
            "pages": redaction.get("pages", 0),
            "total_redactions": redaction.get("total_redactions", 0)
        }
    
    return response

@router.post("/redact/{document_id}")
async def redact_document(
    document_id: str = Path(..., description="Document ID from upload response"),
    redaction_color: str = Form("black", description="Color to use for redaction boxes")
):
    """
    Redact sensitive information from a document
    
    Args:
        document_id: The document ID from the upload response
        redaction_color: Color to use for redaction boxes (default: black)
        
    Returns:
        JSON with redaction results
    """
    if document_id not in document_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Document not found. It may have been removed from the cache."
        )
    
    document_info = document_cache[document_id]
    
    # Check if we have OCR and PII results
    if "ocr" not in document_info:
        raise HTTPException(
            status_code=400,
            detail="OCR results not available. Run OCR on the document first."
        )
    
    if "pii" not in document_info:
        raise HTTPException(
            status_code=400,
            detail="PII detection results not available. Run PII detection first."
        )
    
    # Get the necessary results
    preprocessing_result = document_info["preprocessing"]
    ocr_results = document_info["ocr"]
    pii_results = document_info["pii"]
    
    # Apply redaction
    try:
        logger.info(f"Redacting document: {document_id}")
        redaction_results = RedactionService.process_document(
            preprocessing_result,
            ocr_results,
            pii_results
        )
        
        document_cache[document_id]["redaction"] = redaction_results
        
        if redaction_results.get("status") != "success":
            return {
                "status": "error",
                "message": redaction_results.get("message", "Unknown redaction error")
            }
        
        # Create redacted PDF
        output_filename = f"{document_id}_redacted.pdf"
        output_path = os.path.join(REDACTED_DIR, output_filename)
        
        pdf_result = RedactionService.create_redacted_pdf(redaction_results, output_path)
        
        if pdf_result.get("status") != "success":
            return {
                "status": "partial_success",
                "message": "Redaction completed but PDF creation failed",
                "redaction": redaction_results,
                "pdf_error": pdf_result.get("message")
            }
        
        # Create redaction report
        report_filename = f"{document_id}_redaction_report.json"
        report_path = os.path.join(REPORTS_DIR, report_filename)
        
        report_result = RedactionService.create_redaction_report(
            redaction_results,
            pii_results,
            report_path
        )
        
        return {
            "status": "success",
            "redaction": {
                "pages": redaction_results.get("pages", 0),
                "total_redactions": redaction_results.get("total_redactions", 0)
            },
            "pdf": {
                "filename": output_filename,
                "path": output_path
            },
            "report": {
                "filename": report_filename,
                "path": report_path
            }
        }
        
    except Exception as e:
        logger.error(f"Error in document redaction: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Redaction error: {str(e)}"
        }

@router.post("/upload-batch")
async def upload_multiple_documents(
    files: List[UploadFile] = File(...),
    ocr: bool = Query(False, description="Run OCR on the uploaded documents"),
    detect_pii: bool = Query(False, description="Detect PII in the documents"),
    analyze_layout: bool = Query(False, description="Analyze document layout")
):
    """
    Endpoint to upload multiple documents at once
    
    Args:
        files: List of files to upload
        ocr: Whether to run OCR on the documents
        detect_pii: Whether to detect PII in the documents
        analyze_layout: Whether to analyze document layout
        
    Returns:
        JSON with upload status and filenames
    """
    results = []
    
    for file in files:
        # Validate file type
        allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/tiff"]
        content_type = file.content_type
        
        if content_type not in allowed_types:
            results.append({
                "filename": file.filename,
                "status": "error",
                "detail": "Invalid file type"
            })
            continue
        
        # Create a unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Save the file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            result = {
                "status": "uploaded", 
                "filename": filename,
                "content_type": content_type,
                "file_path": file_path,
                "document_id": timestamp
            }
            
            # Preprocess the document
            preprocessing_result = PreprocessingService.prepare_document(file_path)
            document_cache[timestamp] = {"preprocessing": preprocessing_result}
            
            if preprocessing_result["status"] == "success":
                result["preprocessing"] = {
                    "status": "success",
                    "pages": len(preprocessing_result.get("processed_pages", []))
                }
                
                # Run OCR if requested
                if ocr:
                    ocr_results = OCRService.process_document(preprocessing_result)
                    document_cache[timestamp]["ocr"] = ocr_results
                    
                    if ocr_results.get("status") == "success":
                        result["ocr"] = {
                            "status": "success",
                            "pages": ocr_results.get("pages", 0)
                        }
                        
                        # Process additional analyses if OCR was successful
                        if detect_pii:
                            pii_results = PIIDetectionService.process_document(ocr_results)
                            document_cache[timestamp]["pii"] = pii_results
                            
                            if pii_results.get("status") == "success":
                                result["pii"] = {
                                    "status": "success",
                                    "sensitivity": pii_results.get("sensitivity", "unknown"),
                                    "entity_count": pii_results.get("entity_count", 0)
                                }
                        
                        if analyze_layout:
                            layout_results = LayoutAnalysisService.process_document(ocr_results)
                            document_cache[timestamp]["layout"] = layout_results
                            
                            if layout_results.get("status") == "success":
                                result["layout"] = {
                                    "status": "success",
                                    "pages": layout_results.get("pages", 0),
                                    "summary": layout_results.get("summary", {})
                                }
            else:
                result["preprocessing"] = {
                    "status": "error",
                    "message": preprocessing_result.get("message", "Unknown preprocessing error")
                }
            
            results.append(result)
            
        except Exception as e:
            logger.error(f"Error processing uploaded file: {str(e)}", exc_info=True)
            results.append({
                "filename": file.filename,
                "status": "error",
                "detail": str(e)
            })
        finally:
            file.file.close()
    
    return {"results": results}
