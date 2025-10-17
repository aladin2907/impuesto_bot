# Data Ingestion Architecture - TuExpertoFiscal NAIL

## Core Principle: One Source = One Script

Each data source type requires its own specialized ingestion script. **Do not create universal scripts** that try to handle multiple source types.

### Why?

1. **Different data structures** - PDFs, HTML, JSON, chat messages all require different parsing
2. **Unique metadata** - Each source has specific metadata needs
3. **Different processing logic** - Telegram needs spam filtering, calendar needs date parsing
4. **Maintenance** - Easier to debug and update specific scripts
5. **Scalability** - Can run scripts independently on different schedules

---

## Planned Ingestion Scripts

### 1. PDF Regulatory Documents
**Script:** `scripts/ingestion/ingest_pdf_documents.py` ✅ DONE

**Purpose:** Ingest Spanish tax laws and regulations (IRPF, IVA, LGT, etc.)

**Processing:**
- Load PDF with `PyPDFLoader`
- Split into semantic chunks (1000 chars)
- Generate embeddings
- Index with metadata: law name, article number, date

**Schedule:** ⚠️ **MANUAL** - Run manually when new laws published (PDFs downloaded manually from BOE)

**Metadata:**
```json
{
  "document_type": "tax_code",
  "law_name": "Ley 35/2006 IRPF",
  "article": "15",
  "source_url": "https://boe.es/...",
  "last_updated": "2024-01-15"
}
```

---

### 2. Tax Calendar
**Script:** `scripts/ingestion/ingest_tax_calendar.py` 🚧 *in progress (парсинг и тесты готовы)*

**Purpose:** Process Spanish tax calendar with deadlines and dates

**Processing:**
- Parse AEAT calendar (HTML or iCal format)
- Extract structured data: date, tax type, deadline, who it applies to
- Store in a **special format** for date-based queries
- Create natural language descriptions for each deadline
- **Enable reminder functionality** - bot will send proactive reminders to groups

