# 💳 Subscription System - TuExpertoFiscal

## Модель подписки

| План | Лимит | Цена | Функции |
|------|-------|------|---------|
| **Free** | 10 сообщений/день | €0 | Базовые инструменты (calendar, calculator) |
| **Premium** | Безлимит | €9.99/мес | Все функции + поиск в документах + приоритетная поддержка |

## Настройка Stripe

### 1. Создай аккаунт Stripe

1. Зарегистрируйся на [stripe.com](https://stripe.com)
2. Подтверди аккаунт

### 2. Получи API ключи

1. Иди в [Dashboard → API Keys](https://dashboard.stripe.com/apikeys)
2. Скопируй:
   - `Publishable key` → `STRIPE_PUBLISHABLE_KEY`
   - `Secret key` → `STRIPE_SECRET_KEY`

### 3. Создай продукт и цены

1. Иди в [Products](https://dashboard.stripe.com/products)
2. Создай продукт:
   - Название: `TuExpertoFiscal Premium`
   - Описание: `Acceso ilimitado al asesor fiscal inteligente`

3. Добавь цены:
   - **Monthly**: €9.99 / month, recurring
   - **Yearly**: €99.99 / year, recurring

4. Скопируй Price IDs:
   - `price_xxx...` → `STRIPE_PRICE_PREMIUM_MONTHLY`
   - `price_yyy...` → `STRIPE_PRICE_PREMIUM_YEARLY`

### 4. Настрой Webhook

1. Иди в [Webhooks](https://dashboard.stripe.com/webhooks)
2. Создай endpoint:
   - URL: `https://your-domain.com/api/stripe/webhook`
   - Events:
     - `checkout.session.completed`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`

3. Скопируй `Signing secret` → `STRIPE_WEBHOOK_SECRET`

### 5. Обнови .env

```env
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PREMIUM_MONTHLY=price_...
STRIPE_PRICE_PREMIUM_YEARLY=price_...
```

## База данных

Выполни миграцию в Supabase SQL Editor:

```bash
# Файл: database/migrations/003_subscriptions_and_limits.sql
```

Это создаст:
- `subscription_plans` - тарифные планы
- `user_subscriptions` - подписки пользователей
- `usage_daily` - отслеживание использования
- `payment_history` - история платежей
- Функции: `get_user_plan`, `can_send_message`, `increment_message_count`

## Telegram команды

| Команда | Описание |
|---------|----------|
| `/subscribe` | Оформить/управлять подпиской |
| `/status` | Проверить статус и лимиты |

## Как это работает

### 1. Проверка лимитов

```python
# В каждом сообщении:
can_send, plan = await subscription_service.can_send_message(telegram_id)
if not can_send:
    # Показываем сообщение о лимите
```

### 2. Оформление подписки

```
Пользователь → /subscribe → Stripe Checkout → Оплата → Webhook → База обновлена
```

### 3. Flow подписки

```
Free User                    Premium User
    │                            │
    ├─ 10 msg/day limit          ├─ Unlimited
    │                            │
    ├─ /subscribe                ├─ /subscribe
    │      │                     │      │
    │      ▼                     │      ▼
    │  Stripe Checkout           │  Stripe Portal
    │      │                     │  (управление)
    │      ▼                     │
    │  Payment Success           │
    │      │                     │
    └──────┴─────────────────────┘
           │
           ▼
    Webhook → update_subscription_from_stripe()
           │
           ▼
    user_subscriptions updated
```

## API Endpoints (FastAPI)

Если нужен webhook endpoint:

```python
# app/api/stripe_webhook.py
from fastapi import APIRouter, Request, HTTPException
from app.services.subscription_service import SubscriptionService

router = APIRouter()
subscription_service = SubscriptionService()

@router.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    success = await subscription_service.handle_webhook(payload, sig_header)

    if not success:
        raise HTTPException(status_code=400, detail="Webhook failed")

    return {"status": "ok"}
```

## Тестирование

### Тестовые карты Stripe

| Номер | Описание |
|-------|----------|
| 4242 4242 4242 4242 | Успешная оплата |
| 4000 0000 0000 0002 | Отклонена |
| 4000 0000 0000 3220 | Требует 3D Secure |

### Тест в боте

1. Отправь 10+ сообщений (достигни лимита)
2. Получи предложение о подписке
3. Используй `/subscribe`
4. Оплати тестовой картой
5. Проверь `/status` - должен быть Premium

## Мониторинг

### Логи

```bash
# Проверить использование
SELECT * FROM usage_daily WHERE usage_date = CURRENT_DATE;

# Проверить подписки
SELECT u.telegram_id, sp.name, us.status, us.current_period_end
FROM user_subscriptions us
JOIN users u ON us.user_id = u.id
JOIN subscription_plans sp ON us.plan_id = sp.id;
```

### Метрики

- Конверсия Free → Premium
- Churn rate
- MRR (Monthly Recurring Revenue)
- Использование лимитов

## Troubleshooting

### "Stripe not initialized"

Проверь `STRIPE_SECRET_KEY` в .env

### "Webhook failed"

1. Проверь `STRIPE_WEBHOOK_SECRET`
2. Проверь что URL доступен извне
3. Проверь логи Stripe Dashboard

### "Subscription not updated"

1. Проверь webhook events в Stripe Dashboard
2. Проверь логи сервера
3. Проверь функцию `update_subscription_from_stripe` в Supabase

---

**Вопросы?** Проверь [Stripe Docs](https://stripe.com/docs) или логи сервера.
