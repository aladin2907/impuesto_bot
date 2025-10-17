#!/usr/bin/env python3
"""
Скрипт для индексации Telegram тредов в Elasticsearch
Создаёт оптимальную структуру для поиска релевантных диалогов
"""

import json
import re
import argparse
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

import os
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import Settings
from app.services.elasticsearch.elasticsearch_service import ElasticsearchService
from app.services.llm.llm_service import LLMService


class TelegramThreadIndexer:
    def __init__(self):
        self.settings = Settings()
        self.es_service = ElasticsearchService()
        self.llm_service = LLMService()
        # Ensure ES is reachable via HTTP service
        try:
            if not self.es_service.ping():
                raise RuntimeError("Failed to connect to Elasticsearch client")
        except Exception as e:
            print(f"❌ Не удалось инициализировать Elasticsearch клиент: {e}")
            raise
        
        # Ключевые слова для категоризации
        self.tax_keywords = [
            'автономо', 'irpf', 'iva', 'ss', 'социальное', 'налог', 'tax', 
            'factura', 'фактура', 'declaracion', 'декларация', 'retencion', 
            'retención', 'cuota', 'квота', 'trimestre', 'autonomo'
        ]
        
        self.visa_keywords = [
            'visa', 'виза', 'residencia', 'резиденция', 'nomad', 'номад', 
            'extranjero', 'иностранец', 'pasaporte', 'паспорт', 'nie', 
            'dni', 'полиция', 'policia', 'внж', 'временная'
        ]
        
        self.business_keywords = [
            'empresa', 'компания', 'sociedad', 'общество', 'contrato', 
            'контракт', 'empleado', 'сотрудник', 'freelance', 'фриланс', 
            'cliente', 'клиент', 'банк', 'bank', 'счет', 'cuenta'
        ]

    def extract_keywords(self, text: str) -> List[str]:
        """Извлекает ключевые слова из текста"""
        if not text:
            return []
        
        text_lower = text.lower()
        keywords = []
        
        all_keywords = self.tax_keywords + self.visa_keywords + self.business_keywords
        
        for keyword in all_keywords:
            if keyword in text_lower:
                keywords.append(keyword)
        
        return list(set(keywords))

    def categorize_topics(self, keywords: List[str]) -> List[str]:
        """Категоризирует тред по темам"""
        topics = []
        
        if any(k in self.tax_keywords for k in keywords):
            topics.append('tax')
        if any(k in self.visa_keywords for k in keywords):
            topics.append('visa')
        if any(k in self.business_keywords for k in keywords):
            topics.append('business')
        
        return topics

    def calculate_quality_score(self, thread: Dict[str, Any]) -> float:
        """Вычисляет качество треда для приоритизации"""
        score = 0.0
        
        # Базовый балл за количество сообщений
        message_count = thread.get('message_count', 1)
        score += min(message_count * 0.1, 2.0)  # Максимум 2 балла
        
        # Бонус за длинные треды (больше контекста)
        if message_count > 5:
            score += 1.0
        elif message_count > 2:
            score += 0.5
        
        # Бонус за недавние треды
        try:
            last_updated = datetime.fromisoformat(thread['last_updated'].replace('Z', '+00:00'))
            days_ago = (datetime.now().replace(tzinfo=last_updated.tzinfo) - last_updated).days
            
            if days_ago < 30:
                score += 1.0
            elif days_ago < 90:
                score += 0.5
        except:
            pass
        
        # Бонус за наличие ключевых слов
        keywords = self.extract_keywords(' '.join([msg.get('text', '') for msg in thread.get('messages', [])]))
        if keywords:
            score += min(len(keywords) * 0.2, 1.0)  # Максимум 1 балл
        
        return min(score, 5.0)  # Максимум 5 баллов

    def prepare_thread_for_indexing(self, thread: Dict[str, Any], group_name: str) -> Dict[str, Any]:
        """Подготавливает тред для индексации в Elasticsearch"""
        # Объединяем все сообщения
        all_texts = []
        for msg in thread.get('messages', []):
            if msg.get('text'):
                all_texts.append(msg['text'])
        
        content = ' '.join(all_texts)
        
        # Извлекаем ключевые слова
        keywords = self.extract_keywords(content)
        
        # Категоризируем темы
        topics = self.categorize_topics(keywords)
        
        # Вычисляем качество
        quality_score = self.calculate_quality_score(thread)
        
        # Определяем временные метки
        try:
            first_date = datetime.fromisoformat(thread['first_message_date'].replace('Z', '+00:00'))
            year = first_date.year
            month = first_date.month
            quarter = f"Q{(month-1)//3 + 1}"
        except:
            year = 2024
            month = 1
            quarter = "Q1"
        
        return {
            'thread_id': thread['thread_id'],
            'group_name': group_name,
            'group_type': 'it_autonomos' if 'it' in group_name.lower() else 'nomads',
            'first_message_date': thread['first_message_date'],
            'last_updated': thread['last_updated'],
            'message_count': thread['message_count'],
            'max_depth': thread.get('max_depth', 0),
            
            # Основной контент
            'content': content,
            'first_message': thread['messages'][0]['text'] if thread['messages'] else '',
            'last_message': thread['messages'][-1]['text'] if thread['messages'] else '',
            
            # Тематические поля
            'topics': topics,
            'keywords': keywords,
            'tax_related': any(k in self.tax_keywords for k in keywords),
            'visa_related': any(k in self.visa_keywords for k in keywords),
            'business_related': any(k in self.business_keywords for k in keywords),
            
            # Временные метки
            'year': year,
            'month': month,
            'quarter': quarter,
            
            # Качество
            'quality_score': quality_score,
            'relevance_score': 0.0,  # Будет обновляться при поиске
            
            # Метаданные
            'indexed_at': datetime.now().isoformat(),
            'source': 'telegram'
        }

    def create_index_mapping(self):
        """Создаёт mapping для индекса telegram_threads"""
        mapping = {
            "mappings": {
                "properties": {
                    "thread_id": {"type": "keyword"},
                    "group_name": {"type": "keyword"},
                    "group_type": {"type": "keyword"},
                    "first_message_date": {"type": "date"},
                    "last_updated": {"type": "date"},
                    "message_count": {"type": "integer"},
                    "max_depth": {"type": "integer"},
                    
                    # Основной контент для поиска
                    "content": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"}
                        }
                    },
                    
                    # Структурированные поля
                    "first_message": {"type": "text"},
                    "last_message": {"type": "text"},
                    
                    # Тематические теги
                    "topics": {
                        "type": "keyword",
                        "fields": {
                            "text": {"type": "text"}
                        }
                    },
                    
                    # Ключевые слова для фильтрации
                    "keywords": {"type": "keyword"},
                    "tax_related": {"type": "boolean"},
                    "visa_related": {"type": "boolean"},
                    "business_related": {"type": "boolean"},
                    
                    # Временные метки
                    "year": {"type": "integer"},
                    "month": {"type": "integer"},
                    "quarter": {"type": "keyword"},
                    
                    # Релевантность для RAG
                    "relevance_score": {"type": "float"},
                    "quality_score": {"type": "float"},
                    
                    # Метаданные
                    "indexed_at": {"type": "date"},
                    "source": {"type": "keyword"}
                }
            }
        }
        
        return mapping

    def index_threads_from_file(self, file_path: str, group_name: str = None):
        """Индексирует треды из JSON файла"""
        print(f"📁 Загружаем данные из {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and 'threads' in data:
            threads = data['threads']
            if not group_name:
                group_name = data.get('group_title', 'Unknown Group')
        else:
            threads = data
            if not group_name:
                group_name = Path(file_path).stem
        
        print(f"📊 Найдено {len(threads)} тредов в группе '{group_name}'")
        
        # Создаём индекс если не существует (через HTTP сервис)
        index_name = "telegram_threads"
        if not self.es_service.index_exists(index_name):
            print(f"🔨 Создаём индекс {index_name}")
            mapping = self.create_index_mapping()
            self.es_service.create_index(index_name, mapping)
        else:
            print(f"✅ Индекс {index_name} уже существует")
        
        # Индексируем треды батчами
        batch_size = 100
        indexed_count = 0
        
        for i in range(0, len(threads), batch_size):
            batch = threads[i:i + batch_size]
            prepared_batch = []
            
            for thread in batch:
                try:
                    prepared_thread = self.prepare_thread_for_indexing(thread, group_name)
                    prepared_batch.append(prepared_thread)
                except Exception as e:
                    print(f"⚠️ Ошибка при подготовке треда {thread.get('thread_id', 'unknown')}: {e}")
                    continue
            
            if prepared_batch:
                # Индексируем батч
                try:
                    actions = []
                    for thread in prepared_batch:
                        action = {
                            "_index": index_name,
                            "_id": f"{group_name}_{thread['thread_id']}",
                            "_source": thread
                        }
                        actions.append(action)
                    
                    # Bulk через HTTP сервис
                    docs = []
                    for a in actions:
                        doc = a["_source"].copy()
                        doc["_id"] = a["_id"]
                        docs.append(doc)
                    self.es_service.bulk_index(index_name, docs)
                    indexed_count += len(docs)
                    print(f"📤 Индексировано {len(docs)} тредов (всего: {indexed_count}/{len(threads)})")
                        
                except Exception as e:
                    print(f"❌ Ошибка при индексации батча: {e}")
        
        print(f"✅ Индексация завершена! Всего проиндексировано: {indexed_count} тредов")
        return indexed_count

    def test_search(self, query: str, limit: int = 5):
        """Тестирует поиск по индексированным тредам"""
        print(f"🔍 Тестируем поиск: '{query}'")
        
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["content^2", "first_message^1.5", "last_message^1.5"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "size": limit,
            "_source": ["thread_id", "group_name", "content", "topics", "quality_score", "first_message_date"]
        }
        
        try:
            results = self.es_service.search(
                index_name="telegram_threads",
                query=search_body["query"],
                size=limit
            )
            print(f"📊 Найдено результатов: {len(results)}")
            for hit in results:
                score = hit.get("_score", 0)
                print(f"\n🎯 Score: {score:.2f}")
                print(f"Thread: {hit.get('thread_id')} ({hit.get('group_name')})")
                print(f"Topics: {hit.get('topics', [])}")
                print(f"Quality: {hit.get('quality_score', 0):.1f}")
                print(f"Content: {hit.get('content','')[:200]}...")
        except Exception as e:
            print(f"❌ Ошибка при поиске: {e}")


def main():
    parser = argparse.ArgumentParser(description='Индексация Telegram тредов в Elasticsearch')
    parser.add_argument('file', help='Путь к JSON файлу с тредами')
    parser.add_argument('--group-name', help='Название группы (по умолчанию из файла)')
    parser.add_argument('--test-search', help='Тестовый поиск после индексации')
    parser.add_argument('--limit', type=int, default=5, help='Лимит результатов поиска')
    
    args = parser.parse_args()
    
    indexer = TelegramThreadIndexer()
    
    try:
        # Индексируем треды
        indexed_count = indexer.index_threads_from_file(args.file, args.group_name)
        
        # Тестовый поиск если указан
        if args.test_search:
            indexer.test_search(args.test_search, args.limit)
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
