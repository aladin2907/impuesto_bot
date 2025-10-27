#!/usr/bin/env python3
"""
Generate and add embeddings to PDF documents in Elasticsearch
This enables semantic search for PDF content
"""

import sys
import time
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.elasticsearch_service import elastic_service
from app.services.llm.llm_service import LLMService
from app.config.settings import settings


class PDFEmbeddingsGenerator:
    """Generate embeddings for PDF documents and update Elasticsearch"""
    
    def __init__(self):
        self.elastic = elastic_service
        self.llm = LLMService()
        self.index_name = "pdf_documents"
        self.batch_size = 10  # Process N documents at a time
        self.sleep_between_batches = 2  # seconds
        
    def initialize(self) -> bool:
        """Initialize services"""
        print("=" * 60)
        print("📄 PDF Embeddings Generator")
        print("=" * 60)
        
        # Connect to Elasticsearch
        if not self.elastic.connect():
            print("❌ Failed to connect to Elasticsearch")
            return False
        
        # Initialize LLM
        if not self.llm.initialize():
            print("❌ Failed to initialize LLM service")
            return False
        
        print("✅ Services initialized")
        return True
    
    def check_index_mapping(self) -> bool:
        """Check if pdf_documents has content_embedding field"""
        try:
            mapping = self.elastic.client.indices.get_mapping(index=self.index_name)
            properties = mapping[self.index_name]['mappings']['properties']
            
            if 'content_embedding' in properties:
                print("✅ Index already has content_embedding field")
                return True
            else:
                print("⚠️  Index missing content_embedding field")
                return False
                
        except Exception as e:
            print(f"❌ Error checking mapping: {e}")
            return False
    
    def update_index_mapping(self) -> bool:
        """Add content_embedding field to existing index"""
        try:
            print("\n📝 Updating index mapping...")
            
            # Add new field mapping
            mapping_update = {
                "properties": {
                    "content_embedding": {
                        "type": "dense_vector",
                        "dims": 1536,
                        "index": True,
                        "similarity": "cosine"
                    }
                }
            }
            
            self.elastic.client.indices.put_mapping(
                index=self.index_name,
                body=mapping_update
            )
            
            print("✅ Mapping updated successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error updating mapping: {e}")
            return False
    
    def get_documents_without_embeddings(self) -> List[Dict]:
        """Get all PDF documents that don't have embeddings yet"""
        try:
            # Query for documents without content_embedding field
            response = self.elastic.client.search(
                index=self.index_name,
                body={
                    "query": {
                        "bool": {
                            "must_not": {
                                "exists": {
                                    "field": "content_embedding"
                                }
                            }
                        }
                    },
                    "_source": ["document_id", "chunk_id", "content", "document_title"],
                    "size": 10000  # Get all documents (adjust if you have more)
                },
                scroll='5m'
            )
            
            documents = []
            scroll_id = response['_scroll_id']
            
            # Collect all documents
            while len(response['hits']['hits']) > 0:
                for hit in response['hits']['hits']:
                    doc = hit['_source']
                    doc['_id'] = hit['_id']
                    documents.append(doc)
                
                # Get next batch
                response = self.elastic.client.scroll(
                    scroll_id=scroll_id,
                    scroll='5m'
                )
            
            # Clear scroll
            self.elastic.client.clear_scroll(scroll_id=scroll_id)
            
            print(f"📊 Found {len(documents)} documents without embeddings")
            return documents
            
        except Exception as e:
            print(f"❌ Error fetching documents: {e}")
            return []
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            if not text or len(text.strip()) == 0:
                print("⚠️  Empty text, skipping")
                return None
            
            # Truncate if too long (OpenAI limit is ~8K tokens)
            max_chars = 8000
            if len(text) > max_chars:
                text = text[:max_chars]
            
            embedding = self.llm.embeddings_model.embed_query(text)
            return embedding
            
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            return None
    
    def update_document_with_embedding(self, doc_id: str, embedding: List[float]) -> bool:
        """Update document in Elasticsearch with embedding"""
        try:
            self.elastic.client.update(
                index=self.index_name,
                id=doc_id,
                body={
                    "doc": {
                        "content_embedding": embedding,
                        "embedding_generated_at": datetime.utcnow().isoformat()
                    }
                }
            )
            return True
            
        except Exception as e:
            print(f"❌ Error updating document {doc_id}: {e}")
            return False
    
    def process_documents(self, documents: List[Dict]) -> Dict:
        """Process all documents and add embeddings"""
        stats = {
            'total': len(documents),
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        print(f"\n{'=' * 60}")
        print(f"Processing {stats['total']} documents...")
        print(f"{'=' * 60}\n")
        
        start_time = time.time()
        
        for i, doc in enumerate(documents, 1):
            doc_id = doc.get('_id')
            content = doc.get('content', '')
            title = doc.get('document_title', '')
            
            # Progress indicator
            if i % 10 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (stats['total'] - i) / rate if rate > 0 else 0
                print(f"[{i}/{stats['total']}] Progress: {i/stats['total']*100:.1f}% | "
                      f"Rate: {rate:.1f} docs/s | ETA: {eta/60:.1f}min")
            
            stats['processed'] += 1
            
            # Skip if no content
            if not content or len(content.strip()) < 10:
                stats['skipped'] += 1
                continue
            
            # Generate embedding
            # Combine title and content for better semantic understanding
            text_for_embedding = f"{title}\n\n{content}" if title else content
            embedding = self.generate_embedding(text_for_embedding)
            
            if embedding is None:
                stats['failed'] += 1
                continue
            
            # Update document
            if self.update_document_with_embedding(doc_id, embedding):
                stats['successful'] += 1
            else:
                stats['failed'] += 1
            
            # Rate limiting (be nice to OpenAI API)
            if i % self.batch_size == 0:
                time.sleep(self.sleep_between_batches)
        
        elapsed_total = time.time() - start_time
        
        print(f"\n{'=' * 60}")
        print(f"✅ Processing completed!")
        print(f"{'=' * 60}")
        print(f"Total documents: {stats['total']}")
        print(f"Processed: {stats['processed']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Skipped: {stats['skipped']}")
        print(f"Time elapsed: {elapsed_total/60:.1f} minutes")
        print(f"Average rate: {stats['processed']/elapsed_total:.2f} docs/sec")
        print(f"{'=' * 60}")
        
        return stats
    
    def verify_embeddings(self) -> Dict:
        """Verify that embeddings were added successfully"""
        try:
            # Count documents with embeddings
            response = self.elastic.client.count(
                index=self.index_name,
                body={
                    "query": {
                        "exists": {
                            "field": "content_embedding"
                        }
                    }
                }
            )
            
            with_embeddings = response['count']
            
            # Count total documents
            total_response = self.elastic.client.count(index=self.index_name)
            total = total_response['count']
            
            print(f"\n📊 Verification:")
            print(f"   Total documents: {total}")
            print(f"   With embeddings: {with_embeddings}")
            print(f"   Coverage: {with_embeddings/total*100:.1f}%")
            
            return {
                'total': total,
                'with_embeddings': with_embeddings,
                'coverage': with_embeddings/total*100
            }
            
        except Exception as e:
            print(f"❌ Error verifying: {e}")
            return {}
    
    def run(self):
        """Main execution"""
        if not self.initialize():
            return False
        
        # Check if mapping needs update
        has_embedding_field = self.check_index_mapping()
        if not has_embedding_field:
            if not self.update_index_mapping():
                return False
        
        # Get documents without embeddings
        documents = self.get_documents_without_embeddings()
        if not documents:
            print("\n✅ All documents already have embeddings!")
            self.verify_embeddings()
            return True
        
        # Estimate time and cost
        estimated_time_min = (len(documents) / self.batch_size * self.sleep_between_batches) / 60
        estimated_cost = len(documents) * 0.0001  # ~$0.0001 per embedding
        
        print(f"\n📊 Estimates:")
        print(f"   Documents to process: {len(documents)}")
        print(f"   Estimated time: {estimated_time_min:.1f} minutes")
        print(f"   Estimated cost: ${estimated_cost:.2f}")
        print()
        
        # Ask for confirmation
        confirmation = input("⚠️  Continue? (yes/no): ")
        if confirmation.lower() not in ['yes', 'y']:
            print("❌ Cancelled by user")
            return False
        
        # Process documents
        stats = self.process_documents(documents)
        
        # Verify results
        self.verify_embeddings()
        
        print("\n🎉 PDF embeddings generation completed!")
        return True


def main():
    """Main entry point"""
    generator = PDFEmbeddingsGenerator()
    success = generator.run()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()


