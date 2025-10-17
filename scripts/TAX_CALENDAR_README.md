# Tax Calendar Sync Pipeline

Complete pipeline for scraping and loading AEAT tax calendar data into Supabase.

## Overview

The tax calendar contains structured deadline information for various Spanish taxes (IRPF, IVA, Retenciones, Sociedades). 

**Important**: Calendar data is stored **only in Supabase**, NOT in Elasticsearch. 

- ✅ **Supabase**: Structured deadlines in `calendar_deadlines` table
- ❌ **Elasticsearch**: Only for normative documents and Telegram threads

## Quick Start

### Run Complete Pipeline

Scrape + Load for **current and next year** (default):

```bash
python scripts/sync_tax_calendar.py
```

Or specify custom years:

```bash
python scripts/sync_tax_calendar.py --years 2025 2026 2027
```

This will:
1. Scrape AEAT calendar for each specified year
2. Save to `data/tax_calendar_YYYY.json`
3. Load into Supabase `calendar_deadlines` table

**By default**, it processes current year (2025) and next year (2026)

## Individual Steps

### 1. Scrape Calendar Only

```bash
python scripts/data_collection/scrape_tax_calendar.py --year 2025 --output data/tax_calendar.json
```

### 2. Load to Supabase Only

```bash
python scripts/ingestion/ingest_calendar_rest_api.py
```

(Uses `data/tax_calendar.json` by default)

## Database Schema

Data is stored in the `calendar_deadlines` table with the following structure:

- `deadline_date` - Deadline date (DATE)
- `tax_type` - Tax type (IRPF, IVA, Retenciones, Sociedades)
- `tax_model` - Model number (Modelo 100, 111, 130, 200, 303)
- `description` - Full description in Spanish
- `applies_to` - Who it applies to (autonomos, empresas, etc.)
- `region` - Region (national or specific community)
- `payment_required` - Whether payment is required (BOOLEAN)
- `declaration_required` - Whether declaration is required (BOOLEAN)
- `penalty_for_late` - Penalty description for late submission
- `year`, `quarter`, `month` - Time period information

## Statistics

Per year calendar contains:
- **Total**: ~14 deadlines
- **IRPF**: 5 deadlines (Modelo 100, 130)
- **IVA**: 4 deadlines (Modelo 303)
- **Retenciones**: 4 deadlines (Modelo 111)
- **Sociedades**: 1 deadline (Modelo 200)

Current DB should have data for 2025 and 2026 (28 deadlines total)

## Data Source

- **Source**: AEAT (Agencia Estatal de Administración Tributaria)
- **URL**: https://sede.agenciatributaria.gob.es/Sede/calendario-contribuyente.html
- **Sync Frequency**: Monthly (recommended)

## Technical Details

### API Used

Uses Supabase REST API instead of direct PostgreSQL connection for better compatibility.

### Upsert Logic

The script uses upsert with conflict resolution on `(deadline_date, tax_type, tax_model)`:
- If deadline exists → Updates description and other fields
- If deadline is new → Inserts new record

### Source Tracking

All deadlines are linked to a `knowledge_sources` entry:
- `source_type`: calendar
- `source_name`: AEAT Tax Calendar

## Automation

For automatic syncing, add to cron:

```bash
# Sync tax calendar on the 1st of each month at 3 AM (current + next year)
0 3 1 * * cd /path/to/impuesto_bot && source venv/bin/activate && python scripts/sync_tax_calendar.py
```

This will automatically sync current year and next year calendars.

## Verification

Check loaded data:

```bash
curl "https://mslfndlzjqttteihiopt.supabase.co/rest/v1/calendar_deadlines?select=deadline_date,tax_type,tax_model&order=deadline_date.asc" \
  -H "apikey: YOUR_API_KEY"
```

## Notes

- Calendar data is **NOT indexed in Elasticsearch** (only stored in Supabase)
- Each year should be synced separately
- Old deadlines for the same year are cleared before inserting new ones
- Mock data is currently used (real scraping logic needs AEAT website parsing)

## Next Steps

- [ ] Implement real AEAT website scraping (currently uses mock data)
- [ ] Add support for regional calendar variations
- [ ] Implement reminder notifications based on deadlines
- [ ] Add validation for deadline dates

