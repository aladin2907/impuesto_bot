# Hybrid Search Implementation

## Overview

TuExpertoFiscal uses **Hybrid Search** combining two powerful search methods:
1. **Semantic Search** (kNN with embeddings) - понимает смысл запроса
2. **Keyword Search** (BM25) - точное совпадение слов

## Architecture

```
User Query: "налоги автономо испания"
     ↓
1. Generate Embedding (OpenAI text-embedding-3-small)
     ↓                      ↓
2a. kNN Search        2b. Keyword Search (BM25)
    (semantic)             (exact match)
     ↓                      ↓
3. Elasticsearch combines both → Hybrid Results
     ↓
4. Top 10 ranked results
```

## Implementation

### Supported Indices

| Index | Semantic | Keyword | Status |
|-------|----------|---------|--------|
| `telegram_threads` | ✅ kNN | ✅ BM25 | **Active** |
| `pdf_documents` | ❌ | ✅ BM25 | Keyword-only |
| `calendar_deadlines` | ❌ | ✅ BM25 | Keyword-only |
| `news_articles` | ❌ | ✅ BM25 | Keyword-only |
| `aeat_resources` | ❌ | ✅ BM25 | Keyword-only |

### Code Example

```python
def _search_telegram(self, query: str) -> List[Dict]:
    # 1. Generate embedding
    query_embedding = self._generate_query_embedding(query)
    
    if query_embedding:
        # HYBRID SEARCH
        search_body = {
            "query": {
                "bool": {
                    "should": [
                        # Keyword search (BM25)
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["content^2", "first_message", ...],
                                "type": "best_fields"
                            }
                        }
                    ]
                }
            },
            "knn": {
                "field": "content_embedding",
                "query_vector": query_embedding,
                "k": 10,
                "num_candidates": 50
            }
        }
    else:
        # FALLBACK: Keyword-only
        search_body = {"query": {"multi_match": ...}}
```

## Performance

### Telegram (75k+ documents)

| Search Type | Time | Score Range | Relevance |
|-------------|------|-------------|-----------|
| Keyword-only | ~120ms | 9-10 | Good |
| **Hybrid** | **~750ms** | **20-25** | **Excellent** |

**Breakdown:**
- Embedding generation: ~300ms (OpenAI API)
- Elasticsearch kNN: ~250ms
- Network + processing: ~200ms

### Comparison

**Keyword-only search:**
```
Query: "налоги автономо"
Results: exact word matches
Score: 9.5 - generic match
```

**Hybrid search:**
```
Query: "налоги автономо" 
Results: semantic understanding + word matches
Score: 24.15 - highly relevant (understands context)
```

## Configuration

### Requirements

1. **OpenAI API Key** (for embeddings)
```bash
OPENAI_API_KEY=sk-proj-...
```

2. **Elasticsearch 9.x+** with kNN support

3. **Embeddings in index** (telegram_threads)
```json
{
  "content_embedding": [0.009, 0.056, ...],  // 1536 dimensions
  "content": "Actual text content"
}
```

### Elasticsearch Mapping

```json
{
  "mappings": {
    "properties": {
      "content_embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      },
      "content": {
        "type": "text",
        "analyzer": "standard"
      }
    }
  }
}
```

## Testing

### Local Test

```python
from app.services.search_service import search_service

search_service.initialize()

# Test hybrid search
results = search_service._search_telegram("налоги автономо испания")
print(f"Found {len(results)} results")
for r in results[:3]:
    print(f"Score: {r['score']:.2f} - {r['text'][:100]}")
```

### Production Test

```bash
curl -X POST http://63.180.170.54/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_context": {"channel_type": "telegram", "channel_user_id": "test"},
    "query_text": "налоги автономо",
    "channels": ["telegram"],
    "top_k": 5
  }'
```

**Expected logs:**
```
✅ POST https://api.openai.com/v1/embeddings HTTP/1.1 200 OK
✅ POST .../telegram_threads/_search [status:200 duration:0.256s]
✅ Telegram hybrid (kNN + keyword) search returned 10 results
✅ Results sent to webhook: 200
```

## Fallback Behavior

If embedding generation fails:
- ❌ OpenAI API error
- ❌ Missing API key
- ❌ Network timeout

→ **Automatic fallback to keyword-only search**
→ No error, search continues with BM25

```python
query_embedding = self._generate_query_embedding(query)
if query_embedding:
    # HYBRID search
else:
    # FALLBACK: keyword-only search
```

## Future Improvements

### 1. Add embeddings for PDF documents

```python
# Generate embeddings for all PDF chunks
for doc in pdf_documents:
    embedding = openai.embeddings.create(
        model="text-embedding-3-small",
        input=doc['content']
    )
    doc['content_embedding'] = embedding.data[0].embedding
```

### 2. Batch embedding generation

```python
# Generate embeddings for multiple queries at once
embeddings = openai.embeddings.create(
    model="text-embedding-3-small",
    input=[query1, query2, query3]
)
```

### 3. Embedding caching

```python
# Cache embeddings in Redis
cache_key = f"embedding:{hash(query)}"
cached = redis.get(cache_key)
if cached:
    return json.loads(cached)
```

### 4. Re-ranking

```python
# Use cross-encoder for re-ranking top results
from sentence_transformers import CrossEncoder
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
scores = reranker.predict([(query, r['text']) for r in results])
```

## Monitoring

### Metrics to track

- **Embedding generation time** (should be < 500ms)
- **Search time** (should be < 300ms)
- **Score distribution** (hybrid should be > 15)
- **Fallback rate** (how often keyword-only is used)

### Logs

```python
print(f"Telegram {search_type} search returned {len(results)} results")
# Output: "Telegram hybrid (kNN + keyword) search returned 10 results"
```

## Troubleshooting

### Issue: "Error generating embedding: 401"
**Solution:** Check OpenAI API key in .env

### Issue: "runtime error" in Elasticsearch
**Solution:** Check Elasticsearch version (need 9.x+ for kNN)

### Issue: Low scores (< 10)
**Solution:** Embeddings not generated, fallback to keyword-only

### Issue: Slow search (> 2s)
**Solution:** 
- Check OpenAI API latency
- Check Elasticsearch performance
- Consider caching embeddings

## References

- [Elasticsearch kNN Search](https://www.elastic.co/guide/en/elasticsearch/reference/current/knn-search.html)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Hybrid Search Best Practices](https://www.elastic.co/blog/improving-information-retrieval-elastic-stack-hybrid)

---

*Implemented: 2025-10-26*  
*Status: Production Ready ✅*

