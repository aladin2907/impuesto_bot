# Анализ структуры данных Telegram групп для оптимального поиска

## Обзор собранных данных

### IT Autonomos [Spain]
- **Сообщений**: 18,852
- **Тредов**: 6,195
- **Средняя длина треда**: 3.0 сообщения
- **Распределение**: 47% одиночных сообщений, 17% из 2 сообщений

### Digital Nomad Spain
- **Сообщений**: 165,004
- **Тредов**: 69,719
- **Средняя длина треда**: 2.4 сообщения
- **Распределение**: 62% одиночных сообщений, 14% из 2 сообщений

## Тематический анализ

### Топ ключевые слова (IT Autonomos):
1. **налог** (363) - налоговая тематика
2. **автономо** (143) - автономная деятельность
3. **ss** (93) - социальное страхование
4. **контракт** (85) - договорные отношения
5. **номад** (78) - цифровые кочевники
6. **клиент** (74) - клиентские отношения
7. **nie** (44) - идентификационный номер
8. **iva** (36) - НДС
9. **паспорт** (33) - документооборот
10. **фактура** (32) - выставление счетов

## Рекомендуемая структура для Elasticsearch

### 1. Основной индекс: `telegram_threads`

```json
{
  "mappings": {
    "properties": {
      "thread_id": {"type": "keyword"},
      "group_name": {"type": "keyword"},
      "group_type": {"type": "keyword"}, // "it_autonomos", "nomads"
      "first_message_date": {"type": "date"},
      "last_updated": {"type": "date"},
      "message_count": {"type": "integer"},
      "max_depth": {"type": "integer"},
      
      // Основной контент для поиска
      "content": {
        "type": "text",
        "analyzer": "standard",
        "fields": {
          "keyword": {"type": "keyword"},
          "suggest": {"type": "completion"}
        }
      },
      
      // Структурированные поля
      "first_message": {"type": "text"},
      "last_message": {"type": "text"},
      "all_messages": {"type": "text"},
      
      // Тематические теги
      "topics": {
        "type": "keyword",
        "fields": {
          "text": {"type": "text"}
        }
      },
      
      // Ключевые слова для фильтрации
      "keywords": {"type": "keyword"},
      "tax_related": {"type": "boolean"},
      "visa_related": {"type": "boolean"},
      "business_related": {"type": "boolean"},
      
      // Временные метки
      "year": {"type": "integer"},
      "month": {"type": "integer"},
      "quarter": {"type": "keyword"},
      
      // Релевантность для RAG
      "relevance_score": {"type": "float"},
      "quality_score": {"type": "float"}
    }
  }
}
```

### 2. Дополнительный индекс: `telegram_messages`

```json
{
  "mappings": {
    "properties": {
      "message_id": {"type": "keyword"},
      "thread_id": {"type": "keyword"},
      "group_name": {"type": "keyword"},
      "date": {"type": "date"},
      "sender_id": {"type": "keyword"},
      "text": {"type": "text"},
      "depth": {"type": "integer"},
      "is_question": {"type": "boolean"},
      "is_answer": {"type": "boolean"},
      "contains_links": {"type": "boolean"},
      "language": {"type": "keyword"}
    }
  }
}
```

## Стратегия индексации

### 1. Подготовка контента

```python
def prepare_thread_for_indexing(thread):
    # Объединяем все сообщения в один текст
    all_texts = [msg['text'] for msg in thread['messages'] if msg['text']]
    content = ' '.join(all_texts)
    
    # Извлекаем ключевые слова
    keywords = extract_keywords(content)
    
    # Определяем тематику
    topics = categorize_topics(keywords)
    
    return {
        'thread_id': thread['thread_id'],
        'group_name': thread['group_name'],
        'content': content,
        'first_message': thread['messages'][0]['text'] if thread['messages'] else '',
        'last_message': thread['messages'][-1]['text'] if thread['messages'] else '',
        'topics': topics,
        'keywords': keywords,
        'tax_related': any(k in ['автономо', 'irpf', 'iva', 'ss', 'налог'] for k in keywords),
        'visa_related': any(k in ['visa', 'виза', 'nomad', 'номад', 'residencia'] for k in keywords),
        'business_related': any(k in ['контракт', 'клиент', 'компания', 'фактура'] for k in keywords),
        'message_count': thread['message_count'],
        'first_message_date': thread['first_message_date'],
        'last_updated': thread['last_updated']
    }
```

### 2. Стратегия поиска

#### A. Семантический поиск (векторный)
- Используем embeddings для понимания смысла
- Ищем похожие по смыслу треды
- Хорошо работает для сложных вопросов

#### B. Ключевой поиск (BM25)
- Поиск по конкретным терминам
- Фильтрация по тематикам
- Быстрый поиск по ключевым словам

#### C. Гибридный поиск
- Комбинируем семантический + BM25
- Взвешиваем результаты
- Максимальная точность

### 3. Оптимизация для RAG

```python
def search_relevant_threads(query, filters=None):
    # 1. Предварительная фильтрация по тематике
    if filters:
        base_query = {
            "bool": {
                "must": [{"match": {"content": query}}],
                "filter": filters
            }
        }
    else:
        base_query = {"match": {"content": query}}
    
    # 2. Гибридный поиск
    search_body = {
        "query": {
            "bool": {
                "should": [
                    # Семантический поиск
                    {
                        "knn": {
                            "field": "content_embedding",
                            "query_vector": generate_embedding(query),
                            "k": 10,
                            "num_candidates": 100
                        }
                    },
                    # BM25 поиск
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["content^2", "first_message^1.5", "last_message^1.5"],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    }
                ]
            }
        },
        "size": 20,
        "_source": ["thread_id", "content", "topics", "first_message_date", "group_name"]
    }
    
    return es.search(index="telegram_threads", body=search_body)
```

## Рекомендации по реализации

### 1. Приоритеты индексации
1. **Длинные треды** (>5 сообщений) - больше контекста
2. **Треды с вопросами** - содержат конкретные проблемы
3. **Недавние треды** - актуальная информация
4. **Треды с ключевыми словами** - релевантные темы

### 2. Фильтрация качества
- Исключать спам и рекламу
- Приоритизировать треды с ответами
- Учитывать рейтинг участников

### 3. Обновление данных
- Еженедельное обновление новых сообщений
- Переиндексация при изменении структуры
- Мониторинг качества поиска

### 4. Метрики качества
- Precision@10 для релевантности
- Время ответа поиска
- Покрытие тематик
- Пользовательская обратная связь

## Следующие шаги

1. **Создать скрипт индексации** - `scripts/ingestion/index_telegram_threads.py`
2. **Настроить Elasticsearch mapping** - создать индексы с правильной структурой
3. **Реализовать поиск** - интегрировать в RAG pipeline
4. **Тестировать качество** - проверить релевантность результатов
5. **Оптимизировать** - настроить веса и фильтры

---

*Разработано NAIL - Nahornyi AI Lab*

