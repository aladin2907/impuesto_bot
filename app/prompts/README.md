# 📝 Prompts - AI Tax Consultant

Эта папка содержит все промпты для AI налогового консультанта TuExpertoFiscal.

## 📂 Структура

```
app/prompts/
├── __init__.py                    # Экспорт всех промптов
├── README.md                      # Этот файл
│
├── base_system.py                 # Базовый системный промпт
│
├── tax_calendar.py                # Промпт для вопросов о сроках
├── tax_calculation.py             # Промпт для расчётов налогов
├── legal_interpretation.py        # Промпт для толкования законов
├── practical_advice.py            # Промпт для практических советов
├── news_update.py                 # Промпт для новостей
├── general_info.py                # Промпт для общих вопросов
│
├── classifier.py                  # Промпт для классификатора запросов
└── bot_messages.py                # Сообщения Telegram бота
```

## 🎯 Типы промптов

### 1. Базовый системный промпт
**Файл:** `base_system.py`
**Использование:** Применяется ко всем запросам как основа
**Содержит:**
- Роль агента (TuExpertoFiscal)
- Основные правила работы
- Мультиязычность
- Форматирование для Telegram

### 2. Специализированные промпты (QueryType)

Каждый тип запроса имеет свой промпт:

| Файл | QueryType | Назначение |
|------|-----------|------------|
| `tax_calendar.py` | TAX_CALENDAR | Вопросы о сроках и дедлайнах |
| `tax_calculation.py` | TAX_CALCULATION | Расчёты налогов |
| `legal_interpretation.py` | LEGAL_INTERPRETATION | Толкование законов |
| `practical_advice.py` | PRACTICAL_ADVICE | Практические советы |
| `news_update.py` | NEWS_UPDATE | Новости и обновления |
| `general_info.py` | GENERAL_INFO | Общая информация |

### 3. Промпт классификатора
**Файл:** `classifier.py`
**Использование:** QueryClassifier определяет тип запроса
**Содержит:**
- Описание 6 категорий запросов
- Примеры для каждой категории
- Правила классификации

### 4. Сообщения бота
**Файл:** `bot_messages.py`
**Использование:** Статические сообщения Telegram бота
**Содержит:**
- `START_MESSAGE` - приветствие (/start)
- `HELP_MESSAGE` - помощь (/help)
- `ABOUT_MESSAGE` - о боте (/about)
- `CALENDAR_INTRO_MESSAGE` - введение для календаря
- `LOW_CONFIDENCE_WARNING_ES` - предупреждение на испанском
- `LOW_CONFIDENCE_WARNING_RU` - предупреждение на русском

## 🔧 Как использовать

### Импорт промптов

```python
from app.prompts import (
    BASE_SYSTEM_PROMPT,
    TAX_CALENDAR_PROMPT,
    CLASSIFICATION_SYSTEM_PROMPT,
    START_MESSAGE
)
```

### Пример использования в коде

```python
# В ResponseGenerator
from app.prompts import BASE_SYSTEM_PROMPT, TAX_CALENDAR_PROMPT

system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n{TAX_CALENDAR_PROMPT}"
```

```python
# В Telegram боте
from app.prompts import START_MESSAGE

await message.answer(START_MESSAGE, parse_mode=ParseMode.MARKDOWN)
```

## ✏️ Редактирование промптов

### Правила редактирования:

1. **Мультиязычность** - все промпты должны поддерживать ES/RU/EN/UK
2. **Markdown** - использовать только простой Markdown для Telegram (`*`, `_`, <code>`</code>)
3. **Структура** - сохранять формат и структуру промпта
4. **Тестирование** - после изменений тестировать на разных языках

### Где что редактировать:

| Что изменить | Где |
|--------------|-----|
| Роль агента | `base_system.py` |
| Инструкции для расчётов | `tax_calculation.py` |
| Примеры классификации | `classifier.py` |
| Текст приветствия | `bot_messages.py` |

## 🔄 Версионирование

При значительных изменениях промптов:

1. Создать копию старой версии с датой
2. Обновить промпт
3. Протестировать
4. Задокументировать изменения

Пример:
```
tax_calendar.py             # Текущая версия
tax_calendar_2026_01.py     # Версия от января 2026
```

## 📊 Метрики эффективности

После изменения промптов отслеживать:
- Точность классификации
- Качество ответов (user feedback)
- Среднее время ответа
- Confidence score

## 🚀 Best Practices

1. **Краткость** - промпты должны быть лаконичными
2. **Конкретность** - четкие инструкции
3. **Примеры** - давать примеры где возможно
4. **Язык** - использовать язык, понятный LLM
5. **Тестирование** - тестировать на edge cases

## 📝 TODO

- [ ] Добавить промпты для новых QueryType (если появятся)
- [ ] A/B тестирование разных версий промптов
- [ ] Метрики эффективности промптов
- [ ] Промпты для error handling

---

**Создано:** Февраль 2026
**Обновлено:** {{ дата последнего обновления }}
