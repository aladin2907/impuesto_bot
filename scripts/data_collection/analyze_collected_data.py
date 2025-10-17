#!/usr/bin/env python3
"""
Скрипт для анализа собранных данных
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import re

# Добавляем корневую папку в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import Settings


class DataAnalyzer:
    """Класс для анализа собранных данных"""
    
    def __init__(self):
        self.settings = Settings()
        self.data_dir = Path("data")
        
        # Папки с данными
        self.data_folders = {
            "telegram_threads": "data/telegram_threads",
            "tax_documents": "data/tax_documents", 
            "aeat_forms": "data/aeat_forms",
            "news_articles": "data/news_articles",
            "tax_calendar": "data/tax_calendar"
        }
    
    def analyze_telegram_data(self) -> dict:
        """Анализирует данные Telegram"""
        print("\n📱 Анализ данных Telegram:")
        print("-" * 40)
        
        telegram_dir = Path(self.data_folders["telegram_threads"])
        if not telegram_dir.exists():
            print("   ❌ Папка не существует")
            return {"status": "not_found"}
        
        # Ищем JSON файлы
        json_files = list(telegram_dir.glob("*.json"))
        if not json_files:
            print("   ❌ JSON файлы не найдены")
            return {"status": "no_files"}
        
        total_threads = 0
        total_messages = 0
        groups = {}
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    threads = data
                elif isinstance(data, dict) and 'threads' in data:
                    threads = data['threads']
                else:
                    continue
                
                group_name = json_file.stem
                groups[group_name] = {
                    "threads": len(threads),
                    "messages": sum(len(thread.get('messages', [])) for thread in threads)
                }
                
                total_threads += len(threads)
                total_messages += groups[group_name]["messages"]
                
                print(f"   📄 {json_file.name}")
                print(f"      Тредов: {len(threads)}")
                print(f"      Сообщений: {groups[group_name]['messages']}")
                
            except Exception as e:
                print(f"   ❌ Ошибка чтения {json_file.name}: {e}")
        
        result = {
            "status": "success",
            "total_threads": total_threads,
            "total_messages": total_messages,
            "groups": groups,
            "files_count": len(json_files)
        }
        
        print(f"\n   📊 Итого:")
        print(f"      Файлов: {len(json_files)}")
        print(f"      Тредов: {total_threads}")
        print(f"      Сообщений: {total_messages}")
        
        return result
    
    def analyze_tax_documents(self) -> dict:
        """Анализирует налоговые документы"""
        print("\n📄 Анализ налоговых документов:")
        print("-" * 40)
        
        docs_dir = Path(self.data_folders["tax_documents"])
        if not docs_dir.exists():
            print("   ❌ Папка не существует")
            return {"status": "not_found"}
        
        html_files = list(docs_dir.glob("*.html"))
        if not html_files:
            print("   ❌ HTML файлы не найдены")
            return {"status": "no_files"}
        
        total_size = 0
        documents = {}
        
        for html_file in html_files:
            try:
                size = html_file.stat().st_size
                total_size += size
                
                documents[html_file.name] = {
                    "size": size,
                    "size_mb": size / 1024 / 1024
                }
                
                print(f"   📄 {html_file.name}")
                print(f"      Размер: {size / 1024 / 1024:.2f} MB")
                
            except Exception as e:
                print(f"   ❌ Ошибка чтения {html_file.name}: {e}")
        
        result = {
            "status": "success",
            "total_size": total_size,
            "total_size_mb": total_size / 1024 / 1024,
            "documents": documents,
            "files_count": len(html_files)
        }
        
        print(f"\n   📊 Итого:")
        print(f"      Файлов: {len(html_files)}")
        print(f"      Общий размер: {total_size / 1024 / 1024:.2f} MB")
        
        return result
    
    def analyze_aeat_forms(self) -> dict:
        """Анализирует формы AEAT"""
        print("\n📋 Анализ форм AEAT:")
        print("-" * 40)
        
        forms_dir = Path(self.data_folders["aeat_forms"])
        if not forms_dir.exists():
            print("   ❌ Папка не существует")
            return {"status": "not_found"}
        
        pdf_files = list(forms_dir.glob("*.pdf"))
        if not pdf_files:
            print("   ❌ PDF файлы не найдены")
            return {"status": "no_files"}
        
        total_size = 0
        forms = {}
        
        for pdf_file in pdf_files:
            try:
                size = pdf_file.stat().st_size
                total_size += size
                
                forms[pdf_file.name] = {
                    "size": size,
                    "size_mb": size / 1024 / 1024
                }
                
                print(f"   📄 {pdf_file.name}")
                print(f"      Размер: {size / 1024 / 1024:.2f} MB")
                
            except Exception as e:
                print(f"   ❌ Ошибка чтения {pdf_file.name}: {e}")
        
        result = {
            "status": "success",
            "total_size": total_size,
            "total_size_mb": total_size / 1024 / 1024,
            "forms": forms,
            "files_count": len(pdf_files)
        }
        
        print(f"\n   📊 Итого:")
        print(f"      Файлов: {len(pdf_files)}")
        print(f"      Общий размер: {total_size / 1024 / 1024:.2f} MB")
        
        return result
    
    def analyze_news_articles(self) -> dict:
        """Анализирует новостные статьи"""
        print("\n📰 Анализ новостных статей:")
        print("-" * 40)
        
        news_dir = Path(self.data_folders["news_articles"])
        if not news_dir.exists():
            print("   ❌ Папка не существует")
            return {"status": "not_found"}
        
        json_files = list(news_dir.glob("*.json"))
        if not json_files:
            print("   ❌ JSON файлы не найдены")
            return {"status": "no_files"}
        
        total_articles = 0
        sources = {}
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    articles = json.load(f)
                
                if isinstance(articles, list):
                    article_count = len(articles)
                    total_articles += article_count
                    
                    # Группируем по источникам
                    for article in articles:
                        source = article.get('source', 'Unknown')
                        if source not in sources:
                            sources[source] = 0
                        sources[source] += 1
                    
                    print(f"   📄 {json_file.name}")
                    print(f"      Статей: {article_count}")
                
            except Exception as e:
                print(f"   ❌ Ошибка чтения {json_file.name}: {e}")
        
        result = {
            "status": "success",
            "total_articles": total_articles,
            "sources": sources,
            "files_count": len(json_files)
        }
        
        print(f"\n   📊 Итого:")
        print(f"      Файлов: {len(json_files)}")
        print(f"      Статей: {total_articles}")
        print(f"      Источники: {sources}")
        
        return result
    
    def analyze_tax_calendar(self) -> dict:
        """Анализирует налоговый календарь"""
        print("\n📅 Анализ налогового календаря:")
        print("-" * 40)
        
        calendar_dir = Path(self.data_folders["tax_calendar"])
        if not calendar_dir.exists():
            print("   ❌ Папка не существует")
            return {"status": "not_found"}
        
        json_files = list(calendar_dir.glob("*.json"))
        if not json_files:
            print("   ❌ JSON файлы не найдены")
            return {"status": "no_files"}
        
        total_deadlines = 0
        years = {}
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    deadlines = data
                elif isinstance(data, dict) and 'deadlines' in data:
                    deadlines = data['deadlines']
                else:
                    continue
                
                deadline_count = len(deadlines)
                total_deadlines += deadline_count
                
                # Группируем по годам
                for deadline in deadlines:
                    year = deadline.get('year', 'Unknown')
                    if year not in years:
                        years[year] = 0
                    years[year] += 1
                
                print(f"   📄 {json_file.name}")
                print(f"      Сроков: {deadline_count}")
                
            except Exception as e:
                print(f"   ❌ Ошибка чтения {json_file.name}: {e}")
        
        result = {
            "status": "success",
            "total_deadlines": total_deadlines,
            "years": years,
            "files_count": len(json_files)
        }
        
        print(f"\n   📊 Итого:")
        print(f"      Файлов: {len(json_files)}")
        print(f"      Сроков: {total_deadlines}")
        print(f"      Годы: {years}")
        
        return result
    
    def analyze_all_data(self) -> dict:
        """Анализирует все собранные данные"""
        print("🔍 TuExpertoFiscal NAIL - Анализ собранных данных")
        print("=" * 60)
        
        results = {}
        
        # Анализируем каждый тип данных
        results["telegram"] = self.analyze_telegram_data()
        results["tax_documents"] = self.analyze_tax_documents()
        results["aeat_forms"] = self.analyze_aeat_forms()
        results["news_articles"] = self.analyze_news_articles()
        results["tax_calendar"] = self.analyze_tax_calendar()
        
        # Общая статистика
        print("\n" + "=" * 60)
        print("📊 ОБЩАЯ СТАТИСТИКА:")
        print("=" * 60)
        
        total_files = 0
        total_size_mb = 0
        
        for data_type, result in results.items():
            if result["status"] == "success":
                total_files += result.get("files_count", 0)
                total_size_mb += result.get("total_size_mb", 0)
                
                print(f"   ✅ {data_type}: {result.get('files_count', 0)} файлов")
            else:
                print(f"   ❌ {data_type}: {result['status']}")
        
        print(f"\n   📊 Итого:")
        print(f"      Файлов: {total_files}")
        print(f"      Размер: {total_size_mb:.2f} MB")
        
        # Сохраняем результаты анализа
        analysis_file = self.data_dir / "data_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Результаты анализа сохранены: {analysis_file}")
        
        return results


def main():
    """Основная функция"""
    analyzer = DataAnalyzer()
    analyzer.analyze_all_data()


if __name__ == "__main__":
    main()
