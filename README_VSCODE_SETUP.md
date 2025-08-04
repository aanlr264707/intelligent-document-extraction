# VSCode Setup Guide for Intelligent Document Extraction

This comprehensive guide will walk you through setting up the Intelligent Document Extraction application in VSCode with Python 3.10.

## Prerequisites

- Python 3.10 installed on your system
- VSCode installed
- Git installed
- Basic familiarity with command line operations

## Step 1: Clone the Repository

1. Open VSCode
2. Open the integrated terminal (`Ctrl+`` ` or `View > Terminal`)
3. Navigate to your desired directory and clone the repository:

```bash
git clone https://github.com/aanlr264707/intelligent-document-extraction.git
cd intelligent-document-extraction
```

## Step 2: Open Project in VSCode

1. In VSCode, go to `File > Open Folder`
2. Select the `intelligent-document-extraction` folder
3. VSCode will open the project

## Step 3: Install VSCode Extensions

Install these recommended extensions for the best development experience:

1. **Python** (Microsoft) - Essential for Python development
2. **Python Debugger** (Microsoft) - For debugging Python applications
3. **Pylance** (Microsoft) - Advanced Python language support
4. **autoDocstring** (Nils Werner) - For generating docstrings
5. **GitLens** (GitKraken) - Enhanced Git capabilities
6. **Thunder Client** (RangaV) - For testing API endpoints

To install extensions:
- Press `Ctrl+Shift+X` to open Extensions view
- Search for each extension and click "Install"

## Step 4: Set Up Python 3.10 Virtual Environment

1. Open the integrated terminal in VSCode (`Ctrl+`` `)
2. Verify Python 3.10 is available:

```bash
python3.10 --version
```

3. Create a virtual environment:

```bash
python3.10 -m venv venv_310
```

4. Activate the virtual environment:

**On Linux/macOS:**
```bash
source venv_310/bin/activate
```

**On Windows:**
```bash
venv_310\Scripts\activate
```

5. Verify the Python version in the virtual environment:

```bash
python --version
```

You should see `Python 3.10.x`.

## Step 5: Configure VSCode Python Interpreter

1. Press `Ctrl+Shift+P` to open the Command Palette
2. Type "Python: Select Interpreter"
3. Select the interpreter from your virtual environment:
   - Look for `./venv_310/bin/python` (Linux/macOS) or `.\venv_310\Scripts\python.exe` (Windows)
   - If not visible, click "Enter interpreter path..." and browse to the python executable in your venv_310 folder

## Step 6: Install Dependencies

With the virtual environment activated, install the required packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This may take several minutes as it installs AI/ML libraries like PyTorch, Transformers, and OpenCV.

## Step 7: Set Up Environment Variables

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Open the `.env` file in VSCode
3. Configure the following variables:

```env
# Application Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here

# Database Configuration (SQLite is fine for development)
DATABASE_URL=sqlite:///intelligent_extraction.db

# AI Model Configuration (Optional - leave empty to use local models)
OPENAI_API_KEY=
HUGGINGFACE_API_KEY=

# OCR Configuration
TESSERACT_PATH=/usr/bin/tesseract

# Performance Configuration
MAX_DOCUMENT_SIZE_MB=50
PROCESSING_TIMEOUT_SECONDS=60
MAX_CONCURRENT_EXTRACTIONS=5

# Redis/Celery Configuration (Optional - for background processing)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_ACCEPT_CONTENT=['json']
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
CELERY_TIMEZONE=UTC
CELERY_ENABLE_UTC=True
CELERYD_TASK_SOFT_TIME_LIMIT=110
CELERYD_TASK_TIME_LIMIT=120
```

**Note:** You can leave API keys empty - the application will fall back to local models.

### Background Processing Options

The application supports two approaches for background processing:

1. **Threading (Default)**: Uses Python threading for extraction tasks. No additional setup required.
2. **Celery (Optional)**: Uses Redis and Celery for distributed task processing. Better for production environments.

#### To use Celery instead of threading:

**Install Redis:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server

# macOS (with Homebrew)
brew install redis

# Start Redis service
sudo systemctl start redis-server  # Linux
brew services start redis          # macOS
```

**Start Celery Worker:**
```bash
# In a separate terminal, with virtual environment activated
celery -A app.celery_app worker --loglevel=info
```

**Configure the application:**
- Ensure all Celery configuration variables are set in your `.env` file
- The application will automatically detect and use Celery if properly configured

## Step 8: Install System Dependencies

### For OCR functionality (Tesseract):

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng
```

**macOS (with Homebrew):**
```bash
brew install tesseract
```

**Windows:**
Download and install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki

## Step 9: Initialize the Database

Run the database migrations:

```bash
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('Database initialized successfully')"
```

## Step 10: Configure VSCode Settings

Create a `.vscode/settings.json` file in your project root:

