import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.redact import RedactionService

class TestRedactionService:
    """
    Tests for the RedactionService class
    """
    
    def test_redact_text_entities(self):
        """Test text redaction with entity replacement"""
        # Sample text with entities
        text = "Hello, my name is John Doe and my SSN is 123-45-6789"
        
        # Sample entities with positions
        entities = [
            {
                "entity": "PERSON",
                "start": 18,
                "end": 26,
                "confidence": 0.9
            },
            {
                "entity": "US_SSN",
                "start": 38,
                "end": 49,
                "confidence": 0.95
            }
        ]
        
        # Perform redaction
        redacted_text = RedactionService.redact_text_entities(text, entities)
        
        # Check if entities are properly redacted
        assert "[REDACTED_US_SSN]" in redacted_text
        assert "[REDACTED_PERSON]" in redacted_text
        assert "John Doe" not in redacted_text
        assert "123-45-6789" not in redacted_text
    
    def test_redact_text_entities_no_entities(self):
        """Test text redaction with no entities"""
        text = "Hello, this is a sample text without PII"
        redacted_text = RedactionService.redact_text_entities(text, [])
        
        # Check if text is unchanged
        assert redacted_text == text
    
    def test_redact_text_entities_error_handling(self):
        """Test error handling in text redaction"""
        text = "Sample text"
        
        # Invalid entity without start/end
        entities = [{"entity": "TEST"}]
        
        # Should not raise exception, return original text
        redacted_text = RedactionService.redact_text_entities(text, entities)
        assert redacted_text == text
    
    @patch("app.services.redact.Image")
    def test_redact_image(self, mock_image):
        """Test image redaction with bounding boxes"""
        # Setup mock image
        mock_img = MagicMock()
        mock_img.width = 1000
        mock_img.height = 1000
        mock_draw = MagicMock()
        
        # Configure mocks
        mock_image.open.return_value.__enter__.return_value = mock_img
        mock_image.Draw.return_value = mock_draw
        
        # Sample entities with bounding boxes
        entities = [
            {
                "entity": "PERSON",
                "bbox": [100, 100, 200, 50],
                "confidence": 0.9
            }
        ]
        
        # Mock tempfile
        with tempfile.NamedTemporaryFile() as tmp:
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = tmp.name
                
                # Call redact_image
                result_path, redacted_areas = RedactionService.redact_image("test.jpg", entities)
                
                # Verify redaction was applied
                mock_draw.rectangle.assert_called_once()
                assert len(redacted_areas) == 1
                assert redacted_areas[0]["entity_type"] == "PERSON"
    
    def test_process_document(self):
        """Test document processing with redaction"""
        # Create mock document, OCR, and PII data
        document_data = {
            "status": "success",
            "processed_pages": [
                {"page_num": 1, "temp_path": "test1.jpg"},
                {"page_num": 2, "temp_path": "test2.jpg"}
            ]
        }
        
        ocr_results = {
            "status": "success",
            "pages": [
                {"page_num": 1, "text": "Hello John Doe"},
                {"page_num": 2, "text": "SSN: 123-45-6789"}
            ]
        }
        
        pii_results = {
            "status": "success",
            "results": [
                {
                    "status": "success",
                    "page_num": 1,
                    "entities": [
                        {"entity": "PERSON", "start": 6, "end": 14, "bbox": [10, 10, 50, 20]}
                    ]
                },
                {
                    "status": "success",
                    "page_num": 2,
                    "entities": [
                        {"entity": "US_SSN", "start": 5, "end": 16, "bbox": [30, 30, 70, 15]}
                    ]
                }
            ]
        }
        
        # Mock redact_image and redact_text_entities
        with patch.object(RedactionService, 'redact_image') as mock_redact_image, \
             patch.object(RedactionService, 'redact_text_entities') as mock_redact_text:
            
            # Configure mocks
            mock_redact_image.side_effect = [
                ("redacted1.jpg", [{"entity_type": "PERSON", "bbox": [10, 10, 50, 20]}]),
                ("redacted2.jpg", [{"entity_type": "US_SSN", "bbox": [30, 30, 70, 15]}])
            ]
            mock_redact_text.side_effect = [
                "Hello [REDACTED_PERSON]",
                "SSN: [REDACTED_US_SSN]"
            ]
            
            # Call process_document
            result = RedactionService.process_document(document_data, ocr_results, pii_results)
            
            # Verify results
            assert result["status"] == "success"
            assert result["pages"] == 2
            assert result["total_redactions"] == 2
            assert len(result["redacted_pages"]) == 2
            assert len(result["redacted_texts"]) == 2
            assert mock_redact_image.call_count == 2
            assert mock_redact_text.call_count == 2

    @patch("app.services.redact.FPDF")
    @patch("app.services.redact.PDF_LIB_AVAILABLE", True)
    @patch("app.services.redact.Image")
    @patch("os.path.exists")
    def test_create_redacted_pdf(self, mock_exists, mock_image, mock_fpdf):
        """Test creation of redacted PDF from images"""
        # Setup mocks
        mock_exists.return_value = True
        mock_pdf = MagicMock()
        mock_fpdf.return_value = mock_pdf
        mock_img = MagicMock()
        mock_img.size = (800, 600)
        mock_image.open.return_value.__enter__.return_value = mock_img
        
        # Sample redacted results
        redacted_results = {
            "redacted_pages": [
                {"page_num": 1, "status": "success", "redacted_path": "redacted1.jpg", "redactions": 2},
                {"page_num": 2, "status": "success", "redacted_path": "redacted2.jpg", "redactions": 1}
            ],
            "total_redactions": 3
        }
        
        # Call create_redacted_pdf
        result = RedactionService.create_redacted_pdf(redacted_results, "output.pdf")
        
        # Verify PDF creation
        assert result["status"] == "success"
        assert result["total_pages"] == 2
        assert result["total_redactions"] == 3
        assert mock_pdf.add_page.call_count == 2
        assert mock_pdf.image.call_count == 2
        mock_pdf.output.assert_called_once_with("output.pdf")
    
    @patch("app.services.redact.PDF_LIB_AVAILABLE", False)
    def test_create_redacted_pdf_no_library(self):
        """Test PDF creation when library is not available"""
        result = RedactionService.create_redacted_pdf({}, "output.pdf")
        assert result["status"] == "error"
        assert "PDF creation library is not available" in result["message"]
    
    def test_create_redaction_report(self):
        """Test creation of redaction report"""
        # Sample data
        redacted_results = {
            "total_redactions": 3,
            "redacted_pages": [
                {
                    "page_num": 1, 
                    "status": "success", 
                    "redactions": 2,
                    "redacted_areas": [{"entity_type": "PERSON", "bbox": [10, 10, 50, 20]}],
                    "redacted_text": "Hello [REDACTED_PERSON]"
                },
                {
                    "page_num": 2, 
                    "status": "success", 
                    "redactions": 1,
                    "redacted_areas": [{"entity_type": "US_SSN", "bbox": [30, 30, 70, 15]}],
                    "redacted_text": "SSN: [REDACTED_US_SSN]"
                }
            ]
        }
        
        pii_results = {
            "sensitivity": "high",
            "entity_types": ["PERSON", "US_SSN"],
            "entity_count": 3
        }
        
        # Mock file operations
        with patch("builtins.open", MagicMock()), \
             patch("json.dump") as mock_json_dump, \
             patch("os.path.exists") as mock_exists, \
             patch("os.makedirs") as mock_makedirs:
            
            mock_exists.return_value = False
            
            # Call create_redaction_report
            result = RedactionService.create_redaction_report(
                redacted_results, pii_results, "report.json"
            )
            
            # Verify report creation
            assert result["status"] == "success"
            assert mock_makedirs.called
            assert mock_json_dump.called
            
            # Verify report content
            report_data = mock_json_dump.call_args[0][0]
            assert report_data["summary"]["total_pages"] == 2
            assert report_data["summary"]["total_redactions"] == 3
            assert report_data["summary"]["sensitivity"] == "high"
            assert len(report_data["pages"]) == 2
            
            # Check for redacted text in report
            assert "redacted_text" in report_data["pages"][0]
            assert report_data["pages"][0]["redacted_text"] == "Hello [REDACTED_PERSON]"

    @pytest.mark.skipif(not hasattr(RedactionService, 'redact_pdf'), 
                       reason="redact_pdf method not implemented")
    @patch("app.services.redact.PYPDF2_AVAILABLE", True)
    @patch("app.services.redact.PyPDF2")
    def test_redact_pdf_with_pypdf2(self, mock_pypdf2):
        """Test PDF redaction using PyPDF2"""
        # Mock PyPDF2 components
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_pypdf2.PdfReader.return_value = mock_reader
        mock_pypdf2.PdfWriter.return_value = mock_writer
        mock_reader.pages = [MagicMock(), MagicMock()]
        
        # Sample entities
        entities = [
            {"page_num": 1, "entity": "PERSON", "start": 10, "end": 20},
            {"page_num": 2, "entity": "US_SSN", "start": 30, "end": 40}
        ]
        
        # Call redact_pdf
        with patch("builtins.open", MagicMock()):
            result = RedactionService.redact_pdf("input.pdf", entities, "output.pdf")
        
        # Verify redaction
        assert result["status"] == "success"
        assert result["pages_processed"] == 2
        assert result["total_redactions"] == 2
        assert mock_writer.add_page.call_count == 2
        mock_writer.write.assert_called_once()
