-- ============================================================
-- Subscription & Usage Limits System
-- ============================================================
-- Модель: 3 тарифа
-- Free: 5 запросов/день, 10/неделю (попробовать, но не хватит)
-- Basic €2.99: 25 запросов/день (обычный пользователь)
-- Pro €9.99: безлимит + все функции (power user)
-- ============================================================

-- 1. Subscription Plans - тарифные планы
CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,              -- 'free', 'basic', 'pro'
    display_name TEXT NOT NULL,             -- 'Free', 'Basic', 'Pro'
    description TEXT,
    price_monthly DECIMAL(10,2) DEFAULT 0,  -- Цена в евро
    price_yearly DECIMAL(10,2) DEFAULT 0,   -- Годовая цена (скидка)
    stripe_price_id_monthly TEXT,           -- Stripe Price ID для месячной подписки
    stripe_price_id_yearly TEXT,            -- Stripe Price ID для годовой подписки
    daily_message_limit INTEGER DEFAULT 5,  -- Лимит сообщений в день (NULL = безлимит)
    weekly_message_limit INTEGER,           -- Лимит сообщений в неделю (NULL = безлимит)
    features JSONB DEFAULT '{}',            -- Дополнительные фичи
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Вставляем 3 тарифных плана
INSERT INTO subscription_plans (name, display_name, description, price_monthly, price_yearly, daily_message_limit, weekly_message_limit, features)
VALUES
    ('free', 'Free', 'Plan gratuito - prueba el bot', 0, 0, 5, 10,
     '{"tools": ["calendar", "calculator"], "document_search": false, "history_days": 7, "priority": false}'),
    ('basic', 'Basic', 'Para autónomos y freelancers', 2.99, 29.99, 25, NULL,
     '{"tools": ["calendar", "calculator", "document_search"], "history_days": 30, "priority": false, "reminders": true}'),
    ('pro', 'Pro', 'Acceso ilimitado a todas las funciones', 9.99, 99.99, NULL, NULL,
     '{"tools": ["calendar", "calculator", "document_search"], "history_days": null, "priority": true, "reminders": true, "export_pdf": true, "whatsapp_alerts": true}')
ON CONFLICT (name) DO NOTHING;


-- 2. User Subscriptions - подписки пользователей
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'cancelled', 'expired', 'past_due'
    billing_period TEXT DEFAULT 'monthly',  -- 'monthly', 'yearly'

    -- Stripe данные
    stripe_customer_id TEXT,                -- Stripe Customer ID
    stripe_subscription_id TEXT,            -- Stripe Subscription ID

    -- Даты
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id)  -- Один пользователь = одна подписка
);

CREATE INDEX idx_user_subscriptions_user ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_stripe ON user_subscriptions(stripe_subscription_id);


-- 3. Usage Tracking - отслеживание использования
CREATE TABLE IF NOT EXISTS usage_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
    message_count INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,          -- Опционально для будущего
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, usage_date)
);

CREATE INDEX idx_usage_daily_user_date ON usage_daily(user_id, usage_date);


-- 4. Payment History - история платежей (для отчётности)
CREATE TABLE IF NOT EXISTS payment_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES user_subscriptions(id),

    -- Stripe данные
    stripe_payment_intent_id TEXT,
    stripe_invoice_id TEXT,

    amount DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'EUR',
    status TEXT NOT NULL,                   -- 'succeeded', 'failed', 'pending', 'refunded'

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payment_history_user ON payment_history(user_id);
CREATE INDEX idx_payment_history_stripe ON payment_history(stripe_payment_intent_id);


-- ============================================================
-- Functions
-- ============================================================

-- Функция: Получить текущий план пользователя (с дневным И недельным лимитом)
CREATE OR REPLACE FUNCTION get_user_plan(p_telegram_id BIGINT)
RETURNS TABLE (
    plan_name TEXT,
    daily_limit INTEGER,
    weekly_limit INTEGER,
    messages_today INTEGER,
    messages_this_week INTEGER,
    messages_remaining INTEGER,
    is_premium BOOLEAN,
    expires_at TIMESTAMPTZ
) AS $$
DECLARE
    v_user_id UUID;
    v_plan subscription_plans%ROWTYPE;
    v_usage_today INTEGER;
    v_usage_week INTEGER;
    v_remaining_daily INTEGER;
    v_remaining_weekly INTEGER;
    v_remaining INTEGER;
