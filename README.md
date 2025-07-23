# Intelligent Document Extraction Powered by GenAI

A comprehensive AI-powered document extraction system that automates the extraction of structured data from unstructured documents across various industries, with a primary focus on legal document processing.

## Features

- **Multi-format Document Processing**: Support for PDFs, Word documents, scanned images, and handwritten notes
- **Natural Language Extraction**: Users can specify extraction requirements in plain English
- **GenAI + Vision Language Models**: Intelligent text and visual element extraction
- **Legal Document Specialization**: Contract analysis, clause identification, risk flagging
- **Tabular Data Extraction**: Including tables spanning multiple pages
- **Multiple Output Formats**: CSV, JSON, XML for enterprise integration
- **Audit Trails**: Comprehensive logging and user feedback loops
- **High Performance**: Process documents within 30 seconds, handle 2,000 documents/hour

## Architecture

The system consists of several key components:

1. **Document Input Handler**: Processes various document formats
2. **Natural Language Processor**: Interprets user extraction requirements
3. **GenAI Extraction Engine**: Core extraction logic using AI models
4. **Vision Language Model**: Multi-modal analysis of text and visual elements
5. **Legal Document Processor**: Specialized legal document analysis
6. **Output Generator**: Structured data output in multiple formats
7. **Web Interface**: User-friendly dashboard for interaction
8. **API Layer**: RESTful API for enterprise integration

## Installation

### Prerequisites

**For macOS users:**
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required system dependencies
brew install libmagic
```

**For Linux users:**
```bash
# Ubuntu/Debian
sudo apt-get install libmagic1

# CentOS/RHEL
sudo yum install file-libs
```

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd intelligent-document-extraction

# Create and activate virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# Run the application
python app.py
```

### Troubleshooting

**ImportError: failed to find libmagic**
- **macOS**: Install libmagic using `brew install libmagic`
- **Linux**: Install libmagic1 using your package manager
- **Windows**: libmagic is included with python-magic-bin package

## Usage

### Web Interface
1. Navigate to `http://localhost:5000`
2. Upload your document
3. Specify extraction requirements in natural language
4. Review and download extracted data

### API Usage
```python
import requests

# Upload document and specify extraction
response = requests.post('http://localhost:5000/api/extract', {
    'file': open('document.pdf', 'rb'),
    'requirements': 'Extract the effective date and party names from this contract'
})

extracted_data = response.json()
```

## Configuration

See `.env.example` for configuration options including:
- AI model API keys
- Database settings
- Security configurations
- Performance tuning parameters

## Testing

```bash
# Run unit tests
python -m pytest tests/

# Run integration tests
python -m pytest tests/integration/

# Test with handwritten documents
python -m pytest tests/handwritten/
```

## Compliance

The system is designed to comply with:
- GDPR (General Data Protection Regulation)
- CCPA (California Consumer Privacy Act)
- Legal privilege requirements
- Industry-standard security practices

## License

[License information to be added]
