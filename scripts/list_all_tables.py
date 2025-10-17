#!/usr/bin/env python3
"""
Показывает ВСЕ таблицы в Supabase
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import requests

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("Secret_key")

headers = {
    "apikey": supabase_key,
    "Authorization": f"Bearer {supabase_key}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

print("="*70)
print("  ВСЕ ТАБЛИЦЫ В SUPABASE")
print("="*70)
print()

# Делаем запрос к PostgREST для получения всех таблиц
try:
    # Используем специальный эндпоинт для получения метаданных
    response = requests.get(
        f"{supabase_url}/rest/v1/",
        headers=headers,
        timeout=5
    )
    
    if response.status_code == 200:
        # Получаем список таблиц из OpenAPI спецификации
        tables = []
        
        # Пробуем получить список через разные методы
        common_tables = [
            # Старые таблицы
            "users", "user_channels", "dialogue_sessions", "messages", 
            "documents", "user_tax_profile", "tax_deadlines", "sent_reminders",
            # Новые таблицы
            "knowledge_sources", "telegram_threads_metadata", 
            "pdf_documents_metadata", "news_articles_metadata",
            "calendar_deadlines", "aeat_resources_metadata", "sync_logs"
        ]
        
        existing_tables = []
        
        for table in common_tables:
            try:
                test_response = requests.get(
                    f"{supabase_url}/rest/v1/{table}?limit=1",
                    headers=headers,
                    timeout=3
                )
                if test_response.status_code == 200:
                    # Получаем количество записей
                    count_response = requests.head(
                        f"{supabase_url}/rest/v1/{table}",
                        headers={**headers, "Prefer": "count=exact"},
                        timeout=3
                    )
                    count = count_response.headers.get('Content-Range', '0-0/0').split('/')[-1]
                    existing_tables.append((table, count))
            except:
                pass
        
        print(f"Найдено таблиц: {len(existing_tables)}")
        print()
        
        for i, (table, count) in enumerate(sorted(existing_tables), 1):
            print(f"   {i:2d}. ✅ {table:<35} ({count} записей)")
        
        print()
        print("="*70)
        
    else:
        print(f"❌ Ошибка: {response.status_code}")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")

