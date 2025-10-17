"""
LLM Service using LangChain
Provides unified interface for working with different LLM providers
"""

from typing import List, Optional, Tuple
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage
from app.config.settings import settings


class LLMService:
    """Service for managing LLM operations with different providers"""
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ):
        """
        Initialize LLM service
        
        Args:
            provider: LLM provider name (openai, google, anthropic, openrouter)
            model: Model name
            temperature: Sampling temperature
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        
        self.chat_model = None
        self.embeddings_model = None
        
    def initialize(self) -> bool:
        """Initialize the LLM and embeddings models"""
        try:
            # Initialize chat model based on provider
            if self.provider == "openai":
                self.chat_model = ChatOpenAI(
                    model=self.model,
                    temperature=self.temperature,
                    api_key=settings.OPENAI_API_KEY
                )
                self.embeddings_model = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    api_key=settings.OPENAI_API_KEY
                )
                
            elif self.provider == "google":
                self.chat_model = ChatGoogleGenerativeAI(
                    model=self.model,
                    temperature=self.temperature,
                    google_api_key=settings.GOOGLE_API_KEY
                )
                self.embeddings_model = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    google_api_key=settings.GOOGLE_API_KEY
                )
                
            elif self.provider == "anthropic":
                self.chat_model = ChatAnthropic(
                    model=self.model,
                    temperature=self.temperature,
                    anthropic_api_key=settings.ANTHROPIC_API_KEY
                )
                # Anthropic doesn't have embeddings, fallback to OpenAI
                self.embeddings_model = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    api_key=settings.OPENAI_API_KEY
                )
                
            elif self.provider == "openrouter":
                # OpenRouter uses OpenAI-compatible API
                self.chat_model = ChatOpenAI(
                    model=self.model,
                    temperature=self.temperature,
                    api_key=settings.OPENROUTER_API_KEY,
                    base_url="https://openrouter.ai/api/v1"
                )
                # OpenRouter doesn't have embeddings, fallback to OpenAI
                self.embeddings_model = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    api_key=settings.OPENAI_API_KEY
                )
                
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            print(f"✅ LLM Service initialized: {self.provider} / {self.model}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize LLM Service: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate text response
        
        Args:
            prompt: User prompt/question
            system_prompt: System instructions (optional)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        try:
            messages = []
            
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            messages.append(HumanMessage(content=prompt))
            
            # Set max_tokens if provided
            if max_tokens:
                response = self.chat_model.invoke(
                    messages,
                    max_tokens=max_tokens
                )
            else:
                response = self.chat_model.invoke(messages)
            
            return response.content
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return f"Error: {str(e)}"
    
    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Async version of generate"""
        try:
            messages = []
            
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            messages.append(HumanMessage(content=prompt))
            
            if max_tokens:
                response = await self.chat_model.ainvoke(
                    messages,
                    max_tokens=max_tokens
                )
            else:
                response = await self.chat_model.ainvoke(messages)
            
            return response.content
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return f"Error: {str(e)}"
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (list of floats)
        """
        try:
            embedding = self.embeddings_model.embed_query(text)
            return embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts at once (more efficient)
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.embeddings_model.embed_documents(texts)
            return embeddings
        except Exception as e:
            print(f"Error generating batch embeddings: {e}")
            return []
    
    def get_info(self) -> dict:
        """Get information about current configuration"""
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "chat_model_type": type(self.chat_model).__name__,
            "embeddings_model_type": type(self.embeddings_model).__name__
        }


# Global instance (can be initialized once)
llm_service = LLMService()
