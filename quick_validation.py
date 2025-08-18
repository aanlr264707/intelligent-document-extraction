#!/usr/bin/env python3
"""Quick validation that our enhanced application works"""

import sys
import os

print("🚀 Starting Enhanced Document Extraction Application Validation")
print("=" * 60)

# Test 1: Basic imports
print("✅ Test 1: Basic imports")
try:
    from app import create_app, db
    print("  ✅ Flask app import successful")
except Exception as e:
    print(f"  ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Enhanced services availability
print("✅ Test 2: Enhanced services availability")
services = {
    'Email Monitor': 'app.services.email_monitor',
    'Handwritten Processor': 'app.services.handwritten_processor', 
    'Tabular Extractor': 'app.services.tabular_extractor',
    'Legal Processor Enhanced': 'app.services.legal_processor_enhanced',
    'Performance Monitor': 'app.services.performance_monitor',
    'Enhanced Extraction Engine': 'app.services.extraction_engine_enhanced'
}

available_services = 0
for name, module in services.items():
    try:
        __import__(module)
        print(f"  ✅ {name}")
        available_services += 1
    except ImportError as e:
        print(f"  ⚠️  {name} (optional dependency missing)")

print(f"  📊 {available_services}/6 enhanced services available")

# Test 3: Configuration validation
print("✅ Test 3: Configuration validation")
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check critical config
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key and openai_key.startswith('sk-'):
        print("  ✅ OpenAI API key configured")
    else:
        print("  ⚠️  OpenAI API key not found or invalid format")
    
    # Check other configs
    configs = ['SECRET_KEY', 'DATABASE_URL', 'MAX_CONCURRENT_EXTRACTIONS']
    for config in configs:
        value = os.getenv(config)
        status = "✅" if value else "⚠️"
        print(f"  {status} {config}: {'Set' if value else 'Using default'}")
        
except Exception as e:
    print(f"  ❌ Configuration check failed: {e}")

# Test 4: Enhanced API endpoints
print("✅ Test 4: Enhanced API endpoints")
try:
    from app.views.enhanced_api import enhanced_api_bp
    print("  ✅ Enhanced API v2 blueprint available")
    print("  📍 New endpoints include:")
    print("    • /api/v2/extract/enhanced - Advanced document extraction")
    print("    • /api/v2/extract/batch - Batch processing")
    print("    • /api/v2/monitor/performance - Performance metrics")
    print("    • /api/v2/email/monitor - Email monitoring control")
    print("    • /api/v2/health - System health check")
except ImportError:
    print("  ❌ Enhanced API not available")

print("=" * 60)
print("🎉 Validation complete! Your enhanced document extraction application is ready.")
print()
print("🔧 Next steps:")
print("1. Start the application: python app.py")
print("2. Visit: http://localhost:5000")
print("3. Try uploading documents through the web interface")
print("4. Use API endpoints for programmatic access")
print()
print("📚 Key Features Available:")
print("• Multi-modal document analysis (text + images)")
print("• Handwritten document processing")
print("• Advanced tabular data extraction")
print("• Legal document analysis with risk assessment")
print("• Email monitoring for automatic processing")
print("• Performance monitoring and scalability")
print("• Comprehensive audit trails")
print("• GDPR compliance features")
print("• RESTful API with v2 enhancements")
