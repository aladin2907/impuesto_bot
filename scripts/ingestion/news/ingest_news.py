#!/usr/bin/env python3
"""
Scrape Spanish tax news from RSS feeds and web sources,
generate embeddings, and insert into Supabase.

Sources:
- Agencia Tributaria (AEAT) noticias
- Expansión (fiscal section)
- Cinco Días (fiscal section)
- El Economista (fiscal section)

Usage:
    python -m scripts.ingestion.news.ingest_news
"""
import os
import sys
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

import requests
from bs4 import BeautifulSoup
from supabase import create_client
from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 50
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# --- RSS / Web sources ---
SOURCES = [
    {
        "name": "AEAT",
        "type": "rss",
        "url": "https://sede.agenciatributaria.gob.es/Sede/todas-noticias.xml",
        "categories": ["general"],
    },
    {
        "name": "Expansión",
        "type": "rss",
        "url": "https://www.expansion.com/rss/fiscal.xml",
        "categories": ["irpf", "iva", "sociedades"],
    },
    {
        "name": "Cinco Días",
        "type": "rss",
        "url": "https://feeds.elpais.com/mrss-s/list/ep/site/cincodias.elpais.com/tag/impuestos_a",
        "categories": ["irpf", "iva", "sociedades"],
    },
    {
        "name": "EuropaPress",
        "type": "rss",
        "url": "https://www.europapress.es/rss/rss.aspx?ch=00347",
        "categories": ["irpf", "iva", "sociedades"],
    },
    {
        "name": "idealista",
        "type": "rss",
        "url": "https://www.idealista.com/news/taxonomy/term/70528/feed",
        "categories": ["irpf", "iva"],
    },
    {
        "name": "infoautonomos",
        "type": "rss",
        "url": "https://www.infoautonomos.com/feed/",
        "categories": ["irpf", "iva", "autonomos"],
    },
]

TAX_KEYWORDS = [
    "irpf", "iva", "impuesto", "hacienda", "tributaria", "fiscal", "renta",
    "autónomo", "autonomo", "declaración", "modelo", "deducción", "exención",
    "contribuyente", "recargo", "sanción", "inspección", "sociedades",
    "retención", "cotización", "seguridad social", "presupuesto",
]


