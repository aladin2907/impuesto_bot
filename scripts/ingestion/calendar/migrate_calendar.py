#!/usr/bin/env python3
"""
Скрипт миграции налогового календаря в Supabase

Загружает дедлайны из JSON файлов в таблицу calendar_deadlines
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.repositories.calendar_repository import CalendarRepository


def load_calendar_data(file_path: str) -> dict:
    """Загрузка данных календаря из JSON"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def transform_deadline(deadline: dict) -> dict:
    """
    Преобразование дедлайна в формат БД

    Входной формат (JSON):
    {
        "deadline_date": "2025-01-20",
        "year": 2025,
        "quarter": "Q4",
        "month": 1,
        "tax_type": "IVA",
        "tax_model": "Modelo 303",
        "description": "...",
        "applies_to": ["autonomos", "empresas"],
        "region": "national",
        "payment_required": true,
        "declaration_required": true,
        "penalty_for_late": "..."
    }
    """
    # Собираем только поля, которые есть в схеме БД
    record = {
        'deadline_date': deadline['deadline_date'],
        'year': deadline['year'],
        'quarter': deadline.get('quarter'),
        'month': deadline['month'],
        'tax_type': deadline['tax_type'],
        'tax_model': deadline['tax_model'],
        'description': deadline['description'],
        'applies_to': deadline['applies_to'],
        'region': deadline['region'],
        'payment_required': deadline.get('payment_required', False),
        'declaration_required': deadline.get('declaration_required', False),
    }

    # Опциональные поля (только если есть в данных)
    if 'penalty_for_late' in deadline and deadline['penalty_for_late']:
        record['penalty_for_late'] = deadline['penalty_for_late']

    return record


def migrate_calendar(data_dir: str = 'data'):
    """
    Миграция календаря в БД

    Args:
        data_dir: Директория с данными
    """
    print("="*70)
    print("📅 МИГРАЦИЯ НАЛОГОВОГО КАЛЕНДАРЯ")
    print("="*70)

    repo = CalendarRepository()

    # Проверяем текущее состояние БД
    existing_count = repo.count()
    print(f"\n📊 Текущее состояние БД:")
    print(f"  Записей в calendar_deadlines: {existing_count}")

    if existing_count > 0:
        response = input(f"\n⚠️  В БД уже есть {existing_count} записей. Удалить? (yes/no): ")
        if response.lower() == 'yes':
            print(f"\n🗑️  Удаление существующих записей...")
            deleted = repo.delete_all()
            print(f"  ✅ Удалено: {deleted} записей")
        else:
            print("  ⏭️  Пропускаем удаление, будет upsert")

    # Загружаем данные из файлов
    calendar_files = [
        f'{data_dir}/tax_calendar_2025.json',
        f'{data_dir}/tax_calendar_2026.json'
    ]

    all_deadlines = []

    for file_path in calendar_files:
        try:
            data = load_calendar_data(file_path)
            deadlines = data.get('deadlines', [])
            print(f"\n📥 {file_path}:")
            print(f"  Дедлайнов: {len(deadlines)}")
            all_deadlines.extend(deadlines)
        except FileNotFoundError:
            print(f"  ⚠️  Файл не найден: {file_path}")
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")

    if not all_deadlines:
        print("\n❌ Нет данных для миграции!")
        return

    print(f"\n{'='*70}")
    print(f"📊 ВСЕГО К ЗАГРУЗКЕ: {len(all_deadlines)} дедлайнов")
    print(f"{'='*70}")

    # Преобразуем данные
    transformed_deadlines = [transform_deadline(d) for d in all_deadlines]

    # Загружаем в БД
    print(f"\n⏳ Загрузка в Supabase...")
    inserted_count = repo.insert_many(transformed_deadlines, batch_size=50)

    print(f"\n{'='*70}")
    print(f"✅ МИГРАЦИЯ ЗАВЕРШЕНА")
    print(f"{'='*70}")
    print(f"  Загружено: {inserted_count} / {len(all_deadlines)} дедлайнов")

    # Проверка
    final_count = repo.count()
    print(f"  Итого в БД: {final_count} записей")

    # Примеры дедлайнов
    print(f"\n📋 Примеры дедлайнов:")
    examples = repo.select_all(limit=3)
    for deadline in examples:
        print(f"  • {deadline['deadline_date']} - {deadline['tax_model']} ({deadline['tax_type']})")


if __name__ == '__main__':
    import os
    os.chdir(project_root)
    migrate_calendar()
