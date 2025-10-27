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
            # Handle both numeric and string user IDs
            try:
                telegram_id = int(request.user_context.channel_user_id)
            except (ValueError, TypeError):
                # If user_id is not numeric, use a hash
                telegram_id = hash(request.user_context.channel_user_id) % 10**9
            
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
            
            # Initialize results for each channel
            telegram_results = []
            pdf_results = []
            calendar_results = []
            news_results = []
            reference_results = []
            
            # Search in each specified channel
            for channel in request.channels:
                print(f"Searching in channel: {channel}")
                
                if channel == SourceType.TELEGRAM:
                    # Search in Telegram data
                    telegram_results = self._search_telegram(request.query_text)
                elif channel == SourceType.PDF:
                    # Search in PDF documents
                    pdf_results = self._search_pdf(request.query_text)
                elif channel == SourceType.CALENDAR:
                    # Search in tax calendar
                    calendar_results = self._search_calendar(request.query_text)
                elif channel == SourceType.NEWS:
                    # Search in news articles
                    news_results = self._search_news(request.query_text)
                elif channel == SourceType.AEAT:
                    # Search in AEAT resources
                    aeat_results = self._search_aeat(request.query_text)
                    # Add AEAT to telegram for now
                    telegram_results.extend(aeat_results)
                elif channel == SourceType.REFERENCE:
                    # Search in reference materials
                    reference_results = self._search_reference(request.query_text)
            
            # Log total results found
            total_results = len(telegram_results) + len(pdf_results) + len(calendar_results) + len(news_results) + len(reference_results)
            print(f"Total results found: {total_results} (telegram: {len(telegram_results)}, pdf: {len(pdf_results)}, calendar: {len(calendar_results)}, news: {len(news_results)}, reference: {len(reference_results)})")
            
            # Step 5: Skip LLM response generation - return clean search results only
            generated_response = None
            
            # Step 6: Save message to database (or mock if not available)
            # Convert channel results to dict for saving
            all_sources = []
            for r in telegram_results:
                all_sources.append({**r, 'source_type': 'telegram'})
            for r in pdf_results:
                all_sources.append({**r, 'source_type': 'pdf'})
            for r in calendar_results:
                all_sources.append({**r, 'source_type': 'calendar'})
            for r in news_results:
                all_sources.append({**r, 'source_type': 'news'})
            for r in reference_results:
                all_sources.append({**r, 'source_type': 'reference'})
            
            if self.supabase.connection:
                self.supabase.save_message(
                    session_id=session_id,
                    user_id=user_id,
                    query_text=request.query_text,
                    response_text=generated_response,
                    sources=all_sources,
                    is_relevant=len(all_sources) > 0
                )
            else:
                print("Mock mode: Message not saved to database")
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Convert channel-specific results to SearchResult models
            telegram_search_results = [SearchResult(text=r['text'], metadata=r['metadata'], score=r['score'], source_type=SourceType.TELEGRAM) for r in telegram_results]
            pdf_search_results = [SearchResult(text=r['text'], metadata=r['metadata'], score=r['score'], source_type=SourceType.PDF) for r in pdf_results]
            calendar_search_results = [SearchResult(text=r['text'], metadata=r['metadata'], score=r['score'], source_type=SourceType.CALENDAR) for r in calendar_results]
            news_search_results = [SearchResult(text=r['text'], metadata=r['metadata'], score=r['score'], source_type=SourceType.NEWS) for r in news_results]
            reference_search_results = [SearchResult(text=r['text'], metadata=r['metadata'], score=r['score'], source_type=SourceType.REFERENCE) for r in reference_results]
            
            return SearchResponse(
                success=True,
                query_text=request.query_text,
                user_id=user_id,
                session_id=session_id,
                telegram_results=telegram_search_results,
                pdf_results=pdf_search_results,
                calendar_results=calendar_search_results,
                news_results=news_search_results,
                reference_results=reference_search_results,
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
    
    def _generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """Generate embedding for search query"""
        try:
            if not self.llm.embeddings_model:
                print("Embeddings model not available")
                return None
            
            # Generate embedding
            embedding = self.llm.embeddings_model.embed_query(query)
            return embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def _search_telegram(self, query: str) -> List[Dict]:
        """Search in Telegram channels data using HYBRID search (semantic + keyword)"""
        if not self.elastic.client:
            print("Elasticsearch client not available")
            return []
        
        try:
            # Generate query embedding for semantic search
            query_embedding = self._generate_query_embedding(query)
            
            if query_embedding:
                # HYBRID SEARCH: Use kNN for semantic + multi_match for keyword
                search_body = {
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
            else:
                # KEYWORD-ONLY SEARCH: fallback if no embeddings
                search_body = {
                    "size": 10,
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["content^2", "first_message", "last_message", "topics", "keywords"],
                            "type": "best_fields"
                        }
                    }
                }
            
            # Execute search
            response = self.elastic.client.search(
                index="telegram_threads",
                body=search_body
            )
            
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                # Get content text
                text = source.get('content', '')
                if not text:
                    text = source.get('first_message', '')
                
                results.append({
                    'text': text,
                    'metadata': {
                        'thread_id': source.get('thread_id'),
                        'group_name': source.get('group_name'),
                        'group_type': source.get('group_type'),
                        'message_count': source.get('message_count'),
                        'topics': source.get('topics', []),
                        'keywords': source.get('keywords', []),
                        'quality_score': source.get('quality_score', 0)
                    },
                    'score': hit['_score']
                })
            
            search_type = "hybrid (kNN + keyword)" if query_embedding else "keyword-only"
            print(f"Telegram {search_type} search returned {len(results)} results")
            return results
            
        except Exception as e:
            print(f"Error searching Telegram: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _translate_query(self, query: str) -> str:
        """
        Translate Russian/Ukrainian/English queries to Spanish
        Supports 4 languages: ES (native), RU, UK, EN
        """
        try:
            # Common tax terms mapping (4 languages → Spanish)
            translations = {
                # Russian (Русский)
                'ндс': 'IVA',
                'налог': 'impuesto',
                'налоги': 'impuestos',
                'автономо': 'autónomo',
                'доход': 'renta',
                'компания': 'sociedad',
                'декларация': 'declaración',
                'размер': 'tipo',
                'ставка': 'tipo',
                'процент': 'porcentaje',
                'оплата': 'pago',
                'срок': 'plazo',
                # Ukrainian (Українська)
                'пдв': 'IVA',
                'податок': 'impuesto',
                'податки': 'impuestos',
                'автономо': 'autónomo',
                'дохід': 'renta',
                'доходи': 'renta',
                'компанія': 'sociedad',
                'декларація': 'declaración',
                'розмір': 'tipo',
                'ставка': 'tipo',
                'відсоток': 'porcentaje',
                'оплата': 'pago',
                'термін': 'plazo',
                # English
                'vat': 'IVA',
                'tax': 'impuesto',
                'taxes': 'impuestos',
                'self-employed': 'autónomo',
                'income': 'renta',
                'company': 'sociedad',
                'declaration': 'declaración',
                'rate': 'tipo',
                'percentage': 'porcentaje',
                'payment': 'pago',
                'deadline': 'plazo'
            }
            
            # Detect if needs translation (Cyrillic = Russian or Ukrainian)
            has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in query)
            query_lower = query.lower()
            
            # Check for English terms
            english_terms = ['vat', 'tax', 'income', 'self-employed', 'company', 'deadline']
            has_english = any(term in query_lower for term in english_terms)
            
            if has_cyrillic or has_english:
                translated = query_lower
                for term, translation in translations.items():
                    translated = translated.replace(term, translation)
                
                if translated != query_lower:
                    print(f"📝 Query translated: '{query}' → '{translated}'")
                    return translated
            
            return query
            
        except Exception as e:
            print(f"Translation error: {e}")
            return query
    
    def _search_pdf(self, query: str) -> List[Dict]:
        """Search in PDF documents using HYBRID search (semantic + keyword + translation)"""
        if not self.elastic.client:
            print("Elasticsearch client not available")
            return []
        
        try:
            # Generate query embedding for semantic search
            query_embedding = self._generate_query_embedding(query)
            
            # Translate query for keyword search
            search_query = self._translate_query(query)
            
            if query_embedding:
                # HYBRID SEARCH: kNN (semantic) + multi_match (keyword with translation)
                search_body = {
                    "size": 10,
                    "query": {
                        "bool": {
                            "should": [
                                # Keyword search with translation
                                {
                                    "multi_match": {
                                        "query": search_query,
                                        "fields": ["content^2", "document_title", "categories"],
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
            else:
                # FALLBACK: Keyword-only with translation
                search_body = {
                    "size": 10,
                    "query": {
                        "multi_match": {
                            "query": search_query,
                            "fields": ["content^2", "document_title", "categories"],
                            "type": "best_fields"
                        }
                    }
                }
            
            response = self.elastic.client.search(
                index="pdf_documents",
                body=search_body
            )
            
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                # Get content text (truncate if too long)
                text = source.get('content', '')[:500]  # First 500 chars
                
                results.append({
                    'text': text,
                    'metadata': {
                        'document_id': source.get('document_id'),
                        'document_title': source.get('document_title'),
                        'document_type': source.get('document_type'),
                        'document_number': source.get('document_number'),
                        'categories': source.get('categories', []),
                        'chunk_index': source.get('chunk_index'),
                        'source': source.get('source')
                    },
                    'score': hit['_score']
                })
            
            search_type = "hybrid (kNN + keyword + translation)" if query_embedding else "keyword + translation"
            print(f"PDF {search_type} search returned {len(results)} results")
            return results
            
        except Exception as e:
            print(f"Error searching PDF: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _search_calendar(self, query: str) -> List[Dict]:
        """Search in tax calendar using Elasticsearch with multilingual support"""
        if not self.elastic.client:
            print("Elasticsearch client not available")
            return []
        
        try:
            # Translate query for better results
            search_query = self._translate_query(query)
            
            response = self.elastic.client.search(
                index="calendar_deadlines",
                body={
                    "query": {
                        "multi_match": {
                            "query": search_query,
                            "fields": ["description^2", "tax_type", "tax_model", "penalty_for_late"],
                            "type": "best_fields"
                        }
                    }
                },
                size=5  # Return 5 results for Calendar
            )
            
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                # Format deadline info
                deadline_text = f"{source.get('description', 'No description')} (Plazo: {source.get('deadline_date')})"
                
                results.append({
                    'text': deadline_text,
                    'metadata': {
                        'deadline_date': source.get('deadline_date'),
                        'tax_type': source.get('tax_type'),
                        'tax_model': source.get('tax_model'),
                        'quarter': source.get('quarter'),
                        'applies_to': source.get('applies_to', []),
                        'payment_required': source.get('payment_required'),
                        'declaration_required': source.get('declaration_required')
                    },
                    'score': hit['_score']
                })
            
            print(f"Calendar search returned {len(results)} results")
            return results
        except Exception as e:
            print(f"Error searching Calendar: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _search_news(self, query: str) -> List[Dict]:
        """Search in news articles using Elasticsearch"""
        if not self.elastic.client:
            print("Elasticsearch client not available")
            return []
        
        try:
            response = self.elastic.client.search(
                index="news_articles",
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["content^2", "article_title", "categories"],
                            "type": "best_fields"
                        }
                    }
                },
                size=5  # Return 5 results for News
            )
            
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                text = source.get('content', '')[:500]  # First 500 chars
                
                results.append({
                    'text': text,
                    'metadata': {
                        'article_title': source.get('article_title'),
                        'article_url': source.get('article_url'),
                        'news_source': source.get('news_source'),
                        'published_at': source.get('published_at'),
                        'categories': source.get('categories', [])
                    },
                    'score': hit['_score']
                })
            
            print(f"News search returned {len(results)} results")
            return results
        except Exception as e:
            print(f"Error searching News: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _search_aeat(self, query: str) -> List[Dict]:
        """Search in AEAT resources using Elasticsearch"""
        if not self.elastic.client:
            print("Elasticsearch client not available")
            return []
        
        try:
            # Check if index exists
            from elasticsearch import NotFoundError
            if not self.elastic.client.indices.exists(index="aeat_resources"):
                print("⚠️ aeat_resources index does not exist, skipping")
                return []
            
            response = self.elastic.client.search(
                index="aeat_resources",
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["content^2", "resource_title", "resource_type", "model_number"],
                            "type": "best_fields"
                        }
                    }
                },
                size=5
            )
            
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                text = source.get('content', '')[:500]  # First 500 chars
                
                results.append({
                    'text': text,
                    'metadata': {
                        'resource_title': source.get('resource_title'),
                        'resource_url': source.get('resource_url'),
                        'resource_type': source.get('resource_type'),
                        'model_number': source.get('model_number'),
                        'categories': source.get('categories', [])
                    },
                    'score': hit['_score']
                })
            
            print(f"AEAT search returned {len(results)} results")
            return results
        except NotFoundError:
            print("⚠️ aeat_resources index not found")
            return []
        except Exception as e:
            print(f"Error searching AEAT: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _search_reference(self, query: str) -> List[Dict]:
        """Search in reference materials using HYBRID search (semantic + keyword + translation)"""
        if not self.elastic.client:
            print("Elasticsearch client not available")
            return []
        
        try:
            # Check if index exists
            from elasticsearch import NotFoundError
            if not self.elastic.client.indices.exists(index="reference_materials"):
                print("⚠️ reference_materials index does not exist, skipping")
                return []
            
            # Generate query embedding for semantic search
            query_embedding = self._generate_query_embedding(query)
            
            # Translate query for keyword search
            search_query = self._translate_query(query)
            
            if query_embedding:
                # HYBRID SEARCH: kNN (semantic) + multi_match (keyword with translation)
                search_body = {
                    "size": 10,
                    "query": {
                        "bool": {
                            "should": [
                                # Keyword search with translation
                                {
                                    "multi_match": {
                                        "query": search_query,
                                        "fields": ["title^3", "content^2", "keywords^2", "category"],
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
            else:
                # FALLBACK: Keyword-only with translation
                search_body = {
                    "size": 10,
                    "query": {
                        "multi_match": {
                            "query": search_query,
                            "fields": ["title^3", "content^2", "keywords^2", "category"],
                            "type": "best_fields"
                        }
                    }
                }
            
            response = self.elastic.client.search(
                index="reference_materials",
                body=search_body
            )
            
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                # Get full content for reference materials
                text = source.get('content', '')
                
                results.append({
                    'text': text,
                    'metadata': {
                        'reference_id': source.get('reference_id'),
                        'title': source.get('title'),
                        'category': source.get('category'),
                        'subcategory': source.get('subcategory'),
                        'keywords': source.get('keywords', []),
                        'applies_to': source.get('applies_to', []),
                        'references': source.get('references', []),
                        'source': source.get('source'),
                        'last_updated': source.get('last_updated')
                    },
                    'score': hit['_score']
                })
            
            search_type = "hybrid (kNN + keyword + translation)" if query_embedding else "keyword + translation"
            print(f"Reference materials {search_type} search returned {len(results)} results")
            return results
            
        except NotFoundError:
            print("⚠️ reference_materials index not found")
            return []
        except Exception as e:
            print(f"Error searching reference materials: {e}")
            import traceback
            traceback.print_exc()
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

