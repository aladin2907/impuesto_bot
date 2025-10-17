#!/usr/bin/env python3
"""
Демонстрация структуры данных для индексации Telegram тредов
Показывает как будут выглядеть документы в Elasticsearch
"""

import json
import re
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path


class TelegramDataAnalyzer:
    def __init__(self):
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

    def analyze_file(self, file_path: str, sample_size: int = 10):
        """Анализирует файл и показывает примеры структуры"""
        print(f"📁 Анализируем файл: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and 'threads' in data:
            threads = data['threads']
            group_name = data.get('group_title', 'Unknown Group')
        else:
            threads = data
            group_name = Path(file_path).stem
        
        print(f"📊 Всего тредов: {len(threads)}")
        print(f"🏷️ Группа: {group_name}")
        
        # Анализируем примеры
        analyzer = TelegramDataAnalyzer()
        
        # Берём треды с разным количеством сообщений
        sample_threads = []
        
        # Одиночные сообщения
        single_threads = [t for t in threads if t['message_count'] == 1][:2]
        sample_threads.extend(single_threads)
        
        # Средние треды
        medium_threads = [t for t in threads if 2 <= t['message_count'] <= 5][:3]
        sample_threads.extend(medium_threads)
        
        # Длинные треды
        long_threads = [t for t in threads if t['message_count'] > 10][:2]
        sample_threads.extend(long_threads)
        
        print(f"\n🔍 Анализируем {len(sample_threads)} примеров тредов:")
        
        for i, thread in enumerate(sample_threads):
            print(f"\n{'='*60}")
            print(f"ТРЕД #{i+1} (ID: {thread['thread_id']})")
            print(f"{'='*60}")
            
            # Подготавливаем для индексации
            indexed_thread = analyzer.prepare_thread_for_indexing(thread, group_name)
            
            print(f"📊 Сообщений: {indexed_thread['message_count']}")
            print(f"📅 Дата: {indexed_thread['first_message_date']}")
            print(f"🏷️ Темы: {indexed_thread['topics']}")
            print(f"🔑 Ключевые слова: {indexed_thread['keywords']}")
            print(f"⭐ Качество: {indexed_thread['quality_score']:.1f}/5.0")
            print(f"💰 Налоговая тема: {indexed_thread['tax_related']}")
            print(f"🛂 Визовая тема: {indexed_thread['visa_related']}")
            print(f"💼 Бизнес тема: {indexed_thread['business_related']}")
            
            print(f"\n📝 Первое сообщение:")
            print(f"   {indexed_thread['first_message'][:150]}...")
            
            if indexed_thread['message_count'] > 1:
                print(f"\n📝 Последнее сообщение:")
                print(f"   {indexed_thread['last_message'][:150]}...")
            
            print(f"\n📄 Полный контент (первые 200 символов):")
            print(f"   {indexed_thread['content'][:200]}...")
        
        # Статистика по всем тредам
        print(f"\n{'='*60}")
        print("СТАТИСТИКА ПО ВСЕМ ТРЕДАМ")
        print(f"{'='*60}")
        
        all_keywords = []
        topic_counts = {'tax': 0, 'visa': 0, 'business': 0}
        quality_scores = []
        
        for thread in threads[:1000]:  # Анализируем первые 1000
            indexed_thread = analyzer.prepare_thread_for_indexing(thread, group_name)
            
            all_keywords.extend(indexed_thread['keywords'])
            
            for topic in indexed_thread['topics']:
                if topic in topic_counts:
                    topic_counts[topic] += 1
            
            quality_scores.append(indexed_thread['quality_score'])
        
        # Топ ключевых слов
        from collections import Counter
        keyword_counts = Counter(all_keywords)
        
        print(f"\n🔑 Топ ключевых слов:")
        for keyword, count in keyword_counts.most_common(10):
            print(f"   {keyword}: {count}")
        
        print(f"\n🏷️ Распределение по темам:")
        for topic, count in topic_counts.items():
            print(f"   {topic}: {count}")
        
        print(f"\n⭐ Статистика качества:")
        print(f"   Среднее: {sum(quality_scores)/len(quality_scores):.2f}")
        print(f"   Максимум: {max(quality_scores):.2f}")
        print(f"   Минимум: {min(quality_scores):.2f}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Анализ структуры Telegram тредов')
    parser.add_argument('file', help='Путь к JSON файлу с тредами')
    parser.add_argument('--sample-size', type=int, default=10, help='Количество примеров для анализа')
    
    args = parser.parse_args()
    
    analyzer = TelegramDataAnalyzer()
    analyzer.analyze_file(args.file, args.sample_size)


if __name__ == "__main__":
    main()

