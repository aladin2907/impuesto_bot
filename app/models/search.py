"""
Data models for search requests and responses
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, AnyHttpUrl
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Types of knowledge sources"""
    TELEGRAM = "telegram"
    PDF = "pdf"
    CALENDAR = "calendar"
    NEWS = "news"
    AEAT = "aeat"
    REGIONAL = "regional"
    ALL = "all"


class SearchFilters(BaseModel):
    """Filters for search queries"""
    source_types: Optional[List[SourceType]] = Field(
        default=None,
        description="Filter by source types (telegram, pdf, news, etc.)"
    )
    date_from: Optional[datetime] = Field(
        default=None,
        description="Filter results from this date"
    )
    date_to: Optional[datetime] = Field(
        default=None,
        description="Filter results until this date"
    )
    tax_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by tax types (IRPF, IVA, Sociedades, etc.)"
    )
    regions: Optional[List[str]] = Field(
        default=None,
        description="Filter by regions (national, Cataluña, Madrid, etc.)"
    )
    only_tax_related: Optional[bool] = Field(
        default=True,
        description="Filter only tax-related content"
    )
    minimum_quality_score: Optional[float] = Field(
        default=2.0,
        description="Minimum quality score for results (0.0-5.0)"
    )


class UserContext(BaseModel):
    """User context information"""
    channel_type: str = Field(
        ...,
        description="Channel type (telegram, whatsapp, web, etc.)",
        examples=["telegram", "whatsapp", "web"]
    )
    channel_user_id: str = Field(
        ...,
        description="User ID in the specific channel"
    )
    user_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional user metadata (username, first_name, etc.)"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Existing session ID (if continuing conversation)"
    )


class SearchRequest(BaseModel):
    """Request model for search endpoint - receives channels list from n8n"""
    user_context: UserContext = Field(
        ...,
        description="User context and identification"
    )
    query_text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query text from user",
        examples=["¿Cuándo tengo que presentar el modelo 303?"]
    )
    channels: List[SourceType] = Field(
        ...,
        description="List of channels to search in (from n8n)",
        examples=[["telegram", "pdf", "calendar"]]
    )
    top_k: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return"
    )
    webhook_url: str = Field(
        default="https://n8n.mafiavlc.org/webhook-test/59c06e61-a477-42df-8959-20f056f33189",
        description="n8n webhook URL to send results to"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
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
        }


class SearchResult(BaseModel):
    """Single search result"""
    text: str = Field(
        ...,
        description="Retrieved text chunk"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the source"
    )
    score: float = Field(
        ...,
        description="Relevance score"
    )
    source_type: Optional[str] = Field(
        default=None,
        description="Type of source (telegram, pdf, news, etc.)"
    )


class SearchResponse(BaseModel):
    """Response model for search endpoint"""
    success: bool = Field(
        ...,
        description="Whether the search was successful"
    )
    query_text: str = Field(
        ...,
        description="Original query text"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User ID in our system"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for this conversation"
    )
    results: List[SearchResult] = Field(
        default_factory=list,
        description="List of search results from specified channels"
    )
    subscription_status: Optional[str] = Field(
        default=None,
        description="User subscription status (free, premium)"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if search failed"
    )
    processing_time_ms: Optional[int] = Field(
        default=None,
        description="Total processing time in milliseconds"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "query_text": "¿Cuándo tengo que presentar el modelo 303?",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": "660e8400-e29b-41d4-a716-446655440001",
                "results": [
                    {
                        "text": "El modelo 303 debe presentarse trimestralmente...",
                        "metadata": {
                            "source_type": "calendar",
                            "tax_type": "IVA"
                        },
                        "score": 0.95,
                        "source_type": "calendar"
                    }
                ],
                "generated_response": "El modelo 303 de IVA debe presentarse trimestralmente...",
                "subscription_status": "free",
                "processing_time_ms": 1250
            }
        }


class SourceResults(BaseModel):
    """Results grouped by source for N8N integration"""
    source: SourceType
    results: List[SearchResult]


class N8NSearchRequest(BaseModel):
    """Request payload for N8N multi-source search"""
    query_text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query text"
    )
    sources: Optional[List[SourceType]] = Field(
        default=None,
        description="List of sources to include (defaults to all)"
    )
    top_k_per_source: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Number of results to fetch per source"
    )
    aggregate_results: bool = Field(
        default=True,
        description="Whether to return a combined result list in addition to per-source results"
    )
    callback_url: Optional[AnyHttpUrl] = Field(
        default=None,
        description="Optional N8N webhook URL to POST the results to"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="External request identifier for tracing"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata to echo back in the response"
    )
    user_context: Optional[UserContext] = Field(
        default=None,
        description="Optional user context; defaults to system context if omitted"
    )
    filters: Optional[SearchFilters] = Field(
        default=None,
        description="Base filters to apply for every source"
    )


class N8NSearchResponse(BaseModel):
    """Response payload for N8N multi-source search"""
    success: bool = Field(default=True)
    query_text: str
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    aggregated_results: Optional[List[SearchResult]] = None
    sources: List[SourceResults]
    callback_status: Optional[str] = Field(
        default=None,
        description="Status of callback delivery (if callback_url provided)"
    )


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint"""
    status: str = Field(
        ...,
        description="Service status"
    )
    elasticsearch_connected: bool = Field(
        ...,
        description="Elasticsearch connection status"
    )
    supabase_connected: bool = Field(
        ...,
        description="Supabase connection status"
    )
    llm_initialized: bool = Field(
        ...,
        description="LLM service initialization status"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Check timestamp"
    )
