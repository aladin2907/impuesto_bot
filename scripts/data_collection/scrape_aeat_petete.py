#!/usr/bin/env python3
"""
Scraper for AEAT Petete consultation system
Source: https://petete.tributos.hacienda.gob.es/consultas/
"""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class AEATPeteteScraper:
    """
    Scraper for AEAT Petete consultation system
    https://petete.tributos.hacienda.gob.es/consultas/
    """
    
    def __init__(self):
        self.base_url = "https://petete.tributos.hacienda.gob.es/consultas/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        })
        self.articles = []
    
    def fetch_page(self, url: str, retries: int = 3) -> Optional[str]:
        """Fetch page with retries"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                if response.status_code == 200:
                    return response.text
                else:
                    print(f"⚠️  Status {response.status_code} for {url}")
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    def extract_categories(self, html: str) -> List[Dict]:
        """Extract consultation categories from main page"""
        soup = BeautifulSoup(html, 'html.parser')
        categories = []
        
        try:
            # Find all category links
            # Structure might vary, adjust selectors based on actual HTML
            category_links = soup.select('a[href*="categoria"]') or soup.select('.categoria a')
            
            for link in category_links:
                category = {
                    'name': link.get_text(strip=True),
                    'url': link.get('href'),
                    'type': 'category'
                }
                
                # Make URL absolute
                if category['url'] and not category['url'].startswith('http'):
                    category['url'] = self.base_url + category['url'].lstrip('/')
                
                categories.append(category)
                print(f"   📂 Found category: {category['name']}")
            
            if not categories:
                print("⚠️  No categories found with standard selectors, trying alternative...")
                # Try alternative selectors
                all_links = soup.find_all('a')
                for link in all_links:
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    # Filter by keywords
                    if any(kw in text.lower() for kw in ['impuesto', 'modelo', 'declaración', 'iva', 'irpf']):
                        if href and text:
                            categories.append({
                                'name': text,
                                'url': href if href.startswith('http') else self.base_url + href.lstrip('/'),
                                'type': 'category'
                            })
            
        except Exception as e:
            print(f"❌ Error extracting categories: {e}")
        
        return categories
    
    def extract_articles_from_category(self, category_url: str) -> List[Dict]:
        """Extract articles from a category page"""
        html = self.fetch_page(category_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        articles = []
        
        try:
            # Find article links - adjust selectors based on actual structure
            article_links = (
                soup.select('.consulta a') or
                soup.select('article a') or
                soup.select('.resultado a') or
                soup.select('a[href*="consulta"]')
            )
            
            for link in article_links:
                article_url = link.get('href')
                if not article_url:
                    continue
                
                # Make URL absolute
                if not article_url.startswith('http'):
                    article_url = self.base_url + article_url.lstrip('/')
                
                article = {
                    'title': link.get_text(strip=True),
                    'url': article_url,
                    'category_url': category_url,
                    'scraped_at': datetime.utcnow().isoformat()
                }
                
                articles.append(article)
        
        except Exception as e:
            print(f"❌ Error extracting articles: {e}")
        
        return articles
    
    def extract_article_content(self, article: Dict) -> Dict:
        """Extract full content from an article page"""
        html = self.fetch_page(article['url'])
        if not html:
            return article
        
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract content - adjust based on actual structure
            content_div = (
                soup.find('div', class_='contenido') or
                soup.find('article') or
                soup.find('main') or
                soup.find('div', id='contenido')
            )
            
            if content_div:
                # Clean content
                for script in content_div.find_all(['script', 'style']):
                    script.decompose()
                
                article['content'] = content_div.get_text(separator='\n', strip=True)
                
                # Extract metadata
                article['content_html'] = str(content_div)
                
                # Try to find related info
                metadata = {}
                
                # Look for tax model numbers
                model_tags = soup.find_all(text=lambda t: 'modelo' in t.lower() if t else False)
                if model_tags:
                    metadata['models_mentioned'] = [tag.strip() for tag in model_tags[:5]]
                
                # Look for dates
                date_tags = soup.find_all(text=lambda t: any(m in t.lower() if t else False 
                                                             for m in ['plazo', 'fecha', 'ejercicio']))
                if date_tags:
                    metadata['dates_mentioned'] = [tag.strip() for tag in date_tags[:3]]
                
                article['metadata'] = metadata
                
            else:
                print(f"⚠️  No content found for: {article['url']}")
                article['content'] = ""
        
        except Exception as e:
            print(f"❌ Error extracting content: {e}")
            article['content'] = ""
        
        return article
    
    def scrape_all(self, max_articles: int = 100) -> List[Dict]:
        """Scrape all available articles"""
        print("=" * 60)
        print("📰 AEAT Petete Scraper")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print()
        
        # Fetch main page
        print("📄 Fetching main page...")
        main_html = self.fetch_page(self.base_url)
        if not main_html:
            print("❌ Failed to fetch main page")
            return []
        
        # Extract categories
        print("\n📂 Extracting categories...")
        categories = self.extract_categories(main_html)
        print(f"   Found {len(categories)} categories")
        
        if not categories:
            print("⚠️  No categories found. The website structure might have changed.")
            print("   Saving HTML for manual inspection...")
            
            debug_file = project_root / "data" / "aeat_petete_debug.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(main_html)
            print(f"   Saved to: {debug_file}")
            return []
        
        # Scrape articles from each category
        all_articles = []
        
        for i, category in enumerate(categories[:10], 1):  # Limit to first 10 categories
            print(f"\n[{i}/{len(categories[:10])}] 📂 {category['name']}")
            print(f"   URL: {category['url']}")
            
            articles = self.extract_articles_from_category(category['url'])
            print(f"   Found {len(articles)} articles")
            
            # Extract full content for each article
            for j, article in enumerate(articles[:10], 1):  # Limit articles per category
                if len(all_articles) >= max_articles:
                    print(f"\n⚠️  Reached max articles limit ({max_articles})")
                    break
                
                print(f"      [{j}/{len(articles[:10])}] {article['title'][:50]}...")
                article['category'] = category['name']
                article = self.extract_article_content(article)
                
                all_articles.append(article)
                time.sleep(1)  # Be polite
            
            if len(all_articles) >= max_articles:
                break
            
            time.sleep(2)  # Be polite between categories
        
        print(f"\n{'=' * 60}")
        print(f"✅ Scraped {len(all_articles)} articles")
        print(f"{'=' * 60}")
        
        return all_articles
    
    def save_to_json(self, articles: List[Dict], output_path: Path):
        """Save articles to JSON file"""
        data = {
            'source': 'AEAT Petete',
            'source_url': self.base_url,
            'scraped_at': datetime.utcnow().isoformat(),
            'total_articles': len(articles),
            'articles': articles
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Saved to: {output_path}")


def main():
    """Main entry point"""
    scraper = AEATPeteteScraper()
    
    # Scrape articles
    articles = scraper.scrape_all(max_articles=50)
    
    if articles:
        # Save to data directory
        output_dir = project_root / "data" / "aeat_articles"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"aeat_petete_{timestamp}.json"
        
        scraper.save_to_json(articles, output_file)
        
        print("\n✅ Scraping completed successfully!")
        print(f"   Articles: {len(articles)}")
        print(f"   File: {output_file}")
    else:
        print("\n⚠️  No articles scraped. Check website structure.")


if __name__ == "__main__":
    main()

