"""
LLM Service Module
Provides unified interface for working with different LLM providers via LangChain
"""

from app.services.llm.llm_service import LLMService, llm_service

__all__ = ['LLMService', 'llm_service']