**Schedule:** ⚠️ **MANUAL** - Annual (December for next year's calendar)

**Special Requirements:**
- Parse dates and convert to structured format
- Link deadlines to relevant tax types
- Enable queries like "When is IRPF due?" or "What deadlines in March?"
- Store both in Elasticsearch (for search) AND Supabase (for structured queries)

**Metadata:**
```json
{
  "document_type": "tax_calendar",
  "deadline_date": "2024-06-30",
  "tax_type": "IRPF",
  "applies_to": "autónomos",
  "quarter": "Q2",
  "description": "Second quarterly payment for autónomos"
}
```

**Additional Table in Supabase:**
Consider adding a `tax_deadlines` table:
```sql
CREATE TABLE tax_deadlines (
    id UUID PRIMARY KEY,
    deadline_date DATE NOT NULL,
    tax_type TEXT NOT NULL,
    description TEXT,
    applies_to TEXT[],
    quarter TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 2b. AEAT iCalendar Synchronisation
**Script:** `scripts/ingestion/sync_aeat_calendar.py` ✅ *alpha-ready*

**Purpose:** Поддерживать актуальную копию официальных календарей AEAT (Google Calendar / .ics) в Supabase.

**Processing:**
- Парсит страницу инструкций AEAT и собирает 18+ официальных `.ics` ссылок (IRPF, IVA, especiales, intrastat и т.д.).
- Скачивает и распаковывает VEVENT события (UID, SUMMARY, DTSTART, STATUS, SEQUENCE...).
- Upsert в таблицу `calendar_events` по `(uid, calendar_type)` с сохранением `STATUS` и `is_active`.

**Schedule:** 🔁 **Еженедельно** (cron/GitHub Actions) — обновить `SEQUENCE`/`STATUS`.

**Next steps:**
- Маппинг ключевых событий (confirmed) в `calendar_deadlines`.
- Уведомления о изменениях (`sequence`/`status`) в Slack/Telegram.

---

### 3. Telegram Groups
**Script:** `scripts/ingestion/ingest_telegram_groups.py` (TODO)

**Purpose:** Parse Telegram groups for real-world Q&A discussions

**Processing:**
- Use Telethon/Pyrogram to read messages
- Filter out spam, ads, off-topic (use cheap LLM)
- Extract question-answer pairs
- Store with conversation context

**Schedule:** 🤖 **AUTOMATED** - Weekly (every Monday at 02:00 AM)

**Special Requirements:**
- Message filtering (spam detection)
- Thread/reply association
- User anonymization (GDPR compliance)
- Detect high-quality answers (likes, replies)

**Metadata:**
```json
{
  "document_type": "telegram_discussion",
  "group_name": "IT Autonomos Spain",
  "message_date": "2024-01-15",
  "is_question": true,
  "has_answer": true,
  "quality_score": 8.5
}
```

---

### 4. News Articles
**Script:** `scripts/ingestion/ingest_news_articles.py` ✅ *готово*

**Purpose:** Scrape tax news from Spanish financial media

**Processing:**
- Загружаем подготовленный JSON (или результат скрапинга) с полями статьи
- Дедублируем по `article_url`, учитываем уже существующие записи в Supabase
- Индексируем текст в Elasticsearch + сохраняем метаданные в `news_articles_metadata`

**Schedule:** 🤖 **AUTOMATED** - Daily (every day at 08:00 AM)

**Special Requirements:**
- RSS/HTML скрапинг (внешний шаг), формирование JSON
- Duplicate detection (по URL + content hash)
- Freshness weighting (relevance_score)

**Metadata:**
```json
{
  "document_type": "news_article",
  "source": "Cinco Días",
  "publication_date": "2024-01-15",
  "author": "Juan García",
  "url": "https://...",
  "relevance_score": 9.2
}
```

---

### 5. AEAT Official Website
**Script:** `scripts/ingestion/ingest_aeat_website.py` ✅ *готово*

**Purpose:** Scrape AEAT official FAQs, guides, and forms

**Processing:**
- Заглушка скрапера формирует JSON (URL, тайтл, тип ресурса, контент)
- Инжестор фильтрует дубликаты по `resource_url`
- Сохраняет метаданные (модель, год, версия) в `aeat_resources_metadata`
- Индексирует текст в Elasticsearch

**Schedule:** ⚠️ **MANUAL** - Monthly or as needed (FAQs rarely change)

**Special Requirements:**
- Respect robots.txt / кеширование исходного HTML
- Отлеживать `version_date` для актуальности
- Линковать инструкции к соответствующим моделям/законам

**Metadata:**
```json
{
  "document_type": "aeat_resource",
  "section": "FAQ",
  "form_number": "Modelo 100",
  "url": "https://sede.agenciatributaria.gob.es/..."
}
```

---

### 6. Valencia Regional Documents
**Script:** `scripts/ingestion/ingest_valencia_dogv.py` ✅ *готово*

**Purpose:** Parse DOGV (Valencian official gazette) for regional tax changes

**Processing:**
- Скрапер/парсер формирует JSON с ключевыми полями (URL, заголовок, дата, контент)
- Инжестор удаляет дубликаты по `source_url`
- Сохраняет метаданные в `pdf_documents_metadata` (region = Valencia)
- Индексирует текст для поиска

**Schedule:** ⚠️ **MANUAL** - When new laws published (PDFs downloaded manually)

**Metadata:**
```json
{
  "document_type": "regional_regulation",
  "region": "Valencia",
  "publication_date": "2024-01-15",
  "dogv_number": "9845"
}
```

---

## Base Architecture

All scripts inherit from `BaseIngestor` which provides:
- LLM service initialization
- Elasticsearch connection
- Supabase connection
- Text splitting
- Common ingestion pipeline

But each script implements its own:
- Data loading (`load_data()`)
- Data parsing (`parse_data()`)
- Metadata extraction (`extract_metadata()`)
- Special processing (`process_special_cases()`)

---

## File Structure

```
scripts/ingestion/
├── base_ingestor.py                 # Base class
├── ingest_pdf_documents.py          # ✅ Tax laws & regulations
├── ingest_tax_calendar.py           # 📅 Special date handling
├── ingest_telegram_groups.py        # 💬 Q&A discussions
├── ingest_news_articles.py          # 📰 Daily news
├── ingest_aeat_website.py           # 🏛️ Official AEAT resources
├── ingest_valencia_dogv.py          # 🏛️ Regional regulations
└── README.md                        # Documentation
```

---

## Guidelines for Creating New Scripts

1. **Inherit from `BaseIngestor`**
2. **Implement source-specific loading**
3. **Define unique metadata structure**
4. **Add appropriate filtering/validation**
5. **Document in README.md**
6. **Add to scheduling configuration**

---

## Calendar Processing - Special Case

The tax calendar is NOT just text to search. It requires:

### Dual Storage Strategy:

1. **Elasticsearch** (for natural language queries)
   - "When is my quarterly payment due?"
   - "What deadlines are in June?"
   
2. **Supabase** (for structured queries)
   - Filter by date range
   - Get all deadlines for specific tax type
   - API endpoints for calendar view

### Processing Pipeline:

```
AEAT Calendar (HTML/iCal)
    ↓
Parse dates & deadlines
    ↓
    ├─→ Elasticsearch: Natural language descriptions
    └─→ Supabase: Structured data (tax_deadlines table)
```

### Example Query Flow:

**User:** "When do I need to pay IRPF as autónomo?"

1. RAG finds relevant calendar chunks in Elasticsearch
2. Bot responds: "Q1 payment due April 20, Q2 due July 20, Q3 due October 20"
3. Backend queries `tax_deadlines` table for exact dates
4. Can send reminders/notifications

---

## Summary

✅ **One source = One script**  
✅ **Each script is specialized**  
✅ **Calendar needs special handling**  
✅ **All inherit common base class**  
✅ **Different schedules for different sources**

---

*Developed by NAIL - Nahornyi AI Lab*
