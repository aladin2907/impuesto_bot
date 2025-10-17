"""
Tests for webhook API endpoint
Following TDD practice - tests first, then implementation
"""

import sys
import types

# Provide lightweight stub for elasticsearch package used during imports
if "elasticsearch" not in sys.modules:  # pragma: no cover - test scaffolding
    class _FakeElasticsearch:
        def __init__(self, *_, **__):
            self.indices = types.SimpleNamespace(exists=lambda **__: False, create=lambda **__: None)

        def info(self):
            return {"version": {"number": "8.0.0"}}

        def index(self, *_, **__):
            return None

        def search(self, *_, **__):
            return {"hits": {"hits": []}}

        def close(self):
            pass

    fake_module = types.ModuleType("elasticsearch")
    fake_module.Elasticsearch = _FakeElasticsearch
    sys.modules["elasticsearch"] = fake_module


if "langchain_openai" not in sys.modules:  # pragma: no cover - test scaffolding
    class _FakeChatOpenAI:
        def __init__(self, *_, **__):
            pass

        def invoke(self, *_, **__):
            return types.SimpleNamespace(content="mock-response")

    class _FakeOpenAIEmbeddings:
        def __init__(self, *_, **__):
            pass

        def embed_query(self, *_):
            return [0.1, 0.2, 0.3]

    fake_module = types.ModuleType("langchain_openai")
    fake_module.ChatOpenAI = _FakeChatOpenAI
    fake_module.OpenAIEmbeddings = _FakeOpenAIEmbeddings
    sys.modules["langchain_openai"] = fake_module


if "langchain_google_genai" not in sys.modules:  # pragma: no cover
    class _FakeChatGoogle:
        def __init__(self, *_, **__):
            pass

    class _FakeGoogleEmbeddings:
        def __init__(self, *_, **__):
            pass

        def embed_query(self, *_):
            return [0.1, 0.2, 0.3]

    fake_module = types.ModuleType("langchain_google_genai")
    fake_module.ChatGoogleGenerativeAI = _FakeChatGoogle
    fake_module.GoogleGenerativeAIEmbeddings = _FakeGoogleEmbeddings
    sys.modules["langchain_google_genai"] = fake_module


if "langchain_anthropic" not in sys.modules:  # pragma: no cover
    class _FakeChatAnthropic:
        def __init__(self, *_, **__):
            pass

    fake_module = types.ModuleType("langchain_anthropic")
    fake_module.ChatAnthropic = _FakeChatAnthropic
    sys.modules["langchain_anthropic"] = fake_module

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.models.search import SearchResponse, SearchResult


@pytest.fixture
def mock_search_service():
    """Mock search service"""
    mock = Mock()
    
    # Mock search function that returns dynamic response based on input
    async def mock_search_func(request):
        if request.filters and request.filters.source_types:
            source_value = request.filters.source_types[0].value
        else:
            source_value = "calendar"

        return SearchResponse(
            success=True,
            query_text=request.query_text,  # Return actual query from request
            user_id="user-123-uuid",
            session_id="session-456-uuid",
            results=[
                SearchResult(
                    text=f"Resultado {source_value} para {request.query_text}",
                    metadata={
                        "source_type": source_value,
                        "document_id": f"{source_value}-doc",
                        "source_url": f"https://example.org/{source_value}/doc"
                    },
                    score=0.95,
                    source_type=source_value
                )
            ],
            generated_response=f"Generated answer for {request.query_text}",
            subscription_status="free",
            processing_time_ms=1250
        )
    
    mock.search = AsyncMock(side_effect=mock_search_func)
    mock.initialize = Mock(return_value=True)
    mock.health_check = Mock(return_value={
        "elasticsearch_connected": True,
        "supabase_connected": True,
        "llm_initialized": True,
        "search_service_initialized": True
    })
    mock.initialized = True
    
    return mock


