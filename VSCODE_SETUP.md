# VSCode Setup Instructions for Intelligent Document Extraction App

## Prerequisites
- Python 3.11 or 3.10 (recommended - Python 3.12 has compatibility issues)
- Redis server
- VSCode with Python extension
- Git

## Environment Setup

### 1. Clone and navigate to the repository
```bash
git clone https://github.com/aanlr264707/intelligent-document-extraction.git
cd intelligent-document-extraction
```

### 2. Set up Python environment
```bash
# Install Python 3.11 if not already installed
pyenv install 3.11.0
pyenv local 3.11.0

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Install system dependencies
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
sudo apt-get install -y libmagic1
sudo apt-get install -y poppler-utils
sudo apt-get install -y redis-server

# macOS
brew install tesseract
brew install libmagic
brew install poppler
brew install redis
```

### 4. Configure environment variables
```bash
cp .env.example .env
```

Edit the `.env` file with your settings:
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///app.db
OPENAI_API_KEY=your-openai-api-key-here  # Optional for AI features
REDIS_URL=redis://localhost:6379/0
UPLOAD_FOLDER=static/uploads
OUTPUT_FOLDER=static/outputs
MAX_CONTENT_LENGTH=16777216  # 16MB
```

### 5. Run environment setup
```bash
python setup_env.py
```

### 6. Initialize database
```bash
flask db upgrade
```

## Running the Application

### 1. Start Redis server
```bash
# Ubuntu/Debian
sudo systemctl start redis-server

# macOS
brew services start redis

# Or manually
redis-server --daemonize yes
```

### 2. Start Celery worker (in separate terminal)
```bash
cd intelligent-document-extraction
source venv/bin/activate
celery -A app.celery_app worker --loglevel=info
```

### 3. Start Flask application (in separate terminal)
```bash
cd intelligent-document-extraction
source venv/bin/activate
python app.py
```

### 4. Access the application
- Web interface: http://localhost:5000
- API endpoints: http://localhost:5000/api/
- Task status: http://localhost:5000/api/task_status/<task_id>

## VSCode Configuration

### 1. Install recommended extensions
- Python (Microsoft)
- Python Docstring Generator
- autoDocstring
- GitLens
- Thunder Client (for API testing)

### 2. Configure Python interpreter
1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
2. Type "Python: Select Interpreter"
3. Select the `venv/bin/python` interpreter from your project directory

### 3. Set up debugging
Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Flask App",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/app.py",
            "console": "integratedTerminal",
            "env": {
                "FLASK_ENV": "development",
                "FLASK_DEBUG": "1"
            }
        },
        {
            "name": "Celery Worker",
            "type": "python",
            "request": "launch",
            "module": "celery",
            "args": ["-A", "app.celery_app", "worker", "--loglevel=info"],
            "console": "integratedTerminal"
        }
    ]
}
```

### 4. Configure workspace settings
Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        "venv": true
    }
}
```

## Testing the Application

### 1. Upload a document
1. Go to http://localhost:5000/upload
2. Upload a PDF, Word doc, or image file (PNG, JPG)
3. Supported formats: PDF, DOCX, DOC, PNG, JPG, JPEG

### 2. Extract data
1. Navigate to the extraction page after upload
2. Enter natural language requirements, for example:
   - "Extract names, dates, and amounts"
   - "Find contract parties, effective dates, and payment terms"
   - "Extract all financial information and key dates"
3. Select output format (JSON, CSV, or XML)
4. Enable legal analysis and risk analysis if needed
5. Submit the extraction request

### 3. View results
1. Check extraction status and results on the results page
2. Export data in JSON, CSV, or XML format using the download buttons
3. Review extracted fields, confidence scores, and legal analysis

### 4. Monitor tasks
- Use the task status endpoint: `/api/task_status/<task_id>`
- Check Celery worker logs for processing details
- Monitor Flask app logs for request handling

### 5. API Testing
Use Thunder Client or curl to test API endpoints:
```bash
# Upload document
curl -X POST -F "file=@document.pdf" http://localhost:5000/api/upload

# Start extraction
curl -X POST -H "Content-Type: application/json" \
  -d '{"document_id": 1, "natural_language_request": "Extract names and dates", "output_format": "json"}' \
  http://localhost:5000/api/extract

# Check task status
curl http://localhost:5000/api/task_status/1
```

## Troubleshooting

### Common Issues

**Redis connection errors**
- Ensure Redis server is running: `redis-cli ping` should return "PONG"
- Check Redis configuration in `.env` file
- Restart Redis: `sudo systemctl restart redis-server`

**Import errors**
- Verify all dependencies are installed: `pip list`
- Reinstall requirements: `pip install -r requirements.txt --force-reinstall`
- Check Python version compatibility (use 3.11 or 3.10)

**Database errors**
- Run database migration: `flask db upgrade`
- Clear database if needed: `python clear_db_raw.py`
- Check database file permissions

**Permission errors**
- Ensure directories are writable: `chmod 755 static/uploads static/outputs`
- Check file ownership: `chown -R $USER:$USER static/`

**Celery worker not processing tasks**
- Check Celery worker logs for errors
- Restart Celery worker
- Verify Redis connection from Celery

**OCR/Vision processing errors**
- Install Tesseract: `sudo apt-get install tesseract-ocr`
- Check image file formats are supported
- Verify poppler-utils for PDF processing

**Memory issues**
- Reduce image resolution for large files
- Monitor system memory usage
- Consider increasing swap space

### Performance Optimization

**For better extraction quality:**
- Use high-resolution, clear images
- Ensure good contrast in scanned documents
- Use PDF format when possible for text documents

**For faster processing:**
- Enable Redis caching
- Use SSD storage for uploads/outputs
- Increase Celery worker concurrency

### Development Tips

**Debugging extraction issues:**
1. Check Celery worker logs for detailed error messages
2. Use the task status endpoint to monitor progress
3. Enable debug logging in Flask app
4. Test with simple documents first

**Adding new features:**
1. Follow existing code patterns in the services directory
2. Add proper error handling and logging
3. Update database models if needed
4. Add corresponding API endpoints

**Testing changes:**
1. Use the provided test scripts in the repository
2. Test with various document types and formats
3. Verify export functionality for all formats
4. Check audit trail functionality

## Additional Resources

- Flask Documentation: https://flask.palletsprojects.com/
- Celery Documentation: https://docs.celeryproject.org/
- Redis Documentation: https://redis.io/documentation
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract

For issues or questions, check the project's GitHub repository or create an issue.
