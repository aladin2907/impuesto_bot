"""
Test script to verify different LLM providers using LangChain
Run this to test which providers are working
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.llm.llm_service import LLMService
from app.config.settings import settings


def test_provider(provider_name: str, model_name: str):
    """Test a specific provider"""
    print(f"\n{'='*60}")
    print(f"Testing {provider_name.upper()} with model: {model_name}")
    print('='*60)
    
    try:
        # Create LLM service instance
        llm = LLMService(
            provider=provider_name,
            model=model_name,
            temperature=0.7
        )
        
        if not llm.initialize():
            print(f"❌ Failed to initialize {provider_name}")
            return False
        
        # Show config info
        print(f"\nConfiguration: {llm.get_info()}")
        
        # Test text generation
        print("\n1. Testing text generation...")
        test_prompt = "What is 2+2? Answer in one sentence."
        response = llm.generate(
            prompt=test_prompt,
            system_prompt="You are a helpful assistant. Be concise."
        )
        print(f"Prompt: {test_prompt}")
        print(f"Response: {response}")
        print("✅ Text generation works")
        
        # Test embeddings
        print("\n2. Testing embeddings...")
        test_text = "Spanish tax law regulation"
        embedding = llm.generate_embedding(test_text)
        if embedding:
            print(f"Generated embedding vector of length: {len(embedding)}")
            print(f"First 5 values: {embedding[:5]}")
            print("✅ Embeddings work")
        else:
            print("⚠️  Embeddings failed")
        
        # Test batch embeddings
        print("\n3. Testing batch embeddings...")
        test_texts = ["Tax code", "Financial regulation", "IVA"]
        embeddings = llm.generate_embeddings_batch(test_texts)
        if embeddings:
            print(f"Generated {len(embeddings)} embeddings")
            print("✅ Batch embeddings work")
        else:
            print("⚠️  Batch embeddings failed")
        
        print(f"\n✅ {provider_name.upper()} provider working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ {provider_name.upper()} provider failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_async(provider_name: str, model_name: str):
    """Test async generation"""
    print(f"\n{'='*60}")
    print(f"Testing ASYNC for {provider_name.upper()}")
    print('='*60)
    
    try:
        llm = LLMService(provider=provider_name, model=model_name)
        if not llm.initialize():
            return False
        
        response = await llm.generate_async(
            prompt="Say 'async works' in one word.",
            system_prompt="Be concise."
        )
        print(f"Async response: {response}")
        print("✅ Async generation works")
        return True
    except Exception as e:
        print(f"❌ Async failed: {e}")
        return False


def main():
    """Test all configured providers"""
    print("=" * 60)
    print("TuExpertoFiscal NAIL - LLM Providers Test (LangChain)")
    print("=" * 60)
    
    # Test configurations for different providers
    tests = [
        ("openai", "gpt-4o-mini"),  # Cheaper model for testing
        ("google", "gemini-pro"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
        ("openrouter", "anthropic/claude-3.5-sonnet"),
    ]
    
    results = {}
    
    for provider_name, model_name in tests:
        try:
            success = test_provider(provider_name, model_name)
            results[provider_name] = success
        except Exception as e:
            print(f"\n❌ Unexpected error testing {provider_name}: {e}")
            results[provider_name] = False
    
    # Test async for the configured provider
    print("\n" + "="*60)
    print("Testing async functionality")
    print("="*60)
    try:
        asyncio.run(test_async(settings.LLM_PROVIDER, settings.LLM_MODEL))
    except Exception as e:
        print(f"❌ Async test failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for provider, success in results.items():
        status = "✅ WORKING" if success else "❌ FAILED"
        print(f"{provider.upper()}: {status}")
    
    print("\n" + "=" * 60)
    print("Current configuration from .env:")
    print(f"  LLM_PROVIDER: {settings.LLM_PROVIDER}")
    print(f"  LLM_MODEL: {settings.LLM_MODEL}")
    print(f"  LLM_TEMPERATURE: {settings.LLM_TEMPERATURE}")
    print("=" * 60)


if __name__ == "__main__":
    main()