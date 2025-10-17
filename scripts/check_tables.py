#!/usr/bin/env python3
"""
Проверка существующих таблиц в Supabase
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
    "Content-Type": "application/json"
}

print("="*70)
print("  ПРОВЕРКА ТАБЛИЦ В SUPABASE")
print("="*70)
print()

# Список таблиц которые должны быть
old_tables = [
    "users",
    "user_channels", 
    "dialogue_sessions",
    "messages",
    "documents",
    "user_tax_profile"
]

new_tables = [
    "knowledge_sources",
    "telegram_threads_metadata",
    "pdf_documents_metadata",
    "news_articles_metadata",
    "calendar_deadlines",
    "aeat_resources_metadata",
    "sync_logs"
]

print("📊 СТАРЫЕ ТАБЛИЦЫ (для бота и пользователей):")
print()
for table in old_tables:
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/{table}?limit=0",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            print(f"   ✅ {table}")
        else:
            print(f"   ❌ {table} (не найдена)")
    except:
        print(f"   ❌ {table} (ошибка)")

print()
print("📚 НОВЫЕ ТАБЛИЦЫ (для базы знаний):")
print()
found_new = False
for table in new_tables:
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/{table}?limit=0",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            print(f"   ✅ {table}")
            found_new = True
        else:
            print(f"   ❌ {table} (не найдена)")
    except:
        print(f"   ❌ {table} (ошибка)")

print()
print("="*70)

if not found_new:
    print("⚠️  НОВЫЕ ТАБЛИЦЫ ДЛЯ БАЗЫ ЗНАНИЙ НЕ СОЗДАНЫ!")
    print()
    print("Нужно развернуть схему:")
    print("./scripts/setup/deploy_supabase_schema.sh")
else:
    print("✅ ВСЕ ТАБЛИЦЫ НА МЕСТЕ!")
print("="*70)

