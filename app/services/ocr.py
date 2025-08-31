from typing import Dict, Any, List, Optional
import os
import logging
from PIL import Image
import json

# Try to import Tesseract with graceful fallback
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# Import preprocessing service
from .preprocess import PreprocessingService

# Configure logging
logger = logging.getLogger(__name__)

class OCRService:
    """
    Service for Optical Character Recognition (OCR)
    
    This service processes document images and extracts text content,
    providing structured output with text regions and positions.
    """
    
    @staticmethod
    def run_ocr(image: Image.Image) -> Dict[str, Any]:
        """
        Run OCR on a PIL Image object
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with OCR results including text and word positions
        """
        if not TESSERACT_AVAILABLE:
            logger.error("Tesseract is not available")
            return {
                "status": "error",
                "message": "Tesseract OCR is not installed or configured",
                "text": "",
                "words": []
            }
        
        try:
            logger.info("Running Tesseract OCR")
            
            # Run Tesseract OCR with PSM 6 (assume single uniform block of text)
            # and output word bounding boxes
            custom_config = r'--psm 6 --oem 3'
            
            # Extract text
            text = pytesseract.image_to_string(image, config=custom_config)
            
            # Get word bounding boxes
            boxes = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)
            
            # Process word boxes into structured format
            words = []
            for i in range(len(boxes['text'])):
                # Skip empty words
                if not boxes['text'][i].strip():
                    continue
                
                # Create word entry with bounding box
                word = {
                    "word": boxes['text'][i],
                    "bbox": [
                        boxes['left'][i],
                        boxes['top'][i],
                        boxes['width'][i],
                        boxes['height'][i]
                    ],
                    "conf": boxes['conf'][i]
                }
                words.append(word)
            
            return {
                "status": "success",
                "text": text,
                "words": words
            }
            
        except Exception as e:
            logger.error(f"OCR processing error: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"OCR processing error: {str(e)}",
                "text": "",
                "words": []
            }
    
    @staticmethod
    def process_image(image_path: str) -> Dict[str, Any]:
        """
        Process an image with OCR
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with OCR results including text and positions
        """
        try:
            # Open the image
            with Image.open(image_path) as img:
                # Run OCR
                ocr_result = OCRService.run_ocr(img)
                return ocr_result
                
        except Exception as e:
            logger.error(f"Error processing image for OCR: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error processing image for OCR: {str(e)}",
                "text": "",
                "words": []
            }
    
    @staticmethod
    def ocr_pdf(pdf_path: str) -> List[Dict[str, Any]]:
        """
        Process a PDF document with OCR
        
        Pipeline: pdf_to_images → normalize_image → run_ocr
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of OCR results, one per page
        """
        try:
            # Process document with preprocessing service
            preprocessing_result = PreprocessingService.prepare_document(pdf_path)
            
            if preprocessing_result["status"] != "success":
                logger.error(f"Preprocessing failed: {preprocessing_result.get('message')}")
                return [{
                    "status": "error",
                    "message": f"Preprocessing failed: {preprocessing_result.get('message')}",
                    "page_num": 0
                }]
            
            # Process each page
            results = []
            for page in preprocessing_result.get("processed_pages", []):
                # Run OCR on the normalized image
                page_result = OCRService.process_image(page["temp_path"])
                page_result["page_num"] = page["page_num"]
                results.append(page_result)
            
            logger.info(f"OCR completed for PDF with {len(results)} pages")
            return results
            
        except Exception as e:
            logger.error(f"Error in OCR pipeline: {str(e)}", exc_info=True)
            return [{
                "status": "error",
                "message": f"Error in OCR pipeline: {str(e)}",
                "page_num": 0
            }]
    
    @staticmethod
    def process_document(document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process all images/pages in a document
        
        Args:
            document_data: Document data from preprocessing service
            
        Returns:
            Dictionary with OCR results for all pages
        """
        if document_data["status"] != "success":
            return {
                "status": "error",
                "message": "Cannot process document due to preprocessing errors"
            }
        
        results = []
        
        for page in document_data.get("processed_pages", []):
            page_result = OCRService.process_image(page["temp_path"])
            page_result["page_num"] = page["page_num"]
            results.append(page_result)
        
        return {
            "status": "success",
            "pages": len(results),
            "results": results
        }
