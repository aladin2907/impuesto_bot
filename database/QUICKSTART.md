# Быстрый старт миграции на pgvector

## 📋 Простая установка

### Используйте этот скрипт: 🔥

**Удаляет старые таблицы базы знаний, создает/сохраняет таблицы пользователей**

1. Откройте Supabase Dashboard → **SQL Editor**
2. Откройте файл: [`migrations/COMPLETE_SETUP.sql`](migrations/COMPLETE_SETUP.sql)
3. Скопируйте весь код
4. Вставьте в SQL Editor
5. Нажмите **RUN**

## 3. Проверьте результат

Должны создаться 3 новые таблицы:
- ✅ `telegram_threads_content`
- ✅ `pdf_documents_content`
- ✅ `news_articles_content`

И обновиться существующая:
- ✅ `calendar_deadlines` (удалены Elasticsearch поля)

## 4. Проверьте, что всё работает

```sql
-- Проверка таблиц
SELECT table_name
FROM information_schema.tables
WHERE table_name IN (
    'telegram_threads_content',
    'pdf_documents_content',
    'news_articles_content'
);

-- Проверка векторных индексов
SELECT indexname
FROM pg_indexes
WHERE indexname LIKE '%embedding%';

-- Статистика (пока пусто)
SELECT * FROM v_vector_store_stats;
```

## Готово! 🎉

Теперь база данных готова к векторному поиску.

**Следующий шаг:** Реализация Python классов для работы с БД

---

Если возникли проблемы, см. полную документацию: [README_MIGRATION.md](README_MIGRATION.md)
