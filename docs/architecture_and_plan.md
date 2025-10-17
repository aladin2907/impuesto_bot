# TuExpertoFiscal NAIL: AI Tax Expert Bot - Architecture & Development Plan

This document outlines the architecture, technology stack, database schema, and step-by-step plan for developing the AI-powered tax expert bot for Spain.

## 1. System Architecture

The system is built on a **Retrieval-Augmented Generation (RAG)** architecture.

- **Data Ingesters:** Scripts for parsing Telegram groups, scraping news websites, and processing official documents (e.g., Spanish Tax Code).
- **Knowledge Base:**
    - **Elasticsearch:** The core search engine, used for powerful hybrid search (semantic vector search + full-text keyword search) to find the most relevant information chunks.
    - **Supabase (PostgreSQL):** The primary relational database for storing structured data like user profiles, conversation history, subscriptions, and document metadata.
- **AI Core:**
    - **Orchestrator (LangChain):** Manages the RAG pipeline. It takes a user query, searches for context in Elasticsearch, and builds a precise prompt for the LLM.
    - **LLM (OpenAI GPT-4o):** The large language model that generates the final, human-like answer based on the user's query and the retrieved context.
- **API & Messaging Interface:**
    - **FastAPI Backend:** A Python-based API server that handles incoming requests from messaging platforms.
    - **Messaging Adapters (aiogram):** Modules responsible for communicating with the APIs of different platforms (Telegram, WhatsApp).

## 2. Technology Stack

- **Backend Language:** Python 3.11+
- **Backend Framework:** FastAPI
- **AI/RAG Framework:** LangChain (unified LLM interface + RAG chains)
- **LLM Providers (via LangChain):**
  - OpenAI (GPT-4o, GPT-4o-mini)
  - Google Gemini (gemini-pro, gemini-1.5-flash)
  - Anthropic Claude (claude-3.5-sonnet)
  - OpenRouter (access to 100+ models)
- **Search & Vector DB:** Elasticsearch (Elastic Cloud) + LangChain integration
- **Relational DB:** Supabase (PostgreSQL)
- **Telegram Bot Framework:** aiogram
- **Deployment (TBD):** Docker, Cloud Run/Render/Heroku

## 3. Database Schema (Supabase/PostgreSQL)

The database is designed to be multi-platform and support subscription models.

- **`users`**: Core user profiles.
- **`user_channels`**: Links users to their accounts on different messaging platforms (Telegram, WhatsApp).
- **`dialogue_sessions`**: Groups conversations for context and summarization.
- **`messages`**: Stores every individual message for history and analysis.
- **`user_tax_profile`**: Stores personal data for tax calculations.
- **`documents`**: Metadata for source documents that are processed and indexed into Elasticsearch.


(The full SQL script is available in `database/schema.sql`)

## 4. Step-by-Step Development Plan

### Phase 1: Foundation (завершено)

1. **[✓] Настроить проект:** Базовая структура, зависимости, `.env`.
2. **[✓] Сервисы ИИ и поиска:** Унифицированный LLM‑сервис, клиенты Supabase и Elasticsearch.
3. **[✓] Схемы данных:** Развёрнута актуальная схема `users`, `messages`, `documents` и пр.
4. **[✓] API и базовый поиск:** FastAPI приложение (`app/api/webhook.py`) + `SearchService` с гибридным поиском и сохранением истории.
5. **[✓] Сбор исходных данных:** Выкачаны Telegram треды, собраны тестовые наборы для календаря, новостей и PDF.

### Phase 2: Автоматизация сбора и индексации

1. **[ ] Привести `BaseIngestor` к общему стандарту:** единая инициализация LLM/ES/Supabase, единое логирование и мониторинг.
2. **[ ] Реализовать недостающие инжесторы:**
   - `ingest_tax_calendar.py` — парсинг календаря и запись в Supabase + Elasticsearch.
   - `ingest_news_articles.py` — ежедневный скрапинг/обновление новостей.
   - `ingest_aeat_website.py`, `ingest_valencia_dogv.py` — официальные и региональные источники.
3. **[ ] Дополнить существующие скрипты индексаторами** (чтобы после загрузки в Supabase данные автоматически попадали в поисковый индекс).
4. **[ ] Настроить расписания:**
   - cron/GitHub Actions для Telegram (еженедельно) и новостей (ежедневно);
   - ручной запуск/cron для календаря и PDF при появлении обновлений.
5. **[ ] Добавить валидацию загрузок:** отчёт об объёмах, дедупликация, трекинг `last_synced_at`.

### Phase 3: Поиск по каждому источнику

1. **[ ] Развести индексы/алиасы в Elasticsearch** по типам источников (telegram/news/pdf/calendar/aeat/regional).
2. **[ ] Добавить сервисные методы поиска** для каждого источника (например, `search_service.search_pdf(...)`, `search_news(...)`) с учётом специфических фильтров.
3. **[ ] Расширить API:**
   - Отдельные эндпоинты вида `/search/pdf`, `/search/news`, либо единый `/search` с параметром `sources`.
   - Строгая валидация набора источников и fallback на общий поиск.
4. **[ ] Обновить документацию и примеры (Swagger, docs/N8N_EXAMPLES.md)** под новый контракт.
5. **[ ] Добавить интеграционные тесты**, покрывающие поиск по каждому источнику и комбинации фильтров.

### Phase 4: Интеграция с n8n (источники + обратная отправка)

1. **[ ] Новый webhook-эндпоинт** (например, `/n8n/search`):
   - принимает список источников, текст запроса, метаданные от n8n;
   - маршрутизирует запрос в нужные под‑поиски;
   - агрегирует и нормализует ответы.
2. **[ ] Обработать обратный вызов:** отправка результатов на `https://n8n.mafiavlc.org/webhook/59c06e61-a477-42df-8959-20f056f33189` с детальной структурой (источник, выдержка, метаданные).
3. **[ ] Логирование и ретраи:** хранить статусы запросов, повторять отправку в n8n при сбоях.
4. **[ ] Обновить `docs/N8N_EXAMPLES.md`** с новым форматом входа/выхода.
5. **[ ] Написать e2e тест/скрипт**, который имитирует n8n вызов и проверяет полный цикл.

### Phase 5: Эксплуатация и масштабирование

1. **[ ] Мониторинг и алерты:** метрики по индексации, времени ответа поиска, ошибкам n8n.
2. **[ ] Кеширование/квотирование:** ограничение запросов по источникам, кеш результатов для горячих тем.
3. **[ ] Резервное копирование данных:** регулярные выгрузки Supabase и снапшоты Elasticsearch.
4. **[ ] Дополнительные каналы:** после стабильной работы — WhatsApp/веб‑виджет, но с переиспользованием новой архитектуры поиска.
5. **[ ] Подготовка к продакшену:** Docker/CI, секреты, ротация ключей, нагрузочные тесты.

---

*Developed by NAIL - Nahornyi AI Lab*
