"""
LangChain-based RAG Service
Using ready-made LangChain components for better multilingual support
"""

from typing import List, Dict, Optional
from langchain.chains import RetrievalQA
from langchain.retrievers import EnsembleRetriever
from langchain_elasticsearch import ElasticsearchRetriever
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.schema import Document
from app.config.settings import settings


class LangChainRAGService:
    """
    Production-ready RAG using LangChain components
    
    Features:
    - Hybrid search (semantic + keyword) via EnsembleRetriever
    - Multilingual support via OpenAI embeddings
    - Query translation
    - Automatic re-ranking
    """
    
    def __init__(self):
        self.embeddings = None
        self.llm = None
        self.retrievers = {}
        self.qa_chains = {}
        
    def initialize(self) -> bool:
        """Initialize LangChain components"""
        try:
            # Initialize embeddings (multilingual by default)
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.OPENAI_API_KEY
            )
            
            # Initialize LLM
            self.llm = ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY
            )
            
            # Initialize retrievers for each index
            self._initialize_retrievers()
            
            print("✅ LangChain RAG Service initialized")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize LangChain RAG: {e}")
            return False
    
    def _initialize_retrievers(self):
        """Initialize Elasticsearch retrievers for each index"""
        
        # Telegram retriever (hybrid: semantic + keyword)
        self.retrievers['telegram'] = ElasticsearchRetriever(
            index_name="telegram_threads",
            body_func=self._build_telegram_query,
            content_field="content",
            url=settings.ELASTICSEARCH_URL,
            api_key=settings.ELASTICSEARCH_API_KEY
        )
        
        # PDF retriever
        self.retrievers['pdf'] = ElasticsearchRetriever(
            index_name="pdf_documents",
            body_func=self._build_pdf_query,
            content_field="content",
            url=settings.ELASTICSEARCH_URL,
            api_key=settings.ELASTICSEARCH_API_KEY
        )
        
        print(f"✅ Initialized {len(self.retrievers)} retrievers")
    
    def _build_telegram_query(self, query: str) -> Dict:
        """
        Build hybrid query for Telegram (kNN + keyword)
        Supports multilingual queries via embeddings
        """
        # Generate embedding for semantic search
        query_embedding = self.embeddings.embed_query(query)
        
        return {
            "size": 10,
            "query": {
                "bool": {
                    "should": [
                        # Keyword search (BM25)
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["content^2", "first_message", "last_message", "topics", "keywords"],
                                "type": "best_fields"
                            }
                        }
                    ]
                }
            },
            "knn": {
                "field": "content_embedding",
                "query_vector": query_embedding,
                "k": 10,
                "num_candidates": 50
            }
        }
    
    def _build_pdf_query(self, query: str) -> Dict:
        """
        Build query for PDF documents
        
        TODO: Add embeddings for semantic search
        For now, uses keyword-only search
        """
        return {
            "size": 10,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["content^2", "document_title", "categories"],
                    "type": "best_fields"
                }
            }
        }
    
    def search(
        self,
        query: str,
        channels: List[str] = None,
        top_k: int = 5
    ) -> Dict[str, List[Document]]:
        """
        Search across multiple channels using LangChain retrievers
        
        Args:
            query: User query (any language)
            channels: List of channels to search ["telegram", "pdf", ...]
            top_k: Number of results per channel
            
        Returns:
            Dict with results per channel
        """
        if channels is None:
            channels = ["telegram", "pdf"]
        
        results = {}
        
        for channel in channels:
            retriever = self.retrievers.get(channel)
            if not retriever:
                print(f"⚠️ No retriever for channel: {channel}")
                results[channel] = []
                continue
            
            try:
                # Use LangChain retriever
                docs = retriever.get_relevant_documents(query)
                results[channel] = docs[:top_k]
                print(f"✅ {channel}: {len(docs)} results")
                
            except Exception as e:
                print(f"❌ Error searching {channel}: {e}")
                results[channel] = []
        
        return results
    
    def search_with_qa(
        self,
        query: str,
        channels: List[str] = None,
        return_sources: bool = True
    ) -> Dict:
        """
        Search + Answer using RetrievalQA chain
        
        This combines retrieval with LLM generation
        
        Args:
            query: User question
            channels: Channels to search
            return_sources: Whether to return source documents
            
        Returns:
            {
                "answer": "Generated answer",
                "sources": [Document, ...],
                "source_channels": {"telegram": 5, "pdf": 3}
            }
        """
        # 1. Retrieve documents
        search_results = self.search(query, channels)
        
        # 2. Combine all documents
        all_docs = []
        source_channels = {}
        for channel, docs in search_results.items():
            all_docs.extend(docs)
            source_channels[channel] = len(docs)
        
        if not all_docs:
            return {
                "answer": "No relevant information found.",
                "sources": [],
                "source_channels": source_channels
            }
        
        # 3. Build RetrievalQA chain
        # Use LangChain's built-in RAG
        from langchain.chains.question_answering import load_qa_chain
        
        chain = load_qa_chain(
            llm=self.llm,
            chain_type="stuff"  # Simple concatenation of docs
        )
        
        # 4. Generate answer
        try:
            result = chain({
                "input_documents": all_docs,
                "question": query
            })
            
            return {
                "answer": result["output_text"],
                "sources": all_docs if return_sources else [],
                "source_channels": source_channels
            }
            
        except Exception as e:
            print(f"❌ Error generating answer: {e}")
            return {
                "answer": f"Error: {e}",
                "sources": all_docs if return_sources else [],
                "source_channels": source_channels
            }
    
    def translate_query(self, query: str, target_lang: str = "es") -> str:
        """
        Translate query to target language using LLM
        Useful for keyword search in Spanish documents
        """
        try:
            prompt = f"Translate this query to {target_lang}: {query}\nTranslation:"
            response = self.llm.predict(prompt)
            return response.strip()
        except Exception as e:
            print(f"❌ Translation error: {e}")
            return query


# Global instance
langchain_rag_service = LangChainRAGService()

