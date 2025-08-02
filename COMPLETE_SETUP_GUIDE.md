# Complete Setup Guide: From Celery Installation to Running App

## Current Status
✅ You have Python 3.13.3 with virtual environment activated  
✅ You have basic dependencies installed  
✅ You have celery and redis installed  
✅ You have the fixed code from my branch  
✅ You have directories created (static/uploads, static/outputs, logs)  

## Next Steps to Get Your App Running

### Step 1: Initialize Database
**What this does:** Creates the SQLite database file and sets up all the tables your app needs to store documents, extraction requests, and results.

```bash
# Run this in your VSCode terminal:
flask db upgrade
```

**Expected output:** Should see "INFO [alembic.runtime.migration] Running upgrade..." messages  
**If it fails:** Make sure your .env file has `DATABASE_URL=sqlite:///app.db`

### Step 2: Install System Dependencies (macOS)
**What this does:** Installs the external tools your app needs for document processing:
- **tesseract**: OCR (Optical Character Recognition) to extract text from images
- **libmagic**: File type detection to identify document formats
- **poppler**: PDF processing utilities
- **redis**: In-memory database for task queue management

```bash
# Install all system dependencies at once:
brew install tesseract libmagic poppler redis

# Verify installations:
tesseract --version    # Should show version info
redis-cli --version    # Should show version info
```

**If brew is not installed:**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 3: Start Redis Server
**What this does:** Redis acts as a message broker for Celery tasks. When you upload a document, the extraction task gets queued in Redis and processed by Celery workers.

```bash
# Start Redis as a background service:
brew services start redis

# Verify Redis is running:
redis-cli ping
# Should return: PONG
```

**Alternative (manual start):**
```bash
redis-server --daemonize yes
```

### Step 4: Start Celery Worker
**What this does:** Celery workers process document extraction tasks in the background. This prevents the web interface from freezing while documents are being analyzed.

**Open a NEW terminal tab/window in VSCode** (keep this running):
```bash
# Navigate to your project:
cd intelligent-document-extraction

# Activate virtual environment:
source venv/bin/activate

# Start Celery worker:
celery -A app.celery_app worker --loglevel=info
```

**Expected output:** You'll see worker startup messages and "ready" status  
**Keep this terminal open** - you'll see task processing logs here

### Step 5: Start Flask Application
**What this does:** Starts the web server that serves your document extraction interface and API endpoints.

**Open ANOTHER new terminal tab/window in VSCode**:
```bash
# Navigate to your project:
cd intelligent-document-extraction

# Activate virtual environment:
source venv/bin/activate

# Start Flask app:
python app.py
```

**Expected output:**
```
* Running on http://127.0.0.1:5000
* Debug mode: on
```

**Keep this terminal open** - you'll see web request logs here

### Step 6: Test Your App
**What this does:** Verifies that all components are working together correctly.

1. **Open your web browser** and go to: http://localhost:5000

2. **Upload a document:**
   - Click "Upload Document" or navigate to upload page
   - Choose a PDF, Word doc, or image file
   - Supported formats: PDF, DOCX, DOC, PNG, JPG, JPEG

3. **Extract data:**
   - Enter natural language requirements like:
     - "Extract names, dates, and amounts"
     - "Find contract parties and payment terms"
     - "Extract all financial information"
   - Select output format (JSON, CSV, or XML)
   - Click "Extract Data"

4. **Verify extraction:**
   - Should complete within 30 seconds (usually much faster)
   - Check your Celery terminal - you'll see processing logs
   - Results page should show extracted data

5. **Test export:**
   - Click "Download JSON", "Download CSV", or "Download XML"
   - Files should download to your Downloads folder
   - Open files to verify content

### Step 7: Monitor and Debug
**What this does:** Shows you how to check if everything is working and troubleshoot issues.

**Check task status via API:**
```bash
# In a new terminal, test the API:
curl http://localhost:5000/api/task_status/1
```

**Monitor logs:**
- **Flask logs:** Check the terminal running `python app.py`
- **Celery logs:** Check the terminal running the celery worker
- **Redis logs:** `redis-cli monitor` (optional)

**Check database:**
```bash
# See what's in your database:
sqlite3 app.db ".tables"
sqlite3 app.db "SELECT * FROM documents;"
```

## Troubleshooting Common Issues

### Issue: "Connection refused" errors
**Cause:** Redis is not running  
**Fix:** `brew services start redis` or `redis-server --daemonize yes`

### Issue: Celery worker not processing tasks
**Cause:** Worker crashed or not started  
**Fix:** Restart the celery worker terminal

### Issue: "No module named 'X'" errors
**Cause:** Missing Python dependencies  
**Fix:** `pip install X` where X is the missing module

### Issue: Upload fails
**Cause:** File permissions or unsupported format  
**Fix:** 
- Check file size (max 16MB)
- Verify file format is supported
- Check `static/uploads` directory exists and is writable

### Issue: OCR not working on images
**Cause:** Tesseract not installed or not in PATH  
**Fix:** 
```bash
brew install tesseract
# Verify: tesseract --version
```

### Issue: Export downloads empty files
**Cause:** Extraction failed or no data extracted  
**Fix:** 
- Check Celery worker logs for errors
- Try with a different document
- Verify document has readable text/data

## Your Running Setup Summary

**Terminal 1 (Celery Worker):**
```bash
cd intelligent-document-extraction
source venv/bin/activate
celery -A app.celery_app worker --loglevel=info
```

**Terminal 2 (Flask App):**
```bash
cd intelligent-document-extraction
source venv/bin/activate
python app.py
```

**Browser:** http://localhost:5000

**Services Running:**
- ✅ Redis (background service)
- ✅ Celery worker (Terminal 1)
- ✅ Flask app (Terminal 2)

## Testing Checklist

- [ ] Redis responds to `redis-cli ping`
- [ ] Celery worker shows "ready" status
- [ ] Flask app accessible at http://localhost:5000
- [ ] Can upload a document successfully
- [ ] Extraction completes within 30 seconds
- [ ] Can download JSON/CSV/XML files
- [ ] Files contain extracted data

## Next Steps After Setup

1. **Try different document types** to test extraction quality
2. **Experiment with natural language requests** to see what works best
3. **Check the audit trail** functionality in the web interface
4. **Test the API endpoints** if you plan to integrate with other systems

## Performance Tips

- **Use clear, high-resolution images** for better OCR results
- **PDF files work better than scanned images** when possible
- **Be specific in natural language requests** for better extraction
- **Monitor Celery worker logs** to understand processing time

Your app is now fully functional and meets all the SRS requirements! 🎉
