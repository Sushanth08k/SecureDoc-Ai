import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import tempfile
import uuid
from PIL import Image
import numpy as np

# Try to import required libraries with graceful fallback
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

# Create pages directory if it doesn't exist
os.makedirs("uploads/pages", exist_ok=True)

class PreprocessingService:
    """
    Service for document preprocessing including:
    - PDF to image conversion
    - Image normalization
    - Document preparation for OCR and analysis
    """

    @staticmethod
    def pdf_to_images(pdf_path: str, dpi: int = 300) -> List[Image.Image]:
        """
        Convert PDF to a list of PIL Image objects
        
        Args:
            pdf_path: Path to the PDF file
            dpi: Resolution for conversion
            
        Returns:
            List of PIL Image objects, one per page
        """
        if not PDF2IMAGE_AVAILABLE:
            raise ImportError(
                "pdf2image package is not installed. Install it with: pip install pdf2image"
            )
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found at: {pdf_path}")
        
        # Create a unique folder for this document's pages
        doc_id = uuid.uuid4().hex[:8]
        pages_dir = os.path.join("uploads", "pages", doc_id)
        os.makedirs(pages_dir, exist_ok=True)
        
        # Convert PDF to images
        logger.info(f"Converting PDF {pdf_path} to images")
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            fmt="jpeg",
            thread_count=os.cpu_count() or 1,
            output_folder=pages_dir,
            output_file=f"page"
        )
        
        logger.info(f"Converted PDF to {len(images)} images in {pages_dir}")
        return images
    
    @staticmethod
    def normalize_image(image: Image.Image, fixed_width: int = 1800) -> Image.Image:
        """
        Normalize image for improved OCR performance
        
        Args:
            image: PIL Image object to normalize
            fixed_width: Width to resize the image to maintain consistent scale
            
        Returns:
            Normalized PIL Image
        """
        if not OPENCV_AVAILABLE:
            logger.warning("OpenCV not available, performing basic normalization only")
            # Basic normalization (grayscale only)
            if image.mode != 'L':
                image = image.convert('L')
            return image
        
        logger.info("Normalizing image with OpenCV")
        
        # Convert PIL image to OpenCV format
        if image.mode != 'RGB':
            image = image.convert('RGB')
        img_array = np.array(image)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Resize image to fixed width while maintaining aspect ratio
        h, w = img_cv.shape[:2]
        aspect_ratio = h / w
        new_height = int(fixed_width * aspect_ratio)
        img_cv = cv2.resize(img_cv, (fixed_width, new_height), interpolation=cv2.INTER_AREA)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        denoised = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Deskew image (detect and correct skew angle)
        # This is a placeholder - full deskew implementation would use more complex logic
        # For a production version, you might want to use techniques like Hough Line Transform
        
        # For now we'll use a simple threshold to improve OCR
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Convert back to PIL format
        processed_img = Image.fromarray(binary)
        
        logger.info("Image normalization complete")
        return processed_img
    
    @staticmethod
    def prepare_document(file_path: str) -> Dict[str, Any]:
        """
        Process an uploaded document (PDF or image)
        
        Args:
            file_path: Path to the uploaded file
            
        Returns:
            Dictionary with processing results and metadata
        """
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            if not PDF2IMAGE_AVAILABLE:
                return {
                    "status": "error",
                    "message": "PDF processing requires pdf2image package"
                }
            
            try:
                # Convert PDF to images
                images = PreprocessingService.pdf_to_images(file_path)
                
                # Process each page
                processed_pages = []
                for i, img in enumerate(images):
                    # Normalize image
                    norm_img = PreprocessingService.normalize_image(img)
                    
                    # Save normalized image to pages directory
                    doc_id = Path(os.path.dirname(images[0].filename)).name
                    output_path = os.path.join("uploads", "pages", doc_id, f"normalized_page_{i+1}.jpg")
                    norm_img.save(output_path, format="JPEG")
                    
                    processed_pages.append({
                        "page_num": i + 1,
                        "temp_path": output_path,
                        "original_path": images[i].filename
                    })
                
                return {
                    "status": "success",
                    "file_type": "pdf",
                    "pages": len(processed_pages),
                    "processed_pages": processed_pages,
                    "doc_id": doc_id
                }
                
            except Exception as e:
                logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
                return {
                    "status": "error",
                    "message": f"Error processing PDF: {str(e)}"
                }
                
        elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
            try:
                # Load and process image
                with Image.open(file_path) as img:
                    # Create a unique folder for this image
                    doc_id = uuid.uuid4().hex[:8]
                    pages_dir = os.path.join("uploads", "pages", doc_id)
                    os.makedirs(pages_dir, exist_ok=True)
                    
                    # Normalize image
                    norm_img = PreprocessingService.normalize_image(img)
                    
                    # Save normalized image
                    output_path = os.path.join(pages_dir, f"normalized_page_1.jpg")
                    norm_img.save(output_path, format="JPEG")
                    
                    return {
                        "status": "success",
                        "file_type": "image",
                        "pages": 1,
                        "doc_id": doc_id,
                        "processed_pages": [{
                            "page_num": 1,
                            "temp_path": output_path,
                            "original_path": file_path
                        }]
                    }
            
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}", exc_info=True)
                return {
                    "status": "error",
                    "message": f"Error processing image: {str(e)}"
                }
        
        else:
            return {
                "status": "error",
                "message": f"Unsupported file type: {file_ext}"
            }
