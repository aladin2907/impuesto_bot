#!/bin/bash
# ============================================================
# Скрипт для развертывания схемы БД в Supabase
# ============================================================

set -e  # Выход при ошибке

echo "======================================================================"
echo "  РАЗВЕРТЫВАНИЕ СХЕМЫ БД В SUPABASE"
echo "======================================================================"
echo ""

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "   Создайте файл .env с параметрами подключения к Supabase"
    exit 1
fi

# Загружаем переменные окружения
source .env

# Проверяем обязательные переменные
if [ -z "$SUPABASE_DB_URL" ]; then
    echo "❌ SUPABASE_DB_URL не задан в .env"
    echo "   Формат: postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"
    exit 1
fi

echo "📋 Параметры подключения:"
echo "   Database URL: ${SUPABASE_DB_URL:0:30}..."
echo ""

# Проверяем наличие psql
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
echo "🚀 Развертываем схему БД..."
echo "   Файл: database/knowledge_base_schema.sql"
echo ""

# Выполняем SQL скрипт
psql "$SUPABASE_DB_URL" -f database/knowledge_base_schema.sql

echo ""
echo "======================================================================"
echo "✅ СХЕМА БД УСПЕШНО РАЗВЕРНУТА!"
echo "======================================================================"
echo ""

# Проверяем созданные таблицы
echo "📊 Проверяем созданные таблицы..."
echo ""

psql "$SUPABASE_DB_URL" -c "
SELECT 
    table_name, 
    (SELECT COUNT(*) FROM information_schema.columns WHERE columns.table_name = tables.table_name) as column_count
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    AND table_name LIKE '%metadata' OR table_name IN ('knowledge_sources', 'calendar_deadlines', 'sync_logs')
ORDER BY table_name;
"

echo ""
echo "✅ Готово! База данных настроена и готова к использованию."
echo ""

