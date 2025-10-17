"""
Elasticsearch service for hybrid search (semantic + keyword)
Handles connection and search operations
"""

from typing import List, Dict, Any
from elasticsearch import Elasticsearch
from app.config.settings import settings


class ElasticsearchService:
    """Service for interacting with Elasticsearch"""
    
    def __init__(self):
        """Initialize Elasticsearch client"""
        self.client = None
        self.index_name = settings.ELASTIC_INDEX_NAME
    
    def connect(self) -> bool:
        """Establish connection to Elasticsearch Cloud"""
        try:
            self.client = Elasticsearch(
                cloud_id=settings.ELASTIC_CLOUD_ID,
                api_key=settings.ELASTIC_API_KEY
            )
            # Test connection
            info = self.client.info()
            print(f"Connected to Elasticsearch: {info['version']['number']}")
            return True
        except Exception as e:
            print(f"Failed to connect to Elasticsearch: {e}")
            return False
    
    def create_index(self, mapping: Dict[str, Any]) -> bool:
        """Create index with specified mapping"""
        try:
            if self.client.indices.exists(index=self.index_name):
                print(f"Index '{self.index_name}' already exists")
                return True
            
            self.client.indices.create(index=self.index_name, body=mapping)
            print(f"Index '{self.index_name}' created successfully")
            return True
        except Exception as e:
            print(f"Failed to create index: {e}")
            return False
    
    def index_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """Index a single document"""
        try:
            self.client.index(
                index=self.index_name,
                id=doc_id,
                body=document
            )
            return True
        except Exception as e:
            print(f"Failed to index document: {e}")
            return False
    
    def hybrid_search(
        self,
        query_text: str,
        query_vector: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining:
        - Semantic search (kNN with vectors)
        - Keyword search (BM25)
        """
        try:
            search_query = {
                "size": top_k,
                "query": {
                    "bool": {
                        "should": [
                            # Semantic search using kNN
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'text_embedding') + 1.0",
                                        "params": {"query_vector": query_vector}
                                    }
                                }
                            },
                            # Keyword search using BM25
                            {
                                "match": {
                                    "text_chunk": {
                                        "query": query_text,
                                        "boost": 1.5
                                    }
                                }
                            }
                        ]
                    }
                },
                "_source": ["text_chunk", "metadata"]
            }
            
            response = self.client.search(index=self.index_name, body=search_query)
            
            results = []
            for hit in response['hits']['hits']:
                results.append({
                    'text': hit['_source']['text_chunk'],
                    'metadata': hit['_source'].get('metadata', {}),
                    'score': hit['_score']
                })
            
            return results
        except Exception as e:
            print(f"Search failed: {e}")
            return []
    
    def close(self):
        """Close Elasticsearch connection"""
        if self.client:
            self.client.close()


# Global instance
elastic_service = ElasticsearchService()

