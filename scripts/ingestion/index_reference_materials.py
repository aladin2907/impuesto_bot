#!/usr/bin/env python3
"""
Index tax reference materials to Elasticsearch
Includes IVA rates, IRPF brackets, and practical guides
"""

import json
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import settings
from app.services.elasticsearch_service import elastic_service
from app.services.llm.openai_service import openai_service


def generate_embedding(text: str) -> list:
    """Generate OpenAI embedding for text"""
    try:
        response = openai_service.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def index_reference_materials():
    """Index reference materials to Elasticsearch"""
    
    # Connect to Elasticsearch
    elastic_service.connect()
    if not elastic_service.client:
        print("❌ Failed to connect to Elasticsearch")
        return False
    
    print("✅ Connected to Elasticsearch")
    
    # Load reference data
    data_file = project_root / "data" / "reference_materials" / "tax_reference_data.json"
    
    if not data_file.exists():
        print(f"❌ Data file not found: {data_file}")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📄 Loaded {len(data['reference_materials'])} reference materials")
    
    # Create index if not exists
    index_name = "reference_materials"
    
    if not elastic_service.client.indices.exists(index=index_name):
        print(f"🔧 Creating index: {index_name}")
        
        mapping = {
            "mappings": {
                "properties": {
                    "reference_id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "category": {"type": "keyword"},
                    "subcategory": {"type": "keyword"},
                    "content": {"type": "text"},
                    "content_embedding": {
                        "type": "dense_vector",
                        "dims": 1536,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "keywords": {"type": "keyword"},
                    "applies_to": {"type": "keyword"},
                    "last_updated": {"type": "date"},
                    "references": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "source_url": {"type": "keyword"},
                    "language": {"type": "keyword"},
                    "created_at": {"type": "date"}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index": {
                    "max_result_window": 10000
                }
            }
        }
        
        elastic_service.client.indices.create(index=index_name, body=mapping)
        print(f"✅ Index created: {index_name}")
    else:
        print(f"ℹ️  Index already exists: {index_name}")
    
    # Index documents
    success_count = 0
    error_count = 0
    
    for material in data['reference_materials']:
        try:
            # Generate embedding
            full_text = f"{material['title']} {material['content']}"
            embedding = generate_embedding(full_text)
            
            if not embedding:
                print(f"⚠️  No embedding for: {material['id']}")
            
            # Prepare document
            doc = {
                "reference_id": material['id'],
                "title": material['title'],
                "category": material['category'],
                "subcategory": material['subcategory'],
                "content": material['content'],
                "content_embedding": embedding,
                "keywords": material.get('keywords', []),
                "applies_to": material.get('applies_to', []),
                "last_updated": material['last_updated'],
                "references": material.get('references', []),
                "source": data['source'],
                "source_url": data['source_url'],
                "language": data['language'],
                "created_at": data['created_at']
            }
            
            # Index document
            elastic_service.client.index(
                index=index_name,
                id=material['id'],
                body=doc
            )
            
            success_count += 1
            print(f"✅ Indexed: {material['id']} - {material['title']}")
            
        except Exception as e:
            error_count += 1
            print(f"❌ Error indexing {material['id']}: {e}")
    
    # Refresh index
    elastic_service.client.indices.refresh(index=index_name)
    
    # Summary
    print("\n" + "="*70)
    print(f"📊 Indexing Summary:")
    print(f"   - Total documents: {len(data['reference_materials'])}")
    print(f"   - Successfully indexed: {success_count}")
    print(f"   - Errors: {error_count}")
    print("="*70)
    
    # Verify
    count_result = elastic_service.client.count(index=index_name)
    print(f"\n✅ Total documents in index: {count_result['count']}")
    
    return error_count == 0


if __name__ == "__main__":
    print("🚀 Starting reference materials indexing...")
    print(f"📁 Project root: {project_root}")
    print(f"🔧 Elasticsearch URL: {settings.ELASTICSEARCH_URL}")
    print()
    
    success = index_reference_materials()
    
    if success:
        print("\n✅ Reference materials indexed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Indexing completed with errors")
        sys.exit(1)

