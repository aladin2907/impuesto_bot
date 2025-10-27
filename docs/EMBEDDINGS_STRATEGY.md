# Embeddings Strategy 🎯

## Overview

This project uses **DIFFERENT embedding models** for different data sources to optimize for cost and quality.

## Current Setup

| Source | Model | Dimensions | Cost | Field Name |
|--------|-------|------------|------|------------|
| **PDF** | OpenAI `text-embedding-3-small` | 1536 | $0.02/1M tokens | `content_embedding` |
| **Telegram** | HuggingFace `multilingual-e5-large` | 1024 | **FREE** | `telegram_embedding` |
| **Calendar** | N/A (keyword only) | - | FREE | - |
| **News** | N/A (keyword only) | - | FREE | - |

## Why Different Models?

### PDF Documents (OpenAI)
- **High quality** legal/tax documents requiring precise semantic understanding
- **Small volume**: 4,051 documents (~$10 one-time cost)
- **Worth the cost** for critical tax law retrieval
- Already generated and indexed ✅

### Telegram Threads (multilingual-e5-large)  
- **Large volume**: 75,714 threads (would cost ~$150 with OpenAI!)
- **Multilingual**: Excellent for Spanish, Russian, English, Ukrainian
- **Community discussions**: Good enough quality for conversational data
- **FREE**: Runs locally with sentence-transformers
- Status: ⚠️ 6.6% coverage (5,003/75,714)

## Implementation Details

### Query Embeddings

**Problem**: Different embedding spaces are **incompatible**!
- OpenAI (1536 dims) ≠ multilingual-e5 (1024 dims)
- Cannot mix embeddings from different models in kNN search

**Current Solution**:
1. **PDF search**: Generate query embeddings with OpenAI → search with kNN + BM25
2. **Telegram search**: **Keyword-only (BM25)** for now
   - No query embeddings needed
   - Fast and works well for keyword matching

**Future Solution** (TODO):
- Install `sentence-transformers` on server
- Generate Telegram query embeddings in real-time with multilingual-e5
- Enable hybrid search (kNN + BM25) for Telegram

### Document Embeddings

Generated offline with scripts:
- **PDF**: `scripts/ingestion/add_pdf_embeddings.py` (OpenAI)
- **Telegram**: `scripts/ingestion/add_telegram_embeddings.py` (multilingual-e5)

## Cost Analysis

### PDF (Already Done) ✅
- Documents: 4,051
- Cost: ~$10 (one-time)
- Status: 100% complete

### Telegram (In Progress) ⚠️
- Documents: 75,714
- Cost with OpenAI: ~$150 ❌
- Cost with multilingual-e5: **$0** ✅
- Status: 6.6% (5,003/75,714)
- Time to complete: ~2-3 hours
- **Savings: $150!**

## How to Generate Embeddings

### PDF (Already Complete)
```bash
# Already done, but for reference:
python scripts/ingestion/add_pdf_embeddings.py
```

### Telegram (Need to Run)
```bash
# Install dependencies
pip install sentence-transformers

# Full generation (~2-3 hours, FREE!)
python scripts/ingestion/add_telegram_embeddings.py

# Test with limited batch
python scripts/ingestion/add_telegram_embeddings.py --limit 1000
```

## Model Details

### multilingual-e5-large

**Source**: [intfloat/multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large)

**Languages**: 100+ including:
- 🇪🇸 Spanish
- 🇷🇺 Russian  
- 🇬🇧 English
- 🇺🇦 Ukrainian

**Performance**:
- Dimensions: 1024
- Speed: ~100 docs/sec (CPU), ~500 docs/sec (GPU)
- Size: ~1.2GB
- Quality: Excellent for multilingual retrieval

**Usage**:
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('intfloat/multilingual-e5-large')

# For indexing documents
embeddings = model.encode([
    "passage: Text to embed..."
], show_progress_bar=True)

# For search queries  
query_embedding = model.encode([
    "query: User search query"
])[0]
```

## Search Strategy

### Current (Hybrid where possible)

```
┌─────────────┬──────────────┬─────────────┬──────────────┐
│   Source    │   Semantic   │   Keyword   │    Status    │
├─────────────┼──────────────┼─────────────┼──────────────┤
│ PDF         │ kNN (OpenAI) │ BM25        │ ✅ Working   │
│ Telegram    │ ❌ Disabled   │ BM25        │ ⚠️ Keyword   │
│ Calendar    │ N/A          │ BM25        │ ✅ Working   │
│ News        │ N/A          │ BM25        │ ✅ Working   │
└─────────────┴──────────────┴─────────────┴──────────────┘
```

### Future (Full Hybrid)

After installing multilingual-e5 on server:

```
┌─────────────┬───────────────────┬─────────────┬──────────────┐
│   Source    │     Semantic      │   Keyword   │    Status    │
├─────────────┼───────────────────┼─────────────┼──────────────┤
│ PDF         │ kNN (OpenAI)      │ BM25        │ ✅ Working   │
│ Telegram    │ kNN (E5-large)    │ BM25        │ 🚀 Planned   │
│ Calendar    │ N/A               │ BM25        │ ✅ Working   │
│ News        │ N/A               │ BM25        │ ✅ Working   │
└─────────────┴───────────────────┴─────────────┴──────────────┘
```

## Next Steps

1. ✅ Create embedding generation script for Telegram
2. ⏳ Run script to generate 70K+ embeddings (FREE!)
3. ⏳ Install `sentence-transformers` on server
4. ⏳ Add real-time query embedding generation for Telegram
5. ⏳ Enable hybrid search (kNN + BM25) for Telegram

## FAQs

**Q: Why not use OpenAI for everything?**
A: Cost! 75K Telegram threads would cost $150 vs FREE with multilingual-e5.

**Q: Is multilingual-e5 good enough?**
A: Yes! It's specifically trained for multilingual retrieval and performs excellently on Spanish/Russian/English/Ukrainian.

**Q: Can we mix OpenAI and E5 embeddings?**
A: No! Different embedding spaces are incompatible. Each source must use its own model consistently.

**Q: How long to generate 75K embeddings?**
A: ~2-3 hours on a modern CPU, ~30-45 minutes on GPU.

**Q: Do we need GPU?**
A: No, CPU works fine. GPU is faster but not required.

## References

- [Sentence Transformers Documentation](https://www.sbert.net/)
- [multilingual-e5-large Model Card](https://huggingface.co/intfloat/multilingual-e5-large)
- [Elasticsearch kNN Search](https://www.elastic.co/guide/en/elasticsearch/reference/current/knn-search.html)

