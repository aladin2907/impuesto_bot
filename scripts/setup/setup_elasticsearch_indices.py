#!/usr/bin/env python3
"""
Скрипт для создания индексов в Elasticsearch
Настраивает mappings для всех типов данных
"""

import os
import sys
from pathlib import Path

# Добавляем корневую папку в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from elasticsearch import Elasticsearch
from app.config.settings import Settings


class ElasticsearchSetup:
    def __init__(self):
        self.settings = Settings()
        self.client = self._connect()
    
    def _connect(self):
        """Подключается к Elasticsearch"""
        try:
            if self.settings.ELASTIC_CLOUD_ID:
                client = Elasticsearch(
                    cloud_id=self.settings.ELASTIC_CLOUD_ID,
                    api_key=self.settings.ELASTIC_API_KEY
                )
            else:
                print("❌ ELASTIC_CLOUD_ID не задан в .env")
                sys.exit(1)
            
            # Проверяем подключение
            if client.ping():
                print("✅ Подключение к Elasticsearch успешно!")
                info = client.info()
                print(f"   Версия: {info['version']['number']}")
                print(f"   Кластер: {info['cluster_name']}")
                return client
            else:
                print("❌ Не удалось подключиться к Elasticsearch")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            sys.exit(1)
    
    def create_telegram_threads_index(self):
        """Создаёт индекс для Telegram тредов"""
        index_name = "telegram_threads"
        
        print(f"\n📋 Создаём индекс: {index_name}")
        
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "russian_english": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "russian_stop", "english_stop"]
                        }
                    },
                    "filter": {
                        "russian_stop": {
                            "type": "stop",
                            "stopwords": "_russian_"
                        },
                        "english_stop": {
                            "type": "stop",
                            "stopwords": "_english_"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "supabase_id": {"type": "keyword"},
                    "thread_id": {"type": "long"},
                    "group_name": {"type": "keyword"},
                    
                    "content": {
                        "type": "text",
                        "analyzer": "russian_english",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "russian": {
                                "type": "text",
                                "analyzer": "russian"
                            },
                            "english": {
                                "type": "text",
                                "analyzer": "english"
                            }
                        }
                    },
                    
                    "first_message": {
                        "type": "text",
                        "analyzer": "russian_english"
                    },
                    "last_message": {
                        "type": "text",
                        "analyzer": "russian_english"
                    },
                    
                    "message_count": {"type": "integer"},
                    "max_depth": {"type": "integer"},
                    
                    "topics": {"type": "keyword"},
                    "keywords": {"type": "keyword"},
                    "tax_related": {"type": "boolean"},
                    "visa_related": {"type": "boolean"},
                    "business_related": {"type": "boolean"},
                    
                    "quality_score": {"type": "float"},
                    "first_message_date": {"type": "date"},
                    "last_updated": {"type": "date"},
                    
                    "indexed_at": {"type": "date"}
                }
            }
        }
        
        try:
            if self.client.indices.exists(index=index_name):
                print(f"   ⚠️  Индекс {index_name} уже существует")
                response = input("   Удалить и пересоздать? (y/N): ")
                if response.lower() == 'y':
                    self.client.indices.delete(index=index_name)
                    print(f"   🗑️  Индекс {index_name} удалён")
                else:
                    print(f"   ⏭️  Пропускаем {index_name}")
                    return
            
            self.client.indices.create(index=index_name, body=mapping)
            print(f"   ✅ Индекс {index_name} создан!")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    def create_pdf_documents_index(self):
        """Создаёт индекс для PDF документов (чанки)"""
        index_name = "pdf_documents"
        
        print(f"\n📋 Создаём индекс: {index_name}")
        
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1
            },
            "mappings": {
                "properties": {
                    "supabase_id": {"type": "keyword"},
                    "document_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    
                    "content": {
                        "type": "text",
                        "analyzer": "spanish",
                        "fields": {
                            "exact": {
                                "type": "text",
                                "analyzer": "standard"
                            }
                        }
                    },
                    
                    "document_title": {"type": "text", "analyzer": "spanish"},
                    "document_type": {"type": "keyword"},
                    "document_number": {"type": "keyword"},
                    
                    "chunk_index": {"type": "integer"},
                    "page_number": {"type": "integer"},
                    
                    "categories": {"type": "keyword"},
                    "region": {"type": "keyword"},
                    "publication_date": {"type": "date"},
                    
                    "indexed_at": {"type": "date"}
                }
            }
        }
        
        try:
            if self.client.indices.exists(index=index_name):
                print(f"   ⚠️  Индекс {index_name} уже существует")
                response = input("   Удалить и пересоздать? (y/N): ")
                if response.lower() == 'y':
                    self.client.indices.delete(index=index_name)
                    print(f"   🗑️  Индекс {index_name} удалён")
                else:
                    print(f"   ⏭️  Пропускаем {index_name}")
                    return
            
            self.client.indices.create(index=index_name, body=mapping)
            print(f"   ✅ Индекс {index_name} создан!")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    def create_news_articles_index(self):
        """Создаёт индекс для новостных статей"""
        index_name = "news_articles"
        
        print(f"\n📋 Создаём индекс: {index_name}")
        
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1
            },
            "mappings": {
                "properties": {
                    "supabase_id": {"type": "keyword"},
                    "article_url": {"type": "keyword"},
                    
                    "title": {
                        "type": "text",
                        "analyzer": "spanish",
                        "fields": {
                            "exact": {"type": "keyword"}
                        }
                    },
                    "content": {"type": "text", "analyzer": "spanish"},
                    "summary": {"type": "text", "analyzer": "spanish"},
                    
                    "news_source": {"type": "keyword"},
                    "author": {"type": "keyword"},
                    
                    "categories": {"type": "keyword"},
                    "keywords": {"type": "keyword"},
                    "tax_related": {"type": "boolean"},
                    
                    "published_at": {"type": "date"},
                    "relevance_score": {"type": "float"},
                    
                    "indexed_at": {"type": "date"}
                }
            }
        }
        
        try:
            if self.client.indices.exists(index=index_name):
                print(f"   ⚠️  Индекс {index_name} уже существует")
                response = input("   Удалить и пересоздать? (y/N): ")
                if response.lower() == 'y':
                    self.client.indices.delete(index=index_name)
                    print(f"   🗑️  Индекс {index_name} удалён")
                else:
                    print(f"   ⏭️  Пропускаем {index_name}")
                    return
            
            self.client.indices.create(index=index_name, body=mapping)
            print(f"   ✅ Индекс {index_name} создан!")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    def create_calendar_deadlines_index(self):
        """Создаёт индекс для налогового календаря"""
        index_name = "calendar_deadlines"
        
        print(f"\n📋 Создаём индекс: {index_name}")
        
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1
            },
            "mappings": {
                "properties": {
                    "supabase_id": {"type": "keyword"},
                    
                    "description": {"type": "text", "analyzer": "spanish"},
                    
                    "deadline_date": {"type": "date"},
                    "year": {"type": "integer"},
                    "quarter": {"type": "keyword"},
                    
                    "tax_type": {"type": "keyword"},
                    "tax_model": {"type": "keyword"},
                    "applies_to": {"type": "keyword"},
                    
                    "indexed_at": {"type": "date"}
                }
            }
        }
        
        try:
            if self.client.indices.exists(index=index_name):
                print(f"   ⚠️  Индекс {index_name} уже существует")
                response = input("   Удалить и пересоздать? (y/N): ")
                if response.lower() == 'y':
                    self.client.indices.delete(index=index_name)
                    print(f"   🗑️  Индекс {index_name} удалён")
                else:
                    print(f"   ⏭️  Пропускаем {index_name}")
                    return
            
            self.client.indices.create(index=index_name, body=mapping)
            print(f"   ✅ Индекс {index_name} создан!")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    def list_indices(self):
        """Выводит список созданных индексов"""
        print(f"\n📊 Список индексов:")
        
        indices = self.client.indices.get_alias(index="*")
        
        for index_name in sorted(indices.keys()):
            if not index_name.startswith('.'):  # Пропускаем системные индексы
                stats = self.client.indices.stats(index=index_name)
                doc_count = stats['_all']['primaries']['docs']['count']
                size = stats['_all']['primaries']['store']['size_in_bytes']
                size_mb = size / 1024 / 1024
                
                print(f"   ✅ {index_name}")
                print(f"      Документов: {doc_count}")
                print(f"      Размер: {size_mb:.2f} MB")
    
    def setup_all(self):
        """Создаёт все индексы"""
        print("\n" + "="*70)
        print("  НАСТРОЙКА ИНДЕКСОВ ELASTICSEARCH")
        print("="*70)
        
        self.create_telegram_threads_index()
        self.create_pdf_documents_index()
        self.create_news_articles_index()
        self.create_calendar_deadlines_index()
        
        self.list_indices()
        
        print("\n" + "="*70)
        print("✅ ВСЕ ИНДЕКСЫ СОЗДАНЫ!")
        print("="*70)
        print()


def main():
    setup = ElasticsearchSetup()
    setup.setup_all()


if __name__ == "__main__":
    main()


