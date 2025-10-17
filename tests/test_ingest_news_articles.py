import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain.schema import Document

from scripts.ingestion.ingest_news_articles import NewsArticlesIngestor


@pytest.fixture
def sample_articles():
    return [
        {
            "article_url": "https://example.com/news/1",
            "article_title": "Cambio IRPF 2025",
            "news_source": "Expansión",
            "author": "Ana Pérez",
            "published_at": "2025-09-29T10:00:00Z",
            "summary": "Resumen IRPF",
            "content": "Contenido...",
            "categories": ["irpf", "autonomos"],
            "keywords": ["IRPF", "2025"],
            "relevance_score": 0.92,
            "tax_related": True,
        },
        {
            "article_url": "https://example.com/news/2",
            "article_title": "IVA nuevas obligaciones",
            "news_source": "Cinco Días",
            "author": "Juan López",
            "published_at": "2025-09-28T12:00:00Z",
            "summary": "Resumen IVA",
            "content": "Contenido IVA...",
            "categories": ["iva"],
            "keywords": ["IVA", "facturación"],
            "relevance_score": 0.85,
            "tax_related": True,
        },
    ]


def test_filter_new_articles_removes_duplicates(sample_articles):
    ingestor = NewsArticlesIngestor()
    duplicate_input = sample_articles + [sample_articles[0]]
    existing_urls = {"https://example.com/news/2"}

    result = ingestor.filter_new_articles(duplicate_input, existing_urls)

    assert len(result) == 1
    assert result[0]["article_url"] == "https://example.com/news/1"


def test_prepare_documents(sample_articles):
    ingestor = NewsArticlesIngestor()
    docs = ingestor.prepare_documents(sample_articles)

    assert len(docs) == 2
    assert all(isinstance(doc, Document) for doc in docs)
    first = docs[0]
    assert "Cambio IRPF" in first.page_content
    assert first.metadata["article_url"] == "https://example.com/news/1"
    assert first.metadata["news_source"] == "Expansión"
    assert first.metadata["published_at"] == datetime.fromisoformat("2025-09-29T10:00:00+00:00")


def test_process_json_deduplicates_and_ingests(tmp_path, sample_articles):
    json_path = tmp_path / "news.json"
    json_path.write_text(json.dumps({"articles": sample_articles}), encoding="utf-8")

    class DummyNewsIngestor(NewsArticlesIngestor):
        def __init__(self):
            super().__init__()
            self.initialize_called = False
            self.cleaned = False
            self.ingested_documents = None
            self.saved_articles = None

        def initialize(self):
            self.initialize_called = True
            return True

        def ingest_documents(self, documents, metadatas=None):
            self.ingested_documents = documents
            return True

        def cleanup(self):
            self.cleaned = True

        def get_existing_urls(self):
            return {"https://example.com/news/2"}

        def save_articles_metadata(self, articles):
            self.saved_articles = articles

    ingestor = DummyNewsIngestor()
    result = ingestor.process_json(json_path)

    assert result is True
    assert ingestor.initialize_called is True
    assert ingestor.cleaned is True
    assert len(ingestor.ingested_documents) == 1
    assert ingestor.ingested_documents[0].metadata["article_url"] == "https://example.com/news/1"
    assert len(ingestor.saved_articles) == 1
