-- ============================================================
-- Migration: Weekly limits → Monthly limits
-- ============================================================
-- Меняем weekly_message_limit → monthly_message_limit
-- Обновляем лимиты планов:
--   Free:  5/день, 20/месяц
--   Basic: 10/день, 50/месяц
--   Pro:   25/день, 150/месяц
-- ============================================================

-- 1. Добавляем новую колонку monthly_message_limit
ALTER TABLE subscription_plans
    ADD COLUMN IF NOT EXISTS monthly_message_limit INTEGER;

-- 2. Обновляем планы
UPDATE subscription_plans SET
    daily_message_limit = 5,
    monthly_message_limit = 20,
    weekly_message_limit = NULL
WHERE name = 'free';

UPDATE subscription_plans SET
    daily_message_limit = 10,
    monthly_message_limit = 50,
    weekly_message_limit = NULL
WHERE name = 'basic';

UPDATE subscription_plans SET
    daily_message_limit = 25,
    monthly_message_limit = 150,
    weekly_message_limit = NULL
WHERE name = 'pro';

-- 3. Дропаем старые функции (return type изменился, нельзя просто CREATE OR REPLACE)
DROP FUNCTION IF EXISTS can_send_message(BIGINT);
DROP FUNCTION IF EXISTS get_user_plan(BIGINT);

-- 4. Создаём get_user_plan с monthly вместо weekly
CREATE OR REPLACE FUNCTION get_user_plan(p_telegram_id BIGINT)
RETURNS TABLE (
    plan_name TEXT,
    daily_limit INTEGER,
    monthly_limit INTEGER,
    messages_today INTEGER,
    messages_this_month INTEGER,
    messages_remaining INTEGER,
    is_premium BOOLEAN,
    expires_at TIMESTAMPTZ
) AS $$
DECLARE
    v_user_id UUID;
    v_plan subscription_plans%ROWTYPE;
    v_usage_today INTEGER;
    v_usage_month INTEGER;
    v_remaining_daily INTEGER;
    v_remaining_monthly INTEGER;
    v_remaining INTEGER;
BEGIN
    -- Находим пользователя
    SELECT id INTO v_user_id FROM users WHERE telegram_id = p_telegram_id;

    IF v_user_id IS NULL THEN
        -- Новый пользователь - Free план
        RETURN QUERY SELECT
            'free'::TEXT,
            5::INTEGER,
            20::INTEGER,
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

    -- Считаем использование за текущий месяц
    SELECT COALESCE(SUM(message_count), 0) INTO v_usage_month
    FROM usage_daily
    WHERE user_id = v_user_id
      AND usage_date >= date_trunc('month', CURRENT_DATE)::DATE;

    -- Вычисляем оставшиеся запросы (минимум из дневного и месячного)
    IF v_plan.daily_message_limit IS NULL THEN
        v_remaining := NULL; -- безлимит
    ELSE
        v_remaining_daily := GREATEST(0, v_plan.daily_message_limit - v_usage_today);
        IF v_plan.monthly_message_limit IS NOT NULL THEN
            v_remaining_monthly := GREATEST(0, v_plan.monthly_message_limit - v_usage_month);
            v_remaining := LEAST(v_remaining_daily, v_remaining_monthly);
        ELSE
            v_remaining := v_remaining_daily;
        END IF;
    END IF;

    RETURN QUERY SELECT
        v_plan.name,
        v_plan.daily_message_limit,
        v_plan.monthly_message_limit,
        v_usage_today,
        v_usage_month,
        v_remaining,
        (v_plan.name IN ('pro', 'basic')),
        (SELECT current_period_end FROM user_subscriptions WHERE user_id = v_user_id AND status = 'active');
END;
$$ LANGUAGE plpgsql;


-- 5. Пересоздаём can_send_message
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

    -- Проверяем лимит (учитывает и дневной и месячный)
    RETURN v_plan.messages_remaining > 0;
END;
$$ LANGUAGE plpgsql;

-- 6. Удаляем старую колонку weekly_message_limit
ALTER TABLE subscription_plans DROP COLUMN IF EXISTS weekly_message_limit;
