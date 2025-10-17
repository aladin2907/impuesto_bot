#!/usr/bin/env python3
"""
Детальный тест подключения к Elasticsearch
"""

import os
import sys
from pathlib import Path

# Добавляем корневую папку в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from elasticsearch import Elasticsearch
from app.config.settings import Settings
import traceback
import requests

def test_with_requests():
    """Тест через requests для сравнения"""
    print("=== Тест через requests ===")
    
    url = "https://36d0e937f1fd4309a2cb624f5f11bed1.us-central1.gcp.cloud.es.io:443"
    headers = {
        "Authorization": "ApiKey eFA2NXI1a0JUb04tRGFBTzktajQ6NnVSaHNaRmZSTUdNRUd2eWg4eERMUQ=="
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ requests работает!")
            return True
        else:
            print(f"❌ requests failed: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ requests error: {e}")
        return False

def test_elasticsearch_client():
    """Тест через elasticsearch client"""
    print("\n=== Тест через elasticsearch client ===")
    
    s = Settings()
    print(f"Cloud ID: {s.ELASTIC_CLOUD_ID}")
    print(f"API Key (first 20): {s.ELASTIC_API_KEY[:20] if s.ELASTIC_API_KEY else 'None'}")
    
    # Вариант 1: cloud_id
    try:
        print("\n--- Вариант 1: cloud_id ---")
        client = Elasticsearch(
            cloud_id=s.ELASTIC_CLOUD_ID,
            api_key=s.ELASTIC_API_KEY,
            verify_certs=True,
            request_timeout=30
        )
        
        result = client.ping()
        print(f"Ping result: {result}")
        
        if result:
            print("✅ cloud_id работает!")
            return client
        else:
            print("❌ cloud_id ping failed")
            
    except Exception as e:
        print(f"❌ cloud_id error: {e}")
        traceback.print_exc()
    
    # Вариант 2: прямой URL
    try:
        print("\n--- Вариант 2: прямой URL ---")
        client = Elasticsearch(
            hosts=['https://36d0e937f1fd4309a2cb624f5f11bed1.us-central1.gcp.cloud.es.io:443'],
            api_key='xP65r5kBToN-DaAO9-j4:6uRhsZFfRMGMEGvyh8xDLQ',
            verify_certs=True,
            request_timeout=30
        )
        
        result = client.ping()
        print(f"Ping result: {result}")
        
        if result:
            print("✅ прямой URL работает!")
            return client
        else:
            print("❌ прямой URL ping failed")
            
    except Exception as e:
        print(f"❌ прямой URL error: {e}")
        traceback.print_exc()
    
    # Вариант 3: без SSL проверки
    try:
        print("\n--- Вариант 3: без SSL проверки ---")
        client = Elasticsearch(
            cloud_id=s.ELASTIC_CLOUD_ID,
            api_key=s.ELASTIC_API_KEY,
            verify_certs=False,
            ssl_show_warn=False,
            request_timeout=30
        )
        
        result = client.ping()
        print(f"Ping result: {result}")
        
        if result:
            print("✅ без SSL работает!")
            return client
        else:
            print("❌ без SSL ping failed")
            
    except Exception as e:
        print(f"❌ без SSL error: {e}")
        traceback.print_exc()
    
    return None

def main():
    print("🔍 Детальный тест подключения к Elasticsearch")
    print("=" * 60)
    
    # Сначала тест через requests
    requests_works = test_with_requests()
    
    # Потом тест через elasticsearch client
    client = test_elasticsearch_client()
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ:")
    print(f"requests: {'✅' if requests_works else '❌'}")
    print(f"elasticsearch client: {'✅' if client else '❌'}")
    
    if client:
        print("\n🎉 Успех! Можем использовать elasticsearch client")
        try:
            info = client.info()
            print(f"Версия: {info['version']['number']}")
            print(f"Кластер: {info['cluster_name']}")
        except Exception as e:
            print(f"Ошибка получения info: {e}")
    else:
        print("\n⚠️  elasticsearch client не работает, используем curl/requests")

if __name__ == "__main__":
    main()
