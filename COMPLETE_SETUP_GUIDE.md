# 📖 Complete Setup Tutorial: Intelligent Document Extraction App

## 🎯 How to Run This App Again in VS Code (Step-by-Step)

### Prerequisites
- VS Code installed
- Python 3.10 installed
- Git installed
- Tesseract OCR installed (`brew install tesseract` on macOS)

---

## 🚀 **OPTION 1: Starting Fresh (Recommended if you don't have the code)**

### Step 1: Clone the Repository
```bash
# Open Terminal in VS Code (Terminal > New Terminal)
git clone https://github.com/aanlr264707/intelligent-document-extraction.git
cd intelligent-document-extraction
```

### Step 2: Checkout the Working Branch
```bash
git checkout devin/1754336632-fix-extraction-python310
```

### Step 3: Open in VS Code
```bash
# Open the project in VS Code
code .
```

---

## 🔄 **OPTION 2: If You Already Have the Code**

### Step 1: Navigate to Project
```bash
# In Terminal, go to your project directory
cd /Users/kumar/intelligent-document-extraction
```

### Step 2: Open in VS Code
```bash
code .
```

### Step 3: Pull Latest Changes (if needed)
```bash
git pull origin devin/1754336632-fix-extraction-python310
```

---

## 🐍 **Python Environment Setup**

### Step 1: Activate the Virtual Environment
In VS Code terminal:
```bash
# Activate the existing virtual environment
source venv_310/bin/activate

# You should see (venv_310) in your terminal prompt
```

### Step 2: Verify Python Environment
```bash
# Check Python version (should be 3.10.x)
python --version

# Check if in virtual environment
which python
# Should show: /Users/kumar/intelligent-document-extraction/venv_310/bin/python
```

### Step 3: Install Dependencies (if needed)
```bash
# Install requirements
pip install -r requirements.txt
```

---

## ✅ **System Validation**

### Step 1: Run System Validation Test
```bash
# This tests all components
python system_validation.py
```

**Expected Output:**
```
INTELLIGENT DOCUMENT EXTRACTION - SYSTEM VALIDATION
============================================================
✅ Tesseract OCR: PASSED
✅ Legal Processor: PASSED  
✅ Document Processor: PASSED
✅ Extraction Engine: PASSED
✅ Flask Application: PASSED

Overall: 5/5 tests passed
🎉 ALL SYSTEMS OPERATIONAL!
```

### Step 2: Test Individual Components (Optional)
```bash
# Test OCR capability
python test_open_source_models.py

# Test legal processor specifically
python -c "
from app.services.legal_processor import LegalProcessor
processor = LegalProcessor()
result = processor.analyze_legal_document('This agreement may be terminated with 30 days notice.', {})
print('Legal processor working:', len(result.get('clauses', [])) > 0)
"
```

---

## 🌐 **Running the Web Application**

### Step 1: Start the Flask App
```bash
# Make sure you're in the project directory with virtual environment active
python app.py
```

**Expected Output:**
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

### Step 2: Access the Application
- Open your web browser
- Go to: `http://localhost:5000` or `http://127.0.0.1:5000`
- You should see the document upload interface

### Step 3: Test Document Upload
1. Upload a PDF document
2. Select extraction type (Legal Document Analysis)
3. Click "Extract Data"
4. View results with extracted clauses and obligations

---

## 🛠️ **VS Code Configuration**

### Step 1: Select Python Interpreter
1. Press `Cmd+Shift+P` (macOS) to open command palette
2. Type "Python: Select Interpreter"
3. Choose: `/Users/kumar/intelligent-document-extraction/venv_310/bin/python`

### Step 2: Configure Terminal (Optional)
1. Go to VS Code Settings (`Cmd+,`)
2. Search for "terminal integrated shell"
3. Make sure it's set to your default shell (zsh)

### Step 3: Install Useful Extensions (Optional)
- Python (Microsoft)
- Pylance (Microsoft) 
- Flask Snippets
- GitLens

---

## 🐛 **Troubleshooting Common Issues**

### Issue 1: "Command not found: python"
**Solution:**
```bash
# Make sure virtual environment is activated
source venv_310/bin/activate

# Or use full path
/Users/kumar/intelligent-document-extraction/venv_310/bin/python app.py
```

### Issue 2: "Module not found" errors
**Solution:**
```bash
# Reinstall requirements
pip install -r requirements.txt

# Or specific packages
pip install flask pytesseract pillow
```

### Issue 3: App hanging on startup
**Solution:**
```bash
# The system now has lazy loading, but if issues persist:
python system_validation.py

# Check if all tests pass
```

### Issue 4: Tesseract not found
**Solution:**
```bash
# Install Tesseract (macOS)
brew install tesseract

# Verify installation
tesseract --version
```

### Issue 5: Database issues
**Solution:**
```bash
# Initialize database
flask db upgrade

# Or reset database
rm instance/intelligent_extraction.db
flask db upgrade
```

---

## 🔍 **Development Commands**

### Running Tests
```bash
# System validation
python system_validation.py

# Open source models test
python test_open_source_models.py

# Specific component test
python -c "from app.services.legal_processor import LegalProcessor; print('✅ Working')"
```

### Database Management
```bash
# Create migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade

# View current revision
flask db current
```

### Development Server
```bash
# Run with debug mode
python app.py

# Or using Flask command
flask run --debug
```

---

## 📁 **Project Structure Quick Reference**
```
intelligent-document-extraction/
├── app.py                          # Main Flask application
├── system_validation.py            # System health check
├── requirements.txt                # Python dependencies
├── venv_310/                       # Virtual environment
├── app/
│   ├── services/                   # Core processing services
│   │   ├── legal_processor.py      # Legal document analysis
│   │   ├── extraction_engine.py    # Main orchestrator
│   │   ├── document_processor.py   # File handling
│   │   └── vision_processor.py     # OCR processing
│   ├── models/                     # Database models
│   ├── views/                      # Web routes
│   └── static/uploads/             # Uploaded files
├── templates/                      # HTML templates
└── instance/                       # Database files
```

---

## 🎉 **Quick Start Checklist**

- [ ] Navigate to project directory
- [ ] Open in VS Code (`code .`)
- [ ] Activate virtual environment (`source venv_310/bin/activate`)
- [ ] Run system validation (`python system_validation.py`)
- [ ] Start Flask app (`python app.py`)
- [ ] Open browser to `http://localhost:5000`
- [ ] Test with a PDF document

---

## 📞 **Need Help?**

If you encounter any issues:

1. **Check system validation first**: `python system_validation.py`
2. **Verify virtual environment**: `which python` should show venv_310 path
3. **Check dependencies**: `pip list` to see installed packages
4. **Review logs**: Look at terminal output for error messages

The system is now stable and should work reliably! 🚀
