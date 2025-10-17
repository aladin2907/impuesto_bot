#!/bin/bash
# ============================================================
# Migration script: Simplify users schema
# Removes user_channels table, moves telegram_id to users
# ============================================================

set -e  # Exit on error

echo "======================================================================"
echo "  МИГРАЦИЯ СХЕМЫ ПОЛЬЗОВАТЕЛЕЙ В SUPABASE"
echo "======================================================================"
echo ""
echo "⚠️  ВНИМАНИЕ!"
echo "   Этот скрипт изменит структуру базы данных:"
echo "   - Добавит telegram_id напрямую в таблицу users"
echo "   - Перенесёт данные из user_channels в users"
echo "   - Удалит таблицу user_channels"
echo "   - Обновит таблицу messages (channel_id -> user_id)"
echo ""
read -p "Продолжить? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Миграция отменена"
    exit 0
fi

echo ""

# Check .env file
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "   Создайте файл .env с параметрами подключения к Supabase"
    exit 1
fi

# Load environment variables
source .env

# Check required variables
if [ -z "$SUPABASE_DB_URL" ]; then
    echo "❌ SUPABASE_DB_URL не задан в .env"
    echo "   Формат: postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"
    exit 1
fi

echo "📋 Параметры подключения:"
echo "   Database URL: ${SUPABASE_DB_URL:0:30}..."
echo ""

# Check psql
if ! command -v psql &> /dev/null; then
    echo "❌ psql не установлен!"
    echo "   Установите PostgreSQL client:"
    echo "   macOS: brew install postgresql"
    echo "   Ubuntu: sudo apt-get install postgresql-client"
    exit 1
fi

echo "🔍 Проверяем подключение к Supabase..."
if psql "$SUPABASE_DB_URL" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ Подключение успешно!"
else
    echo "❌ Не удалось подключиться к Supabase"
    echo "   Проверьте SUPABASE_DB_URL в .env"
    exit 1
fi

echo ""
echo "📊 Проверяем текущее состояние базы..."
echo ""

# Show current state
psql "$SUPABASE_DB_URL" -c "
SELECT 
    'users' as table_name,
    COUNT(*) as record_count
FROM users
UNION ALL
SELECT 
    'user_channels' as table_name,
    COUNT(*) as record_count
FROM user_channels
UNION ALL
SELECT 
    'messages' as table_name,
    COUNT(*) as record_count
FROM messages;
"

echo ""
read -p "Запустить миграцию? (yes/no): " confirm2

if [ "$confirm2" != "yes" ]; then
    echo "❌ Миграция отменена"
    exit 0
fi

echo ""
echo "🚀 Запускаем миграцию..."
echo "   Файл: database/migrate_users_schema.sql"
echo ""

# Run migration
psql "$SUPABASE_DB_URL" -f database/migrate_users_schema.sql

echo ""
echo "======================================================================"
echo "✅ МИГРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!"
echo "======================================================================"
echo ""

# Show final state
echo "📊 Проверяем новое состояние базы..."
echo ""

psql "$SUPABASE_DB_URL" -c "
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
    AND column_name IN ('telegram_id', 'username', 'first_name', 'last_name', 'phone', 'metadata')
ORDER BY ordinal_position;
"

echo ""
echo "📊 Проверяем индексы:"
echo ""

psql "$SUPABASE_DB_URL" -c "
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'users'
    AND indexname LIKE '%telegram%';
"

echo ""
echo "✅ Готово! Схема обновлена."
echo "   Теперь можно получать пользователя одним запросом:"
echo "   SELECT * FROM users WHERE telegram_id = 123456789;"
echo ""

