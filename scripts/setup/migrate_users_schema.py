#!/usr/bin/env python3
"""
Migration script: Simplify users schema
Removes user_channels table, moves telegram_id to users
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_DB_URL = os.getenv('SUPABASE_DB_URL')

if not SUPABASE_DB_URL:
    print("❌ SUPABASE_DB_URL not found in .env")
    sys.exit(1)

print("=" * 70)
print("  МИГРАЦИЯ СХЕМЫ ПОЛЬЗОВАТЕЛЕЙ В SUPABASE")
print("=" * 70)
print()
print("⚠️  ВНИМАНИЕ!")
print("   Этот скрипт изменит структуру базы данных:")
print("   - Добавит telegram_id напрямую в таблицу users")
print("   - Перенесёт данные из user_channels в users")
print("   - Удалит таблицу user_channels")
print("   - Обновит таблицу messages (channel_id -> user_id)")
print()

confirm = input("Продолжить? (yes/no): ")
if confirm.lower() != 'yes':
    print("❌ Миграция отменена")
    sys.exit(0)

print()
print("🔍 Подключаемся к Supabase...")

try:
    conn = psycopg2.connect(SUPABASE_DB_URL)
    conn.autocommit = False
    cursor = conn.cursor()
    
    print("✅ Подключение успешно!")
    print()
    
    # Check current state
    print("📊 Текущее состояние базы:")
    print()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    print(f"   Users: {users_count}")
    
    cursor.execute("SELECT COUNT(*) FROM user_channels")
    channels_count = cursor.fetchone()[0]
    print(f"   User channels: {channels_count}")
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    messages_count = cursor.fetchone()[0]
    print(f"   Messages: {messages_count}")
    print()
    
    confirm2 = input("Запустить миграцию? (yes/no): ")
    if confirm2.lower() != 'yes':
        print("❌ Миграция отменена")
        conn.close()
        sys.exit(0)
    
    print()
    print("🚀 Запускаем миграцию...")
    print()
    
    # Read migration SQL
    migration_sql_path = 'database/migrate_users_schema.sql'
    
    if not os.path.exists(migration_sql_path):
        print(f"❌ Файл миграции не найден: {migration_sql_path}")
        conn.close()
        sys.exit(1)
    
    with open(migration_sql_path, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Execute migration
    cursor.execute(migration_sql)
    conn.commit()
    
    print()
    print("=" * 70)
    print("✅ МИГРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
    print("=" * 70)
    print()
    
    # Show final state
    print("📊 Новое состояние базы:")
    print()
    
    cursor.execute("""
        SELECT 
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_name = 'users'
            AND column_name IN ('telegram_id', 'username', 'first_name', 'last_name', 'phone', 'metadata')
        ORDER BY ordinal_position;
    """)
    
    columns = cursor.fetchall()
    print("   Новые колонки в таблице users:")
    for col in columns:
        nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
        print(f"     - {col[0]:<15} {col[1]:<20} {nullable}")
    
    print()
    
    # Check indexes
    cursor.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'users'
            AND indexname LIKE '%telegram%';
    """)
    
    indexes = cursor.fetchall()
    if indexes:
        print("   Индексы:")
        for idx in indexes:
            print(f"     ✅ {idx[0]}")
    
    print()
    
    # Final count
    cursor.execute("SELECT COUNT(*) FROM users WHERE telegram_id IS NOT NULL")
    users_with_telegram = cursor.fetchone()[0]
    print(f"   Users с telegram_id: {users_with_telegram}")
    
    cursor.close()
    conn.close()
    
    print()
    print("✅ Готово! Теперь можно получать пользователя одним запросом:")
    print("   SELECT * FROM users WHERE telegram_id = 123456789;")
    print()
    
except psycopg2.Error as e:
    print(f"❌ Ошибка базы данных: {e}")
    if conn:
        conn.rollback()
        conn.close()
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Неожиданная ошибка: {e}")
    if conn:
        conn.rollback()
        conn.close()
    sys.exit(1)

