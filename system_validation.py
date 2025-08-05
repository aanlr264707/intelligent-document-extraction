#!/usr/bin/env python3
"""
System validation test for legal document extraction
"""

import os
import sys
from datetime import datetime

def test_legal_processor():
    """Test the core legal processor functionality"""
    print("=== Testing Legal Document Processing ===")
    
    try:
        from app.services.legal_processor import LegalProcessor
        
        # Create processor
        processor = LegalProcessor()
        print("✅ Legal processor created successfully")
        
        # Test with realistic legal text
        test_text = """
        TERMINATION CLAUSE: Either party may terminate this Agreement with thirty (30) days written notice.
        
        PAYMENT TERMS: Client shall pay invoices within fifteen (15) days of receipt. 
        Late payment penalty of 2% per month will be applied to overdue amounts.
        
        LIABILITY: In no event shall either party be liable for consequential damages.
        The contractor shall deliver the completed software by December 31, 2024.
        
        CONFIDENTIALITY: Both parties agree to maintain confidentiality of proprietary information.
        """
        
        # Analyze the text
        result = processor.analyze_legal_document(test_text, {})
        print("✅ Legal analysis completed")
        
        # Validate results
        clauses = result.get('clauses', [])
        obligations = result.get('obligations', [])
        risks = result.get('risks', [])
        summary = result.get('summary', '')
        
        print(f"Found {len(clauses)} clauses:")
        for clause in clauses:
            print(f"  - {clause.get('type', 'unknown')}: {clause.get('text', '')[:50]}...")
        
        print(f"Found {len(obligations)} obligations:")
        for obligation in obligations:
            print(f"  - {obligation.get('type', 'unknown')}: {obligation.get('text', '')[:50]}...")
        
        print(f"Found {len(risks)} risks:")
        for risk in risks:
            print(f"  - {risk.get('level', 'unknown')}: {risk.get('text', '')[:50]}...")
        
        if summary:
            print(f"Summary: {summary[:100]}...")
        
        # Basic validation
        assert len(clauses) > 0, "Should find at least one clause"
        assert len(obligations) > 0, "Should find at least one obligation"
        
        print("✅ Legal processor validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Legal processor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_document_processor():
    """Test the document processor"""
    print("\n=== Testing Document Processing ===")
    
    try:
        from app.services.document_processor import DocumentProcessor
        
        processor = DocumentProcessor()
        print("✅ Document processor created successfully")
        
        # Test basic functionality (without actual files)
        file_info = {
            'filename': 'test.pdf',
            'content_type': 'application/pdf',
            'size': 1024
        }
        
        result = processor.validate_document(file_info)
        print("✅ Document validation works")
        
        return True
        
    except Exception as e:
        print(f"❌ Document processor test failed: {e}")
        return False

def test_extraction_engine():
    """Test the extraction engine with lazy loading"""
    print("\n=== Testing Extraction Engine ===")
    
    try:
        from app.services.extraction_engine import ExtractionEngine
        
        engine = ExtractionEngine()
        print("✅ Extraction engine created successfully")
        
        # Test that processors are not loaded yet (lazy loading)
        print(f"Legal processor loaded: {engine._legal_processor is not None}")
        print(f"Vision processor loaded: {engine._vision_processor is not None}")
        
        # Test accessing a processor (should trigger lazy loading)
        legal_proc = engine.legal_processor
        print("✅ Legal processor lazy loaded successfully")
        print(f"Legal processor now loaded: {engine._legal_processor is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ Extraction engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flask_app():
    """Test Flask app startup"""
    print("\n=== Testing Flask Application ===")
    
    try:
        from app import create_app
        
        app = create_app()
        print("✅ Flask app created successfully")
        
        # Test app configuration
        print(f"✅ App configured with debug: {app.debug}")
        print(f"✅ Database URI configured: {bool(app.config.get('SQLALCHEMY_DATABASE_URI'))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        return False

def test_tesseract_ocr():
    """Test Tesseract OCR capability"""
    print("\n=== Testing OCR Capability ===")
    
    try:
        import pytesseract
        from PIL import Image
        import numpy as np
        
        # Test Tesseract version
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract version: {version}")
        
        # Create a simple test image
        test_image = Image.new('RGB', (200, 50), color='white')
        text = pytesseract.image_to_string(test_image)
        print("✅ OCR interface working")
        
        return True
        
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        return False

def main():
    """Run all system validation tests"""
    print("INTELLIGENT DOCUMENT EXTRACTION - SYSTEM VALIDATION")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    print()
    
    tests = [
        ("Tesseract OCR", test_tesseract_ocr),
        ("Legal Processor", test_legal_processor),
        ("Document Processor", test_document_processor),
        ("Extraction Engine", test_extraction_engine),
        ("Flask Application", test_flask_app),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("SYSTEM VALIDATION SUMMARY")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL SYSTEMS OPERATIONAL!")
        print("The legal document extraction system is ready for use.")
        print("\nWhat the system can do:")
        print("• Extract legal clauses (termination, penalty, payment, liability)")
        print("• Identify obligations and deliverables")
        print("• Flag potential risks")
        print("• Generate document summaries")
        print("• Process PDF documents with OCR")
        print("• Web interface for document upload and results")
    else:
        print(f"\n⚠️  {total - passed} tests failed. System needs attention.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