def fetch_page(url: str) -> Optional[str]:
    """Fetch a web page with proper headers."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"   ⚠️ Failed to fetch {url}: {e}")
        return None


def parse_rss_articles(html: str, source: Dict) -> List[Dict]:
    """Parse RSS feed."""
    soup = BeautifulSoup(html, "html.parser")
    articles = []

    for item in soup.find_all("item")[:30]:
        title = item.find("title")
        link = item.find("link")
        desc = item.find("description")
        pub_date = item.find("pubdate") or item.find("pubDate")

        if not title or not link:
            continue

        title_text = title.get_text(strip=True)
        link_text = link.get_text(strip=True) if link.string else (link.next_sibling or "").strip()
        desc_text = desc.get_text(strip=True) if desc else ""

        # Clean HTML from description
        if desc_text:
            desc_text = BeautifulSoup(desc_text, "html.parser").get_text(strip=True)

        published = None
        if pub_date:
            try:
                published = datetime.strptime(
                    pub_date.get_text(strip=True)[:25], "%a, %d %b %Y %H:%M:%S"
                ).isoformat()
            except ValueError:
                pass

        articles.append({
            "article_title": title_text,
            "article_url": link_text,
            "content": f"{title_text}. {desc_text}",
            "summary": desc_text[:500] if desc_text else title_text,
            "news_source": source["name"],
            "categories": source["categories"],
            "published_at": published,
            "tax_related": True,
        })

    return articles


def parse_web_articles(html: str, source: Dict, base_url: str) -> List[Dict]:
    """Parse news articles from web pages (generic scraper)."""
    soup = BeautifulSoup(html, "html.parser")
    articles = []

    # Find article links — common patterns
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        title = link.get_text(strip=True)

        # Skip navigation, short titles, non-article links
        if not title or len(title) < 20 or len(title) > 300:
            continue
        if any(skip in href.lower() for skip in ["javascript:", "#", "mailto:", "/autor/"]):
            continue

        # Build absolute URL
        if href.startswith("/"):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            href = f"{parsed.scheme}://{parsed.netloc}{href}"
        elif not href.startswith("http"):
            continue

        # Check if tax-related
        combined = (title + " " + href).lower()
        is_tax = any(kw in combined for kw in TAX_KEYWORDS)
        if not is_tax:
            continue

        articles.append({
            "article_title": title,
            "article_url": href,
            "content": title,  # will be enriched below
            "summary": title,
            "news_source": source["name"],
            "categories": source["categories"],
            "published_at": None,
            "tax_related": True,
        })

    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for a in articles:
        if a["article_url"] not in seen_urls:
            seen_urls.add(a["article_url"])
            unique.append(a)

    return unique[:20]  # top 20 per source


def enrich_article(article: Dict) -> Dict:
    """Fetch full article content."""
    html = fetch_page(article["article_url"])
    if not html:
        return article

    soup = BeautifulSoup(html, "html.parser")

    # Try common article body selectors
    body = None
    for selector in ["article", ".article-body", ".noticia-cuerpo", ".article__body",
                     '[itemprop="articleBody"]', ".entry-content", ".story-body"]:
        body = soup.select_one(selector)
        if body:
            break

    if not body:
        # Fallback: get all <p> tags
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)
    else:
        text = body.get_text(separator=" ", strip=True)

    if text and len(text) > 100:
        article["content"] = text[:5000]  # cap at 5000 chars
        article["summary"] = text[:500]

    return article


def generate_embeddings(texts: List[str], client: OpenAI) -> List[List[float]]:
    """Generate OpenAI embeddings."""
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def main():
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY"),
    )

    # Check existing URLs to avoid duplicates
    existing = supabase.table("news_articles_content").select("article_url").execute()
    existing_urls = {r["article_url"] for r in (existing.data or [])}
    print(f"Existing articles in DB: {len(existing_urls)}")

    all_articles = []

    for source in SOURCES:
        print(f"\n🔍 Scraping: {source['name']} ({source['url']})")
        html = fetch_page(source["url"])
        if not html:
            continue

        if source["type"] == "rss":
            articles = parse_rss_articles(html, source)
        else:
            articles = parse_web_articles(html, source, source["url"])

        # Filter out existing
        new_articles = [a for a in articles if a["article_url"] not in existing_urls]
        print(f"   Found {len(articles)} articles, {len(new_articles)} new")

        # Enrich with full content
        for i, article in enumerate(new_articles):
            if len(article["content"]) < 100:
                print(f"   📰 Enriching {i + 1}/{len(new_articles)}: {article['article_title'][:60]}...")
                article = enrich_article(article)
                new_articles[i] = article

        all_articles.extend(new_articles)

    if not all_articles:
        print("\n✅ No new articles to ingest.")
        return

    print(f"\n📊 Total new articles: {len(all_articles)}")

    # Generate embeddings
    print("\n🧠 Generating embeddings...")
    for i in range(0, len(all_articles), 50):
        batch = all_articles[i:i + 50]
        texts = [a["content"][:8000] for a in batch]
        embeddings = generate_embeddings(texts, openai_client)
        for j, emb in enumerate(embeddings):
            all_articles[i + j]["content_embedding"] = emb
        print(f"   Embedded {min(i + 50, len(all_articles))}/{len(all_articles)}")

    # Insert into Supabase
    print(f"\n💾 Inserting into Supabase...")
    inserted = 0
    for article in all_articles:
        try:
            supabase.table("news_articles_content").insert(article).execute()
            inserted += 1
        except Exception as e:
            if "duplicate" in str(e).lower():
                pass  # skip duplicates
            else:
                print(f"   ❌ Failed: {article['article_title'][:50]}: {e}")

    print(f"\n🎉 Done! Inserted {inserted}/{len(all_articles)} articles into news_articles_content")


if __name__ == "__main__":
    main()
