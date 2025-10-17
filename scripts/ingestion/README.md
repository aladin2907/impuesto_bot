# Data Ingestion Scripts

This directory contains scripts for ingesting different types of data into the TuExpertoFiscal NAIL knowledge base.

## Architecture Principle

⚠️ **IMPORTANT:** Each data source type has its own specialized script. Do not create universal scripts.

Each source has unique requirements:
- **PDF laws** - Article extraction, legal structure
- **Tax calendar** - Date parsing, deadline tracking, dual storage (Elasticsearch + Supabase)
- **Telegram** - Spam filtering, Q&A extraction, anonymization
- **News** - RSS parsing, duplicate detection, freshness scoring
- **AEAT** - Structured HTML, form instructions, calculator integration

See `docs/ingestion_architecture.md` for detailed design.

## Structure

```
scripts/ingestion/
├── base_ingestor.py              # Base class with common functionality
├── ingest_pdf_documents.py       # ✅ Tax laws & regulations
├── ingest_tax_calendar.py        # 📅 Tax calendar (special date handling)
├── sync_aeat_calendar.py         # 🔄 AEAT iCalendar synchronisation
├── ingest_telegram_groups.py     # 💬 Telegram Q&A discussions
├── ingest_news_articles.py       # 📰 News articles
├── ingest_aeat_website.py        # 🏛️ AEAT official resources
└── ingest_valencia_dogv.py       # 🏛️ Valencia regional documents
```

## Available Scripts

### 1. PDF Document Ingestion

Ingests PDF files such as Tax Code, Tax Calendar, and regulations.

**Usage:**
```bash
python scripts/ingestion/ingest_pdf_documents.py <path_to_pdf> [options]
```

**Options:**
- `--url <source_url>`: Original URL of the document
- `--type <document_type>`: Type of document (tax_code, tax_calendar, regulation, guide)

**Examples:**

```bash
# Ingest Spanish Tax Code (IRPF)
python scripts/ingestion/ingest_pdf_documents.py \
    data/raw_documents/ley_35_2006_irpf.pdf \
    --url "https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764" \
    --type tax_code

# Ingest Tax Calendar
python scripts/ingestion/ingest_pdf_documents.py \
    data/raw_documents/calendario_fiscal_2024.pdf \
    --url "https://sede.agenciatributaria.gob.es/Sede/ayuda/calendario-contribuyente.html" \
    --type tax_calendar

# Ingest Valencia regional regulation
python scripts/ingestion/ingest_pdf_documents.py \
    data/raw_documents/valencia_medidas_fiscales_2024.pdf \
    --type regulation
```

**What it does:**
1. Loads the PDF file
2. Splits into chunks (1000 chars with 200 overlap)
3. Generates embeddings using configured LLM
4. Indexes into Elasticsearch with hybrid search enabled
5. Saves metadata to Supabase `documents` table

### 2. AEAT iCalendar Sync

Pulls official AEAT calendars (`.ics`) hosted on Google Calendar, parses events and upserts them into Supabase.

**Usage (alpha):**
```bash
python scripts/ingestion/sync_aeat_calendar.py
```

**Features:**
- Автоматически находит список официальных .ics ссылок на странице AEAT.
- Парсит VEVENT записи (UID, SUMMARY, DTSTART, STATUS, SEQUENCE, etc.).
- Upsert в таблицу `calendar_events` по `(uid, calendar_type)` с пометкой отменённых событий.

**TODO:**
- Обвязка расписания (cron/GitHub Actions).
- Автоматический маппинг событий в `calendar_deadlines` после нормализации.

### 3. Tax Calendar Ingestion

Parses structured AEAT calendar data (JSON) and превращает его в поисковые документы.

**Usage (WIP):**
```bash
python scripts/ingestion/ingest_tax_calendar.py data/tax_calendar.json
```

**What is ready:**
- TDD-покрытый парсинг дедлайнов (`tests/test_ingest_tax_calendar.py`)
- Генерация документоориентированного описания с богатыми метаданными

**Next steps:**
- Интеграция с Supabase и Elasticsearch через `BaseIngestor`
- Автоматическое расписание обновлений

### 4. News Articles Ingestion

Processes новостные выгрузки (`news_articles.json`), фильтрует дубликаты и индексирует статьи.

**Usage:**
```bash
python scripts/ingestion/ingest_news_articles.py data/news_articles.json
```

**Features:**
- Дедубликация по `article_url` (учитывает уже существующие записи в Supabase).
- Сохраняет метаданные в `news_articles_metadata` и индексирует текст в Elasticsearch.
- Готово к автоматическому расписанию (e.g. daily cron).

### 5. AEAT Resources Ingestion

Processes официальные ресурсы AEAT (PDF/HTML инструкции, формы) и добавляет их в индекс.

**Usage:**
```bash
python scripts/ingestion/ingest_aeat_website.py data/aeat_resources.json
```

**Features:**
- Дедупликация по `resource_url`, учёт уже загруженных записей (`aeat_resources_metadata`).
- Сохранение метаданных (номер модели, год, версия) и индексация текста в Elasticsearch.
- Подходит для ежемесячного или ручного запуска.

### 6. Valencia DOGV Ingestion

Handles региональные документы DOGV (Valencia) из подготовленного JSON.

**Usage: **
```bash
python scripts/ingestion/ingest_valencia_dogv.py data/valencia_dogv.json
```

**Features:**
- Дедупликация по `source_url`, проверка уже существующих записей в `pdf_documents_metadata`.
- Сохраняет основные метаданные (название, дата публикации, регион) и индексирует текст для поиска.
- Готов к ручному или периодическому запуску при появлении новых региональных законов.

### 7. Telegram Groups (Coming Soon)

Will parse Telegram groups weekly and extract valuable discussions.

### 8. AEAT Website (Coming Soon)

Will scrape AEAT official website for FAQs and guides.

## Common Workflow

All ingestion scripts follow this pattern:

1. **Initialize Services**
   - LLM service (for embeddings)
   - Elasticsearch (for indexing)
   - Supabase (for metadata)

2. **Load Data**
   - Load from source (PDF, web, etc.)

3. **Process**
   - Split into chunks
   - Generate embeddings
   - Add metadata

4. **Store**
   - Index in Elasticsearch
   - Save metadata in Supabase

5. **Cleanup**
   - Close connections

## Configuration

All scripts use settings from `.env`:

```env
# LLM for embeddings
LLM_PROVIDER=openai
OPENAI_API_KEY=...

# Elasticsearch
ELASTIC_CLOUD_ID=...
ELASTIC_API_KEY=...
ELASTIC_INDEX_NAME=tuexpertofiscal_knowledge

# Supabase
SUPABASE_DB_URL=...
```

## Data Storage

- **Raw files:** Store in `data/raw_documents/`
- **Elasticsearch:** Processed chunks with embeddings
- **Supabase:** Document metadata and status

## Development

To create a new ingestor:

1. Create new file: `ingest_<source>.py`
2. Inherit from `BaseIngestor`
3. Implement source-specific loading logic
4. Use parent class methods for common operations

Example:
```python
from scripts.ingestion.base_ingestor import BaseIngestor

class MyIngestor(BaseIngestor):
    def __init__(self):
        super().__init__(document_type="my_type")
    
    def load_data(self, source):
        # Your loading logic
        pass
    
    def process(self, source):
        self.initialize()
        docs = self.load_data(source)
        self.ingest_documents(docs)
        self.cleanup()
```

---

*Developed by NAIL - Nahornyi AI Lab*
