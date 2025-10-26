"""
FastAPI webhook endpoint for N8N integration
Handles search requests from N8N workflow
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Optional, List, Dict, Set, Any
import logging
import httpx
import asyncio

from app.models.search import (
    SearchRequest,
    SearchResponse,
    HealthCheckResponse,
    SearchFilters,
    N8NSearchRequest,
    N8NSearchResponse,
    SourceResults,
    SourceType,
    UserContext,
    SearchResult
)
from app.services.search_service import search_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="TuExpertoFiscal API",
    description="AI-powered Spanish tax assistant API for N8N integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get search service
def get_search_service():
    """Dependency to get initialized search service"""
    if not search_service.initialized:
        logger.info("Initializing search service...")
        if not search_service.initialize():
            raise HTTPException(
                status_code=503,
                detail="Search service initialization failed"
            )
    return search_service


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting TuExpertoFiscal API...")
    
    try:
        if not search_service.initialized:
            success = search_service.initialize()
            if success:
                logger.info("✅ All services initialized successfully")
            else:
                logger.error("❌ Failed to initialize services")
    except Exception as e:
        logger.error(f"❌ Error during startup: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down TuExpertoFiscal API...")
    try:
        search_service.close()
        logger.info("✅ Services closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "service": "TuExpertoFiscal API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


async def process_search_and_send(request: SearchRequest, service, webhook_url: str):
    """
    Background task: process search and send results to n8n webhook
    """
    try:
        logger.info(f"Background task: processing search for query '{request.query_text}'")
        
        # Execute search
        response = await service.search(request)
        
        # Log results
        if response.success:
            logger.info(f"Search successful: {len(response.results)} results, {response.processing_time_ms}ms")
        else:
            logger.warning(f"Search failed: {response.error_message}")
        
        # Send results to n8n webhook
        async with httpx.AsyncClient(timeout=30.0) as client:
            webhook_response = await client.post(
                webhook_url,
                json=response.model_dump()
            )
            logger.info(f"Results sent to webhook: {webhook_response.status_code}")
            
    except Exception as e:
        logger.error(f"Error in background search task: {e}", exc_info=True)


@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check(service = Depends(get_search_service)):
    """
    Health check endpoint
    
    Returns status of all services (Elasticsearch, Supabase, LLM)
    """
    try:
        health = service.health_check()
        
        # Service is healthy if initialized (even in mock mode)
        all_healthy = health.get("search_service_initialized", False)
        
        status_code = 200 if all_healthy else 503
        
        response = HealthCheckResponse(
            status="healthy" if all_healthy else "unhealthy",
            elasticsearch_connected=health.get("elasticsearch_connected", False),
            supabase_connected=health.get("supabase_connected", False),
            llm_initialized=health.get("llm_initialized", False),
            timestamp=datetime.now()
        )
        
        return JSONResponse(
            status_code=status_code,
            content=response.model_dump(mode='json')
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        
        response_data = HealthCheckResponse(
            status="error",
            elasticsearch_connected=False,
            supabase_connected=False,
            llm_initialized=False,
            timestamp=datetime.now()
        )
        
        return JSONResponse(
            status_code=503,
            content={
                **response_data.model_dump(mode='json'),
                "error": str(e)
            }
        )


@app.post("/search", tags=["Search"])
async def search_endpoint(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    service = Depends(get_search_service)
):
    """
    Main search endpoint for N8N integration - async processing
    
    Accepts request, returns 200 OK immediately, then processes search 
    and sends results to n8n webhook.
    
    **Request Parameters:**
    - **user_context**: User identification (channel_type, channel_user_id, metadata)
    - **query_text**: Search query from user (1-1000 characters)
    - **channels**: List of channels to search in (telegram, pdf, calendar, news, aeat)
    - **top_k**: Number of results to return (1-20, default: 5)
    - **webhook_url**: n8n webhook URL to send results to (default: n8n.mafiavlc.org)
    
    **Immediate Response:** 200 OK
    
    **Results sent to webhook_url as POST:**
    ```json
    {
      "success": true,
      "query_text": "...",
      "results": [...],
      "processing_time_ms": 123
    }
    ```
    
    **Example Request:**
    ```json
    {
      "user_context": {
        "channel_type": "telegram",
        "channel_user_id": "123456789"
      },
      "query_text": "IRPF declaración",
      "channels": ["telegram"],
      "top_k": 3,
      "webhook_url": "https://n8n.mafiavlc.org/webhook/59c06e61-a477-42df-8959-20f056f33189"
    }
    ```
    """
    try:
        logger.info(f"Search request from {request.user_context.channel_type}:{request.user_context.channel_user_id}")
        logger.info(f"Query: {request.query_text}")
        logger.info(f"Webhook URL: {request.webhook_url}")
        
        # Add background task to process search and send to webhook
        background_tasks.add_task(process_search_and_send, request, service, request.webhook_url)
        
        # Return 200 OK immediately
        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted", 
                "message": "Search request accepted and processing in background",
                "query": request.query_text,
                "channels": [str(ch) for ch in request.channels]
            }
        )
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _build_filters_for_source(base_filters: Optional[SearchFilters], source: SourceType) -> SearchFilters:
    filters_data: Dict[str, Any] = {}
    if base_filters:
        filters_data = base_filters.model_dump(mode="python")
    filters_data.pop("source_types", None)
    filters_data["source_types"] = [source]
    return SearchFilters(**filters_data)


_DEDUP_KEYS = (
    "document_id",
    "article_url",
    "resource_url",
    "source_url",
    "uid",
    "id",
)


def _result_dedup_key(metadata: Dict[str, Any], text: str) -> str:
    for key in _DEDUP_KEYS:
        value = metadata.get(key)
        if value:
            return f"{key}:{value}"
    return f"text:{hash(text)}"


def _deduplicate_results(results: List[SearchResult]) -> List[SearchResult]:
    unique: List[SearchResult] = []
    seen: Set[str] = set()

    for result in results:
        metadata = result.metadata or {}
        key = _result_dedup_key(metadata, result.text)
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)

    return unique


_DEFAULT_SOURCES: List[SourceType] = [
    source for source in SourceType if source not in {SourceType.ALL}
]


def _normalise_sources(requested: Optional[List[SourceType]]) -> List[SourceType]:
    if not requested or SourceType.ALL in requested:
        return list(_DEFAULT_SOURCES)

    seen: Set[SourceType] = set()
    ordered: List[SourceType] = []
    for source in requested:
        if source in seen:
            continue
        seen.add(source)
        ordered.append(source)
    return ordered


@app.post("/n8n/search", response_model=N8NSearchResponse, tags=["Search"])
async def n8n_search_endpoint(
    request: N8NSearchRequest,
    service = Depends(get_search_service)
):
    """Multi-source search endpoint tailored for N8N workflows."""
    sources = _normalise_sources(request.sources)

    user_context = request.user_context or UserContext(
        channel_type="n8n",
        channel_user_id=request.request_id or "n8n"
    )

    source_groups: List[SourceResults] = []

    for source in sources:
        filters = _build_filters_for_source(request.filters, source)
        search_request = SearchRequest(
            user_context=user_context,
            query_text=request.query_text,
            filters=filters,
            top_k=request.top_k_per_source,
            generate_response=False
        )

        try:
            search_response = await service.search(search_request)
        except Exception as exc:
            logger.error("n8n search failed for source %s: %s", source.value, exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        unique_results = _deduplicate_results(search_response.results)
        source_groups.append(SourceResults(source=source, results=unique_results))

    aggregated: Optional[List[SearchResult]] = None
    if request.aggregate_results:
        combined: List[SearchResult] = []
        for source_block in source_groups:
            combined.extend(source_block.results)
        aggregated = _deduplicate_results(combined)

    response_payload = N8NSearchResponse(
        success=True,
        query_text=request.query_text,
        request_id=request.request_id,
        metadata=request.metadata,
        aggregated_results=aggregated,
        sources=source_groups,
        callback_status=None
    )

    if request.callback_url:
        callback_status = None
        try:
            async with httpx.AsyncClient(timeout=10) as http_client:
                callback_response = await http_client.post(
                    str(request.callback_url),
                    json=response_payload.model_dump(mode="json")
                )
            if callback_response.status_code < 400:
                callback_status = f"delivered:{callback_response.status_code}"
            else:
                callback_status = f"failed:{callback_response.status_code}"
        except Exception as exc:
            logger.error("Failed to POST results to N8N callback: %s", exc)
            callback_status = f"failed:{exc}"

        response_payload = response_payload.model_copy(update={"callback_status": callback_status})

    return response_payload



@app.get("/stats", tags=["Statistics"])
async def get_stats(service = Depends(get_search_service)):
    """
    Get service statistics (optional endpoint for monitoring)
    """
    try:
        health = service.health_check()
        
        return {
            "status": "operational",
            "services": health,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_message": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "app.api.webhook:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