BEGIN
    -- Находим пользователя
    SELECT id INTO v_user_id FROM users WHERE telegram_id = p_telegram_id;

    IF v_user_id IS NULL THEN
        -- Новый пользователь - Free план
        RETURN QUERY SELECT
            'free'::TEXT,
            5::INTEGER,
            10::INTEGER,
            0::INTEGER,
            0::INTEGER,
            5::INTEGER,
            false::BOOLEAN,
            NULL::TIMESTAMPTZ;
        RETURN;
    END IF;

    -- Получаем план пользователя
    SELECT sp.* INTO v_plan
    FROM subscription_plans sp
    JOIN user_subscriptions us ON us.plan_id = sp.id
    WHERE us.user_id = v_user_id
      AND us.status = 'active'
      AND (us.current_period_end IS NULL OR us.current_period_end > NOW());

    -- Если нет активной подписки - Free план
    IF v_plan.id IS NULL THEN
        SELECT * INTO v_plan FROM subscription_plans WHERE name = 'free';
    END IF;

    -- Считаем использование за сегодня
    SELECT COALESCE(message_count, 0) INTO v_usage_today
    FROM usage_daily
    WHERE user_id = v_user_id AND usage_date = CURRENT_DATE;

    IF v_usage_today IS NULL THEN
        v_usage_today := 0;
    END IF;

    -- Считаем использование за эту неделю (понедельник - воскресенье)
    SELECT COALESCE(SUM(message_count), 0) INTO v_usage_week
    FROM usage_daily
    WHERE user_id = v_user_id
      AND usage_date >= date_trunc('week', CURRENT_DATE)::DATE;

    -- Вычисляем оставшиеся запросы (минимум из дневного и недельного)
    IF v_plan.daily_message_limit IS NULL THEN
        v_remaining := NULL; -- безлимит
    ELSE
        v_remaining_daily := GREATEST(0, v_plan.daily_message_limit - v_usage_today);
        IF v_plan.weekly_message_limit IS NOT NULL THEN
            v_remaining_weekly := GREATEST(0, v_plan.weekly_message_limit - v_usage_week);
            v_remaining := LEAST(v_remaining_daily, v_remaining_weekly);
        ELSE
            v_remaining := v_remaining_daily;
        END IF;
    END IF;

    RETURN QUERY SELECT
        v_plan.name,
        v_plan.daily_message_limit,
        v_plan.weekly_message_limit,
        v_usage_today,
        v_usage_week,
        v_remaining,
        (v_plan.name IN ('pro', 'basic')),
        (SELECT current_period_end FROM user_subscriptions WHERE user_id = v_user_id AND status = 'active');
END;
$$ LANGUAGE plpgsql;


-- Функция: Проверить можно ли отправить сообщение
CREATE OR REPLACE FUNCTION can_send_message(p_telegram_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    v_plan RECORD;
BEGIN
    SELECT * INTO v_plan FROM get_user_plan(p_telegram_id);

    -- Безлимитный план
    IF v_plan.daily_limit IS NULL THEN
        RETURN true;
    END IF;

    -- Проверяем лимит (учитывает и дневной и недельный)
    RETURN v_plan.messages_remaining > 0;
END;
$$ LANGUAGE plpgsql;


-- Функция: Инкрементировать счётчик сообщений
CREATE OR REPLACE FUNCTION increment_message_count(p_telegram_id BIGINT)
RETURNS INTEGER AS $$
DECLARE
    v_user_id UUID;
    v_new_count INTEGER;
BEGIN
    -- Находим пользователя
    SELECT id INTO v_user_id FROM users WHERE telegram_id = p_telegram_id;

    IF v_user_id IS NULL THEN
        RETURN 0;
    END IF;

    -- Upsert в usage_daily
    INSERT INTO usage_daily (user_id, usage_date, message_count)
    VALUES (v_user_id, CURRENT_DATE, 1)
    ON CONFLICT (user_id, usage_date)
    DO UPDATE SET
        message_count = usage_daily.message_count + 1,
        updated_at = NOW()
    RETURNING message_count INTO v_new_count;

    RETURN v_new_count;
END;
$$ LANGUAGE plpgsql;


-- Функция: Обновить подписку из Stripe webhook
CREATE OR REPLACE FUNCTION update_subscription_from_stripe(
    p_telegram_id BIGINT,
    p_stripe_customer_id TEXT,
    p_stripe_subscription_id TEXT,
    p_plan_name TEXT,
    p_status TEXT,
    p_period_start TIMESTAMPTZ,
    p_period_end TIMESTAMPTZ
) RETURNS BOOLEAN AS $$
DECLARE
    v_user_id UUID;
    v_plan_id UUID;
BEGIN
    -- Находим пользователя
    SELECT id INTO v_user_id FROM users WHERE telegram_id = p_telegram_id;

    IF v_user_id IS NULL THEN
        RETURN false;
    END IF;

    -- Находим план
    SELECT id INTO v_plan_id FROM subscription_plans WHERE name = p_plan_name;

    IF v_plan_id IS NULL THEN
        RETURN false;
    END IF;

    -- Upsert подписки
    INSERT INTO user_subscriptions (
        user_id, plan_id, status,
        stripe_customer_id, stripe_subscription_id,
        current_period_start, current_period_end
    ) VALUES (
        v_user_id, v_plan_id, p_status,
        p_stripe_customer_id, p_stripe_subscription_id,
        p_period_start, p_period_end
    )
    ON CONFLICT (user_id)
    DO UPDATE SET
        plan_id = v_plan_id,
        status = p_status,
        stripe_customer_id = p_stripe_customer_id,
        stripe_subscription_id = p_stripe_subscription_id,
        current_period_start = p_period_start,
        current_period_end = p_period_end,
        updated_at = NOW();

    -- Обновляем users таблицу для обратной совместимости
    UPDATE users SET
        subscription_status = CASE WHEN p_plan_name IN ('pro', 'basic') THEN p_plan_name ELSE 'free' END,
        subscription_expires_at = p_period_end
    WHERE id = v_user_id;

    RETURN true;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- Indexes for performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_status);
CREATE INDEX IF NOT EXISTS idx_usage_daily_date ON usage_daily(usage_date);
