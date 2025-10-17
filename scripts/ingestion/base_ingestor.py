"""
Base class for data ingestion with common utilities
All specific ingestors inherit from this
"""

import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from langchain.text_splitter import RecursiveCharacterTextSplitter
try:  # pragma: no cover - optional dependency for unit tests
    from langchain_elasticsearch import ElasticsearchStore  # type: ignore
except ImportError:  # pragma: no cover - optional dependency in tests
    ElasticsearchStore = None  # type: ignore
try:  # pragma: no cover - optional dependency for unit tests
    from elasticsearch import Elasticsearch
except ImportError:  # pragma: no cover
    Elasticsearch = None  # type: ignore

from app.services.llm import LLMService
from app.services.supabase_service import supabase_service
from app.config.settings import settings


class BaseIngestor:
    """Base class for all data ingestors"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        document_type: str = "unknown"
    ):
        """
        Initialize the ingestor
        
        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            document_type: Type of document being ingested
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.document_type = document_type
        
        # Initialize services
        self.llm_service = None
        self.elastic_client = None
        self.vectorstore = None
        self.text_splitter = None
        
    def initialize(self) -> bool:
        """Initialize all required services"""
        try:
            print("Initializing services...")
            
            # Initialize LLM service
            self.llm_service = LLMService()
            if not self.llm_service.initialize():
                print("❌ Failed to initialize LLM service")
                return False
            
            if Elasticsearch is None:
                raise RuntimeError(
                    "python-elasticsearch not installed. "
                    "Add `elasticsearch` to requirements to enable ingestion."
                )

            # Initialize Elasticsearch client
            self.elastic_client = Elasticsearch(
                cloud_id=settings.ELASTIC_CLOUD_ID,
                api_key=settings.ELASTIC_API_KEY
            )
            
            # Test connection
            info = self.elastic_client.info()
            print(f"✅ Connected to Elasticsearch: {info['version']['number']}")
            
            if ElasticsearchStore is None:
                raise RuntimeError(
                    "langchain-elasticsearch not installed. "
                    "Add `langchain-elasticsearch` to requirements to enable ingestion."
                )

            # Initialize ElasticsearchStore
            self.vectorstore = ElasticsearchStore(
                es_connection=self.elastic_client,
                index_name=settings.ELASTIC_INDEX_NAME,
                embedding=self.llm_service.embeddings_model,
                strategy=ElasticsearchStore.ApproxRetrievalStrategy(
                    hybrid=True  # Enable hybrid search (semantic + keyword)
                )
            )
            
            # Initialize text splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
            )
            
            # Connect to Supabase
            if not supabase_service.connect():
                print("❌ Failed to connect to Supabase")
                return False
            
            print("✅ All services initialized")
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_document_metadata(
        self,
        file_name: str,
        source_url: Optional[str] = None,
        status: str = "completed"
    ) -> Optional[str]:
        """
        Save document metadata to Supabase
        
        Returns:
            Document ID (UUID) or None
        """
        try:
            cursor = supabase_service.connection.cursor()
            cursor.execute("""
                INSERT INTO documents 
                (file_name, source_url, document_type, status, last_processed_at, created_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (file_name, source_url, self.document_type, status))
            
            doc_id = cursor.fetchone()['id']
            supabase_service.connection.commit()
            
            print(f"✅ Document metadata saved with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            print(f"❌ Failed to save metadata: {e}")
            supabase_service.connection.rollback()
            return None
    
    def ingest_documents(
        self,
        documents: List[Any],
        metadatas: Optional[List[Dict]] = None
    ) -> bool:
        """
        Split documents into chunks and ingest into Elasticsearch
        
        Args:
            documents: List of LangChain Document objects
            metadatas: Optional list of metadata dicts
            
        Returns:
            True if successful
        """
        try:
            print(f"Splitting {len(documents)} documents into chunks...")
            
            # Split documents
            chunks = self.text_splitter.split_documents(documents)
            print(f"✅ Created {len(chunks)} chunks")
            
            # Add metadata if provided
            if metadatas:
                for i, chunk in enumerate(chunks):
                    chunk.metadata.update(metadatas[i % len(metadatas)])
            
            # Ingest into Elasticsearch
            print("Indexing into Elasticsearch...")
            self.vectorstore.add_documents(chunks)
            
            print(f"✅ Successfully indexed {len(chunks)} chunks")
            return True
            
        except Exception as e:
            print(f"❌ Ingestion failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup(self):
        """Cleanup connections"""
        if self.elastic_client:
            self.elastic_client.close()
        if supabase_service.connection:
            supabase_service.close()
        print("✅ Cleanup complete")
