#!/usr/bin/env python3
"""
Включает гибридный поиск для существующих индексов
1. Добавляет dense_vector поля в mapping
2. Генерирует embeddings для существующих документов
3. Обновляет search_service.py
"""

import os
import sys
import json
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.elasticsearch.elasticsearch_service import ElasticsearchService
from app.services.llm.llm_service import LLMService
from app.config.settings import Settings

settings = Settings()

# Конфигурация индексов (только те, что реально используются)
INDICES_CONFIG = {
    "telegram_threads": {
        "text_field": "content",
        "embedding_field": "content_embedding"
    },
    "pdf_documents": {
        "text_field": "content",
        "embedding_field": "content_embedding"
    }
}


def add_vector_field_to_mapping(es_service: ElasticsearchService, index_name: str, embedding_field: str):
    """Добавляет dense_vector поле в существующий индекс"""
    
    print(f"\n🔧 Обновление mapping для {index_name}...")
    
    # OpenAI text-embedding-3-small имеет размерность 1536
    mapping = {
        "properties": {
            embedding_field: {
                "type": "dense_vector",
                "dims": 1536,
                "index": True,
                "similarity": "cosine"
            }
        }
    }
    
    try:
        # Проверяем существование индекса
        if not es_service.index_exists(index_name):
            print(f"⚠️  Индекс {index_name} не существует")
            return False
        
        # Добавляем поле в mapping через requests API
        import requests
        url = f"{es_service.base_url}/{index_name}/_mapping"
        response = requests.put(
            url,
            headers=es_service.headers,
            json=mapping,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ Добавлено поле {embedding_field} в {index_name}")
            return True
        else:
            print(f"❌ Ошибка обновления mapping: {response.status_code}")
            print(f"   {response.text[:300]}")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка обновления mapping: {e}")
        return False


def generate_embeddings_for_index(
    es_service: ElasticsearchService,
    llm_service: LLMService,
    index_name: str,
    text_field: str,
    embedding_field: str,
    batch_size: int = 50
):
    """Генерирует embeddings для всех документов в индексе"""
    
    print(f"\n📊 Генерация embeddings для {index_name}...")
    
    try:
        import requests
        
        # Получаем общее количество документов
        count_url = f"{es_service.base_url}/{index_name}/_count"
        count_response = requests.get(count_url, headers=es_service.headers, timeout=30)
        count_response.raise_for_status()
        total_docs = count_response.json()['count']
        print(f"Всего документов: {total_docs}")
        
        if total_docs == 0:
            print("⚠️  Индекс пустой")
            return 0
        
        # Scroll API для получения всех документов
        scroll_time = '5m'
        search_url = f"{es_service.base_url}/{index_name}/_search?scroll={scroll_time}"
        search_body = {
            "query": {"match_all": {}},
            "_source": [text_field],
            "size": batch_size
        }
        
        response = requests.post(search_url, headers=es_service.headers, json=search_body, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        scroll_id = result['_scroll_id']
        hits = result['hits']['hits']
        
        processed = 0
        updated = 0
        
        while hits:
            # Подготавливаем батч для генерации embeddings
            texts = []
            doc_ids = []
            
            for hit in hits:
                text = hit['_source'].get(text_field, '')
                if text and len(text.strip()) > 0:
                    texts.append(text[:8000])  # Ограничиваем длину для API
                    doc_ids.append(hit['_id'])
            
            if texts:
                # Генерируем embeddings батчом
                try:
                    embeddings = llm_service.generate_embeddings_batch(texts)
                    
                    if embeddings and len(embeddings) == len(texts):
                        # Обновляем документы через bulk API
                        bulk_url = f"{es_service.base_url}/_bulk"
                        bulk_lines = []
                        for doc_id, embedding in zip(doc_ids, embeddings):
                            bulk_lines.append(json.dumps({"update": {"_id": doc_id, "_index": index_name}}))
                            bulk_lines.append(json.dumps({"doc": {embedding_field: embedding}}))
                        
                        bulk_body = "\n".join(bulk_lines) + "\n"
                        headers = es_service.headers.copy()
                        headers["Content-Type"] = "application/x-ndjson"
                        
                        bulk_response = requests.post(bulk_url, headers=headers, data=bulk_body, timeout=60)
                        
                        if bulk_response.status_code == 200:
                            updated += len(embeddings)
                        else:
                            print(f"⚠️  Bulk update вернул {bulk_response.status_code}")
                    
                except Exception as e:
                    print(f"⚠️  Ошибка генерации embeddings для батча: {e}")
            
            processed += len(hits)
            print(f"  Обработано: {processed}/{total_docs}, обновлено: {updated}")
            
            # Получаем следующий батч
            scroll_url = f"{es_service.base_url}/_search/scroll"
            scroll_body = {"scroll": scroll_time, "scroll_id": scroll_id}
            scroll_response = requests.post(scroll_url, headers=es_service.headers, json=scroll_body, timeout=30)
            scroll_response.raise_for_status()
            result = scroll_response.json()
            scroll_id = result['_scroll_id']
            hits = result['hits']['hits']
        
        # Очищаем scroll
        delete_scroll_url = f"{es_service.base_url}/_search/scroll"
        requests.delete(delete_scroll_url, headers=es_service.headers, json={"scroll_id": scroll_id}, timeout=10)
        
        print(f"✅ Обновлено {updated} документов с embeddings")
        return updated
        
    except Exception as e:
        print(f"❌ Ошибка генерации embeddings: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    print("=" * 70)
    print("🚀 ВКЛЮЧЕНИЕ ГИБРИДНОГО ПОИСКА")
    print("=" * 70)
    print("\nИспользуем модель: OpenAI text-embedding-3-small (dims: 1536)")
    print("Метрика similarity: cosine")
    
    # Инициализация сервисов
    print("\n📦 Инициализация сервисов...")
    
    es_service = ElasticsearchService()
    if not es_service.ping():
        print("❌ Не удалось подключиться к Elasticsearch")
        return 1
    print("✅ Elasticsearch подключен")
    
    llm_service = LLMService()
    if not llm_service.initialize():
        print("❌ Не удалось инициализировать LLM service")
        return 1
    print(f"✅ LLM service инициализирован: {llm_service.provider} / {llm_service.model}")
    
    # Обрабатываем каждый индекс
    total_updated = 0
    
    for index_name, config in INDICES_CONFIG.items():
        print("\n" + "=" * 70)
        print(f"📁 Индекс: {index_name}")
        print("=" * 70)
        
        # 1. Добавляем векторное поле в mapping
        if not add_vector_field_to_mapping(
            es_service=es_service,
            index_name=index_name,
            embedding_field=config["embedding_field"]
        ):
            print(f"⚠️  Пропускаем индекс {index_name}")
            continue
        
        # 2. Генерируем embeddings для существующих документов
        updated_count = generate_embeddings_for_index(
            es_service=es_service,
            llm_service=llm_service,
            index_name=index_name,
            text_field=config["text_field"],
            embedding_field=config["embedding_field"],
            batch_size=50
        )
        
        total_updated += updated_count
        print(f"✅ Индекс {index_name} готов к гибридному поиску")
    
    # Итоги
    print("\n" + "=" * 70)
    print(f"✅ ГОТОВО!")
    print("=" * 70)
    print(f"Всего документов обновлено с embeddings: {total_updated}")
    print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
    print("1. Обновить search_service.py для использования гибридного поиска")
    print("2. Протестировать поиск")
    print("\nГибридный поиск = BM25 (keyword) + kNN (vector) + RRF")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