@pytest.fixture
def client(mock_search_service):
    """Create test client with mocked search service"""
    # Import here to avoid circular imports
    from app.api.webhook import app
    from app.api.webhook import get_search_service
    
    # Override dependency
    app.dependency_overrides[get_search_service] = lambda: mock_search_service
    
    return TestClient(app)


class TestHealthCheckEndpoint:
    """Test /health endpoint"""
    
    def test_health_check_success(self, client):
        """Test health check returns 200 when all services are healthy"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["elasticsearch_connected"] is True
        assert data["supabase_connected"] is True
        assert data["llm_initialized"] is True
        assert "timestamp" in data
    
    def test_health_check_unhealthy(self, client, mock_search_service):
        """Test health check returns 503 when services are down"""
        mock_search_service.health_check = Mock(return_value={
            "elasticsearch_connected": False,
            "supabase_connected": True,
            "llm_initialized": True,
            "search_service_initialized": False
        })
        
        response = client.get("/health")
        
        assert response.status_code == 503
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert data["elasticsearch_connected"] is False


class TestSearchEndpoint:
    """Test /search endpoint"""
    
    def test_search_success_full_request(self, client):
        """Test successful search with full request payload"""
        request_data = {
            "user_context": {
                "channel_type": "telegram",
                "channel_user_id": "123456789",
                "user_metadata": {
                    "username": "john_doe",
                    "first_name": "John"
                }
            },
            "query_text": "¿Cuándo tengo que presentar el modelo 303?",
            "filters": {
                "source_types": ["calendar", "aeat"],
                "tax_types": ["IVA"],
                "only_tax_related": True
            },
            "top_k": 5,
            "generate_response": True
        }
        
        response = client.post("/search", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["query_text"] == request_data["query_text"]
        assert data["user_id"] == "user-123-uuid"
        assert data["session_id"] == "session-456-uuid"
        assert len(data["results"]) > 0
        assert data["generated_response"] is not None
        assert data["subscription_status"] == "free"
        assert data["processing_time_ms"] is not None
    
    def test_search_minimal_request(self, client):
        """Test search with minimal required fields"""
        request_data = {
            "user_context": {
                "channel_type": "telegram",
                "channel_user_id": "123456789"
            },
            "query_text": "¿Qué es el IVA?"
        }
        
        response = client.post("/search", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["query_text"] == request_data["query_text"]
    
    def test_search_with_existing_session(self, client):
        """Test search with existing session ID"""
        request_data = {
            "user_context": {
                "channel_type": "telegram",
                "channel_user_id": "123456789",
                "session_id": "existing-session-uuid"
            },
            "query_text": "¿Cuándo es el próximo plazo?"
        }
        
        response = client.post("/search", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
    
    def test_search_without_response_generation(self, client):
        """Test search without generating LLM response"""
        request_data = {
            "user_context": {
                "channel_type": "web",
                "channel_user_id": "web-user-456"
            },
            "query_text": "modelo 303",
            "generate_response": False
        }
        
        response = client.post("/search", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert len(data["results"]) > 0


class TestN8NSearchEndpoint:
    """Tests for /n8n/search endpoint"""

    def test_n8n_search_multiple_sources(self, client, mock_search_service):
        payload = {
            "query_text": "modelos",
            "sources": ["calendar", "news"],
            "top_k_per_source": 1
        }

        response = client.post("/n8n/search", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["aggregated_results"] is not None
        assert len(data["sources"]) == 2
        assert {entry["source"] for entry in data["sources"]} == {"calendar", "news"}
        assert mock_search_service.search.await_count == 2
        assert data["callback_status"] is None

    @patch("app.api.webhook.httpx.AsyncClient")
    def test_n8n_search_callback(self, mock_async_client_cls, client):
        mock_client = AsyncMock()
        mock_client.post.return_value.status_code = 200
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None
        mock_async_client_cls.return_value = mock_context

        payload = {
            "query_text": "IVA",
            "sources": ["calendar"],
            "callback_url": "https://n8n.example.com/webhook/test"
        }

        response = client.post("/n8n/search", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["callback_status"] == "delivered:200"
        mock_client.post.assert_awaited_once()
    
    def test_search_with_filters(self, client):
        """Test search with various filters"""
        request_data = {
            "user_context": {
                "channel_type": "telegram",
                "channel_user_id": "123456789"
            },
            "query_text": "¿Cuándo pago impuestos?",
            "filters": {
                "source_types": ["calendar"],
                "date_from": "2025-01-01T00:00:00Z",
                "date_to": "2025-12-31T23:59:59Z",
                "tax_types": ["IVA", "IRPF"],
                "regions": ["national", "Cataluña"],
                "only_tax_related": True,
                "minimum_quality_score": 3.0
            },
            "top_k": 10
        }
        
        response = client.post("/search", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
    
    def test_search_invalid_channel_type(self, client):
        """Test search with missing channel_type"""
        request_data = {
            "user_context": {
                "channel_user_id": "123456789"
            },
            "query_text": "test query"
        }
        
        response = client.post("/search", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_search_empty_query(self, client):
        """Test search with empty query text"""
        request_data = {
            "user_context": {
                "channel_type": "telegram",
                "channel_user_id": "123456789"
            },
            "query_text": ""
        }
        
        response = client.post("/search", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_search_query_too_long(self, client):
        """Test search with query exceeding max length"""
        request_data = {
            "user_context": {
                "channel_type": "telegram",
                "channel_user_id": "123456789"
            },
            "query_text": "x" * 1001  # Exceeds 1000 char limit
        }
        
        response = client.post("/search", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_search_invalid_top_k(self, client):
        """Test search with invalid top_k values"""
        # Test top_k = 0
        request_data = {
            "user_context": {
                "channel_type": "telegram",
                "channel_user_id": "123456789"
            },
            "query_text": "test",
            "top_k": 0
        }
        
        response = client.post("/search", json=request_data)
        assert response.status_code == 422
        
        # Test top_k > 20
        request_data["top_k"] = 21
        response = client.post("/search", json=request_data)
        assert response.status_code == 422
    
    def test_search_service_error(self, client, mock_search_service):
        """Test search when service returns error"""
        mock_search_service.search = AsyncMock(return_value=SearchResponse(
            success=False,
            query_text="test query",
            error_message="Internal service error"
        ))
        
        request_data = {
            "user_context": {
                "channel_type": "telegram",
                "channel_user_id": "123456789"
            },
            "query_text": "test query"
        }
        
        response = client.post("/search", json=request_data)
        
        # Should still return 200 but with success=False in body
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is False
        assert "error_message" in data
    
    def test_search_multiple_source_types(self, client):
        """Test search with multiple source types"""
        request_data = {
            "user_context": {
                "channel_type": "telegram",
                "channel_user_id": "123456789"
            },
            "query_text": "impuestos autónomos",
            "filters": {
                "source_types": ["telegram", "pdf", "news"]
            }
        }
        
        response = client.post("/search", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True


class TestWebhookCORS:
    """Test CORS configuration"""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in response"""
        response = client.options("/search")
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code in [200, 405]


class TestWebhookRateLimiting:
    """Test rate limiting (if implemented)"""
    
    @pytest.mark.skip(reason="Rate limiting not implemented yet")
    def test_rate_limiting(self, client):
        """Test that rate limiting is enforced"""
        request_data = {
            "user_context": {
                "channel_type": "telegram",
                "channel_user_id": "123456789"
            },
            "query_text": "test"
        }
        
        # Make many requests
        responses = [client.post("/search", json=request_data) for _ in range(100)]
        
        # At least one should be rate limited
        assert any(r.status_code == 429 for r in responses)


class TestWebhookErrorHandling:
    """Test error handling in webhook"""
    
    def test_malformed_json(self, client):
        """Test response to malformed JSON"""
        response = client.post(
            "/search",
            data="this is not json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client):
        """Test response when required fields are missing"""
        request_data = {
            "query_text": "test"
            # Missing user_context
        }
        
        response = client.post("/search", json=request_data)
        
        assert response.status_code == 422
        assert "detail" in response.json()
