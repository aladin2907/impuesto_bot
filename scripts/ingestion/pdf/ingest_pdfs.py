#!/usr/bin/env python3
"""
Ingestion script for Spanish tax law PDFs into Supabase pgvector.

Reads PDFs, splits into semantic chunks, generates OpenAI embeddings (1536d),
and inserts into pdf_documents_content table.

Usage:
    python -m scripts.ingestion.pdf.ingest_pdfs
"""
import os
import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from pypdf import PdfReader
from supabase import create_client
from openai import OpenAI

# --- Config ---
PDF_DIR = project_root / "data" / "pdf_documents"
CHUNK_SIZE = 1000       # characters per chunk
CHUNK_OVERLAP = 200     # overlap between chunks
BATCH_SIZE = 50         # rows per Supabase insert batch
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# Document metadata
PDF_METADATA = {
    "Ley_35_2006.pdf": {
        "document_id": "ley_35_2006_irpf",
        "document_title": "Ley 35/2006, del Impuesto sobre la Renta de las Personas Físicas (IRPF)",
        "document_type": "law",
        "categories": ["irpf"],
        "region": "national",
        "source_url": "https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764",
        "publication_date": "2006-11-29",
    },
    "Ley_37_1992.pdf": {
        "document_id": "ley_37_1992_iva",
        "document_title": "Ley 37/1992, del Impuesto sobre el Valor Añadido (IVA)",
        "document_type": "law",
        "categories": ["iva"],
        "region": "national",
        "source_url": "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740",
        "publication_date": "1992-12-29",
    },
    "Ley_27_2014.pdf": {
        "document_id": "ley_27_2014_sociedades",
        "document_title": "Ley 27/2014, del Impuesto sobre Sociedades",
        "document_type": "law",
        "categories": ["sociedades"],
        "region": "national",
        "source_url": "https://www.boe.es/buscar/act.php?id=BOE-A-2014-12328",
        "publication_date": "2014-11-28",
    },
    "RD_439_2007.pdf": {
        "document_id": "rd_439_2007_reglamento_irpf",
        "document_title": "Real Decreto 439/2007, Reglamento del IRPF",
        "document_type": "regulation",
        "categories": ["irpf"],
        "region": "national",
        "source_url": "https://www.boe.es/buscar/act.php?id=BOE-A-2007-6820",
        "publication_date": "2007-03-31",
    },
}


def extract_text_from_pdf(pdf_path: Path) -> List[Dict]:
    """Extract text from PDF, return list of {page_number, text}."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append({"page_number": i + 1, "text": text.strip()})
    return pages


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks at sentence boundaries."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end near chunk boundary
            for sep in ['. ', '.\n', '\n\n', '; ', '\n']:
                last_sep = text.rfind(sep, start + chunk_size // 2, end + 100)
                if last_sep > start:
                    end = last_sep + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk and len(chunk) > 50:  # skip tiny chunks
            chunks.append(chunk)

        start = end - overlap
        if start >= len(text):
            break

    return chunks


def prepare_chunks(pdf_path: Path, metadata: Dict) -> List[Dict]:
    """Extract PDF → split into chunks → add metadata."""
    filename = pdf_path.name
    print(f"\n📄 Processing: {filename}")

    pages = extract_text_from_pdf(pdf_path)
    print(f"   Pages extracted: {len(pages)}")

    all_chunks = []
    chunk_index = 0

    for page_data in pages:
        page_num = page_data["page_number"]
        page_chunks = chunk_text(page_data["text"])

        for chunk_text_content in page_chunks:
            all_chunks.append({
                "document_id": metadata["document_id"],
                "document_title": metadata["document_title"],
                "document_type": metadata["document_type"],
                "content": chunk_text_content,
                "chunk_index": chunk_index,
                "page_number": page_num,
                "categories": metadata["categories"],
                "region": metadata["region"],
                "source_url": metadata.get("source_url"),
                "publication_date": metadata.get("publication_date"),
                "metadata": {"filename": filename},
            })
            chunk_index += 1

    print(f"   Chunks created: {chunk_index}")
    return all_chunks


def generate_embeddings(texts: List[str], client: OpenAI) -> List[List[float]]:
    """Generate OpenAI embeddings for a batch of texts."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def main():
    # Init clients
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY"),
    )

    # Collect all chunks from all PDFs
    all_chunks = []
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files in {PDF_DIR}")

    for pdf_path in sorted(pdf_files):
        metadata = PDF_METADATA.get(pdf_path.name)
        if not metadata:
            print(f"⚠️  No metadata for {pdf_path.name}, skipping")
            continue
        chunks = prepare_chunks(pdf_path, metadata)
        all_chunks.extend(chunks)

    print(f"\n📊 Total chunks to embed: {len(all_chunks)}")

    # Generate embeddings in batches
    print("\n🧠 Generating OpenAI embeddings...")
    embedding_batch_size = 100  # OpenAI supports up to 2048
    for i in range(0, len(all_chunks), embedding_batch_size):
        batch = all_chunks[i:i + embedding_batch_size]
        texts = [c["content"] for c in batch]
        embeddings = generate_embeddings(texts, openai_client)
        for j, emb in enumerate(embeddings):
            all_chunks[i + j]["content_embedding"] = emb
        print(f"   Embedded {min(i + embedding_batch_size, len(all_chunks))}/{len(all_chunks)}")

    # Insert into Supabase
    print(f"\n💾 Inserting {len(all_chunks)} chunks into Supabase...")
    inserted = 0
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i:i + BATCH_SIZE]
        try:
            result = supabase.table("pdf_documents_content").insert(batch).execute()
            count = len(result.data) if result.data else 0
            inserted += count
            print(f"   ✅ Batch {i // BATCH_SIZE + 1}: {count} rows inserted")
        except Exception as e:
            print(f"   ❌ Batch {i // BATCH_SIZE + 1} failed: {e}")
            # Try one by one
            for row in batch:
                try:
                    supabase.table("pdf_documents_content").insert(row).execute()
                    inserted += 1
                except Exception as e2:
                    print(f"      ❌ Row {row['document_id']}:{row['chunk_index']} failed: {e2}")

    print(f"\n🎉 Done! Inserted {inserted}/{len(all_chunks)} chunks into pdf_documents_content")


if __name__ == "__main__":
    main()
