# 🚀 Инструкция по развертыванию базы данных

**Проект**: TuExpertoFiscal NAIL  
**Дата**: 1 октября 2025

---

## 📋 Что будем делать:

1. ✅ Развернуть SQL схему в Supabase
2. ✅ Создать индексы в Elasticsearch
3. ✅ Проверить подключения

---

## 1️⃣ SUPABASE - Развертывание SQL схемы

### Шаг 1: Подготовка .env файла

Создай файл `.env` в корне проекта с параметрами Supabase:

```bash
# Supabase
SUPABASE_URL=https://mslfndlzjqttteihiopt.supabase.co
SUPABASE_KEY=your_anon_key_here
SUPABASE_DB_URL=postgresql://postgres:[YOUR_PASSWORD]@db.mslfndlzjqttteihiopt.supabase.co:5432/postgres
```

**Как получить SUPABASE_DB_URL:**
1. Зайди в Supabase Dashboard
2. Project Settings → Database
3. Connection String → URI
4. Скопируй и вставь (замени `[YOUR-PASSWORD]` на реальный пароль)

### Шаг 2: Установка PostgreSQL client (если не установлен)

**macOS:**
```bash
brew install postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt-get install postgresql-client
```

**Проверка:**
```bash
psql --version
# Должно показать версию, например: psql (PostgreSQL) 15.3
```

### Шаг 3: Запуск скрипта развертывания

```bash
# Делаем скрипт исполняемым
chmod +x scripts/setup/deploy_supabase_schema.sh

# Запускаем
./scripts/setup/deploy_supabase_schema.sh
```

**Что делает скрипт:**
- ✅ Проверяет .env файл
- ✅ Проверяет подключение к Supabase
- ✅ Выполняет SQL скрипт `database/knowledge_base_schema.sql`
- ✅ Создаёт все таблицы:
  - `knowledge_sources`
  - `telegram_threads_metadata`
  - `pdf_documents_metadata`
  - `news_articles_metadata`
  - `calendar_deadlines`
  - `aeat_resources_metadata`
  - `sync_logs`
- ✅ Создаёт индексы и триггеры
- ✅ Добавляет тестовые данные источников

**Ожидаемый вывод:**
```
======================================================================
  РАЗВЕРТЫВАНИЕ СХЕМЫ БД В SUPABASE
======================================================================

📋 Параметры подключения:
   Database URL: postgresql://postgres:***...

🔍 Проверяем подключение к Supabase...
✅ Подключение успешно!

🚀 Развертываем схему БД...
   Файл: database/knowledge_base_schema.sql

CREATE EXTENSION
CREATE TABLE
CREATE TABLE
...
INSERT 0 2
INSERT 0 2
...

======================================================================
✅ СХЕМА БД УСПЕШНО РАЗВЕРНУТА!
======================================================================

📊 Проверяем созданные таблицы...

            table_name             | column_count 
-----------------------------------+--------------
 aeat_resources_metadata           |           18
 calendar_deadlines                |           15
 knowledge_sources                 |           11
 news_articles_metadata            |           17
 pdf_documents_metadata            |           24
 sync_logs                         |           14
 telegram_threads_metadata         |           24

✅ Готово! База данных настроена и готова к использованию.
```

### Шаг 4: Проверка в Supabase Dashboard

1. Зайди в Supabase Dashboard
2. Table Editor → должны появиться все таблицы
3. SQL Editor → выполни тестовый запрос:

```sql
SELECT source_type, source_name, is_active 
FROM knowledge_sources;
```

Должны увидеть 2 Telegram группы и другие источники!

---

## 2️⃣ ELASTICSEARCH - Создание индексов

### Шаг 1: Проверка .env файла

Добавь в `.env` параметры Elasticsearch:

```bash
# Elasticsearch
ELASTIC_CLOUD_ID=your_cloud_id_here
ELASTIC_API_KEY=your_api_key_here
```

**Как получить:**
1. Зайди в Elastic Cloud Console
2. Deployments → твой deployment
3. Cloud ID → скопируй
4. Management → API Keys → Create API Key

### Шаг 2: Установка зависимостей

```bash
# Активируем виртуальное окружение
source venv/bin/activate

# Проверяем что elasticsearch установлен
pip list | grep elasticsearch

# Если нет - устанавливаем
pip install elasticsearch
```

### Шаг 3: Запуск скрипта создания индексов

```bash
# Делаем скрипт исполняемым
chmod +x scripts/setup/setup_elasticsearch_indices.py

# Запускаем
python scripts/setup/setup_elasticsearch_indices.py
```

**Что делает скрипт:**
- ✅ Подключается к Elasticsearch
- ✅ Создаёт индексы:
  - `telegram_threads` - для Telegram тредов
  - `pdf_documents` - для PDF чанков
  - `news_articles` - для новостей
  - `calendar_deadlines` - для календаря
- ✅ Настраивает mappings и analyzers
- ✅ Выводит список созданных индексов

