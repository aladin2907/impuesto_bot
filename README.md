# TuExpertoFiscal NAIL

AI-powered tax expert bot for Spain, providing accurate answers based on Spanish tax law, news, and community discussions.

## Features

- 🤖 AI-powered responses using RAG (Retrieval-Augmented Generation)
- 🔍 Hybrid search (semantic + keyword) with Elasticsearch
- 📚 Knowledge base including Spanish Tax Code, tax calendar, and news
- 💬 Multi-platform support (Telegram, WhatsApp)
- 👤 User management with subscription tiers
- 📊 Conversation history and summarization
- 🔄 Automated weekly parsing of Telegram channels

## Technology Stack

- **Backend:** Python 3.11+, FastAPI
- **AI/RAG:** LangChain, OpenAI GPT-4o
- **Search Engine:** Elasticsearch (Elastic Cloud)
- **Database:** Supabase (PostgreSQL)
- **Messaging:** aiogram (Telegram)

## Project Structure

```
impuesto_bot/
├── app/
│   ├── config/         # Configuration and settings
│   ├── services/       # Business logic (Elastic, Supabase, RAG)
│   ├── models/         # Data models
│   └── utils/          # Helper functions
├── scripts/            # Data ingestion and automation scripts
├── database/           # SQL schemas and migrations
├── docs/               # Documentation
└── tests/              # Unit and integration tests
```

## Setup

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

### 3. Initialize Database

Run the SQL script in your Supabase dashboard:

```bash
# Copy the contents of database/schema.sql and execute in Supabase SQL Editor
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload
```

## Development Roadmap

See `docs/architecture_and_plan.md` for the complete development plan.

## License

Proprietary - All rights reserved

---

*Developed by NAIL - Nahornyi AI Lab*

