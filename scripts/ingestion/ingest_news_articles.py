"""
Ингестор новостных статей в поисковый индекс и Supabase.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Set

from langchain.schema import Document

try:  # pragma: no cover
    from scripts.ingestion.base_ingestor import BaseIngestor
except ModuleNotFoundError:  # pragma: no cover
    class BaseIngestor:  # type: ignore
        def __init__(self, *_, document_type: str | None = None, **__):
            self.document_type = document_type

try:  # pragma: no cover
    from app.services.supabase_service import supabase_service
except ModuleNotFoundError:  # pragma: no cover
    supabase_service = None  # type: ignore


def _parse_datetime(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class NewsArticlesIngestor(BaseIngestor):
    """Ингестор новостей."""

    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 100):
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            document_type="news",
        )

    def load_articles(self, source: Path | str) -> List[dict]:
        path = Path(source)
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        articles = payload.get("articles", [])
        return [article for article in articles if article.get("article_url")]

    def filter_new_articles(self, articles: Iterable[dict], existing_urls: Set[str]) -> List[dict]:
        seen: Set[str] = set()
        filtered: List[dict] = []

        for article in articles:
            url = article.get("article_url")
            if not url or url in existing_urls or url in seen:
                continue
            seen.add(url)
            filtered.append(article)

        return filtered

    def prepare_documents(self, articles: Iterable[dict]) -> List[Document]:
        documents: List[Document] = []

        for article in articles:
            summary = article.get("summary") or ""
            content = article.get("content") or ""
            body = "\n".join(filter(None, [article.get("article_title"), summary, content]))

            published_at = _parse_datetime(article.get("published_at"))

            metadata = {
                "source_type": "news",
                "article_url": article.get("article_url"),
                "article_title": article.get("article_title"),
                "news_source": article.get("news_source"),
                "author": article.get("author"),
                "published_at": published_at,
                "summary": summary,
                "categories": article.get("categories") or [],
                "keywords": article.get("keywords") or [],
                "relevance_score": article.get("relevance_score"),
                "tax_related": article.get("tax_related", False),
            }

            doc = Document(
                page_content=body.strip(),
                metadata=metadata,
            )
            documents.append(doc)

        return documents

    def get_existing_urls(self) -> Set[str]:
        if not supabase_service or not getattr(supabase_service, "connection", None):
            return set()
        try:
            cursor = supabase_service.connection.cursor()
            cursor.execute("SELECT article_url FROM news_articles_metadata")
            rows = cursor.fetchall()
            return {row["article_url"] for row in rows if row.get("article_url")}
        except Exception:
            supabase_service.connection.rollback()
            return set()

    def save_articles_metadata(self, articles: Iterable[dict]) -> None:
        if not supabase_service or not getattr(supabase_service, "connection", None):
            return

        try:
            cursor = supabase_service.connection.cursor()
            for article in articles:
                cursor.execute(
                    """
                    INSERT INTO news_articles_metadata (
                        article_url,
                        article_title,
                        news_source,
                        author,
                        published_at,
                        scraped_at,
                        summary,
                        content_length,
                        categories,
                        keywords,
                        tax_related,
                        relevance_score,
                        metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (article_url) DO NOTHING
                    """,
                    (
                        article.get("article_url"),
                        article.get("article_title"),
                        article.get("news_source"),
                        article.get("author"),
                        _parse_datetime(article.get("published_at")),
                        article.get("summary"),
                        len((article.get("content") or "")),
                        article.get("categories"),
                        article.get("keywords"),
                        article.get("tax_related", False),
                        article.get("relevance_score", 0.0),
                        json.dumps({k: v for k, v in article.items() if k not in {"content"}}),
                    ),
                )
            supabase_service.connection.commit()
        except Exception:
            supabase_service.connection.rollback()

    def process_json(self, json_path: Path | str) -> bool:
        json_path = Path(json_path)
        articles = self.load_articles(json_path)
        if not articles:
            return False

        existing = self.get_existing_urls()
        new_articles = self.filter_new_articles(articles, existing)
        if not new_articles:
            return False

        documents = self.prepare_documents(new_articles)
        if not documents:
            return False

        if not self.initialize():
            return False

        try:
            self.save_articles_metadata(new_articles)
            success = self.ingest_documents(documents)
            return success
        finally:
            self.cleanup()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest news articles JSON into search index")
    parser.add_argument("json_path", help="Path to JSON file with articles")
    args = parser.parse_args()

    ingestor = NewsArticlesIngestor()
    success = ingestor.process_json(args.json_path)
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover - CLI
    main()
