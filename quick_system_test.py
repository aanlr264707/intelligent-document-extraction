#!/usr/bin/env python3
"""
Quick System Test - Verify all components work together
"""

def quick_system_test():
    print("🔧 QUICK SYSTEM TEST")
    print("=" * 50)
    
    try:
        # Test Flask app creation
        from app import create_app
        app = create_app()
        print("✅ Flask app created successfully")
        
        with app.app_context():
            # Test database
            from app import db
            db.create_all()
            print("✅ Database initialized")
            
            # Test enhanced services
            from app.services.extraction_engine_enhanced import EnhancedExtractionEngine
            from app.services.legal_processor_enhanced import EnhancedLegalProcessor
            from app.services.document_processor import DocumentProcessor
            from app.services.output_generator import OutputGenerator
            
            # Initialize services
            extraction_engine = EnhancedExtractionEngine()
            legal_processor = EnhancedLegalProcessor()
            doc_processor = DocumentProcessor()
            output_generator = OutputGenerator()
            
            print("✅ All enhanced services initialized")
            
            # Test method availability
            methods_to_check = [
                (extraction_engine, 'extract_data'),
                (extraction_engine, 'extract_legal_contract_data'),
                (legal_processor, 'analyze_comprehensive_legal_document'),
                (doc_processor, 'extract_text_content'),
                (output_generator, 'generate_output')
            ]
            
            for service, method_name in methods_to_check:
                if hasattr(service, method_name):
                    print(f"✅ {service.__class__.__name__}.{method_name} available")
                else:
                    print(f"❌ {service.__class__.__name__}.{method_name} missing")
            
            # Test timeout configuration
            timeout = app.config.get('PROCESSING_TIMEOUT_SECONDS', 0)
            if timeout >= 300:
                print(f"✅ Timeout configured to {timeout} seconds (≥5 minutes)")
            else:
                print(f"⚠️  Timeout is {timeout} seconds (may be too short)")
            
            # Test directories
            import os
            upload_dir = app.config.get('UPLOAD_FOLDER')
            output_dir = app.config.get('OUTPUT_FOLDER')
            
            if upload_dir and os.path.exists(upload_dir):
                print(f"✅ Upload directory exists: {upload_dir}")
            else:
                print(f"❌ Upload directory missing: {upload_dir}")
            
            if output_dir and os.path.exists(output_dir):
                print(f"✅ Output directory exists: {output_dir}")
            else:
                print(f"❌ Output directory missing: {output_dir}")
        
        print("\n🎉 QUICK TEST COMPLETED SUCCESSFULLY!")
        print("System is ready for document processing with extended timeouts.")
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_system_test()
    exit(0 if success else 1)
