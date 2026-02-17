#!/usr/bin/env python3
"""
Скрипт миграции Telegram тредов в Supabase

Применяет фильтрацию согласно TELEGRAM_FILTERING_STRATEGY.md:
- IT Autonomos: все треды с ≥2 сообщениями
- Nomads: последний год + ≥2 сообщений + налоговые темы
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.repositories.telegram_repository import TelegramRepository
from app.services.embeddings.huggingface_embeddings import HuggingFaceEmbeddings


# Keywords для фильтрации Nomads
TAX_KEYWORDS = [
    # Налоги
    'autonomo', 'autónomo', 'impuesto', 'iva', 'irpf', 'hacienda', 'gestor',
    'factura', 'modelo', 'declaracion', 'declaración', 'renta', 'fiscal', 'aeat',
    # Номад специфика
    'nomad', 'visa', 'tie', 'empadronamiento', 'residencia',
    'seguridad social', 'cotizacion', 'cotización', 'freelance',
    # Дополнительные
    'счет', 'банк', 'bank', 'cuenta', 'страховка', 'seguro', 'налог',
    'номада', 'прописка', 'ние'
]


def load_telegram_data(file_path: str) -> dict:
    """Загрузка данных из JSON"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def filter_it_autonomos(threads: List[Dict]) -> List[Dict]:
    """
    Фильтрация IT Autonomos: только треды с ≥2 сообщениями

    Args:
        threads: Список всех тредов

    Returns:
        Отфильтрованные треды
    """
    return [t for t in threads if t['message_count'] >= 2]


def filter_nomads(threads: List[Dict]) -> List[Dict]:
    """
    Фильтрация Nomads:
    - Последний год (2024-10-01 → 2025-10-31)
    - ≥2 сообщения
    - Налоговые/номад темы

    Args:
        threads: Список всех тредов

    Returns:
        Отфильтрованные треды
    """
    start_date = datetime(2024, 10, 1, tzinfo=timezone.utc)
    end_date = datetime(2025, 10, 31, tzinfo=timezone.utc)

    filtered = []

    for thread in threads:
        try:
            # Фильтр по дате
            thread_date = datetime.fromisoformat(thread['first_message_date'].replace('Z', '+00:00'))
            if not (start_date <= thread_date <= end_date):
                continue

            # Фильтр по количеству сообщений
            if thread['message_count'] < 2:
                continue

            # Фильтр по keywords
            content_text = ' '.join([msg.get('text', '').lower() for msg in thread.get('messages', [])])
            has_keywords = any(keyword.lower() in content_text for keyword in TAX_KEYWORDS)

            if has_keywords:
                filtered.append(thread)

        except Exception as e:
            print(f"⚠️ Ошибка при фильтрации треда {thread.get('thread_id')}: {e}")
            continue

    return filtered


def extract_content(thread: Dict) -> str:
    """
    Извлечение текстового контента из треда

    Args:
        thread: Данные треда

    Returns:
        Объединенный текст всех сообщений
    """
    messages = thread.get('messages', [])
    texts = [msg.get('text', '') for msg in messages if msg.get('text')]
    return '\n\n'.join(texts)


def calculate_quality_score(thread: Dict, content: str) -> float:
    """
    Расчет качества треда

    Args:
        thread: Данные треда
        content: Текстовый контент

    Returns:
        Оценка качества (0.0 - 1.0)
    """
    # Простая формула: длина × количество сообщений
    base_score = len(content) * thread['message_count'] * 0.001
    return min(base_score, 1.0)


def transform_thread(thread: Dict, group_name: str, embedding: List[float]) -> Dict[str, Any]:
    """
    Преобразование треда в формат БД

    Args:
        thread: Исходные данные треда
        group_name: Название группы
        embedding: Вектор embedding

    Returns:
        Запись для БД
    """
    content = extract_content(thread)
    quality_score = calculate_quality_score(thread, content)

    return {
        'thread_id': thread['thread_id'],
        'group_name': group_name,
        'content': content,
        'content_embedding': embedding,
        'message_count': thread['message_count'],
        'first_message_date': thread['first_message_date'],
        'last_updated': thread['last_updated'],
        'quality_score': quality_score,
        # Опциональные поля можно добавить позже
        # 'topics': None,
        # 'keywords': None,
    }


