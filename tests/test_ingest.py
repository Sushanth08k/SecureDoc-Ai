import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_endpoint(clean_uploads, test_files_dir):
    """Test the document upload endpoint"""
    # Create a test PDF file
    pdf_path = os.path.join(test_files_dir, "test.pdf")
    with open(pdf_path, "wb") as f:
        # Create an empty PDF file for testing
        f.write(b"%PDF-1.5\n%EOF\n")
    
    # Upload the test file
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/ingest/upload",
            files={"file": ("test.pdf", f, "application/pdf")}
        )
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "uploaded"
    assert "filename" in result
    assert result["content_type"] == "application/pdf"
    
    # Verify the file was saved
    assert os.path.exists(os.path.join("uploads", result["filename"]))

def test_upload_invalid_filetype(clean_uploads, test_files_dir):
    """Test uploading an invalid file type"""
    # Create a test text file
    txt_path = os.path.join(test_files_dir, "test.txt")
    with open(txt_path, "w") as f:
        f.write("This is a test file")
    
    # Try to upload the test file
    with open(txt_path, "rb") as f:
        response = client.post(
            "/ingest/upload",
            files={"file": ("test.txt", f, "text/plain")}
        )
    
    # Check response
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]
