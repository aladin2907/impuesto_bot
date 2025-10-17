"""
Test script to verify connections to Elasticsearch and Supabase
Run this after setting up your .env file
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.elasticsearch_service import elastic_service
from app.services.supabase_service import supabase_service
from app.config.settings import settings


def main():
    """Test all service connections"""
    print("=" * 50)
    print("TuExpertoFiscal NAIL - Connection Test")
    print("=" * 50)
    print()
    
    # Validate settings
    print("1. Validating environment variables...")
    if not settings.validate():
        print("❌ Missing required environment variables!")
        print("Please check your .env file")
        return
    print("✅ Environment variables loaded")
    print()
    
    # Test Elasticsearch
    print("2. Testing Elasticsearch connection...")
    if elastic_service.connect():
        print("✅ Elasticsearch connected successfully")
    else:
        print("❌ Elasticsearch connection failed")
    print()
    
    # Test Supabase
    print("3. Testing Supabase connection...")
    if supabase_service.connect():
        print("✅ Supabase connected successfully")
    else:
        print("❌ Supabase connection failed")
    print()
    
    # Cleanup
    elastic_service.close()
    supabase_service.close()
    
    print("=" * 50)
    print("Connection test completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()

