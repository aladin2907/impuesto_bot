#!/usr/bin/env python3
"""
Add embeddings to Telegram threads using FREE multilingual-e5-large model
Uses sentence-transformers for local embedding generation (no API costs!)

Differences from PDF embeddings:
- PDF: OpenAI text-embedding-3-small (1536 dims) 
- Telegram: multilingual-e5-large (1024 dims)
- Separate field: telegram_embedding (vs content_embedding for PDFs)
"""

import sys
from pathlib import Path
from typing import List, Dict
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.elasticsearch_service import elastic_service

# Check if sentence-transformers is installed
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("❌ sentence-transformers not installed!")
    print("Install it: pip install sentence-transformers")
    sys.exit(1)


class TelegramEmbeddingGenerator:
    """Generate embeddings for Telegram threads using FREE multilingual model"""
    
    def __init__(self):
        self.index_name = "telegram_threads"
        self.batch_size = 100  # Process 100 threads at a time
        self.embedding_field = "telegram_embedding"  # Separate field!
        
        print("🔧 Loading multilingual-e5-large model...")
        print("   (First run will download ~1.2GB, then cached)")
        
        # Load the FREE multilingual model
        self.model = SentenceTransformer('intfloat/multilingual-e5-large')
        
        print(f"✅ Model loaded! Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
        
    def get_text_for_embedding(self, thread: Dict) -> str:
        """Extract and prepare text from thread for embedding"""
        parts = []
        
        # First message (most important)
        if thread.get('first_message'):
            parts.append(thread['first_message'])
        
        # Last message (conclusion/resolution)
        if thread.get('last_message'):
            parts.append(thread['last_message'])
        
        # Topics/keywords
        if thread.get('topics'):
            parts.append(' '.join(thread['topics']))
        
        if thread.get('keywords'):
            parts.append(' '.join(thread['keywords'][:10]))  # Top 10 keywords
        
        # Combine with spaces
        text = ' '.join(parts)
        
        # Truncate to reasonable length (model handles up to 512 tokens)
        return text[:2000]  # ~500 tokens
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using multilingual-e5-large"""
        try:
            # Add query prefix for better retrieval (model-specific)
            # For retrieval tasks, prefix queries with "query: "
            prefixed_texts = [f"passage: {text}" for text in texts]
            
            embeddings = self.model.encode(
                prefixed_texts,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            print(f"❌ Error generating embeddings: {e}")
            return []
    
    def count_threads_without_embeddings(self) -> int:
        """Count threads without embeddings"""
        response = elastic_service.client.count(
            index=self.index_name,
            body={
                "query": {
                    "bool": {
                        "must_not": {
                            "exists": {"field": self.embedding_field}
                        }
                    }
                }
            }
        )
        return response['count']
    
    def process_batch(self, threads: List[Dict]) -> int:
        """Process a batch of threads and add embeddings"""
        if not threads:
            return 0
        
        # Extract texts
        texts = [self.get_text_for_embedding(thread) for thread in threads]
        
        # Generate embeddings
        embeddings = self.generate_embeddings(texts)
        
        if len(embeddings) != len(threads):
            print(f"⚠️  Warning: Got {len(embeddings)} embeddings for {len(threads)} threads")
            return 0
        
        # Update documents in Elasticsearch
        success_count = 0
        for thread, embedding in zip(threads, embeddings):
            try:
                elastic_service.client.update(
                    index=self.index_name,
                    id=thread['_id'],
                    body={
                        "doc": {
                            self.embedding_field: embedding
                        }
                    }
                )
                success_count += 1
            except Exception as e:
                print(f"❌ Error updating thread {thread['_id']}: {e}")
        
        return success_count
    
    def run(self, limit: int = None):
        """Main process to add embeddings to all threads"""
        
        # Connect to Elasticsearch
        elastic_service.connect()
        if not elastic_service.client:
            print("❌ Failed to connect to Elasticsearch")
            return
        
        print(f"✅ Connected to Elasticsearch: {elastic_service.client.info()['version']['number']}")
        
        # Check if index exists
        if not elastic_service.client.indices.exists(index=self.index_name):
            print(f"❌ Index '{self.index_name}' does not exist!")
            return
        
        # Count threads without embeddings
        total_without = self.count_threads_without_embeddings()
        
        if limit:
            total_to_process = min(total_without, limit)
        else:
            total_to_process = total_without
        
        print("\n" + "="*70)
        print(f"📊 TELEGRAM EMBEDDINGS GENERATION")
        print("="*70)
        print(f"Total threads WITHOUT embeddings: {total_without}")
        print(f"Threads to process: {total_to_process}")
        print(f"Batch size: {self.batch_size}")
        print(f"Model: intfloat/multilingual-e5-large (1024 dims)")
        print(f"Field: {self.embedding_field}")
        print(f"Cost: $0 (FREE!) 🎉")
        print("="*70)
        
        if total_to_process == 0:
            print("\n✅ All threads already have embeddings!")
            return
        
        # Process in batches
        processed = 0
        total_time = 0
        
        while processed < total_to_process:
            batch_start = time.time()
            
            # Fetch batch of threads without embeddings
            response = elastic_service.client.search(
                index=self.index_name,
                body={
                    "size": self.batch_size,
                    "query": {
                        "bool": {
                            "must_not": {
                                "exists": {"field": self.embedding_field}
                            }
                        }
                    },
                    "_source": ["thread_id", "first_message", "last_message", "topics", "keywords"]
                }
            )
            
            hits = response['hits']['hits']
            if not hits:
                break
            
            # Prepare threads with IDs
            threads = []
            for hit in hits:
                thread = hit['_source']
                thread['_id'] = hit['_id']
                threads.append(thread)
            
            # Process batch
            success = self.process_batch(threads)
            processed += success
            
            batch_time = time.time() - batch_start
            total_time += batch_time
            
            # Calculate stats
            avg_time_per_doc = batch_time / len(threads) if threads else 0
            docs_per_sec = len(threads) / batch_time if batch_time > 0 else 0
            progress = (processed / total_to_process) * 100
            
            print(f"📦 Batch: {success}/{len(threads)} | "
                  f"Progress: {processed}/{total_to_process} ({progress:.1f}%) | "
                  f"Speed: {docs_per_sec:.1f} docs/sec | "
                  f"Time: {batch_time:.1f}s")
        
        # Final summary
        print("\n" + "="*70)
        print(f"✅ COMPLETED!")
        print("="*70)
        print(f"Total processed: {processed}/{total_to_process}")
        print(f"Total time: {total_time/60:.1f} minutes")
        print(f"Average: {total_time/processed if processed > 0 else 0:.2f} sec/doc")
        
        # Verify
        remaining = self.count_threads_without_embeddings()
        print(f"\nThreads still WITHOUT embeddings: {remaining}")
        
        if remaining == 0:
            print("🎉 ALL THREADS NOW HAVE EMBEDDINGS!")
        
        print("="*70)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Add FREE embeddings to Telegram threads using multilingual-e5-large"
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of threads to process (for testing)'
    )
    
    args = parser.parse_args()
    
    generator = TelegramEmbeddingGenerator()
    generator.run(limit=args.limit)


if __name__ == "__main__":
    main()

