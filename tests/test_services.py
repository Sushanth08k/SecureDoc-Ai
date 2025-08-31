import pytest
from app.services.preprocess import PreprocessingService
from app.services.ocr import OCRService
from app.services.pii import PIIDetectionService
import os
import tempfile
from PIL import Image

class TestPreprocessing:
    """Tests for the preprocessing service"""
    
    def test_normalize_image(self):
        """Test image normalization"""
        # Create a test image
        img = Image.new('RGB', (100, 100), color='white')
        
        # Normalize the image
        normalized = PreprocessingService.normalize_image(img)
        
        # Check that normalization produced a grayscale image
        assert normalized.mode == 'L'

class TestOCR:
    """Tests for the OCR service"""
    
    def test_process_image_placeholder(self):
        """Test OCR image processing placeholder"""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            Image.new('RGB', (100, 100), color='white').save(tmp.name)
            
            # Process the image with OCR
            result = OCRService.process_image(tmp.name)
            
            # Check that the placeholder returns expected format
            assert result["status"] == "placeholder"
            assert "message" in result
            
        # Clean up
        os.unlink(tmp.name)

class TestPIIDetection:
    """Tests for the PII detection service"""
    
    def test_detect_ssn(self):
        """Test SSN detection"""
        text = "My SSN is 123-45-6789 and my friend's is 987654321"
        result = PIIDetectionService.detect_pii(text)
        
        # Check that SSNs were detected
        assert "ssn" in result
        assert len(result["ssn"]) == 2
        
    def test_detect_email(self):
        """Test email detection"""
        text = "Contact me at test@example.com or admin@test.org"
        result = PIIDetectionService.detect_pii(text)
        
        # Check that emails were detected
        assert "email" in result
        assert len(result["email"]) == 2