**Ожидаемый вывод:**
```
======================================================================
  НАСТРОЙКА ИНДЕКСОВ ELASTICSEARCH
======================================================================

✅ Подключение к Elasticsearch успешно!
   Версия: 8.11.0
   Кластер: impuesto-bot

📋 Создаём индекс: telegram_threads
   ✅ Индекс telegram_threads создан!

📋 Создаём индекс: pdf_documents
   ✅ Индекс pdf_documents создан!

📋 Создаём индекс: news_articles
   ✅ Индекс news_articles создан!

📋 Создаём индекс: calendar_deadlines
   ✅ Индекс calendar_deadlines создан!

📊 Список индексов:
   ✅ calendar_deadlines
      Документов: 0
      Размер: 0.00 MB
   ✅ news_articles
      Документов: 0
      Размер: 0.00 MB
   ✅ pdf_documents
      Документов: 0
      Размер: 0.00 MB
   ✅ telegram_threads
      Документов: 0
      Размер: 0.00 MB

======================================================================
✅ ВСЕ ИНДЕКСЫ СОЗДАНЫ!
======================================================================
```

### Шаг 4: Проверка в Kibana (опционально)

1. Зайди в Elastic Cloud Console
2. Kibana → Stack Management → Index Management
3. Должны увидеть все 4 индекса!

---

## 3️⃣ ПРОВЕРКА ПОДКЛЮЧЕНИЙ

Запусти тестовый скрипт:

```bash
python scripts/test_connections.py
```

**Ожидаемый вывод:**
```
==================================================
TuExpertoFiscal NAIL - Connection Test
==================================================

1. Validating environment variables...
✅ Environment variables loaded

2. Testing Elasticsearch connection...
✅ Elasticsearch connected successfully
   Cluster: impuesto-bot
   Version: 8.11.0
   Indices: 4

3. Testing Supabase connection...
✅ Supabase connected successfully
   Tables found: 7

==================================================
✅ All connections successful!
==================================================
```

---

## 4️⃣ ЧТО ДАЛЬШЕ?

После успешного развертывания:

### Следующие шаги:

1. **Индексация Telegram тредов**
   ```bash
   python scripts/ingestion/index_telegram_threads.py it_threads.json
   python scripts/ingestion/index_telegram_threads.py nomads_threads.json
   ```

2. **Индексация календаря**
   ```bash
   python scripts/ingestion/index_calendar.py data/tax_calendar.json
   ```

3. **Индексация новостей**
   ```bash
   python scripts/ingestion/index_news.py data/news_articles.json
   ```

4. **Обработка и индексация PDF**
   ```bash
   python scripts/ingestion/index_pdf_documents.py data/pdf_documents/
   ```

5. **Тестирование поиска**
   ```bash
   python scripts/test_search.py "автономо налоги"
   ```

---

## 🔧 Troubleshooting

### Проблема: "psql: command not found"
**Решение:**
```bash
# macOS
brew install postgresql

# Ubuntu
sudo apt-get install postgresql-client
```

### Проблема: "Connection refused" при подключении к Supabase
**Решение:**
- Проверь SUPABASE_DB_URL в .env
- Проверь пароль (должен быть без скобок)
- Проверь IP whitelist в Supabase (должен быть 0.0.0.0/0)

### Проблема: "Authentication failed" в Elasticsearch
**Решение:**
- Проверь ELASTIC_CLOUD_ID и ELASTIC_API_KEY
- Создай новый API Key с правами "All"
- Проверь что deployment активен

### Проблема: "Table already exists"
**Решение:**
```bash
# Удали все таблицы и пересоздай
psql "$SUPABASE_DB_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
./scripts/setup/deploy_supabase_schema.sh
```

### Проблема: "Index already exists" в Elasticsearch
**Решение:**
Скрипт спросит: "Удалить и пересоздать? (y/N)"
Введи `y` для пересоздания индекса

---

## 📊 Структура после развертывания

### Supabase (7 таблиц):
```
✅ knowledge_sources          - реестр источников
✅ telegram_threads_metadata  - метаданные тредов
✅ pdf_documents_metadata     - метаданные PDF
✅ news_articles_metadata     - метаданные новостей
✅ calendar_deadlines         - налоговые дедлайны
✅ aeat_resources_metadata    - ресурсы AEAT
✅ sync_logs                  - логи синхронизации
```

### Elasticsearch (4 индекса):
```
✅ telegram_threads    - поиск по тредам
✅ pdf_documents       - поиск по PDF чанкам
✅ news_articles       - поиск по новостям
✅ calendar_deadlines  - поиск по календарю
```

---

## ✅ Чеклист развертывания

- [ ] Создан файл `.env` с параметрами Supabase
- [ ] Создан файл `.env` с параметрами Elasticsearch
- [ ] Установлен PostgreSQL client (psql)
- [ ] Запущен `deploy_supabase_schema.sh`
- [ ] Все таблицы созданы в Supabase
- [ ] Запущен `setup_elasticsearch_indices.py`
- [ ] Все индексы созданы в Elasticsearch
- [ ] Запущен `test_connections.py` - всё работает
- [ ] Готов к индексации данных!

---

*Разработано NAIL - Nahornyi AI Lab*
