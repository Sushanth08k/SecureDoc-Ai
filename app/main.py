from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from .routers import ingest
from .routers import audit

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

app = FastAPI(
    title="SecureDoc AI",
    description="API for secure document processing, OCR, and PII redaction",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingest.router)
app.include_router(audit.router)

# Serve static files for uploaded and processed documents
if os.path.isdir("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
if os.path.isdir("redacted"):
    app.mount("/redacted", StaticFiles(directory="redacted"), name="redacted")
if os.path.isdir("reports"):
    app.mount("/reports", StaticFiles(directory="reports"), name="reports")

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify service status
    """
    return {"status": "healthy", "service": "securedoc_ai"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
