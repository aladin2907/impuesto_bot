#!/usr/bin/env python3
"""
Diagnostic script to check all service connections
Run this on the server to diagnose the issue
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

def check_env_vars():
    """Check if all required environment variables are set"""
    print("\n" + "="*60)
    print("🔍 CHECKING ENVIRONMENT VARIABLES")
    print("="*60)
    
    required_vars = {
        'Elasticsearch': ['ELASTIC_CLOUD_ID', 'ELASTIC_API_KEY'],
        'Supabase': ['SUPABASE_URL', 'SUPABASE_DB_URL', 'SUPABASE_KEY'],
        'LLM': ['LLM_PROVIDER', 'OPENAI_API_KEY']
    }
    
    all_good = True
    for service, vars_list in required_vars.items():
        print(f"\n{service}:")
        for var in vars_list:
            value = os.getenv(var)
            if value:
                # Mask sensitive data
                if 'KEY' in var or 'URL' in var:
                    masked = value[:20] + '...' if len(value) > 20 else value
                else:
                    masked = value
                print(f"  ✅ {var} = {masked}")
            else:
                print(f"  ❌ {var} is NOT SET")
                all_good = False
    
    return all_good


def check_elasticsearch():
    """Test Elasticsearch connection"""
    print("\n" + "="*60)
    print("🔍 TESTING ELASTICSEARCH CONNECTION")
    print("="*60)
    
    try:
        from app.services.elasticsearch_service import elastic_service
        
        print("\n1. Attempting to connect...")
        connected = elastic_service.connect()
        
        if connected:
            print("  ✅ Connected successfully!")
            
            # Try to get cluster info
            if elastic_service.client:
                info = elastic_service.client.info()
                print(f"\n2. Cluster info:")
                print(f"  - Version: {info['version']['number']}")
                print(f"  - Cluster name: {info['cluster_name']}")
                
                # Try to list indices
                indices = elastic_service.client.cat.indices(format='json')
                print(f"\n3. Available indices:")
                for idx in indices:
                    print(f"  - {idx['index']} ({idx['docs.count']} docs)")
                
                return True
        else:
            print("  ❌ Connection failed!")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_supabase():
    """Test Supabase connection"""
    print("\n" + "="*60)
    print("🔍 TESTING SUPABASE CONNECTION")
    print("="*60)
    
    try:
        from app.services.supabase_service import supabase_service
        
        print("\n1. Attempting to connect...")
        connected = supabase_service.connect()
        
        if connected:
            print("  ✅ Connected successfully!")
            
            # Try to query database
            cursor = supabase_service.connection.cursor()
            
            print("\n2. Testing database access...")
            cursor.execute("SELECT COUNT(*) as count FROM users")
            result = cursor.fetchone()
            print(f"  - Users table: {result['count']} users")
            
            cursor.execute("SELECT COUNT(*) as count FROM dialogue_sessions")
            result = cursor.fetchone()
            print(f"  - Sessions table: {result['count']} sessions")
            
            cursor.execute("SELECT COUNT(*) as count FROM messages")
            result = cursor.fetchone()
            print(f"  - Messages table: {result['count']} messages")
            
            return True
        else:
            print("  ❌ Connection failed!")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_llm():
    """Test LLM service"""
    print("\n" + "="*60)
    print("🔍 TESTING LLM SERVICE")
    print("="*60)
    
    try:
        from app.services.llm.llm_service import llm_service
        
        print("\n1. Attempting to initialize...")
        initialized = llm_service.initialize()
        
        if initialized:
            print("  ✅ Initialized successfully!")
            print(f"  - Provider: {os.getenv('LLM_PROVIDER')}")
            print(f"  - Model: {os.getenv('LLM_MODEL')}")
            return True
        else:
            print("  ❌ Initialization failed!")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search():
    """Test actual search functionality"""
    print("\n" + "="*60)
    print("🔍 TESTING SEARCH SERVICE")
    print("="*60)
    
    try:
        from app.services.search_service import search_service
        
        print("\n1. Initializing search service...")
        initialized = search_service.initialize()
        
        if not initialized:
            print("  ❌ Search service initialization failed!")
            return False
        
        print("  ✅ Search service initialized")
        
        # Check health
        print("\n2. Health check:")
        health = search_service.health_check()
        for service, status in health.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {service}: {status}")
        
        return all(health.values())
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*60)
    print("🚀 TuExpertoFiscal - CONNECTION DIAGNOSTICS")
    print("="*60)
    
    results = {
        'Environment Variables': check_env_vars(),
        'Elasticsearch': check_elasticsearch(),
        'Supabase': check_supabase(),
        'LLM Service': check_llm(),
        'Search Service': test_search()
    }
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    for service, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {service}: {'PASS' if status else 'FAIL'}")
    
    all_pass = all(results.values())
    
    if all_pass:
        print("\n🎉 All services are working correctly!")
    else:
        print("\n⚠️  Some services failed. Please check the details above.")
        print("\n💡 Common fixes:")
        print("  1. Check .env file has all required variables")
        print("  2. Verify Elasticsearch credentials are valid")
        print("  3. Check Supabase URL and database URL are correct")
        print("  4. Ensure network connectivity to external services")
        print("  5. Check firewall settings if running on server")
    
    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())


