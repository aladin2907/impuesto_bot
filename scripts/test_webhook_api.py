#!/usr/bin/env python3
"""
Script to test the webhook API
Run this after starting the API server to verify it's working correctly
"""

import requests
import json
import time
from datetime import datetime

# API Configuration
API_BASE_URL = "http://localhost:8000"
API_TIMEOUT = 30


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(test_name, success, response=None, error=None):
    """Print test result"""
    status = "✅ PASSED" if success else "❌ FAILED"
    print(f"\n{status} - {test_name}")
    
    if response:
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response Preview: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
            except:
                print(f"Response: {response.text[:200]}...")
    
    if error:
        print(f"Error: {error}")


def test_health_check():
    """Test health check endpoint"""
    print_section("Testing Health Check Endpoint")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=API_TIMEOUT)
        
        if response.status_code in [200, 503]:
            data = response.json()
            print_result("Health Check", True, response)
            
            # Print detailed status
            print("\nService Status:")
            print(f"  - Elasticsearch: {'✅' if data.get('elasticsearch_connected') else '❌'}")
            print(f"  - Supabase: {'✅' if data.get('supabase_connected') else '❌'}")
            print(f"  - LLM: {'✅' if data.get('llm_initialized') else '❌'}")
            
            return data.get('status') == 'healthy'
        else:
            print_result("Health Check", False, response)
            return False
            
    except Exception as e:
        print_result("Health Check", False, error=str(e))
        return False


def test_search_minimal():
    """Test search with minimal request"""
    print_section("Testing Search - Minimal Request")
    
    request_data = {
        "user_context": {
            "channel_type": "test",
            "channel_user_id": "test-user-123"
        },
        "query_text": "¿Qué es el IVA?"
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/search",
            json=request_data,
            timeout=API_TIMEOUT
        )
        elapsed_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            success = data.get('success', False)
            
            print_result("Search Minimal", success, response)
            
            if success:
                print(f"\nResponse Details:")
                print(f"  - User ID: {data.get('user_id')}")
                print(f"  - Session ID: {data.get('session_id')}")
                print(f"  - Results Count: {len(data.get('results', []))}")
                print(f"  - Has LLM Response: {'✅' if data.get('generated_response') else '❌'}")
                print(f"  - Processing Time: {data.get('processing_time_ms')}ms")
                print(f"  - Actual Request Time: {elapsed_time:.0f}ms")
                
                if data.get('generated_response'):
                    print(f"\nGenerated Response Preview:")
                    print(f"  {data['generated_response'][:200]}...")
            
            return success
        else:
            print_result("Search Minimal", False, response)
            return False
            
    except Exception as e:
        print_result("Search Minimal", False, error=str(e))
        return False


def test_search_with_filters():
    """Test search with filters"""
    print_section("Testing Search - With Filters")
    
    request_data = {
        "user_context": {
            "channel_type": "test",
            "channel_user_id": "test-user-456",
            "user_metadata": {
                "username": "test_user",
                "first_name": "Test"
            }
        },
        "query_text": "¿Cuándo tengo que presentar el modelo 303?",
        "filters": {
            "source_types": ["calendar", "aeat"],
            "tax_types": ["IVA"],
            "only_tax_related": True,
            "minimum_quality_score": 2.0
        },
        "top_k": 5,
        "generate_response": True
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/search",
            json=request_data,
            timeout=API_TIMEOUT
        )
        elapsed_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            success = data.get('success', False)
            
            print_result("Search With Filters", success, response)
            
            if success:
                print(f"\nFiltered Results:")
                print(f"  - Results Count: {len(data.get('results', []))}")
                print(f"  - Processing Time: {data.get('processing_time_ms')}ms")
                
                # Show source types in results
                if data.get('results'):
                    source_types = [r.get('source_type') for r in data['results']]
                    print(f"  - Source Types: {', '.join(set(filter(None, source_types)))}")
            
            return success
        else:
            print_result("Search With Filters", False, response)
            return False
            
    except Exception as e:
        print_result("Search With Filters", False, error=str(e))
        return False


