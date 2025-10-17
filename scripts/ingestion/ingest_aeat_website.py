"""
Ингестор официальных ресурсов AEAT (инструкции, формы, FAQ).
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


class AEATResourcesIngestor(BaseIngestor):
    """Ингестор для официальных ресурсов AEAT."""

    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 150):
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            document_type="aeat_resource",
        )

    def load_resources(self, source: Path | str) -> List[dict]:
        path = Path(source)
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        resources = payload.get("resources", [])
        return [res for res in resources if res.get("resource_url")]

    def get_existing_urls(self) -> Set[str]:
        if not supabase_service or not getattr(supabase_service, "connection", None):
            return set()
        try:
            cursor = supabase_service.connection.cursor()
            cursor.execute("SELECT resource_url FROM aeat_resources_metadata")
            rows = cursor.fetchall()
            return {row["resource_url"] for row in rows if row.get("resource_url")}
        except Exception:
            supabase_service.connection.rollback()
            return set()

    def filter_new_resources(self, resources: Iterable[dict], existing_urls: Set[str]) -> List[dict]:
        seen: Set[str] = set()
        filtered: List[dict] = []

        for res in resources:
            url = res.get("resource_url")
            if not url or url in existing_urls or url in seen:
                continue
            seen.add(url)
            filtered.append(res)

        return filtered

    def prepare_documents(self, resources: Iterable[dict]) -> List[Document]:
        documents: List[Document] = []

        for res in resources:
            title = res.get("resource_title") or ""
            summary = res.get("summary") or ""
            content = res.get("content") or ""
            text = "\n".join(filter(None, [title, summary, content])).strip()

            metadata = {
                "source_type": "aeat",
                "resource_url": res.get("resource_url"),
                "resource_title": title,
                "resource_type": res.get("resource_type"),
                "model_number": res.get("model_number"),
                "fiscal_year": res.get("fiscal_year"),
                "language": res.get("language", "es"),
                "version_date": _parse_date(res.get("version_date")),
                "is_current_version": res.get("is_current_version", True),
            }

            doc = Document(page_content=text, metadata=metadata)
            documents.append(doc)

        return documents

    def save_resources_metadata(self, resources: Iterable[dict]) -> None:
        if not supabase_service or not getattr(supabase_service, "connection", None):
            return

        try:
            cursor = supabase_service.connection.cursor()
            for res in resources:
                cursor.execute(
                    """
                    INSERT INTO aeat_resources_metadata (
                        resource_url,
                        resource_title,
                        resource_type,
                        model_number,
                        fiscal_year,
                        language,
                        version_date,
                        is_current_version,
                        metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (resource_url) DO NOTHING
                    """,
                    (
                        res.get("resource_url"),
                        res.get("resource_title"),
                        res.get("resource_type"),
                        res.get("model_number"),
                        res.get("fiscal_year"),
                        res.get("language", "es"),
                        _parse_date(res.get("version_date")),
                        res.get("is_current_version", True),
                        json.dumps({k: v for k, v in res.items() if k not in {"content"}}),
                    ),
                )
            supabase_service.connection.commit()
        except Exception:
            supabase_service.connection.rollback()

    def process_json(self, json_path: Path | str) -> bool:
        json_path = Path(json_path)
        resources = self.load_resources(json_path)
        if not resources:
            return False

        existing = self.get_existing_urls()
        new_resources = self.filter_new_resources(resources, existing)
        if not new_resources:
            return False

        documents = self.prepare_documents(new_resources)
        if not documents:
            return False

        if not self.initialize():
            return False

        try:
            self.save_resources_metadata(new_resources)
            success = self.ingest_documents(documents)
            return success
        finally:
            self.cleanup()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest AEAT resources JSON into search index")
    parser.add_argument("json_path", help="Path to JSON file with AEAT resources")
    args = parser.parse_args()

    ingestor = AEATResourcesIngestor()
    success = ingestor.process_json(args.json_path)
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
