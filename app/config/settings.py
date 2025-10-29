"""
Configuration settings for TuExpertoFiscal NAIL
Loads environment variables and provides application settings
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""
    
    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # openai, google, anthropic, openrouter
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Google (Gemini)
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Anthropic (Claude)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # OpenRouter
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    
    # HuggingFace
    HUGGINGFACE_API_TOKEN: str = os.getenv("HUGGINGFACE_API_TOKEN", "")
    
    # Elasticsearch
    ELASTIC_CLOUD_ID: str = os.getenv("ELASTIC_CLOUD_ID", "")
    ELASTIC_API_KEY: str = os.getenv("ELASTIC_API_KEY", "")
    ELASTIC_INDEX_NAME: str = os.getenv("ELASTIC_INDEX_NAME", "tuexpertofiscal_knowledge")
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL", "")
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_WEBHOOK_URL: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_URL")
    
    # Telegram API (for parsing groups)
    TELEGRAM_API_ID: str = os.getenv("TELEGRAM_API_ID", "")
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_PHONE: str = os.getenv("TELEGRAM_PHONE", "")
    
    # WhatsApp
    WHATSAPP_API_TOKEN: Optional[str] = os.getenv("WHATSAPP_API_TOKEN")
    
    # Application
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    def validate(self) -> bool:
        """Validate that all required settings are present"""
        required = [
            self.OPENAI_API_KEY,
            self.ELASTIC_CLOUD_ID,
            self.ELASTIC_API_KEY,
            self.SUPABASE_URL,
            self.SUPABASE_KEY,
        ]
        return all(required)


# Global settings instance
settings = Settings()

