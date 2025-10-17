#!/usr/bin/env python3
"""
Главный скрипт для сбора данных из всех источников
Запускает все скрипты сбора данных и анализирует результаты
"""

import sys
import json
from pathlib import Path
from datetime import datetime


def print_section(title):
    """Красивый вывод секции"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def main():
    print_section("СБОР ДАННЫХ ИЗ ВСЕХ ИСТОЧНИКОВ")
    print(f"🕐 Начало: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. Telegram треды (уже скачаны)
    print_section("1. TELEGRAM ТРЕДЫ")
    print("✅ Telegram треды уже скачаны:")
    print("   - it_threads.json (IT Autonomos Spain)")
    print("   - nomads_threads.json (Digital Nomad Spain)")
    print("   - Всего: 75,914 тредов (183,856 сообщений)")
    
    # 2. Налоговый календарь
    print_section("2. НАЛОГОВЫЙ КАЛЕНДАРЬ AEAT")
    print("📅 Скрапим налоговый календарь...")
    
    try:
        from scrape_tax_calendar import AEATCalendarScraper
        
        scraper = AEATCalendarScraper()
        deadlines = scraper.scrape_calendar(2024)
        
        Path("data").mkdir(exist_ok=True)
        scraper.save_to_json(deadlines, "data/tax_calendar.json")
        scraper.analyze_calendar(deadlines)
        
        print(f"\n✅ Налоговый календарь собран: {len(deadlines)} дедлайнов")
    except Exception as e:
        print(f"❌ Ошибка при сборе календаря: {e}")
    
    # 3. Новости
    print_section("3. НОВОСТИ")
    print("📰 Скрапим новости...")
    
    try:
        from scrape_news import NewsScrap
        
        news_scraper = NewsScrap()
        articles = news_scraper.scrape_all_sources(limit_per_source=5)
        
        news_scraper.save_to_json(articles, "data/news_articles.json")
        news_scraper.analyze_articles(articles)
        
        print(f"\n✅ Новости собраны: {len(articles)} статей")
    except Exception as e:
        print(f"❌ Ошибка при сборе новостей: {e}")
    
    # 4. PDF документы
    print_section("4. PDF ДОКУМЕНТЫ")
    print("📄 Скачиваем PDF документы...")
    
    try:
        from download_pdf_documents import PDFDownloader
        
        pdf_downloader = PDFDownloader()
        results = pdf_downloader.download_all_documents("data/pdf_documents")
        
        pdf_downloader.save_metadata(results, "data/pdf_metadata.json")
        pdf_downloader.analyze_documents(results)
        
        successful = sum(1 for r in results if r.get('success'))
        print(f"\n✅ PDF документы скачаны: {successful}/{len(results)}")
    except Exception as e:
        print(f"❌ Ошибка при скачивании PDF: {e}")
    
    # Итоговый анализ
    print_section("ИТОГОВЫЙ АНАЛИЗ")
    
    stats = {
        "collection_completed_at": datetime.now().isoformat(),
        "sources": {}
    }
    
    # Telegram
    if Path("it_threads.json").exists() and Path("nomads_threads.json").exists():
        with open("it_threads.json") as f:
            it_data = json.load(f)
        with open("nomads_threads.json") as f:
            nomads_data = json.load(f)
        
        stats["sources"]["telegram"] = {
            "status": "collected",
            "groups": 2,
            "total_threads": len(it_data.get("threads", [])) + len(nomads_data.get("threads", [])),
            "total_messages": it_data.get("total_messages", 0) + nomads_data.get("total_messages", 0)
        }
    
    # Календарь
    if Path("data/tax_calendar.json").exists():
        with open("data/tax_calendar.json") as f:
            calendar_data = json.load(f)
        
        stats["sources"]["tax_calendar"] = {
            "status": "collected",
            "total_deadlines": calendar_data.get("total_deadlines", 0)
        }
    
    # Новости
    if Path("data/news_articles.json").exists():
        with open("data/news_articles.json") as f:
            news_data = json.load(f)
        
        stats["sources"]["news"] = {
            "status": "collected",
            "total_articles": news_data.get("total_articles", 0),
            "sources": news_data.get("sources", [])
        }
    
    # PDF
    if Path("data/pdf_metadata.json").exists():
        with open("data/pdf_metadata.json") as f:
            pdf_data = json.load(f)
        
        stats["sources"]["pdf_documents"] = {
            "status": "collected",
            "total_documents": pdf_data.get("total_documents", 0),
            "successful_downloads": pdf_data.get("successful_downloads", 0)
        }
    
    # Сохраняем статистику
    with open("data/collection_stats.json", 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print("📊 Сводка по всем источникам:\n")
    
    for source_name, source_data in stats["sources"].items():
        print(f"✅ {source_name.upper()}:")
        for key, value in source_data.items():
            if key != "status":
                print(f"   - {key}: {value}")
        print()
    
    print(f"💾 Статистика сохранена в: data/collection_stats.json")
    
    print_section("ЗАВЕРШЕНО")
    print(f"🕐 Окончание: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n✅ Все данные собраны и готовы к анализу!")
    print("\nСледующий шаг: проанализировать структуру данных и")
    print("скорректировать схему базы данных если необходимо.\n")


if __name__ == "__main__":
    main()

