"""
Search service that integrates Elasticsearch, Supabase, and LLM
Provides unified search interface for knowledge base
"""

import time
from typing import List, Optional, Tuple, Dict
from datetime import datetime

from app.models.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchFilters,
    SourceType
)
from app.services.elasticsearch_service import elastic_service
from app.services.supabase_service import supabase_service
from app.services.llm.llm_service import llm_service


class SearchService:
    """Unified search service for TuExpertoFiscal"""
    
    def __init__(self):
        """Initialize search service with all dependencies"""
        self.elastic = elastic_service
        self.supabase = supabase_service
        self.llm = llm_service
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize all service connections"""
        try:
            print("Initializing search service...")
            
            # Try to connect to Supabase
            supabase_connected = self.supabase.connect()
            if not supabase_connected:
                print("Warning: Supabase not available, using mock mode")
            
            # Try to initialize LLM service
            llm_initialized = self.llm.initialize()
            if not llm_initialized:
                print("Warning: LLM not available, using mock mode")
            
            # Try to connect to Elasticsearch
            elastic_connected = self.elastic.connect()
            if not elastic_connected:
                print("Warning: Elasticsearch not available, using mock mode")
            
            # Service is initialized even in mock mode
            self.initialized = True
            print("✅ Search service initialized successfully (mock mode)")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing search service: {e}")
            return False
    
    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Execute search request with full pipeline:
        1. Get or create user
        2. Create/get session
        3. Generate embedding for query
        4. Search Elasticsearch with filters
        5. Generate LLM response (if requested)
        6. Save message to database
        """
        start_time = time.time()
        
        try:
            # Validate service is initialized
            if not self.initialized:
                return SearchResponse(
                    success=False,
                    query_text=request.query_text,
                    error_message="Search service not initialized"
                )
            
            # Step 1: Get or create user (or mock)
            telegram_id = int(request.user_context.channel_user_id)
            user_metadata = request.user_context.user_metadata or {}
            
            if self.supabase.connection:
                user_data = self.supabase.get_or_create_user(
                    telegram_id=telegram_id,
                    username=user_metadata.get('username'),
                    first_name=user_metadata.get('first_name'),
                    last_name=user_metadata.get('last_name'),
                    phone=user_metadata.get('phone')
                )
                
                if not user_data:
                    return SearchResponse(
                        success=False,
                        query_text=request.query_text,
                        error_message="Failed to get/create user"
                    )
                
                user_id = user_data['id']
            else:
                # Mock user
                user_id = f"mock_user_{telegram_id}"
            
            # Get subscription status
            if self.supabase.connection:
                subscription_status = self.supabase.get_user_subscription_status(user_id)
            else:
                subscription_status = "free"  # Mock subscription
            
            # Step 2: Create or use existing session
            session_id = request.user_context.session_id
            if not session_id:
                if self.supabase.connection:
                    session_id = self.supabase.create_dialogue_session(user_id)
                else:
                    session_id = f"mock_session_{user_id}_{int(time.time())}"  # Mock session
            
            if not session_id:
                return SearchResponse(
                    success=False,
                    query_text=request.query_text,
                    user_id=user_id,
                    subscription_status=subscription_status,
                    error_message="Failed to create session"
                )
            
            # Step 3: Search directly in Elasticsearch by text query (no embeddings)
            print(f"Searching in Elasticsearch for: {request.query_text}")
            
            # Step 4: Search in specified channels
            print(f"Searching in channels: {request.channels}")
            search_results = []
            
            # Search in each specified channel
            for channel in request.channels:
                print(f"Searching in channel: {channel}")
                
                if channel == SourceType.TELEGRAM:
                    # Search in Telegram data
                    channel_results = self._search_telegram(request.query_text)
                elif channel == SourceType.PDF:
                    # Search in PDF documents
                    channel_results = self._search_pdf(request.query_text)
                elif channel == SourceType.CALENDAR:
                    # Search in tax calendar
                    channel_results = self._search_calendar(request.query_text)
                elif channel == SourceType.NEWS:
                    # Search in news articles
                    channel_results = self._search_news(request.query_text)
                elif channel == SourceType.AEAT:
                    # Search in AEAT resources
                    channel_results = self._search_aeat(request.query_text)
                else:
                    # Mock results for unknown channels
                    channel_results = [
                        {
                            'text': f"Resultado de {channel} para '{request.query_text}': Información relevante encontrada.",
                            'metadata': {'source_type': channel, 'category': 'tax_info'},
                            'score': 0.8
                        }
                    ]
                
                search_results.extend(channel_results)
            
            # If no results, return empty list
            if not search_results:
                print("No results found in any channel")
            
            # Limit results to top_k
            search_results = search_results[:request.top_k or 5]
            
            # Convert to SearchResult models
            results = [
                SearchResult(
                    text=result['text'],
                    metadata=result['metadata'],
                    score=result['score'],
                    source_type=result['metadata'].get('source_type')
                )
                for result in search_results
            ]
            
            # Step 5: Skip LLM response generation - return clean search results only
            generated_response = None
            
            # Step 6: Save message to database (or mock if not available)
            if self.supabase.connection:
                self.supabase.save_message(
                    session_id=session_id,
                    user_id=user_id,
                    query_text=request.query_text,
                    response_text=generated_response,
                    sources=[r.model_dump() for r in results],
                    is_relevant=len(results) > 0
                )
            else:
                print("Mock mode: Message not saved to database")
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return SearchResponse(
                success=True,
                query_text=request.query_text,
                user_id=user_id,
                session_id=session_id,
                results=results,
                subscription_status=subscription_status,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            print(f"Error in search: {e}")
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return SearchResponse(
                success=False,
                query_text=request.query_text,
                error_message=str(e),
                processing_time_ms=processing_time_ms
            )
    
    def _apply_filters(
        self,
        results: List[dict],
        filters: SearchFilters
    ) -> List[dict]:
        """Apply post-search filters to results"""
        filtered_results = results
        
        # Filter by source types
        if filters.source_types and SourceType.ALL not in filters.source_types:
            filtered_results = [
                r for r in filtered_results
                if r.get('metadata', {}).get('source_type') in [st.value for st in filters.source_types]
            ]
        
        # Filter by date range
        if filters.date_from or filters.date_to:
            filtered_results = self._filter_by_date(
                filtered_results,
                filters.date_from,
                filters.date_to
            )
        
        # Filter by tax types
        if filters.tax_types:
            filtered_results = [
                r for r in filtered_results
                if r.get('metadata', {}).get('tax_type') in filters.tax_types
            ]
        
        # Filter by regions
        if filters.regions:
            filtered_results = [
                r for r in filtered_results
                if r.get('metadata', {}).get('region') in filters.regions
            ]
        
        # Filter by quality score (for telegram threads)
        if filters.minimum_quality_score is not None:
            filtered_results = [
                r for r in filtered_results
                if r.get('metadata', {}).get('quality_score', 5.0) >= filters.minimum_quality_score
            ]
        
        return filtered_results
    
    def _filter_by_date(
        self,
        results: List[dict],
        date_from: Optional[datetime],
        date_to: Optional[datetime]
    ) -> List[dict]:
        """Filter results by date range"""
        filtered = []
        
        for result in results:
            metadata = result.get('metadata', {})
            
            # Try to get date from various fields
            result_date = None
            for date_field in ['published_at', 'last_updated', 'deadline_date', 'date']:
                if date_field in metadata:
                    date_str = metadata[date_field]
                    try:
                        if isinstance(date_str, str):
                            result_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        elif isinstance(date_str, datetime):
                            result_date = date_str
                        break
                    except:
                        continue
            
            if not result_date:
                # No date found, include by default
                filtered.append(result)
                continue
            
            # Apply date filters
            if date_from and result_date < date_from:
                continue
            if date_to and result_date > date_to:
                continue
            
            filtered.append(result)
        
        return filtered
    
    async def _generate_llm_response(
        self,
        query: str,
        search_results: List[SearchResult]
    ) -> str:
        """Generate LLM response based on search results"""
        try:
            # Build context from search results
            context_parts = []
            for i, result in enumerate(search_results[:3], 1):  # Use top 3 results
                source_type = result.metadata.get('source_type', 'unknown')
                context_parts.append(f"[Source {i} - {source_type}]\n{result.text}\n")
            
            context = "\n".join(context_parts)
            
            # Build system prompt
            system_prompt = """Eres TuExpertoFiscal, un asistente experto en fiscalidad española.
Tu trabajo es responder preguntas sobre impuestos en España de manera clara, precisa y útil.

Directrices:
- Usa la información proporcionada en el contexto para responder
- Si no hay suficiente información, indica claramente qué información falta
- Sé específico con fechas, plazos y procedimientos
- Usa un tono profesional pero amigable
- Responde en español
- Si mencionas leyes o normativas, cita la fuente cuando esté disponible en el contexto
"""
            
            # Build user prompt
            user_prompt = f"""Contexto:
{context}

Pregunta del usuario: {query}

Responde basándote en el contexto proporcionado."""
            
            # Generate response
            response = await self.llm.generate_async(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=800
            )
            
            return response
            
        except Exception as e:
            print(f"Error generating LLM response: {e}")
            return f"Lo siento, no pude generar una respuesta. Error: {str(e)}"
    
    
    def health_check(self) -> dict:
        """Check health of all services"""
        return {
            "elasticsearch_connected": self.elastic.client is not None,
            "supabase_connected": self.supabase.connection is not None,
            "llm_initialized": self.llm.chat_model is not None,
            "search_service_initialized": self.initialized
        }
    
    def _search_telegram(self, query: str) -> List[Dict]:
        """Search in Telegram channels data using Elasticsearch"""
        if not self.elastic.client:
            return []
        
        try:
            # Use Elasticsearch text search
            response = self.elastic.client.search(
                index="telegram_threads",
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["text", "title"],
                            "type": "best_fields"
                        }
                    }
                },
                size=5
            )
            
            results = []
            for hit in response['hits']['hits']:
                results.append({
                    'text': hit['_source'].get('text', ''),
                    'metadata': hit['_source'].get('metadata', {}),
                    'score': hit['_score']
                })
            return results
        except Exception as e:
            print(f"Error searching Telegram: {e}")
            return []
    
    def _search_pdf(self, query: str) -> List[Dict]:
        """Search in PDF documents using Elasticsearch"""
        if not self.elastic.client:
            return []
        
        try:
            response = self.elastic.client.search(
                index="pdf",
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["text", "title"],
                            "type": "best_fields"
                        }
                    }
                },
                size=5
            )
            
            results = []
            for hit in response['hits']['hits']:
                results.append({
                    'text': hit['_source'].get('text', ''),
                    'metadata': hit['_source'].get('metadata', {}),
                    'score': hit['_score']
                })
            return results
        except Exception as e:
            print(f"Error searching PDF: {e}")
            return []
    
    def _search_calendar(self, query: str) -> List[Dict]:
        """Search in tax calendar using Elasticsearch"""
        if not self.elastic.client:
            return []
        
        try:
            response = self.elastic.client.search(
                index="calendar",
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["text", "title", "deadline_date"],
                            "type": "best_fields"
                        }
                    }
                },
                size=5
            )
            
            results = []
            for hit in response['hits']['hits']:
                results.append({
                    'text': hit['_source'].get('text', ''),
                    'metadata': hit['_source'].get('metadata', {}),
                    'score': hit['_score']
                })
            return results
        except Exception as e:
            print(f"Error searching Calendar: {e}")
            return []
    
    def _search_news(self, query: str) -> List[Dict]:
        """Search in news articles using Elasticsearch"""
        if not self.elastic.client:
            return []
        
        try:
            response = self.elastic.client.search(
                index="news",
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["text", "title"],
                            "type": "best_fields"
                        }
                    }
                },
                size=5
            )
            
            results = []
            for hit in response['hits']['hits']:
                results.append({
                    'text': hit['_source'].get('text', ''),
                    'metadata': hit['_source'].get('metadata', {}),
                    'score': hit['_score']
                })
            return results
        except Exception as e:
            print(f"Error searching News: {e}")
            return []
    
    def _search_aeat(self, query: str) -> List[Dict]:
        """Search in AEAT resources using Elasticsearch"""
        if not self.elastic.client:
            return []
        
        try:
            response = self.elastic.client.search(
                index="aeat",
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["text", "title"],
                            "type": "best_fields"
                        }
                    }
                },
                size=5
            )
            
            results = []
            for hit in response['hits']['hits']:
                results.append({
                    'text': hit['_source'].get('text', ''),
                    'metadata': hit['_source'].get('metadata', {}),
                    'score': hit['_score']
                })
            return results
        except Exception as e:
            print(f"Error searching AEAT: {e}")
            return []

    def close(self):
        """Close all service connections"""
        try:
            self.elastic.close()
            self.supabase.close()
            print("Search service connections closed")
        except Exception as e:
            print(f"Error closing search service: {e}")


# Global instance
search_service = SearchService()

