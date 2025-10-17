"""
Tests for SearchService
Following TDD practice - tests first, then implementation
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from app.models.search import (
    SearchRequest,
    SearchResponse,
    SearchFilters,
    UserContext,
    SourceType
)
from app.services.search_service import SearchService


@pytest.fixture
def mock_elastic_service():
    """Mock Elasticsearch service"""
    mock = Mock()
    mock.connect = Mock(return_value=True)
    mock.hybrid_search = Mock(return_value=[
        {
            'text': 'El modelo 303 debe presentarse trimestralmente',
            'metadata': {
                'source_type': 'calendar',
                'tax_type': 'IVA',
                'deadline_date': '2025-04-20'
            },
            'score': 0.95
        },
        {
            'text': 'El IVA es un impuesto indirecto sobre el consumo',
            'metadata': {
                'source_type': 'pdf',
                'document_type': 'law'
            },
            'score': 0.85
        }
    ])
    mock.close = Mock()
    return mock


@pytest.fixture
def mock_supabase_service():
    """Mock Supabase service"""
    mock = Mock()
    mock.connect = Mock(return_value=True)
    # Now returns full user dict instead of just id
    mock.get_or_create_user = Mock(return_value={
        'id': 'user-123-uuid',
        'telegram_id': 123456789,
        'username': 'john_doe',
        'subscription_status': 'free'
    })
    mock.get_user_subscription_status = Mock(return_value='free')
    mock.create_dialogue_session = Mock(return_value='session-456-uuid')
    mock.save_message = Mock(return_value=True)
    mock.connection = Mock()
    mock.close = Mock()
    return mock


@pytest.fixture
def mock_llm_service():
    """Mock LLM service"""
    mock = Mock()
    mock.initialize = Mock(return_value=True)
    mock.generate_embedding = Mock(return_value=[0.1] * 1536)  # Fake embedding
    mock.generate_async = AsyncMock(return_value="El modelo 303 de IVA debe presentarse trimestralmente...")
    mock.chat_model = Mock()
    return mock


@pytest.fixture
def search_service(mock_elastic_service, mock_supabase_service, mock_llm_service):
    """Create SearchService with mocked dependencies"""
    service = SearchService()
    service.elastic = mock_elastic_service
    service.supabase = mock_supabase_service
    service.llm = mock_llm_service
    service.initialized = True
    return service


@pytest.fixture
def sample_search_request():
    """Sample search request"""
    return SearchRequest(
        user_context=UserContext(
            channel_type="telegram",
            channel_user_id="123456789",
            user_metadata={"username": "john_doe", "first_name": "John"}
        ),
        query_text="¿Cuándo tengo que presentar el modelo 303?",
        filters=SearchFilters(
            source_types=[SourceType.CALENDAR, SourceType.AEAT],
            tax_types=["IVA"],
            only_tax_related=True
        ),
        top_k=5,
        generate_response=True
    )


class TestSearchServiceInitialization:
    """Test search service initialization"""
    
    def test_initialize_success(self, mock_elastic_service, mock_supabase_service, mock_llm_service):
        """Test successful initialization of all services"""
        service = SearchService()
        service.elastic = mock_elastic_service
        service.supabase = mock_supabase_service
        service.llm = mock_llm_service
        
        result = service.initialize()
        
        assert result is True
        assert service.initialized is True
        mock_elastic_service.connect.assert_called_once()
        mock_supabase_service.connect.assert_called_once()
        mock_llm_service.initialize.assert_called_once()
    
    def test_initialize_elasticsearch_fails(self, mock_elastic_service, mock_supabase_service, mock_llm_service):
        """Test initialization fails when Elasticsearch connection fails"""
        mock_elastic_service.connect = Mock(return_value=False)
        
        service = SearchService()
        service.elastic = mock_elastic_service
        service.supabase = mock_supabase_service
        service.llm = mock_llm_service
        
        result = service.initialize()
        
        assert result is False
        assert service.initialized is False


class TestSearchServiceSearch:
    """Test search functionality"""
    
    @pytest.mark.asyncio
    async def test_search_success_with_response_generation(self, search_service, sample_search_request):
        """Test successful search with LLM response generation"""
        response = await search_service.search(sample_search_request)
        
        assert response.success is True
        assert response.query_text == sample_search_request.query_text
        assert response.user_id == 'user-123-uuid'
        assert response.session_id == 'session-456-uuid'
        assert response.subscription_status == 'free'
        assert len(response.results) > 0
        assert response.generated_response is not None
        assert response.processing_time_ms is not None
        
        # Verify services were called
        search_service.supabase.get_or_create_user.assert_called_once()
        search_service.supabase.create_dialogue_session.assert_called_once()
        search_service.llm.generate_embedding.assert_called_once()
        search_service.elastic.hybrid_search.assert_called_once()
        search_service.llm.generate_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_without_response_generation(self, search_service, sample_search_request):
        """Test search without generating LLM response"""
        sample_search_request.generate_response = False
        
        response = await search_service.search(sample_search_request)
        
        assert response.success is True
        assert len(response.results) > 0
        assert response.generated_response is None
        
        # Verify LLM generate was NOT called
        search_service.llm.generate_async.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_search_with_existing_session(self, search_service, sample_search_request):
        """Test search with existing session ID"""
        sample_search_request.user_context.session_id = "existing-session-uuid"
        
        response = await search_service.search(sample_search_request)
        
        assert response.success is True
        assert response.session_id == "existing-session-uuid"
        
        # Verify create_dialogue_session was NOT called
        search_service.supabase.create_dialogue_session.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_search_service_not_initialized(self, search_service, sample_search_request):
        """Test search fails when service not initialized"""
        search_service.initialized = False
        
        response = await search_service.search(sample_search_request)
        
        assert response.success is False
        assert response.error_message == "Search service not initialized"
    
    @pytest.mark.asyncio
    async def test_search_user_creation_fails(self, search_service, sample_search_request):
        """Test search fails when user creation fails"""
        search_service.supabase.get_or_create_user = Mock(return_value=None)
        
        response = await search_service.search(sample_search_request)
        
        assert response.success is False
        assert "user" in response.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_search_embedding_generation_fails(self, search_service, sample_search_request):
        """Test search fails when embedding generation fails"""
        search_service.llm.generate_embedding = Mock(return_value=[])
        
        response = await search_service.search(sample_search_request)
        
        assert response.success is False
        assert "embedding" in response.error_message.lower()


class TestSearchServiceFilters:
    """Test search filters application"""
    
    def test_filter_by_source_types(self, search_service):
        """Test filtering results by source types"""
        results = [
            {'text': 'text1', 'metadata': {'source_type': 'calendar'}, 'score': 0.9},
            {'text': 'text2', 'metadata': {'source_type': 'pdf'}, 'score': 0.8},
            {'text': 'text3', 'metadata': {'source_type': 'telegram'}, 'score': 0.7}
        ]
        
        filters = SearchFilters(source_types=[SourceType.CALENDAR, SourceType.PDF])
        filtered = search_service._apply_filters(results, filters)
        
        assert len(filtered) == 2
        assert all(r['metadata']['source_type'] in ['calendar', 'pdf'] for r in filtered)
    
    def test_filter_by_tax_types(self, search_service):
        """Test filtering results by tax types"""
        results = [
            {'text': 'text1', 'metadata': {'tax_type': 'IVA'}, 'score': 0.9},
            {'text': 'text2', 'metadata': {'tax_type': 'IRPF'}, 'score': 0.8},
            {'text': 'text3', 'metadata': {'tax_type': 'IVA'}, 'score': 0.7}
        ]
        
        filters = SearchFilters(tax_types=['IVA'])
        filtered = search_service._apply_filters(results, filters)
        
        assert len(filtered) == 2
        assert all(r['metadata']['tax_type'] == 'IVA' for r in filtered)
    
    def test_filter_by_quality_score(self, search_service):
        """Test filtering results by quality score"""
        results = [
            {'text': 'text1', 'metadata': {'quality_score': 4.5}, 'score': 0.9},
            {'text': 'text2', 'metadata': {'quality_score': 1.5}, 'score': 0.8},
            {'text': 'text3', 'metadata': {'quality_score': 3.0}, 'score': 0.7}
        ]
        
        filters = SearchFilters(minimum_quality_score=3.0)
        filtered = search_service._apply_filters(results, filters)
        
        assert len(filtered) == 2
        assert all(r['metadata']['quality_score'] >= 3.0 for r in filtered)


class TestSearchServiceHealthCheck:
    """Test health check functionality"""
    
    def test_health_check_all_services_healthy(self, search_service):
        """Test health check when all services are healthy"""
        health = search_service.health_check()
        
        assert health['elasticsearch_connected'] is True
        assert health['supabase_connected'] is True
        assert health['llm_initialized'] is True
        assert health['search_service_initialized'] is True
    
    def test_health_check_elasticsearch_down(self, search_service):
        """Test health check when Elasticsearch is down"""
        search_service.elastic.client = None
        
        health = search_service.health_check()
        
        assert health['elasticsearch_connected'] is False
        assert health['supabase_connected'] is True


class TestSearchServiceCleanup:
    """Test service cleanup"""
    
    def test_close_closes_all_services(self, search_service):
        """Test that close() closes all service connections"""
        search_service.close()
        
        search_service.elastic.close.assert_called_once()
        search_service.supabase.close.assert_called_once()

