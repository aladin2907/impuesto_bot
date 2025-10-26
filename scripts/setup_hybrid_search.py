#!/usr/bin/env python3
"""
Настройка гибридного поиска в Elasticsearch
Использует Inference API для автоматической генерации embeddings
"""

import os
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from elasticsearch import Elasticsearch
from app.config.settings import Settings

settings = Settings()

# Инициализация клиента
# API key format: "id:api_key" или можно передать кортеж
api_key_parts = settings.ELASTIC_API_KEY.split(':') if ':' in settings.ELASTIC_API_KEY else None
client = Elasticsearch(
    "https://36d0e937f1fd4309a2cb624f5f11bed1.us-central1.gcp.cloud.es.io:443",
    api_key=(api_key_parts[0], api_key_parts[1]) if api_key_parts else settings.ELASTIC_API_KEY,
    request_timeout=60  # Увеличиваем timeout для inference
)

# Inference model для embeddings (многоязычная модель)
INFERENCE_ID = ".multilingual-e5-small-elasticsearch"

# Индексы для обновления
INDICES = {
    "telegram_threads": {
        "text_field": "content",
        "embedding_field": "content_embedding"
    },
    "pdf_documents": {
        "text_field": "content",
        "embedding_field": "content_embedding"
    },
    "calendar_deadlines": {
        "text_field": "description",
        "embedding_field": "description_embedding"
    },
    "news_articles": {
        "text_field": "content",
        "embedding_field": "content_embedding"
    }
}


def add_inference_pipeline(index_name: str, text_field: str, embedding_field: str):
    """Создает inference pipeline для автоматической генерации embeddings"""
    
    pipeline_id = f"{index_name}_inference_pipeline"
    
    pipeline_config = {
        "description": f"Inference pipeline for {index_name}",
        "processors": [
            {
                "inference": {
                    "model_id": INFERENCE_ID,
                    "input_output": {
                        "input_field": text_field,
                        "output_field": embedding_field
                    }
                }
            }
        ]
    }
    
    try:
        # Удаляем старый pipeline если есть
        try:
            client.ingest.delete_pipeline(id=pipeline_id)
            print(f"  Удален старый pipeline: {pipeline_id}")
        except:
            pass
        
        # Создаем новый pipeline
        client.ingest.put_pipeline(id=pipeline_id, body=pipeline_config)
        print(f"✅ Создан pipeline: {pipeline_id}")
        return pipeline_id
        
    except Exception as e:
        print(f"❌ Ошибка создания pipeline: {e}")
        return None


def update_index_mapping(index_name: str, embedding_field: str):
    """Добавляет поле dense_vector в mapping индекса"""
    
    mapping = {
        "properties": {
            embedding_field: {
                "type": "dense_vector",
                "dims": 384,  # Размерность для multilingual-e5-small
                "index": True,
                "similarity": "cosine"
            }
        }
    }
    
    try:
        client.indices.put_mapping(index=index_name, body=mapping)
        print(f"✅ Обновлен mapping для {index_name}")
        return True
    except Exception as e:
        print(f"❌ Ошибка обновления mapping: {e}")
        return False


def configure_index_for_hybrid_search(index_name: str, text_field: str, embedding_field: str):
    """Настраивает индекс для гибридного поиска"""
    
    print(f"\n🔧 Настройка гибридного поиска для {index_name}...")
    
    # 1. Проверяем существование индекса
    if not client.indices.exists(index=index_name):
        print(f"⚠️  Индекс {index_name} не существует, пропускаем")
        return False
    
    # 2. Добавляем поле для embeddings
    if not update_index_mapping(index_name, embedding_field):
        return False
    
    # 3. Создаем inference pipeline
    pipeline_id = add_inference_pipeline(index_name, text_field, embedding_field)
    if not pipeline_id:
        return False
    
    # 4. Устанавливаем default pipeline для автоматической обработки новых документов
    try:
        client.indices.put_settings(
            index=index_name,
            body={
                "index": {
                    "default_pipeline": pipeline_id
                }
            }
        )
        print(f"✅ Установлен default pipeline для {index_name}")
    except Exception as e:
        print(f"❌ Ошибка установки default pipeline: {e}")
        return False
    
    print(f"✅ Гибридный поиск настроен для {index_name}")
    return True


def test_inference():
    """Тестируем inference для генерации embeddings"""
    print("\n🧪 Тестирование inference...")
    
    test_text = "IVA declaración trimestral modelo 303"
    
    try:
        result = client.inference.inference(
            inference_id=INFERENCE_ID,
            body={
                "input": test_text
            }
        )
        
        embedding = result['results'][0]['embedding']
        print(f"✅ Inference работает!")
        print(f"  Текст: {test_text}")
        print(f"  Размерность вектора: {len(embedding)}")
        print(f"  Первые 5 значений: {embedding[:5]}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка inference: {e}")
        return False


def main():
    print("=" * 60)
    print("🚀 НАСТРОЙКА ГИБРИДНОГО ПОИСКА В ELASTICSEARCH")
    print("=" * 60)
    
    # Проверка подключения
    try:
        info = client.info()
        print(f"\n✅ Подключен к Elasticsearch {info['version']['number']}")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return 1
    
    # Тестируем inference
    if not test_inference():
        print("\n❌ Inference не работает, прерываем настройку")
        return 1
    
    # Настраиваем каждый индекс
    print("\n" + "=" * 60)
    print("📦 НАСТРОЙКА ИНДЕКСОВ")
    print("=" * 60)
    
    success_count = 0
    for index_name, config in INDICES.items():
        if configure_index_for_hybrid_search(
            index_name=index_name,
            text_field=config["text_field"],
            embedding_field=config["embedding_field"]
        ):
            success_count += 1
    
    # Итоги
    print("\n" + "=" * 60)
    print(f"✅ ГОТОВО: {success_count}/{len(INDICES)} индексов настроены")
    print("=" * 60)
    
    print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
    print("1. Реиндексировать существующие документы для генерации embeddings:")
    print("   python scripts/reindex_with_embeddings.py")
    print("")
    print("2. Обновить search_service.py для использования гибридного поиска")
    print("")
    print("3. Новые документы будут автоматически получать embeddings при индексации")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

