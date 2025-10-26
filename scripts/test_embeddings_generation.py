#!/usr/bin/env python3
"""
Тестовый скрипт для проверки генерации embeddings
Обрабатывает только первые 100 документов
"""

import os
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.elasticsearch.elasticsearch_service import ElasticsearchService
from app.services.llm.llm_service import LLMService
import requests

def test_embeddings():
    print("🧪 ТЕСТ ГЕНЕРАЦИИ EMBEDDINGS")
    print("=" * 60)
    
    # Инициализация
    es_service = ElasticsearchService()
    llm_service = LLMService()
    
    if not llm_service.initialize():
        print("❌ Не удалось инициализировать LLM")
        return
    
    print(f"✅ LLM инициализирован: {llm_service.provider}")
    
    # Тестируем на 3 документах
    index_name = "telegram_threads"
    text_field = "content"
    embedding_field = "content_embedding"
    
    # Получаем 3 документа
    search_url = f"{es_service.base_url}/{index_name}/_search"
    search_body = {
        "query": {"match_all": {}},
        "_source": [text_field],
        "size": 3
    }
    
    response = requests.post(search_url, headers=es_service.headers, json=search_body, timeout=30)
    hits = response.json()['hits']['hits']
    
    print(f"\n📊 Тестируем на {len(hits)} документах...")
    
    # Подготавливаем тексты
    texts = []
    doc_ids = []
    for hit in hits:
        text = hit['_source'].get(text_field, '')
        if text:
            texts.append(text[:8000])
            doc_ids.append(hit['_id'])
            print(f"\nДокумент {hit['_id']}:")
            print(f"  Текст: {text[:100]}...")
    
    # Генерируем embeddings
    print(f"\n🔄 Генерация embeddings для {len(texts)} текстов...")
    embeddings = llm_service.generate_embeddings_batch(texts)
    
    if embeddings:
        print(f"✅ Сгенерировано {len(embeddings)} embeddings")
        print(f"   Размерность: {len(embeddings[0])}")
        print(f"   Первые 5 значений: {embeddings[0][:5]}")
        
        # Обновляем документы
        print(f"\n📤 Обновление документов в Elasticsearch...")
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
            print(f"✅ Документы обновлены!")
            
            # Проверяем что embeddings сохранились
            print(f"\n🔍 Проверка сохраненных embeddings...")
            for doc_id in doc_ids:
                get_url = f"{es_service.base_url}/{index_name}/_doc/{doc_id}"
                get_response = requests.get(get_url, headers=es_service.headers, timeout=10)
                doc = get_response.json()['_source']
                
                if embedding_field in doc:
                    print(f"  ✅ {doc_id}: embedding есть (dims: {len(doc[embedding_field])})")
                else:
                    print(f"  ❌ {doc_id}: embedding НЕТ")
        else:
            print(f"❌ Ошибка bulk update: {bulk_response.status_code}")
            print(bulk_response.text[:500])
    else:
        print("❌ Не удалось сгенерировать embeddings")

if __name__ == "__main__":
    test_embeddings()

