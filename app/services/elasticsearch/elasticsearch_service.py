#!/usr/bin/env python3
"""
Elasticsearch сервис через requests (обход проблемы с официальным клиентом)
"""

import requests
import json
import base64
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Добавляем корневую папку в путь
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import Settings


class ElasticsearchService:
    """Сервис для работы с Elasticsearch через HTTP API"""
    
    def __init__(self):
        self.settings = Settings()
        # Derive base_url from ELASTIC_CLOUD_ID
        self.base_url = self._derive_base_url(self.settings.ELASTIC_CLOUD_ID)
        # Compute Base64 for ApiKey header from id:key in .env
        raw_api_key = (self.settings.ELASTIC_API_KEY or "").strip()
        self.api_key_b64 = base64.b64encode(raw_api_key.encode()).decode() if raw_api_key else ""
        self.headers = {
            "Authorization": f"ApiKey {self.api_key_b64}",
            "Content-Type": "application/json"
        }

    def _derive_base_url(self, cloud_id: str) -> str:
        try:
            if not cloud_id or ":" not in cloud_id:
                raise ValueError("Invalid ELASTIC_CLOUD_ID")
            _, b64 = cloud_id.split(":", 1)
            decoded = base64.b64decode(b64).decode()
            # Format: host$es_id$kibana_id
            parts = decoded.split("$")
            host = parts[0]
            es_id = parts[1]
            return f"https://{es_id}.{host}"
        except Exception:
            # Fallback to known URL if derivation fails
            return "https://36d0e937f1fd4309a2cb624f5f11bed1.us-central1.gcp.cloud.es.io:443"
    
    def ping(self) -> bool:
        """Проверка подключения"""
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            print(f"Ping response: {response.status_code}")
            if response.status_code != 200:
                print(f"Ping error: {response.text[:200]}")
            return response.status_code == 200
        except Exception as e:
            print(f"Ping exception: {e}")
            return False
    
    def info(self) -> Dict[str, Any]:
        """Получение информации о кластере"""
        response = requests.get(self.base_url, headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def index_exists(self, index_name: str) -> bool:
        """Проверка существования индекса"""
        try:
            url = f"{self.base_url}/{index_name}"
            response = requests.head(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def create_index(self, index_name: str, mapping: Dict[str, Any]) -> bool:
        """Создание индекса"""
        try:
            url = f"{self.base_url}/{index_name}"
            response = requests.put(url, headers=self.headers, json=mapping, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Индекс {index_name} создан")
                return True
            elif response.status_code == 400 and "already_exists_exception" in response.text:
                print(f"⚠️  Индекс {index_name} уже существует")
                return True
            else:
                print(f"❌ Ошибка создания индекса {index_name}: {response.status_code}")
                print(f"   {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка создания индекса {index_name}: {e}")
            return False
    
    def index_document(self, index_name: str, doc_id: str, document: Dict[str, Any]) -> bool:
        """Индексация документа"""
        try:
            url = f"{self.base_url}/{index_name}/_doc/{doc_id}"
            response = requests.put(url, headers=self.headers, json=document, timeout=30)
            
            if response.status_code in [200, 201]:
                return True
            else:
                print(f"❌ Ошибка индексации документа {doc_id}: {response.status_code}")
                print(f"   {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка индексации документа {doc_id}: {e}")
            return False
    
    def bulk_index(self, index_name: str, documents: List[Dict[str, Any]]) -> bool:
        """Массовая индексация документов"""
        try:
            url = f"{self.base_url}/_bulk"
            
            # Формируем bulk запрос
            bulk_data = []
            for doc in documents:
                # Метаданные для индексации
                bulk_data.append({
                    "index": {
                        "_index": index_name,
                        "_id": doc.get("_id", doc.get("id"))
                    }
                })
                # Сам документ (убираем _id если есть)
                doc_copy = doc.copy()
                doc_copy.pop("_id", None)
                doc_copy.pop("id", None)
                bulk_data.append(doc_copy)
            
            # Конвертируем в NDJSON формат
            ndjson_lines = []
            for item in bulk_data:
                ndjson_lines.append(json.dumps(item))
            
            ndjson_data = "\n".join(ndjson_lines) + "\n"
            
            headers = self.headers.copy()
            headers["Content-Type"] = "application/x-ndjson"
            response = requests.post(
                url,
                headers=headers,
                data=ndjson_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("errors"):
                    print(f"⚠️  Некоторые документы не индексированы: {result['errors']}")
                else:
                    print(f"✅ Успешно проиндексировано {len(documents)} документов")
                return True
            else:
                print(f"❌ Ошибка bulk индексации: {response.status_code}")
                print(f"   {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка bulk индексации: {e}")
            return False
    
    def search(self, index_name: str, query: Dict[str, Any], size: int = 10) -> List[Dict[str, Any]]:
        """Поиск по индексу"""
        try:
            url = f"{self.base_url}/{index_name}/_search"
            
            search_body = {
                "query": query,
                "size": size
            }
            
            response = requests.post(url, headers=self.headers, json=search_body, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            hits = result.get("hits", {}).get("hits", [])
            results: List[Dict[str, Any]] = []
            for hit in hits:
                source = hit.get("_source", {})
                out = {
                    "_id": hit.get("_id"),
                    "_score": hit.get("_score"),
                }
                out.update(source)
                results.append(out)
            return results
            
        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
            return []
    
    def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Получение статистики индекса"""
        try:
            url = f"{self.base_url}/{index_name}/_stats"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return {}
    
    def list_indices(self) -> List[str]:
        """Список всех индексов"""
        try:
            url = f"{self.base_url}/_cat/indices?format=json"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            indices = response.json()
            return [idx["index"] for idx in indices if not idx["index"].startswith(".")]
            
        except Exception as e:
            print(f"❌ Ошибка получения списка индексов: {e}")
            return []


def main():
    """Тест сервиса"""
    print("🔍 Тест ElasticsearchService")
    print("=" * 50)
    
    es = ElasticsearchService()
    
    # Проверка подключения
    if es.ping():
        print("✅ Подключение успешно!")
        
        # Информация о кластере
        info = es.info()
        print(f"Версия: {info['version']['number']}")
        print(f"Кластер: {info['cluster_name']}")
        
        # Список индексов
        indices = es.list_indices()
        print(f"Индексы: {indices}")
        
    else:
        print("❌ Не удалось подключиться")


if __name__ == "__main__":
    main()
