# Scheduling & Automation - TuExpertoFiscal NAIL

This document describes which processes run automatically and which are manual.

## Automation Strategy

### 🤖 Automated (Scheduled Jobs)

These scripts run automatically on a schedule:

#### 1. Telegram Group Parser
- **Script:** `scripts/ingestion/ingest_telegram_groups.py`
- **Frequency:** Weekly (every Monday at 02:00 AM)
- **Why automated:** Groups are active daily, need fresh discussions regularly
- **Implementation:** GitHub Actions / Cron job / Celery Beat

#### 2. News Scraper
- **Script:** `scripts/ingestion/ingest_news_articles.py`
- **Frequency:** Daily (every day at 08:00 AM)
- **Why automated:** News updates daily, need fresh content
- **Implementation:** GitHub Actions / Cron job / Celery Beat

#### 3. Tax Calendar Reminders
- **Script:** `scripts/reminders/send_calendar_reminders.py` (TODO)
- **Frequency:** Daily check + send reminders 7 days before deadline
- **Why automated:** Proactive notifications to users
- **Implementation:** Cron job checking `tax_deadlines` table
- **Target:** Send to Telegram groups and individual users

**Example Reminder:**
```
🔔 НАЛОГОВОЕ НАПОМИНАНИЕ

📅 Через 7 дней (30 июня) - дедлайн по IRPF Q2

👤 Для кого: Autónomos
💰 Что: Квартальный платёж IRPF за Q2

🔗 Подробнее: [ссылка на статью/калькулятор]
```

---

### ⚠️ Manual (Run as Needed)

These scripts are run manually when needed:

#### 1. PDF Tax Laws
- **Script:** `scripts/ingestion/ingest_pdf_documents.py`
- **Frequency:** When new laws published (1-4 times per year)
- **Why manual:** Laws don't change often, PDFs need manual download from BOE
- **Process:**
  1. Download PDF from BOE manually
  2. Place in `data/raw_documents/`
  3. Run script with appropriate parameters

#### 2. Tax Calendar
- **Script:** `scripts/ingestion/ingest_tax_calendar.py`
- **Frequency:** Annual (December for next year)
- **Why manual:** Calendar published once per year, needs review
- **Process:**
  1. Download/parse AEAT calendar in December
  2. Run script to load into DB
  3. Verify all dates are correct

#### 3. AEAT Website FAQs
- **Script:** `scripts/ingestion/ingest_aeat_website.py`
- **Frequency:** Monthly or as needed
- **Why manual:** FAQs rarely change, need to verify content quality
- **Process:**
  1. Run script monthly
  2. Review what was scraped
  3. Manual quality check

#### 4. Valencia Regional Documents
- **Script:** `scripts/ingestion/ingest_valencia_dogv.py`
- **Frequency:** When new regional laws published
- **Why manual:** Infrequent updates, need manual PDF download
- **Process:**
  1. Monitor DOGV for new fiscal laws
  2. Download PDF manually
  3. Run script

---

## Implementation Options

### Option 1: GitHub Actions (Recommended for Start)

**Pros:**
- Free for public repos
- Easy setup
- No infrastructure needed

**Cons:**
- Limited to 2000 minutes/month on free tier
- Can't run very frequently

**Setup:**
```yaml
# .github/workflows/ingest_telegram.yml
name: Ingest Telegram Weekly

on:
  schedule:
    - cron: '0 2 * * 1'  # Every Monday at 2 AM

jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run Telegram ingestion
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ELASTIC_CLOUD_ID: ${{ secrets.ELASTIC_CLOUD_ID }}
          # ... other secrets
        run: python scripts/ingestion/ingest_telegram_groups.py
```

### Option 2: Server Cron Jobs

**Pros:**
- Full control
- No limits
- Can run very frequently

**Cons:**
- Need a server
- Manual setup

**Setup:**
```bash
# crontab -e

# Telegram ingestion - Every Monday at 2 AM
0 2 * * 1 cd /path/to/impuesto_bot && /path/to/venv/bin/python scripts/ingestion/ingest_telegram_groups.py

# News ingestion - Every day at 8 AM
0 8 * * * cd /path/to/impuesto_bot && /path/to/venv/bin/python scripts/ingestion/ingest_news_articles.py

# Calendar reminders - Every day at 9 AM
0 9 * * * cd /path/to/impuesto_bot && /path/to/venv/bin/python scripts/reminders/send_calendar_reminders.py
```

### Option 3: Celery Beat (For Production)

**Pros:**
- Professional task queue
- Monitoring and retry logic
- Distributed workers

**Cons:**
- More complex setup
- Requires Redis/RabbitMQ

**Setup:**
```python
# celery_config.py
from celery import Celery
from celery.schedules import crontab

app = Celery('tuexpertofiscal')

app.conf.beat_schedule = {
    'ingest-telegram-weekly': {
        'task': 'tasks.ingest_telegram',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),
    },
    'ingest-news-daily': {
        'task': 'tasks.ingest_news',
        'schedule': crontab(hour=8, minute=0),
    },
    'send-reminders-daily': {
        'task': 'tasks.send_calendar_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
}
```

---

## Reminder System Design

### Calendar Reminders Flow

```
┌─────────────────────┐
│ tax_deadlines table │
│ in Supabase         │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────────┐
│ Daily Cron Job          │
│ Check upcoming deadlines│
└──────────┬──────────────┘
           │
           ↓
    ┌──────────────┐
    │ 7 days before?│
    └──────┬───────┘
           │ Yes
           ↓
┌──────────────────────────┐
│ Generate reminder message│
│ (with LLM if needed)     │
└──────────┬───────────────┘
           │
           ↓
    ┌──────────────────┐
    │ Send to:         │
    ├──────────────────┤
    │ • Telegram groups│
    │ • Premium users  │
    │ • Saved users    │
    └──────────────────┘
```

### Database Query for Reminders

```sql
-- Find deadlines in next 7 days that we haven't reminded about yet
SELECT * FROM tax_deadlines
WHERE deadline_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
AND id NOT IN (
  SELECT deadline_id FROM sent_reminders
  WHERE sent_at > CURRENT_DATE - INTERVAL '30 days'
);
```

### New Table Needed

```sql
CREATE TABLE sent_reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deadline_id UUID REFERENCES tax_deadlines(id),
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    channel_type TEXT,  -- 'telegram', 'whatsapp'
    channel_id TEXT,    -- group_id or user_id
    message_id TEXT     -- for tracking
);
```

---

## Summary

| Task | Type | Frequency | Tool |
|------|------|-----------|------|
| Telegram Groups | 🤖 Auto | Weekly (Mon 02:00) | GitHub Actions / Cron |
| News Articles | 🤖 Auto | Daily (08:00) | GitHub Actions / Cron |
| Calendar Reminders | 🤖 Auto | Daily check (09:00) | Cron |
| Tax Laws (PDF) | ⚠️ Manual | As needed | Manual run |
| Tax Calendar | ⚠️ Manual | Annual (Dec) | Manual run |
| AEAT Website | ⚠️ Manual | Monthly | Manual run |
| Valencia DOGV | ⚠️ Manual | As needed | Manual run |

---

## Next Steps

1. [ ] Implement Telegram ingestion script
2. [ ] Implement News scraper script
3. [ ] Implement Calendar reminder script
4. [ ] Set up GitHub Actions for automation
5. [ ] Create `sent_reminders` table in Supabase
6. [ ] Test reminder flow

---

*Developed by NAIL - Nahornyi AI Lab*