```json
{
    "python.defaultInterpreterPath": "./venv_310/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/venv_310": true
    },
    "python.analysis.extraPaths": ["./app"],
    "python.envFile": "${workspaceFolder}/.env"
}
```

## Step 11: Configure Launch Configuration for Debugging

Create a `.vscode/launch.json` file:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Flask App",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/app.py",
            "env": {
                "FLASK_ENV": "development",
                "FLASK_DEBUG": "1"
            },
            "args": [],
            "jinja": true,
            "console": "integratedTerminal"
        },
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        }
    ]
}
```

## Step 12: Test the Installation

1. **Run the application:**

```bash
python app.py
```

You should see output like:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

2. **Test in browser:**
   - Open http://127.0.0.1:5000 in your browser
   - You should see the application homepage

3. **Test document upload:**
   - Upload a test document (PDF, DOCX, etc.)
   - Try the extraction functionality

## Step 13: Development Workflow

### Running the Application

**Method 1: Terminal**
```bash
source venv_310/bin/activate  # Activate virtual environment
python app.py
```

**Method 2: VSCode Debugger**
- Press `F5` or go to `Run > Start Debugging`
- Select "Flask App" configuration

### Testing API Endpoints

Use Thunder Client extension or curl:

```bash
# Test document upload
curl -X POST -F "file=@test_document.pdf" http://localhost:5000/api/upload

# Test extraction
curl -X POST -F "document_id=1" -F "requirements=Extract contract dates" http://localhost:5000/api/extract
```

### Debugging

1. Set breakpoints by clicking in the left margin of code lines
2. Press `F5` to start debugging
3. Use the Debug Console to inspect variables
4. Step through code with `F10` (step over) and `F11` (step into)

## Step 14: Common Issues and Troubleshooting

### Issue: "Module not found" errors
**Solution:** Ensure the virtual environment is activated and all dependencies are installed:
```bash
source venv_310/bin/activate
pip install -r requirements.txt
```

### Issue: Tesseract not found
**Solution:** Install Tesseract and update the path in `.env`:
```env
TESSERACT_PATH=/usr/bin/tesseract  # Linux/macOS
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe  # Windows
```

### Issue: Database errors
**Solution:** Reinitialize the database:
```bash
rm intelligent_extraction.db  # Remove existing database
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### Issue: Port already in use
**Solution:** Kill the process using port 5000:
```bash
# Linux/macOS
lsof -ti:5000 | xargs kill -9

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Issue: Extraction takes too long or hangs
**Solution:** Check the logs and ensure timeout settings in `.env`:
```env
PROCESSING_TIMEOUT_SECONDS=60
```

## Step 15: Development Best Practices

### Code Formatting
Install and configure Black formatter:
```bash
pip install black
```

Format code: `Ctrl+Shift+I` or `Format Document`

### Git Workflow
1. Create feature branches: `git checkout -b feature/your-feature`
2. Commit regularly with descriptive messages
3. Push to remote: `git push origin feature/your-feature`

### Testing
Run tests (if available):
```bash
python -m pytest tests/
```

### Environment Management
- Always activate the virtual environment before working
- Keep requirements.txt updated when adding new dependencies
- Use `.env` for environment-specific configuration

## Step 16: Application Features

### Document Upload
- Supports PDF, DOCX, images, and handwritten documents
- Drag and drop interface
- Automatic file type detection

### Extraction Features
- Natural language extraction requests
- Multi-modal analysis (text + visual elements)
- Legal document processing with clause identification
- Risk analysis and flagging
- Tabular data extraction

### Output Formats
- JSON for structured data
- CSV for tabular data
- XML for enterprise integration

### Advanced Features
- Audit trails for compliance
- User feedback loops for accuracy improvement
- Dynamic field mapping
- Template reuse for recurring document types

## Step 17: API Documentation

### Key Endpoints

**Upload Document:**
```
POST /api/upload
Content-Type: multipart/form-data
Body: file=<document>
```

**Extract Data:**
```
POST /api/extract
Content-Type: multipart/form-data
Body: 
  document_id=<id>
  requirements=<natural language description>
  output_format=<json|csv|xml>
```

**Check Status:**
```
GET /api/status/<extraction_id>
```

**Get Results:**
```
GET /api/results/<extraction_id>
```

## Step 18: Performance Optimization

### For Development
- Use local models when OpenAI API is not available
- Adjust timeout settings based on document complexity
- Monitor memory usage with large documents

### For Production
- Configure Redis for Celery task queue
- Set up proper logging and monitoring
- Implement rate limiting for API endpoints
- Use environment-specific configuration

## Conclusion

You now have a fully functional development environment for the Intelligent Document Extraction application. The application supports:

- Multi-format document processing
- AI-powered extraction with fallback to local models
- Legal document analysis
- Export/import functionality
- Comprehensive audit trails

For additional help or issues, refer to the application logs and error messages, which provide detailed debugging information.
