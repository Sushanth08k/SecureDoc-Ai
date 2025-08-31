# SecureDoc AI

SecureDoc AI is a document processing service that performs Optical Character Recognition (OCR), layout analysis, PII (Personally Identifiable Information) detection, and document redaction.

## Features

- **Document Ingestion**: Upload PDFs or images for processing
- **Document Preprocessing**: Convert PDFs to images, normalize for optimal OCR
- **OCR Processing**: Extract text content with spatial information
- **Layout Analysis**: Detect document structure, form fields, tables, and text blocks
- **PII Detection**: Identify sensitive information like SSNs, credit cards, names, etc.
- **Document Redaction**: 
  - **Text Redaction**: Replace sensitive text with "[REDACTED_<ENTITY>]" markers
  - **Image Redaction**: Apply black boxes over sensitive information in images
  - **PDF Redaction**: Redact directly in PDF files using PyPDF2 or pikepdf
- **Metadata Storage**: Store document metadata and PII findings in PostgreSQL
- **Audit Logging**: Track all document operations with database persistence
- **Redaction Reports**: Generate detailed reports of redacted information

## Project Structure

```
securedoc_ai/
├── app/                      # Main application code
│   ├── main.py               # FastAPI application entry point
│   ├── routers/              # API route definitions
│   │   ├── ingest.py         # Document ingestion endpoints
│   ├── services/             # Core services
│   │   ├── preprocess.py     # Document preprocessing utilities
│   │   ├── ocr.py            # OCR service
│   │   ├── layout.py         # Layout analysis service
│   │   ├── pii.py            # PII detection service
│   │   ├── redact.py         # Document redaction service
│   ├── db/                   # Database models and utilities
│       ├── models.py         # SQLAlchemy models
│       ├── audit.py          # Audit logging utilities
├── uploads/                  # Directory for uploaded documents
├── redacted/                 # Directory for redacted documents
├── reports/                  # Directory for redaction reports
├── tests/                    # Test suite
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container definition
└── docker-compose.yml        # Docker Compose configuration
```

## Getting Started

### Prerequisites

- Python 3.9+
- Docker and Docker Compose (for containerized deployment)
- Tesseract OCR
- Poppler (for PDF processing)
- PostgreSQL (for metadata and audit storage)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-org/securedoc-ai.git
   cd securedoc-ai
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install Tesseract OCR:
   - Windows: Download from [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
   - Ubuntu: `sudo apt install tesseract-ocr`
   - macOS: `brew install tesseract`

4. Install Poppler:
   - Windows: See [pdf2image documentation](https://github.com/Belval/pdf2image)
   - Ubuntu: `sudo apt install poppler-utils`
   - macOS: `brew install poppler`

5. Download spaCy model (if using Presidio for PII detection):
   ```
   python -m spacy download en_core_web_sm
   ```

6. Set up PostgreSQL:
   ```
   # Create database
   createdb securedoc
   
   # Run migrations (if using Alembic)
   alembic upgrade head
   ```

7. Run the application:
   ```
   uvicorn app.main:app --reload
   ```

### Docker Deployment

Build and run with Docker Compose:

```
docker-compose up -d
```

## API Endpoints

- `GET /health`: Check service health
- `POST /ingest/upload`: Upload a document (PDF or image)
  - Query parameters:
    - `ocr` (bool): Run OCR on the document
    - `detect_pii` (bool): Detect PII in the document
    - `analyze_layout` (bool): Analyze document layout
- `POST /ingest/upload-batch`: Upload multiple documents
- `GET /ingest/document/{document_id}`: Get document processing info
- `POST /ingest/redact/{document_id}`: Redact PII in a document

## Example Usage

### Upload and Process a Document

```bash
curl -X POST "http://localhost:8000/ingest/upload?ocr=true&detect_pii=true&analyze_layout=true" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@example.pdf"
```

### Redact a Document

```bash
curl -X POST "http://localhost:8000/ingest/redact/20230615_123456" \
  -H "accept: application/json" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "redaction_color=black"
```

### Redaction Features

#### Text Redaction
Replaces detected PII entities with "[REDACTED_<ENTITY>]" markers. For example:
- Original: "Hello, my name is John Smith"
- Redacted: "Hello, my name is [REDACTED_PERSON]"

#### Image Redaction
Applies black boxes over detected PII in document images, preserving the original document layout.

#### PDF Redaction
Performs redaction directly in PDF documents using either PyPDF2 or pikepdf, maintaining the original document structure.

## Development

### Running Tests

```
pytest
```

### Database Models

The system uses SQLAlchemy ORM with the following models:
- `Document`: Stores document metadata
- `DocumentPage`: Tracks individual pages within documents
- `PIIFinding`: Records detected PII entities
- `AuditLog`: Tracks all document operations

## License

[MIT License](LICENSE)

## Contributions

Contributions are welcome! Please feel free to submit a Pull Request.