def migrate_telegram(data_dir: str = 'data'):
    """
    Миграция Telegram тредов в БД

    Args:
        data_dir: Директория с данными
    """
    print("="*70)
    print("📱 МИГРАЦИЯ TELEGRAM ТРЕДОВ")
    print("="*70)

    repo = TelegramRepository()
    embeddings_gen = HuggingFaceEmbeddings()

    # Проверяем текущее состояние БД
    existing_count = repo.count()
    print(f"\n📊 Текущее состояние БД:")
    print(f"  Записей в telegram_threads_content: {existing_count}")

    if existing_count > 0:
        response = input(f"\n⚠️  В БД уже есть {existing_count} записей. Удалить? (yes/no): ")
        if response.lower() == 'yes':
            print(f"\n🗑️  Удаление существующих записей...")
            deleted = repo.delete_all()
            print(f"  ✅ Удалено: {deleted} записей")
        else:
            print("  ⏭️  Пропускаем удаление")

    # Загружаем и фильтруем данные
    print(f"\n{'='*70}")
    print("📥 ЗАГРУЗКА И ФИЛЬТРАЦИЯ ДАННЫХ")
    print(f"{'='*70}")

    all_threads = []

    # IT Autonomos
    it_file = f'{data_dir}/telegram_threads/it_threads.json'
    print(f"\n🔹 IT Autonomos Spain:")
    try:
        it_data = load_telegram_data(it_file)
        it_filtered = filter_it_autonomos(it_data['threads'])
        print(f"  Всего: {len(it_data['threads']):,} тредов")
        print(f"  После фильтрации (≥2 msg): {len(it_filtered):,} тредов")
        all_threads.extend([(t, 'it_autonomos_spain') for t in it_filtered])
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")

    # Nomads
    nomads_file = f'{data_dir}/telegram_threads/nomads_threads.json'
    print(f"\n🔹 Chat for Nomads:")
    try:
        nomads_data = load_telegram_data(nomads_file)
        nomads_filtered = filter_nomads(nomads_data['threads'])
        print(f"  Всего: {len(nomads_data['threads']):,} тредов")
        print(f"  После фильтрации: {len(nomads_filtered):,} тредов")
        all_threads.extend([(t, 'chat_for_nomads') for t in nomads_filtered])
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")

    if not all_threads:
        print("\n❌ Нет данных для миграции!")
        return

    print(f"\n{'='*70}")
    print(f"📊 ВСЕГО К ЗАГРУЗКЕ: {len(all_threads):,} тредов")
    print(f"{'='*70}")

    # Генерация embeddings
    print(f"\n⏳ Генерация embeddings...")
    print(f"  (Используем локальную модель multilingual-e5-large)")

    contents = [extract_content(t[0]) for t in all_threads]

    # Батч-генерация (намного быстрее!)
    embeddings = embeddings_gen.generate_batch(
        contents,
        prefix="passage: ",  # для документов в базе
        batch_size=32,
        show_progress=True
    )

    print(f"\n✅ Embeddings сгенерированы!")

    # Преобразование данных
    print(f"\n⏳ Подготовка данных для загрузки...")
    transformed_threads = []

    for (thread, group_name), embedding in zip(all_threads, embeddings):
        if embedding is None:
            print(f"  ⚠️ Пропускаем тред {thread['thread_id']} (нет embedding)")
            continue

        try:
            record = transform_thread(thread, group_name, embedding)
            transformed_threads.append(record)
        except Exception as e:
            print(f"  ⚠️ Ошибка при преобразовании треда {thread['thread_id']}: {e}")

    print(f"  ✅ Подготовлено: {len(transformed_threads)} записей")

    # Загрузка в БД
    print(f"\n⏳ Загрузка в Supabase...")
    inserted_count = repo.insert_many(transformed_threads, batch_size=100)

    print(f"\n{'='*70}")
    print(f"✅ МИГРАЦИЯ ЗАВЕРШЕНА")
    print(f"{'='*70}")
    print(f"  Загружено: {inserted_count} / {len(transformed_threads)} тредов")

    # Проверка
    final_count = repo.count()
    print(f"  Итого в БД: {final_count} записей")

    # Статистика по группам
    print(f"\n📊 Статистика по группам:")
    it_count = len([t for t in repo.get_by_group('it_autonomos_spain', limit=10000)])
    nomads_count = len([t for t in repo.get_by_group('chat_for_nomads', limit=10000)])
    print(f"  IT Autonomos: {it_count:,} тредов")
    print(f"  Nomads: {nomads_count:,} тредов")


if __name__ == '__main__':
    import os
    os.chdir(project_root)
    migrate_telegram()
