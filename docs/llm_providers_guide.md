# LLM Providers Guide - TuExpertoFiscal NAIL

This guide explains how to work with different LLM providers in TuExpertoFiscal NAIL using **LangChain**.

## Architecture

We use LangChain's unified interface for all LLM providers. This gives us:
- **Consistency:** Same API for all providers
- **Reliability:** Battle-tested implementations
- **Features:** Async, streaming, callbacks out of the box
- **Flexibility:** Easy to switch between providers

## Supported Providers

### 1. OpenAI
- **Models:** GPT-4o, GPT-4, GPT-4-turbo, GPT-3.5-turbo
- **Best for:** High quality responses, embeddings
- **Cost:** Medium to High
- **Setup:** Requires `OPENAI_API_KEY`

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

### 2. Google Gemini
- **Models:** gemini-pro, gemini-1.5-pro, gemini-1.5-flash
- **Best for:** Fast responses, good quality, cost-effective
- **Cost:** Low to Medium
- **Setup:** Requires `GOOGLE_API_KEY`

```env
LLM_PROVIDER=google
LLM_MODEL=gemini-pro
GOOGLE_API_KEY=...
```

### 3. Anthropic (Claude)
- **Models:** Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- **Best for:** Excellent reasoning, long context, coding
- **Cost:** Medium to High
- **Setup:** Requires `ANTHROPIC_API_KEY`

```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=...
```

### 4. OpenRouter
- **Models:** Access to 100+ models (Claude, Llama, Mistral, etc.)
- **Best for:** Flexibility, trying different models
- **Cost:** Varies by model
- **Setup:** Requires `OPENROUTER_API_KEY`

```env
LLM_PROVIDER=openrouter
LLM_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_API_KEY=...
```

Popular OpenRouter models:
- `anthropic/claude-3.5-sonnet` - Excellent quality
- `meta-llama/llama-3.1-70b-instruct` - Open source, good quality
- `mistralai/mixtral-8x7b-instruct` - Fast and cheap

## Usage Examples

### Using the Default Provider (from .env)

```python
from app.services.llm import llm_service

# Initialize with settings from .env
llm_service.initialize()

# Generate response
response = llm_service.generate(
    prompt="What is IVA in Spain?",
    system_prompt="You are a Spanish tax expert."
)
print(response)

# Generate embedding
embedding = llm_service.generate_embedding("Impuesto sobre el valor añadido")

# Batch embeddings (more efficient)
embeddings = llm_service.generate_embeddings_batch([
    "Tax code article 1",
    "Tax code article 2"
])
```

### Switching Providers Dynamically

```python
from app.services.llm import LLMService

# Use different providers for different tasks
cheap_llm = LLMService(
    provider="google",
    model="gemini-1.5-flash",
    temperature=0.3
)
cheap_llm.initialize()

premium_llm = LLMService(
    provider="anthropic",
    model="claude-3-5-sonnet-20241022",
    temperature=0.7
)
premium_llm.initialize()

# Use cheap provider for filtering
is_relevant = cheap_llm.generate(
    prompt="Is this about Spanish taxes? Answer yes or no: 'Hello, how are you?'"
)

# Use premium provider for main response
if "yes" in is_relevant.lower():
    answer = premium_llm.generate(
        prompt="User's actual tax question...",
        system_prompt="You are an expert..."
    )
```

### Async Support (for better performance)

```python
import asyncio
from app.services.llm import LLMService

async def handle_request(user_query: str):
    llm = LLMService()
    llm.initialize()
    
    # Non-blocking async generation
    response = await llm.generate_async(
        prompt=user_query,
        system_prompt="You are a tax expert."
    )
    return response

# Run async
response = asyncio.run(handle_request("What is IRPF?"))
```

### Testing All Providers

Run the test script to check which providers are working:

```bash
python scripts/test_llm_providers.py
```

## Recommended Setup

### Development
Use cheaper models for testing:
```env
LLM_PROVIDER=google
LLM_MODEL=gemini-1.5-flash
```

### Production
Use high-quality models:
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
```

### Cost Optimization Strategy

1. **Pre-filtering:** Use `gemini-1.5-flash` or `gpt-4o-mini` for quick checks
2. **Main responses:** Use `gpt-4o` or `claude-3-5-sonnet` for tax expertise
3. **Embeddings:** Automatically handled by LangChain (OpenAI for most providers)
4. **Batch operations:** Use `generate_embeddings_batch()` for efficiency

## Benefits of Using LangChain

1. **Proven Reliability:** Used by thousands of production applications
2. **Active Development:** Regular updates and security patches
3. **Rich Ecosystem:** Easy integration with vector stores, agents, chains
4. **Community Support:** Large community, lots of examples
5. **Advanced Features:** 
   - Streaming responses
   - Async/await support
   - Callbacks and monitoring
   - Cost tracking

---

*Developed by NAIL - Nahornyi AI Lab*
