#!/usr/bin/env python3
"""
Проверка подключения к Supabase через REST API
"""

import os
import sys
from pathlib import Path

# Добавляем корневую папку в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import requests

# Загружаем .env
load_dotenv()

print("="*70)
print("  ПРОВЕРКА SUPABASE REST API")
print("="*70)
print()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("Secret_key")

if not all([supabase_url, supabase_key]):
    print("❌ SUPABASE_URL или Secret_key не заданы!")
    sys.exit(1)

print(f"✅ URL: {supabase_url}")
print(f"✅ Key: {supabase_key[:20]}...")
print()

# Тестируем REST API
print("🔍 Проверяем REST API...")
print()

try:
    # Простой запрос для проверки подключения
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    
    response = requests.get(
        f"{supabase_url}/rest/v1/",
        headers=headers,
        timeout=10
    )
    
    if response.status_code == 200:
        print("✅ REST API работает!")
        print()
        
        # Проверяем доступные таблицы через REST
        print("📊 Проверяем таблицы через REST API...")
        print()
        
        # Пробуем получить список из пустой таблицы (вернёт структуру)
        test_response = requests.get(
            f"{supabase_url}/rest/v1/knowledge_sources?limit=0",
            headers=headers
        )
        
        if test_response.status_code == 200:
            print("   ✅ Таблица 'knowledge_sources' доступна")
        elif test_response.status_code == 404:
            print("   ⚠️  Таблица 'knowledge_sources' не найдена")
            print("   Нужно развернуть схему БД!")
        else:
            print(f"   ⚠️  Статус: {test_response.status_code}")
        
        print()
        print("="*70)
        print("✅ SUPABASE REST API РАБОТАЕТ!")
        print("="*70)
        print()
        print("💡 Для прямого подключения к PostgreSQL")
        print("   нужно настроить Network Access в Supabase Dashboard")
        
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(f"   {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"❌ Ошибка подключения: {e}")
    sys.exit(1)

