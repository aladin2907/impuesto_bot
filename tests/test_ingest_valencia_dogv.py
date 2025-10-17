import json
from datetime import date
from pathlib import Path

import pytest
from langchain.schema import Document

from scripts.ingestion.ingest_valencia_dogv import ValenciaDOGVIngestor


@pytest.fixture
def sample_docs():
    return [
        {
            "source_url": "https://dogv.gva.es/datos/document/medidas-2025",
            "document_title": "Ley de medidas fiscales 2025",
            "document_type": "regional_regulation",
            "region": "Valencia",
            "publication_date": "2025-01-10",
            "summary": "Resumen medidas fiscales 2025",
            "content": "Contenido completo del DOGV...",
            "categories": ["fiscalidad", "valencia"],
            "tags": ["deducciones", "autonomos"],
        },
        {
            "source_url": "https://dogv.gva.es/datos/document/medidas-2024",
            "document_title": "Ley de medidas fiscales 2024",
            "document_type": "regional_regulation",
            "region": "Valencia",
            "publication_date": "2024-01-12",
            "summary": "Resumen 2024",
            "content": "Contenido 2024...",
        },
    ]


def test_filter_new_documents(sample_docs):
    ingestor = ValenciaDOGVIngestor()
    existing = {"https://dogv.gva.es/datos/document/medidas-2024"}
    incoming = sample_docs + [sample_docs[0]]

    filtered = ingestor.filter_new_documents(incoming, existing)

    assert len(filtered) == 1
    assert filtered[0]["source_url"] == "https://dogv.gva.es/datos/document/medidas-2025"


def test_prepare_documents(sample_docs):
    ingestor = ValenciaDOGVIngestor()
    docs = ingestor.prepare_documents(sample_docs)

    assert len(docs) == 2
    first = docs[0]
    assert isinstance(first, Document)
    assert "Ley de medidas fiscales 2025" in first.page_content
    assert first.metadata["source_url"] == "https://dogv.gva.es/datos/document/medidas-2025"
    assert first.metadata["publication_date"] == date(2025, 1, 10)
    assert first.metadata["region"] == "Valencia"


def test_process_json_runs_ingestion(tmp_path, sample_docs):
    json_path = tmp_path / "dogv.json"
    json_path.write_text(json.dumps({"documents": sample_docs}), encoding="utf-8")

    class DummyIngestor(ValenciaDOGVIngestor):
        def __init__(self):
            super().__init__()
            self.initialize_called = False
            self.cleaned = False
            self.ingested_documents = None
            self.saved_meta = None

        def initialize(self):
            self.initialize_called = True
            return True

        def ingest_documents(self, documents, metadatas=None):
            self.ingested_documents = documents
            return True

        def cleanup(self):
            self.cleaned = True

        def get_existing_urls(self):
            return {"https://dogv.gva.es/datos/document/medidas-2024"}

        def save_documents_metadata(self, docs):
            self.saved_meta = docs

    ingestor = DummyIngestor()
    result = ingestor.process_json(json_path)

    assert result is True
    assert ingestor.initialize_called is True
    assert ingestor.cleaned is True
    assert len(ingestor.ingested_documents) == 1
    assert ingestor.ingested_documents[0].metadata["source_url"] == "https://dogv.gva.es/datos/document/medidas-2025"
    assert len(ingestor.saved_meta) == 1
