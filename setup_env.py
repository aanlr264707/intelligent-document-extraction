#!/usr/bin/env python3
"""Environment setup script for the document extraction app"""

import os
import sys

def setup_environment():
    """Set up the environment for the document extraction app"""
    
    directories = [
        'static/uploads',
        'static/outputs',
        'logs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        try:
            os.chmod(directory, 0o755)
            print(f"✓ Created directory: {directory}")
        except OSError as e:
            print(f"⚠ Warning: Could not set permissions for {directory}: {e}")
    
    required_vars = ['SECRET_KEY', 'DATABASE_URL']
    optional_vars = ['OPENAI_API_KEY', 'REDIS_URL']
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_required:
        print(f"❌ Missing required environment variables: {', '.join(missing_required)}")
        print("Please set these in your .env file")
        return False
    
    if missing_optional:
        print(f"⚠ Missing optional environment variables: {', '.join(missing_optional)}")
        print("App will work with limited functionality")
    
    print("✓ Environment setup complete")
    return True

if __name__ == '__main__':
    if not setup_environment():
        sys.exit(1)
