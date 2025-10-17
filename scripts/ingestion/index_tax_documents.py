#!/usr/bin/env python3
"""
Скрипт для индексации налоговых документов (HTML) в Elasticsearch
Разбивает HTML на чанки и индексирует с метаданными
"""

import os
import sys
import json
import re
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from bs4 import BeautifulSoup

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import Settings
from app.services.elasticsearch.elasticsearch_service import ElasticsearchService


class TaxDocumentIndexer:
    def __init__(self):
        self.settings = Settings()
        self.es_service = ElasticsearchService()
        
        # Обеспечиваем подключение к ES
        if not self.es_service.ping():
            raise RuntimeError("Failed to connect to Elasticsearch")
        
        # Маппинг названий файлов к типам документов
        self.document_types = {
            "LGT_General_Tax_Law": "Ley General Tributaria",
            "IRPF_Personal_Income_Tax": "IRPF - Personal Income Tax",
            "IVA_Value_Added_Tax": "IVA - Value Added Tax",
            "Impuesto_Sociedades_Corporate_Tax": "Corporate Tax",
            "Impuesto_Sucesiones_Donaciones": "Inheritance & Gift Tax",
            "Impuesto_Patrimonio_Wealth_Tax": "Wealth Tax"
        }
        
        # Ключевые слова для категоризации
        self.tax_categories = {
            "autonomo": ["autónomo", "autonomo", "self-employed", "freelance"],
            "empresa": ["empresa", "sociedad", "company", "corporation"],
            "iva": ["iva", "vat", "value added tax", "impuesto sobre el valor añadido"],
            "irpf": ["irpf", "personal income tax", "renta", "income tax"],
            "retenciones": ["retención", "retencion", "withholding", "retention"],
            "declaraciones": ["declaración", "declaracion", "declaration", "return"],
            "sanciones": ["sanción", "sancion", "penalty", "fine", "multa"],
            "procedimientos": ["procedimiento", "procedure", "process", "tramite"]
        }

    def extract_text_from_html(self, html_content: str) -> str:
        """Извлекает чистый текст из HTML"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Удаляем скрипты и стили
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Получаем текст
            text = soup.get_text()
            
            # Очищаем текст
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            print(f"⚠️ Ошибка парсинга HTML: {e}")
            return html_content

    def split_text_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Разбивает текст на чанки с перекрытием"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Ищем границу предложения для лучшего разбиения
            if end < len(text):
                # Ищем последнюю точку, восклицательный или вопросительный знак
                for i in range(end, max(start + chunk_size - 100, start), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks

    def extract_categories(self, text: str) -> List[str]:
        """Извлекает категории из текста"""
        text_lower = text.lower()
        categories = []
        
        for category, keywords in self.tax_categories.items():
            if any(keyword in text_lower for keyword in keywords):
                categories.append(category)
        
        return categories

    def prepare_chunk_for_indexing(self, chunk: str, chunk_index: int, document_info: Dict[str, Any]) -> Dict[str, Any]:
        """Подготавливает чанк для индексации"""
        categories = self.extract_categories(chunk)
        
        return {
            "document_id": document_info["document_id"],
            "chunk_id": f"{document_info['document_id']}_chunk_{chunk_index}",
            "chunk_index": chunk_index,
            
            # Основной контент
            "content": chunk,
            
            # Метаданные документа
            "document_title": document_info["title"],
            "document_type": document_info["type"],
            "document_number": document_info.get("number", ""),
            
            # Категории и теги
            "categories": categories,
            "tax_related": len(categories) > 0,
            
            # Временные метки
            "indexed_at": datetime.now().isoformat(),
            "source": "tax_documents"
        }

    def create_index_mapping(self):
        """Создаёт mapping для индекса pdf_documents"""
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "spanish_text": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "spanish_stop", "spanish_stemmer"]
                        }
                    },
                    "filter": {
                        "spanish_stop": {
                            "type": "stop",
                            "stopwords": "_spanish_"
                        },
                        "spanish_stemmer": {
                            "type": "stemmer",
                            "language": "spanish"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "document_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},
                    
                    # Основной контент для поиска
                    "content": {
                        "type": "text",
                        "analyzer": "spanish_text",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "exact": {
                                "type": "text",
                                "analyzer": "standard"
                            }
                        }
                    },
                    
                    # Метаданные документа
                    "document_title": {
                        "type": "text",
                        "analyzer": "spanish_text"
                    },
                    "document_type": {"type": "keyword"},
                    "document_number": {"type": "keyword"},
                    
                    # Категории и теги
                    "categories": {"type": "keyword"},
                    "tax_related": {"type": "boolean"},
                    
                    # Временные метки
                    "indexed_at": {"type": "date"},
                    "source": {"type": "keyword"}
                }
            }
        }
        
        return mapping

    def index_document_file(self, file_path: str) -> int:
        """Индексирует один HTML файл"""
        print(f"📄 Обрабатываем: {file_path}")
        
        # Определяем информацию о документе
        filename = Path(file_path).stem
        document_type = self.document_types.get(filename, "Unknown")
        
        # Читаем HTML файл
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            print(f"❌ Ошибка чтения файла {file_path}: {e}")
            return 0
        
        # Извлекаем текст
        text = self.extract_text_from_html(html_content)
        print(f"   📊 Размер текста: {len(text)} символов")
        
        # Разбиваем на чанки
        chunks = self.split_text_into_chunks(text)
        print(f"   📦 Создано чанков: {len(chunks)}")
        
        # Подготавливаем документы для индексации
        document_info = {
            "document_id": filename,
            "title": document_type,
            "type": "tax_law",
            "number": self.extract_document_number(text)
        }
        
        prepared_chunks = []
        for i, chunk in enumerate(chunks):
            prepared_chunk = self.prepare_chunk_for_indexing(chunk, i, document_info)
            prepared_chunks.append(prepared_chunk)
        
        # Создаём индекс если не существует
        index_name = "pdf_documents"
        if not self.es_service.index_exists(index_name):
            print(f"🔨 Создаём индекс {index_name}")
            mapping = self.create_index_mapping()
            self.es_service.create_index(index_name, mapping)
        else:
            print(f"✅ Индекс {index_name} уже существует")
        
        # Индексируем чанки батчами
        batch_size = 50
        indexed_count = 0
        
        for i in range(0, len(prepared_chunks), batch_size):
            batch = prepared_chunks[i:i + batch_size]
            
            # Добавляем _id для каждого чанка
            for chunk in batch:
                chunk["_id"] = chunk["chunk_id"]
            
            try:
                self.es_service.bulk_index(index_name, batch)
                indexed_count += len(batch)
                print(f"   📤 Индексировано {len(batch)} чанков (всего: {indexed_count}/{len(prepared_chunks)})")
            except Exception as e:
                print(f"   ❌ Ошибка индексации батча: {e}")
        
        print(f"   ✅ Документ проиндексирован: {indexed_count} чанков")
        return indexed_count

    def extract_document_number(self, text: str) -> str:
        """Извлекает номер документа из текста"""
        # Ищем паттерны типа "Ley 58/2003" или "Real Decreto 123/2024"
        patterns = [
            r'Ley\s+(\d+/\d+)',
            r'Real\s+Decreto\s+(\d+/\d+)',
            r'Decreto\s+(\d+/\d+)',
            r'Orden\s+(\d+/\d+)',
            r'Resolución\s+(\d+/\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ""

    def index_all_documents(self, documents_dir: str) -> int:
        """Индексирует все HTML документы в папке"""
        print("🚀 Начинаем индексацию налоговых документов")
        print("=" * 60)
        
        docs_path = Path(documents_dir)
        if not docs_path.exists():
            print(f"❌ Папка не существует: {documents_dir}")
            return 0
        
        # Находим все HTML файлы
        html_files = list(docs_path.glob("*.html"))
        if not html_files:
            print(f"❌ HTML файлы не найдены в {documents_dir}")
            return 0
        
        print(f"📁 Найдено {len(html_files)} HTML файлов")
        
        total_chunks = 0
        for html_file in html_files:
            chunks_count = self.index_document_file(str(html_file))
            total_chunks += chunks_count
            print()
        
        print("=" * 60)
        print(f"✅ Индексация завершена! Всего проиндексировано: {total_chunks} чанков")
        return total_chunks

    def test_search(self, query: str, limit: int = 5):
        """Тестирует поиск по индексированным документам"""
        print(f"🔍 Тестируем поиск: '{query}'")
        
        search_query = {
            "multi_match": {
                "query": query,
                "fields": ["content^2", "document_title^1.5"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        }
        
        try:
            results = self.es_service.search(
                index_name="pdf_documents",
                query=search_query,
                size=limit
            )
            
            print(f"📊 Найдено результатов: {len(results)}")
            
            for hit in results:
                score = hit.get("_score", 0)
                print(f"\n🎯 Score: {score:.2f}")
                print(f"Document: {hit.get('document_title')} ({hit.get('document_id')})")
                print(f"Categories: {hit.get('categories', [])}")
                print(f"Content: {hit.get('content', '')[:200]}...")
                
        except Exception as e:
            print(f"❌ Ошибка при поиске: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Индексация налоговых документов в Elasticsearch')
    parser.add_argument('--documents-dir', default='data/tax_documents', help='Папка с HTML документами')
    parser.add_argument('--test-search', help='Тестовый поиск после индексации')
    parser.add_argument('--limit', type=int, default=5, help='Лимит результатов поиска')
    
    args = parser.parse_args()
    
    indexer = TaxDocumentIndexer()
    
    try:
        # Индексируем документы
        total_chunks = indexer.index_all_documents(args.documents_dir)
        
        # Тестовый поиск если указан
        if args.test_search and total_chunks > 0:
            indexer.test_search(args.test_search, args.limit)
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
