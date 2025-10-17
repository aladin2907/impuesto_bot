"""
Ингестор региональных документов DOGV (Valencia).
"""

from __future__ import annotations

import json
from datetime import datetime, date
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


def _parse_date(value: str | None) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


class ValenciaDOGVIngestor(BaseIngestor):
    """Ингестор региональных документов DOGV."""

    def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 120):
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            document_type="regional",
        )

    def load_documents(self, source: Path | str) -> List[dict]:
        path = Path(source)
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        documents = payload.get("documents", [])
        return [doc for doc in documents if doc.get("source_url")]

    def get_existing_urls(self) -> Set[str]:
        if not supabase_service or not getattr(supabase_service, "connection", None):
            return set()
        try:
            cursor = supabase_service.connection.cursor()
            cursor.execute("SELECT source_url FROM pdf_documents_metadata")
            rows = cursor.fetchall()
            return {row["source_url"] for row in rows if row.get("source_url")}
        except Exception:
            supabase_service.connection.rollback()
            return set()

    def filter_new_documents(self, documents: Iterable[dict], existing_urls: Set[str]) -> List[dict]:
        seen: Set[str] = set()
        filtered: List[dict] = []

        for doc in documents:
            url = doc.get("source_url")
            if not url or url in existing_urls or url in seen:
                continue
            seen.add(url)
            filtered.append(doc)

        return filtered

    def prepare_documents(self, documents: Iterable[dict]) -> List[Document]:
        prepared: List[Document] = []
        for doc in documents:
            title = doc.get("document_title") or ""
            summary = doc.get("summary") or ""
            content = doc.get("content") or ""
            text = "\n".join(filter(None, [title, summary, content])).strip()

            metadata = {
                "source_type": "regional",
                "source_url": doc.get("source_url"),
                "document_title": title,
                "document_type": doc.get("document_type") or "regional_regulation",
                "region": doc.get("region", "Valencia"),
                "publication_date": _parse_date(doc.get("publication_date")),
                "categories": doc.get("categories") or [],
                "tags": doc.get("tags") or [],
            }

            prepared.append(Document(page_content=text, metadata=metadata))
        return prepared

    def save_documents_metadata(self, documents: Iterable[dict]) -> None:
        if not supabase_service or not getattr(supabase_service, "connection", None):
            return

        try:
            cursor = supabase_service.connection.cursor()
            for doc in documents:
                cursor.execute(
                    """
                    INSERT INTO pdf_documents_metadata (
                        document_title,
                        document_type,
                        source_url,
                        description,
                        publication_date,
                        region,
                        metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        doc.get("document_title"),
                        doc.get("document_type") or "regional_regulation",
                        doc.get("source_url"),
                        doc.get("summary"),
                        _parse_date(doc.get("publication_date")),
                        doc.get("region", "Valencia"),
                        json.dumps({k: v for k, v in doc.items() if k not in {"content"}}),
                    ),
                )
            supabase_service.connection.commit()
        except Exception:
            supabase_service.connection.rollback()

    def process_json(self, json_path: Path | str) -> bool:
        json_path = Path(json_path)
        documents = self.load_documents(json_path)
        if not documents:
            return False

        existing = self.get_existing_urls()
        new_docs = self.filter_new_documents(documents, existing)
        if not new_docs:
            return False

        prepared = self.prepare_documents(new_docs)
        if not prepared:
            return False

        if not self.initialize():
            return False

        try:
            self.save_documents_metadata(new_docs)
            success = self.ingest_documents(prepared)
            return success
        finally:
            self.cleanup()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest Valencia DOGV regional documents")
    parser.add_argument("json_path", help="Path to JSON with DOGV documents")
    args = parser.parse_args()

    ingestor = ValenciaDOGVIngestor()
    success = ingestor.process_json(args.json_path)
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
