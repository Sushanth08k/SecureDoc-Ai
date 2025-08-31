import pytest
from fastapi.testclient import TestClient
import os
import shutil
from app.main import app

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "securedoc_ai"}

# Create a fixture for test files directory
@pytest.fixture(scope="module")
def test_files_dir():
    """Create a temporary directory for test files"""
    os.makedirs("test_files", exist_ok=True)
    yield "test_files"
    # Clean up after tests
    shutil.rmtree("test_files", ignore_errors=True)

# Setup and teardown for uploads directory
@pytest.fixture(scope="function")
def clean_uploads():
    """Ensure uploads directory is clean before and after tests"""
    os.makedirs("uploads", exist_ok=True)
    yield
    # Clean up uploads directory after test
    for file in os.listdir("uploads"):
        file_path = os.path.join("uploads", file)
        if os.path.isfile(file_path):
            os.unlink(file_path)
