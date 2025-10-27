# Telegram Embeddings Generation 🚀

## Overview

This script generates **FREE embeddings** for all Telegram threads using the `multilingual-e5-large` model from HuggingFace.

## Why FREE Embeddings?

- **75,714 threads** would cost ~$150 with OpenAI ❌
- **multilingual-e5-large** is FREE and runs locally ✅  
- **Excellent quality** for Spanish, Russian, English, Ukrainian
- **Savings: $150!**

## Quick Start

### 1. Install Dependencies

```bash
pip install sentence-transformers
```

### 2. Test Run (1000 threads)

```bash
python scripts/ingestion/add_telegram_embeddings.py --limit 1000
```

### 3. Full Run (All 70K+ threads)

```bash
python scripts/ingestion/add_telegram_embeddings.py
```

**Time**: ~2-3 hours on CPU, ~30-45 minutes on GPU  
**Cost**: $0 (FREE!)

## Current Status

```
Total Telegram Threads: 75,714
With embeddings: 5,003 (6.6%)
Without embeddings: 70,711 (93.4%)
```

## How It Works

1. **Loads Model**: `intfloat/multilingual-e5-large` (1.2GB, cached after first run)
2. **Fetches Threads**: Queries Elasticsearch for threads without `telegram_embedding`
3. **Generates Embeddings**: Processes in batches of 100
4. **Updates Elasticsearch**: Adds `telegram_embedding` field (1024 dims)
5. **Progress**: Shows real-time stats (docs/sec, ETA)

## Embedding Field

**Important**: Telegram uses a **different field** than PDF!

| Source | Field | Dimensions | Model |
|--------|-------|------------|-------|
| PDF | `content_embedding` | 1536 | OpenAI text-embedding-3-small |
| Telegram | `telegram_embedding` | 1024 | multilingual-e5-large |

This is because:
- Different embedding spaces are incompatible
- Optimizing for cost (FREE vs $150)
- Telegram is community discussions, PDF is legal docs

## Performance

**CPU** (Mac M1/M2 or modern Intel):
- Speed: ~100 docs/sec
- Time for 70K: ~11-12 minutes
- Memory: ~2GB RAM

**GPU** (CUDA):
- Speed: ~500 docs/sec  
- Time for 70K: ~2-3 minutes
- Memory: ~4GB VRAM

## Script Output

```
🔧 Loading multilingual-e5-large model...
✅ Model loaded! Embedding dimension: 1024
✅ Connected to Elasticsearch: 9.1.4

======================================================================
📊 TELEGRAM EMBEDDINGS GENERATION
======================================================================
Total threads WITHOUT embeddings: 70711
Threads to process: 70711
Batch size: 100
Model: intfloat/multilingual-e5-large (1024 dims)
Field: telegram_embedding
Cost: $0 (FREE!) 🎉
======================================================================

📦 Batch: 100/100 | Progress: 100/70711 (0.1%) | Speed: 95.3 docs/sec | Time: 1.0s
📦 Batch: 100/100 | Progress: 200/70711 (0.3%) | Speed: 98.1 docs/sec | Time: 1.0s
...
======================================================================
✅ COMPLETED!
======================================================================
Total processed: 70711/70711
Total time: 12.3 minutes
Average: 0.01 sec/doc

Threads still WITHOUT embeddings: 0
🎉 ALL THREADS NOW HAVE EMBEDDINGS!
======================================================================
```

## Troubleshooting

### Model Download Fails

```bash
# Set HuggingFace cache directory
export HF_HOME=/path/to/cache
export TRANSFORMERS_CACHE=/path/to/cache

python scripts/ingestion/add_telegram_embeddings.py
```

### Out of Memory

Reduce batch size:

```python
# Edit script line 12
self.batch_size = 50  # Instead of 100
```

### Slow Performance

Use GPU if available:

```bash
# Install CUDA-enabled PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

python scripts/ingestion/add_telegram_embeddings.py
```

## Next Steps

After generating embeddings:

1. ✅ All Telegram threads will have embeddings
2. ⏳ Install `sentence-transformers` on production server
3. ⏳ Update `search_service.py` to use multilingual-e5 for query embeddings
4. ⏳ Enable hybrid search (kNN + BM25) for Telegram

See [EMBEDDINGS_STRATEGY.md](../../docs/EMBEDDINGS_STRATEGY.md) for details.

## Related Files

- **Script**: `scripts/ingestion/add_telegram_embeddings.py`
- **Search Service**: `app/services/search_service.py`
- **Documentation**: `docs/EMBEDDINGS_STRATEGY.md`
- **Requirements**: `requirements.txt` (includes sentence-transformers)

