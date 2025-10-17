#!/usr/bin/env python3
"""
Скрипт для скрапинга новостных статей о налогах
"""

import os
import sys
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse
import time
import re
from datetime import datetime
import json

# Добавляем корневую папку в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import Settings


class NewsScraper:
    """Класс для скрапинга новостных статей"""
    
    def __init__(self):
        self.settings = Settings()
        self.download_dir = Path("data/news_articles")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Источники новостей
        self.news_sources = [
            {
                "name": "Cinco_Dias",
                "url": "https://cincodias.elpais.com/tag/impuestos/",
                "base_url": "https://cincodias.elpais.com",
                "description": "Cinco Días - Tax News"
            },
            {
                "name": "Expansion_Fiscalidad",
                "url": "https://www.expansion.com/economia/politica/fiscalidad.html",
                "base_url": "https://www.expansion.com",
                "description": "Expansión - Fiscalidad"
            },
            {
                "name": "El_Economista_Fiscal",
                "url": "https://www.eleconomista.es/economia/fiscal",
                "base_url": "https://www.eleconomista.es",
                "description": "El Economista - Fiscal"
            }
        ]
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def extract_articles_from_cinco_dias(self, html: str, base_url: str) -> list:
        """Извлекает статьи с Cinco Días"""
        articles = []
        
        # Ищем ссылки на статьи
        article_links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*articulo[^"]*"[^>]*>', html, re.IGNORECASE)
        
        for link in article_links[:10]:  # Берем первые 10
            if link.startswith('/'):
                full_url = urljoin(base_url, link)
            else:
                full_url = link
            
            # Извлекаем заголовок
            title_match = re.search(r'<a[^>]*href="' + re.escape(link) + r'"[^>]*>([^<]+)</a>', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "Sin título"
            
            articles.append({
                "title": title,
                "url": full_url,
                "source": "Cinco Días"
            })
        
        return articles
    
    def extract_articles_from_expansion(self, html: str, base_url: str) -> list:
        """Извлекает статьи с Expansión"""
        articles = []
        
        # Ищем ссылки на статьи
        article_links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*articulo[^"]*"[^>]*>', html, re.IGNORECASE)
        
        for link in article_links[:10]:  # Берем первые 10
            if link.startswith('/'):
                full_url = urljoin(base_url, link)
            else:
                full_url = link
            
            # Извлекаем заголовок
            title_match = re.search(r'<a[^>]*href="' + re.escape(link) + r'"[^>]*>([^<]+)</a>', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "Sin título"
            
            articles.append({
                "title": title,
                "url": full_url,
                "source": "Expansión"
            })
        
        return articles
    
    def extract_articles_from_economista(self, html: str, base_url: str) -> list:
        """Извлекает статьи с El Economista"""
        articles = []
        
        # Ищем ссылки на статьи
        article_links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*articulo[^"]*"[^>]*>', html, re.IGNORECASE)
        
        for link in article_links[:10]:  # Берем первые 10
            if link.startswith('/'):
                full_url = urljoin(base_url, link)
            else:
                full_url = link
            
            # Извлекаем заголовок
            title_match = re.search(r'<a[^>]*href="' + re.escape(link) + r'"[^>]*>([^<]+)</a>', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "Sin título"
            
            articles.append({
                "title": title,
                "url": full_url,
                "source": "El Economista"
            })
        
        return articles
    
    def scrape_news_source(self, source_info: dict) -> list:
        """Скрапит один источник новостей"""
        try:
            print(f"\n📰 Скрапим: {source_info['name']}")
            print(f"   URL: {source_info['url']}")
            
            response = self.session.get(source_info['url'], timeout=30)
            response.raise_for_status()
            
            # Извлекаем статьи в зависимости от источника
            if "cincodias" in source_info['url']:
                articles = self.extract_articles_from_cinco_dias(response.text, source_info['base_url'])
            elif "expansion" in source_info['url']:
                articles = self.extract_articles_from_expansion(response.text, source_info['base_url'])
            elif "eleconomista" in source_info['url']:
                articles = self.extract_articles_from_economista(response.text, source_info['base_url'])
            else:
                articles = []
            
            print(f"   ✅ Найдено статей: {len(articles)}")
            return articles
            
        except Exception as e:
            print(f"   ❌ Ошибка скрапинга {source_info['name']}: {e}")
            return []
    
    def scrape_all_sources(self) -> list:
        """Скрапит все источники новостей"""
        print("🚀 Начинаем скрапинг новостных статей")
        print("=" * 60)
        
        all_articles = []
        
        for source in self.news_sources:
            articles = self.scrape_news_source(source)
            all_articles.extend(articles)
            time.sleep(2)  # Пауза между запросами
        
        print(f"\n📊 Всего найдено статей: {len(all_articles)}")
        return all_articles
    
    def save_articles(self, articles: list) -> None:
        """Сохраняет статьи в JSON файл"""
        if not articles:
            print("❌ Нет статей для сохранения")
            return
        
        # Добавляем метаданные
        for article in articles:
            article["scraped_at"] = datetime.now().isoformat()
            article["relevance_score"] = 0.8  # Базовый рейтинг
        
        # Сохраняем в JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_articles_{timestamp}.json"
        file_path = self.download_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Статьи сохранены: {file_path}")
        print(f"📊 Количество статей: {len(articles)}")
    
    def list_saved_articles(self) -> None:
        """Показывает список сохраненных статей"""
        print("\n📁 Сохраненные статьи:")
        print("-" * 40)
        
        if not self.download_dir.exists():
            print("   Папка не существует")
            return
        
        json_files = list(self.download_dir.glob("*.json"))
        if not json_files:
            print("   JSON файлы не найдены")
            return
        
        for file_path in sorted(json_files):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    articles = json.load(f)
                
                print(f"   📄 {file_path.name}")
                print(f"      Статей: {len(articles)}")
                print(f"      Дата: {articles[0].get('scraped_at', 'N/A')}")
                print(f"      Путь: {file_path}")
                
            except Exception as e:
                print(f"   ❌ Ошибка чтения {file_path.name}: {e}")


def main():
    """Основная функция"""
    scraper = NewsScraper()
    
    print("🔍 TuExpertoFiscal NAIL - Скрапинг новостных статей")
    print("=" * 60)
    
    # Показываем источники
    print("\n📋 Источники новостей:")
    for i, source in enumerate(scraper.news_sources, 1):
        print(f"   {i}. {source['name']} - {source['description']}")
    
    # Скрапим все источники
    articles = scraper.scrape_all_sources()
    
    # Сохраняем
    scraper.save_articles(articles)
    
    # Показываем результат
    scraper.list_saved_articles()


if __name__ == "__main__":
    main()