def test_search_without_response():
    """Test search without LLM response generation"""
    print_section("Testing Search - Without LLM Response")
    
    request_data = {
        "user_context": {
            "channel_type": "test",
            "channel_user_id": "test-user-789"
        },
        "query_text": "IRPF autónomos",
        "top_k": 3,
        "generate_response": False
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/search",
            json=request_data,
            timeout=API_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            success = data.get('success', False) and not data.get('generated_response')
            
            print_result("Search Without Response", success, response)
            
            if success:
                print(f"\nResults:")
                print(f"  - Results Count: {len(data.get('results', []))}")
                print(f"  - Has LLM Response: {'❌' if not data.get('generated_response') else '✅ (unexpected!)'}")
            
            return success
        else:
            print_result("Search Without Response", False, response)
            return False
            
    except Exception as e:
        print_result("Search Without Response", False, error=str(e))
        return False


def test_search_validation_errors():
    """Test validation error handling"""
    print_section("Testing Validation Errors")
    
    # Test 1: Empty query
    print("\nTest 1: Empty query text")
    try:
        response = requests.post(
            f"{API_BASE_URL}/search",
            json={
                "user_context": {"channel_type": "test", "channel_user_id": "test"},
                "query_text": ""
            },
            timeout=API_TIMEOUT
        )
        success = response.status_code == 422
        print_result("Empty Query Validation", success, response)
    except Exception as e:
        print_result("Empty Query Validation", False, error=str(e))
    
    # Test 2: Missing user_context
    print("\nTest 2: Missing user_context")
    try:
        response = requests.post(
            f"{API_BASE_URL}/search",
            json={"query_text": "test query"},
            timeout=API_TIMEOUT
        )
        success = response.status_code == 422
        print_result("Missing User Context Validation", success, response)
    except Exception as e:
        print_result("Missing User Context Validation", False, error=str(e))
    
    # Test 3: Invalid top_k
    print("\nTest 3: Invalid top_k (exceeds max)")
    try:
        response = requests.post(
            f"{API_BASE_URL}/search",
            json={
                "user_context": {"channel_type": "test", "channel_user_id": "test"},
                "query_text": "test",
                "top_k": 100  # Exceeds max of 20
            },
            timeout=API_TIMEOUT
        )
        success = response.status_code == 422
        print_result("Invalid Top K Validation", success, response)
    except Exception as e:
        print_result("Invalid Top K Validation", False, error=str(e))


def test_stats_endpoint():
    """Test stats endpoint"""
    print_section("Testing Stats Endpoint")
    
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=API_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            print_result("Stats Endpoint", True, response)
            
            print("\nStats Details:")
            print(f"  - Status: {data.get('status')}")
            print(f"  - Services: {json.dumps(data.get('services', {}), indent=4)}")
            
            return True
        else:
            print_result("Stats Endpoint", False, response)
            return False
            
    except Exception as e:
        print_result("Stats Endpoint", False, error=str(e))
        return False


def main():
    """Run all tests"""
    print("\n" + "🔥" * 30)
    print("  TuExpertoFiscal API Test Suite")
    print("🔥" * 30)
    print(f"\nTesting API at: {API_BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "Health Check": test_health_check(),
        "Search Minimal": test_search_minimal(),
        "Search With Filters": test_search_with_filters(),
        "Search Without Response": test_search_without_response(),
        "Stats Endpoint": test_stats_endpoint()
    }
    
    # Validation errors test (doesn't contribute to pass/fail)
    test_search_validation_errors()
    
    # Summary
    print_section("Test Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed")
    print("\nDetailed Results:")
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status} - {test_name}")
    
    if passed == total:
        print("\n🎉 All tests passed! API is working correctly!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the logs above.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

