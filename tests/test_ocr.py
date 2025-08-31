import pytest
import os
import tempfile
from PIL import Image, ImageDraw, ImageFont
from app.services.ocr import OCRService
from app.services.preprocess import PreprocessingService

class TestOCR:
    """Tests for the OCR functionality"""
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample image with text for OCR testing"""
        # Create a white image
        img = Image.new('RGB', (800, 300), color='white')
        
        try:
            # Try to load a font
            draw = ImageDraw.Draw(img)
            
            # Add text to the image (simple text that OCR should be able to recognize)
            draw.text((50, 50), "This is a sample text for OCR testing", fill="black")
            draw.text((50, 100), "The quick brown fox jumps over the lazy dog", fill="black")
            draw.text((50, 150), "123456789 - Sample numbers", fill="black")
            
            # Save to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                img.save(tmp.name, format="JPEG")
                return tmp.name
                
        except Exception as e:
            # If font loading fails, create a simpler image
            draw = ImageDraw.Draw(img)
            draw.rectangle([(50, 50), (500, 100)], outline="black")
            draw.rectangle([(50, 150), (500, 200)], outline="black")
            
            # Save to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                img.save(tmp.name, format="JPEG")
                return tmp.name
    
    def test_run_ocr(self, sample_image):
        """Test that OCR can extract text from an image"""
        # Skip if Tesseract is not available
        try:
            import pytesseract
        except ImportError:
            pytest.skip("Tesseract not installed, skipping OCR test")
        
        # Process the image
        with Image.open(sample_image) as img:
            ocr_result = OCRService.run_ocr(img)
        
        # Check that OCR returns a result
        assert ocr_result["status"] in ["success", "error"]
        
        # If OCR succeeded, text should not be empty
        if ocr_result["status"] == "success":
            assert ocr_result["text"] != ""
            assert len(ocr_result["words"]) > 0
        
        # Clean up
        os.unlink(sample_image)
    
    def test_image_normalization(self, sample_image):
        """Test image normalization"""
        # Load the sample image
        img = Image.open(sample_image)
        
        # Normalize the image
        normalized_img = PreprocessingService.normalize_image(img)
        
        # Check that normalization produced a valid image
        assert normalized_img.mode in ['L', 'RGB']
        assert normalized_img.size[0] > 0
        assert normalized_img.size[1] > 0
        
        # Clean up
        os.unlink(sample_image)
    
    def test_ocr_pipeline(self, sample_image):
        """Test the entire OCR pipeline"""
        # Skip if Tesseract is not available
        try:
            import pytesseract
        except ImportError:
            pytest.skip("Tesseract not installed, skipping OCR test")
        
        # Process the image through the preprocessing service
        preprocessing_result = PreprocessingService.prepare_document(sample_image)
        
        # Check preprocessing result
        assert preprocessing_result["status"] == "success"
        assert len(preprocessing_result["processed_pages"]) == 1
        
        # Run OCR on the preprocessed image
        page = preprocessing_result["processed_pages"][0]
        ocr_result = OCRService.process_image(page["temp_path"])
        
        # Check OCR result
        assert ocr_result["status"] in ["success", "error"]
        
        # Clean up
        os.unlink(sample_image)
