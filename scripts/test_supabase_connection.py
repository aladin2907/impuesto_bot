#!/usr/bin/env python3
"""
Быстрая проверка подключения к Supabase
"""

import os
import sys
from pathlib import Path

# Добавляем корневую папку в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import psycopg2

# Загружаем .env
load_dotenv()

print("="*70)
print("  ПРОВЕРКА ПОДКЛЮЧЕНИЯ К SUPABASE")
print("="*70)
print()

# Проверяем переменные окружения
print("1️⃣  Проверяем переменные окружения...")
print()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("Secret_key")
supabase_db_url = os.getenv("SUPABASE_DB_URL")

print(f"   SUPABASE_URL: {supabase_url}")
print(f"   Secret_key: {supabase_key[:20]}..." if supabase_key else "   Secret_key: NOT SET")
print(f"   SUPABASE_DB_URL: {supabase_db_url[:50]}..." if supabase_db_url else "   SUPABASE_DB_URL: NOT SET")
print()

if not all([supabase_url, supabase_key, supabase_db_url]):
    print("❌ Не все переменные заданы в .env файле!")
    sys.exit(1)

print("✅ Все переменные загружены!")
print()

# Проверяем подключение к БД
print("2️⃣  Проверяем подключение к PostgreSQL...")
print()

try:
    conn = psycopg2.connect(supabase_db_url)
    cursor = conn.cursor()
    
    # Проверяем версию PostgreSQL
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"✅ Подключение успешно!")
    print(f"   PostgreSQL версия: {version.split(',')[0]}")
    print()
    
    # Проверяем список таблиц
    print("3️⃣  Проверяем таблицы в базе данных...")
    print()
    
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    
    tables = cursor.fetchall()
    
    if tables:
        print(f"   Найдено таблиц: {len(tables)}")
        print()
        for table in tables:
            # Получаем количество записей
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
            count = cursor.fetchone()[0]
            print(f"   ✅ {table[0]:<35} ({count} записей)")
    else:
        print("   ⚠️  Таблицы не найдены. Нужно развернуть схему!")
        print()
        print("   Запусти: ./scripts/setup/deploy_supabase_schema.sh")
    
    cursor.close()
    conn.close()
    
    print()
    print("="*70)
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
    print("="*70)
    print()
    
except psycopg2.OperationalError as e:
    print(f"❌ Ошибка подключения:")
    print(f"   {e}")
    print()
    print("   Проверь:")
    print("   - Правильность пароля в SUPABASE_DB_URL")
    print("   - Настройки firewall в Supabase (должен быть разрешён IP 0.0.0.0/0)")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Неожиданная ошибка: {e}")
    sys.exit(1)

