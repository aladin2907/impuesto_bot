"""
Main entry point for TuExpertoFiscal API
Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from app.api.webhook import app

# This allows running with: uvicorn main:app
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting TuExpertoFiscal API Server...")
    print("📚 Documentation: http://localhost:8000/docs")
    print("🔍 Health check: http://localhost:8000/health")
    print("🌐 Search endpoint: http://localhost:8000/search")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

