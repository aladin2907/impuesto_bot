import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain.schema import Document

from scripts.ingestion.ingest_aeat_website import AEATResourcesIngestor


@pytest.fixture
def sample_resources():
    return [
        {
            "resource_url": "https://sede.agenciatributaria.gob.es/Modelo303.pdf",
            "resource_title": "Instrucciones Modelo 303",
            "resource_type": "guide",
            "model_number": "Modelo 303",
            "fiscal_year": 2025,
            "language": "es",
            "version_date": "2025-01-15",
            "is_current_version": True,
            "summary": "Guía para la autoliquidación del IVA",
            "content": "Contenido detallado del modelo 303...",
        },
        {
            "resource_url": "https://sede.agenciatributaria.gob.es/Modelo111.pdf",
            "resource_title": "Instrucciones Modelo 111",
            "resource_type": "guide",
            "model_number": "Modelo 111",
            "fiscal_year": 2025,
            "language": "es",
            "version_date": "2025-01-10",
            "is_current_version": True,
            "summary": "Guía de retenciones",
            "content": "Contenido 111...",
        },
    ]


def test_filter_new_resources_ignores_existing(sample_resources):
    ingestor = AEATResourcesIngestor()
    existing = {"https://sede.agenciatributaria.gob.es/Modelo111.pdf"}
    incoming = sample_resources + [sample_resources[0]]

    filtered = ingestor.filter_new_resources(incoming, existing)

    assert len(filtered) == 1
    assert filtered[0]["resource_url"] == "https://sede.agenciatributaria.gob.es/Modelo303.pdf"


def test_prepare_documents(sample_resources):
    ingestor = AEATResourcesIngestor()
    docs = ingestor.prepare_documents(sample_resources)

    assert len(docs) == 2
    doc = docs[0]
    assert isinstance(doc, Document)
    assert "Instrucciones Modelo 303" in doc.page_content
    assert doc.metadata["resource_url"] == "https://sede.agenciatributaria.gob.es/Modelo303.pdf"
    assert doc.metadata["model_number"] == "Modelo 303"
    assert doc.metadata["version_date"] == date(2025, 1, 15)


def test_process_json_deduplicates_and_ingests(tmp_path, sample_resources):
    json_path = tmp_path / "aeat_resources.json"
    json_path.write_text(json.dumps({"resources": sample_resources}), encoding="utf-8")

    class DummyIngestor(AEATResourcesIngestor):
        def __init__(self):
            super().__init__()
            self.initialize_called = False
            self.cleaned = False
            self.ingested_documents = None
            self.saved_metadata = None

        def initialize(self):
            self.initialize_called = True
            return True

        def ingest_documents(self, documents, metadatas=None):
            self.ingested_documents = documents
            return True

        def cleanup(self):
            self.cleaned = True

        def get_existing_urls(self):
            return {"https://sede.agenciatributaria.gob.es/Modelo111.pdf"}

        def save_resources_metadata(self, resources):
            self.saved_metadata = resources

    ingestor = DummyIngestor()
    result = ingestor.process_json(json_path)

    assert result is True
    assert ingestor.initialize_called is True
    assert ingestor.cleaned is True
    assert len(ingestor.ingested_documents) == 1
    assert ingestor.ingested_documents[0].metadata["resource_url"] == "https://sede.agenciatributaria.gob.es/Modelo303.pdf"
    assert len(ingestor.saved_metadata) == 1
