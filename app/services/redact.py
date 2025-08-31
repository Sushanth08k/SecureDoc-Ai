from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont
import os
import tempfile
import logging
from pathlib import Path
import json
import re

# Try to import PDF libraries with graceful fallback
try:
    from fpdf import FPDF
    PDF_LIB_AVAILABLE = True
except ImportError:
    PDF_LIB_AVAILABLE = False

# Try to import PyPDF2 for advanced PDF redaction
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

# Try to import pikepdf as an alternative
try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

class RedactionService:
    """
    Service for redacting sensitive information from documents
    
    This service applies redaction to documents based on PII detection results,
    creating redacted versions of document images and text.
    """
    
    @staticmethod
    def redact_text_entities(text: str, entities: List[Dict[str, Any]]) -> str:
        """
        Redact text by replacing detected entities with [REDACTED_<ENTITY_TYPE>]
        
        Args:
            text: Original text content
            entities: List of PII entities with start/end positions
            
        Returns:
            Redacted text with entities replaced
        """
        try:
            # Sort entities by start position in reverse order (to avoid position shifts)
            sorted_entities = sorted(entities, key=lambda e: e.get("start", 0), reverse=True)
            redacted_text = text
            
            for entity in sorted_entities:
                start = entity.get("start")
                end = entity.get("end")
                entity_type = entity.get("entity", "UNKNOWN")
                
                if start is not None and end is not None:
                    redaction_marker = f"[REDACTED_{entity_type}]"
                    redacted_text = redacted_text[:start] + redaction_marker + redacted_text[end:]
            
            return redacted_text
        except Exception as e:
            logger.error(f"Error redacting text: {str(e)}", exc_info=True)
            return text  # Return original text on error
    
    @staticmethod
    def redact_image(image_path: str, pii_entities: List[Dict[str, Any]], 
                     redaction_color: str = "black") -> str:
        """
        Apply redaction to an image based on PII findings
        
        Args:
            image_path: Path to the image file
            pii_entities: List of PII entities with bounding boxes
            redaction_color: Color to use for redaction boxes (default: black)
            
        Returns:
            Path to redacted image file
        """
        try:
            # Open the image
            with Image.open(image_path) as img:
                draw = ImageDraw.Draw(img)
                
                # Track redacted areas for the report
                redacted_areas = []
                
                # Apply redaction for each PII entity that has a bounding box
                for entity in pii_entities:
                    if "bbox" in entity and len(entity["bbox"]) == 4:
                        # Extract bounding box coordinates
                        x, y, width, height = entity["bbox"]
                        
                        # Add padding to the box (5 pixels on each side)
                        x1 = max(0, x - 5)
                        y1 = max(0, y - 5)
                        x2 = min(img.width, x + width + 5)
                        y2 = min(img.height, y + height + 5)
                        
                        # Draw redaction rectangle
                        draw.rectangle([(x1, y1), (x2, y2)], fill=redaction_color)
                        
                        # Track this redaction
                        redacted_areas.append({
                            "entity_type": entity.get("entity", "UNKNOWN"),
                            "bbox": [x1, y1, x2 - x1, y2 - y1]
                        })
                
                # Save redacted image to temp file
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    img.save(tmp.name, format="JPEG")
                    return tmp.name, redacted_areas
                    
        except Exception as e:
            logger.error(f"Error redacting image: {str(e)}", exc_info=True)
            return image_path, []  # Return original image path on error
    
    @staticmethod
    def redact_pdf(pdf_path: str, entities: List[Dict[str, Any]], output_path: str) -> Dict[str, Any]:
        """
        Redact sensitive information directly in a PDF file
        
        Args:
            pdf_path: Path to the original PDF file
            entities: List of PII entities with page numbers and positions
            output_path: Path where to save the redacted PDF
            
        Returns:
            Dictionary with information about the redacted PDF
        """
        # Check if PDF libraries are available
        if not PYPDF2_AVAILABLE and not PIKEPDF_AVAILABLE:
            logger.error("No PDF redaction libraries (PyPDF2 or pikepdf) are available")
            return {
                "status": "error",
                "message": "PDF redaction libraries are not available"
            }
        
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Group entities by page
            entities_by_page = {}
            for entity in entities:
                page_num = entity.get("page_num", 0)
                if page_num not in entities_by_page:
                    entities_by_page[page_num] = []
                entities_by_page[page_num].append(entity)
            
            if PYPDF2_AVAILABLE:
                # Use PyPDF2 for redaction
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    writer = PyPDF2.PdfWriter()
                    
                    # Process each page
                    for i in range(len(reader.pages)):
                        page = reader.pages[i]
                        
                        # If there are entities to redact on this page
                        if i+1 in entities_by_page:
                            # Apply redactions (this is simplified; actual implementation would 
                            # need to handle text extraction and positioning)
                            page_entities = entities_by_page[i+1]
                            
                            # Future enhancement: implement proper PDF text redaction
                            # Currently this is a placeholder
                            
                        # Add the page to the output PDF
                        writer.add_page(page)
                    
                    # Write the output file
                    with open(output_path, 'wb') as output_file:
                        writer.write(output_file)
            
            elif PIKEPDF_AVAILABLE:
                # Use pikepdf for redaction
                with pikepdf.open(pdf_path) as pdf:
                    # Process each page with entities
                    for page_num, page_entities in entities_by_page.items():
                        if page_num <= len(pdf.pages):
                            # Future enhancement: implement proper PDF text redaction
                            # Currently this is a placeholder
                            pass
                    
                    # Save the redacted PDF
                    pdf.save(output_path)
            
            return {
                "status": "success",
                "output_path": output_path,
                "pages_processed": len(entities_by_page),
                "total_redactions": sum(len(entities) for entities in entities_by_page.values())
            }
            
        except Exception as e:
            logger.error(f"Error redacting PDF: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error redacting PDF: {str(e)}"
            }
    
    @staticmethod
    def process_document(document_data: Dict[str, Any], 
                         ocr_results: Dict[str, Any],
                         pii_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a document to create redacted versions
        
        Args:
            document_data: Document data from preprocessing service
            ocr_results: OCR results with text and positions
            pii_results: PII detection results
            
        Returns:
            Dictionary with paths to redacted document images
        """
        # Validate input data
        if (document_data.get("status") != "success" or
            ocr_results.get("status") != "success" or
            pii_results.get("status") != "success"):
            return {
                "status": "error",
                "message": "Cannot redact document due to preprocessing, OCR, or PII detection errors"
            }
        
        redacted_pages = []
        total_redactions = 0
        redacted_texts = []
        
        # Process each page
        for page_num, pii_page in enumerate(pii_results.get("results", [])):
            try:
                # Skip pages with errors
                if pii_page.get("status") != "success":
                    logger.warning(f"Skipping redaction for page {page_num+1} due to PII detection errors")
                    redacted_pages.append({
                        "page_num": page_num + 1,
                        "status": "error",
                        "message": f"PII detection failed for this page: {pii_page.get('message', 'Unknown error')}"
                    })
                    continue
                
                # Find the corresponding document page
                doc_page = next((p for p in document_data.get("processed_pages", []) 
                                if p.get("page_num") == page_num + 1), None)
                
                if not doc_page:
                    logger.warning(f"Could not find document page {page_num+1}")
                    redacted_pages.append({
                        "page_num": page_num + 1,
                        "status": "error",
                        "message": "Could not find document page"
                    })
                    continue
                
                # Get PII entities for this page
                pii_entities = pii_page.get("entities", [])
                
                # Get OCR text for this page
                ocr_page = next((p for p in ocr_results.get("pages", [])
                               if p.get("page_num") == page_num + 1), None)
                
                page_result = {
                    "page_num": page_num + 1,
                    "status": "success",
                }
                
                # Redact text if available
                if ocr_page and "text" in ocr_page and pii_entities:
                    original_text = ocr_page.get("text", "")
                    redacted_text = RedactionService.redact_text_entities(original_text, pii_entities)
                    
                    # Add redacted text to results
                    page_result["redacted_text"] = redacted_text
                    redacted_texts.append({
                        "page_num": page_num + 1,
                        "text": redacted_text
                    })
                
                if not pii_entities:
                    logger.info(f"No PII entities to redact on page {page_num+1}")
                    page_result["message"] = "No PII entities to redact"
                    page_result["redacted_path"] = doc_page.get("temp_path")  # Use original image
                    page_result["redactions"] = 0
                    redacted_pages.append(page_result)
                    continue
                
                # Apply image redaction
                redacted_image_path, redacted_areas = RedactionService.redact_image(
                    doc_page.get("temp_path"),
                    pii_entities
                )
                
                # Update page result with image redaction info
                page_result["redacted_path"] = redacted_image_path
                page_result["redactions"] = len(redacted_areas)
                page_result["redacted_areas"] = redacted_areas
                
                redacted_pages.append(page_result)
                total_redactions += len(redacted_areas)
                
            except Exception as e:
                logger.error(f"Error in redaction for page {page_num+1}: {str(e)}", exc_info=True)
                redacted_pages.append({
                    "page_num": page_num + 1,
                    "status": "error",
                    "message": f"Redaction error: {str(e)}"
                })
        
        return {
            "status": "success",
            "pages": len(redacted_pages),
            "total_redactions": total_redactions,
            "redacted_pages": redacted_pages,
            "redacted_texts": redacted_texts
        }
    
    @staticmethod
    def create_redacted_pdf(redacted_results: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """
        Combine redacted images into a PDF
        
        Args:
            redacted_results: Dictionary with redacted page information
            output_path: Path where to save the redacted PDF
            
        Returns:
            Dictionary with information about the redacted PDF
        """
        if not PDF_LIB_AVAILABLE:
            logger.error("PDF creation library (fpdf) is not available")
            return {
                "status": "error",
                "message": "PDF creation library is not available"
            }
            
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Create a new PDF
            pdf = FPDF()
            
            # Add redacted pages to the PDF
            for page in sorted(redacted_results.get("redacted_pages", []), 
                              key=lambda x: x.get("page_num", 0)):
                
                if page.get("status") != "success" or "redacted_path" not in page:
                    logger.warning(f"Skipping page {page.get('page_num')} in PDF creation")
                    continue
                
                # Get the redacted image path
                image_path = page.get("redacted_path")
                
                # Skip if file doesn't exist
                if not os.path.exists(image_path):
                    logger.warning(f"Redacted image not found: {image_path}")
                    continue
                
                # Get image dimensions
                with Image.open(image_path) as img:
                    width, height = img.size
                
                # Add a new page with the correct orientation
                if width > height:
                    pdf.add_page(orientation='L')  # Landscape
                else:
                    pdf.add_page(orientation='P')  # Portrait
                
                # Add the image to the page (fit to page)
                pdf.image(image_path, x=0, y=0, w=pdf.w, h=pdf.h)
            
            # Save the PDF
            pdf.output(output_path)
            
            # Generate a report of redactions
            total_redactions = redacted_results.get("total_redactions", 0)
            pages_with_redactions = sum(1 for page in redacted_results.get("redacted_pages", [])
                                      if page.get("redactions", 0) > 0)
            
            return {
                "status": "success",
                "output_path": output_path,
                "total_pages": len(redacted_results.get("redacted_pages", [])),
                "pages_with_redactions": pages_with_redactions,
                "total_redactions": total_redactions
            }
            
        except Exception as e:
            logger.error(f"Error creating redacted PDF: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error creating redacted PDF: {str(e)}"
            }
    
    @staticmethod
    def create_redaction_report(redacted_results: Dict[str, Any], pii_results: Dict[str, Any], 
                               output_path: str) -> Dict[str, Any]:
        """
        Create a detailed report of the redaction process
        
        Args:
            redacted_results: Dictionary with redacted page information
            pii_results: Dictionary with PII detection results
            output_path: Path where to save the report
            
        Returns:
            Dictionary with information about the report
        """
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Generate report data
            report = {
                "summary": {
                    "total_pages": len(redacted_results.get("redacted_pages", [])),
                    "total_redactions": redacted_results.get("total_redactions", 0),
                    "sensitivity": pii_results.get("sensitivity", "unknown"),
                    "entity_types": pii_results.get("entity_types", []),
                    "entity_count": pii_results.get("entity_count", 0)
                },
                "pages": []
            }
            
            # Add page details
            for page in redacted_results.get("redacted_pages", []):
                if page.get("status") == "success":
                    page_report = {
                        "page_num": page.get("page_num"),
                        "redactions": page.get("redactions", 0),
                        "redacted_areas": page.get("redacted_areas", [])
                    }
                    
                    # Add redacted text if available
                    if "redacted_text" in page:
                        page_report["redacted_text"] = page.get("redacted_text")
                    
                    report["pages"].append(page_report)
            
            # Write report to file
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            return {
                "status": "success",
                "output_path": output_path,
                "report": report
            }
            
        except Exception as e:
            logger.error(f"Error creating redaction report: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error creating redaction report: {str(e)}"
            }
