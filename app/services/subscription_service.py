"""
SubscriptionService - управление подписками и лимитами

Интеграция со Stripe для платежей
Проверка лимитов для Free пользователей
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

import stripe
from supabase import create_client, Client

from app.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class UserPlan:
    """Данные о плане пользователя"""
    plan_name: str
    daily_limit: Optional[int]
    monthly_limit: Optional[int]
    messages_today: int
    messages_this_month: int
    messages_remaining: Optional[int]
    is_premium: bool
    expires_at: Optional[datetime]

    @property
    def can_send_message(self) -> bool:
        """Может ли пользователь отправить сообщение"""
        if self.daily_limit is None:  # Безлимит
            return True
        return self.messages_remaining is not None and self.messages_remaining > 0

    @property
    def _is_monthly_limit_hit(self) -> bool:
        """Достигнут ли именно месячный лимит"""
        if self.monthly_limit is None:
            return False
        return self.messages_this_month >= self.monthly_limit

    @property
    def limit_message_ru(self) -> str:
        """Сообщение о лимите на русском"""
        if self.plan_name == 'free':
            if self._is_monthly_limit_hit:
                return (
                    f"⚠️ Вы использовали все {self.monthly_limit} бесплатных запросов в этом месяце.\n\n"
                    f"Тарифные планы:\n"
                    f"📦 *Basic* — €2.99/мес (10 запросов/день, 50/мес)\n"
                    f"🚀 *Pro* — €9.99/мес (25 запросов/день, 150/мес)\n\n"
                    f"Используйте /subscribe для оформления подписки.\n"
                    f"Месячный лимит сбросится 1-го числа."
                )
            return (
                f"⚠️ Вы использовали все {self.daily_limit} бесплатных запросов на сегодня.\n\n"
                f"Тарифные планы:\n"
                f"📦 *Basic* — €2.99/мес (10 запросов/день, 50/мес)\n"
                f"🚀 *Pro* — €9.99/мес (25 запросов/день, 150/мес)\n\n"
                f"Используйте /subscribe для оформления подписки.\n"
                f"Дневной лимит сбросится через 24 часа."
            )
        if self.plan_name == 'basic':
            if self._is_monthly_limit_hit:
                return (
                    f"⚠️ Вы использовали все {self.monthly_limit} запросов в этом месяце (план Basic).\n\n"
                    f"🚀 Перейдите на *Pro* за €9.99/мес — 25 запросов/день, 150/мес!\n\n"
                    f"Используйте /subscribe для апгрейда."
                )
            return (
                f"⚠️ Вы использовали все {self.daily_limit} запросов на сегодня (план Basic).\n\n"
                f"🚀 Перейдите на *Pro* за €9.99/мес — 25 запросов/день, 150/мес!\n\n"
                f"Используйте /subscribe для апгрейда."
            )
        return (
            f"⚠️ Вы достигли лимита запросов (план Pro).\n\n"
            f"Лимит сбросится завтра."
        )

    @property
    def limit_message_es(self) -> str:
        """Сообщение о лимите на испанском"""
        if self.plan_name == 'free':
            if self._is_monthly_limit_hit:
                return (
                    f"⚠️ Has usado tus {self.monthly_limit} consultas gratuitas de este mes.\n\n"
                    f"Planes disponibles:\n"
                    f"📦 *Basic* — €2.99/mes (10 consultas/día, 50/mes)\n"
                    f"🚀 *Pro* — €9.99/mes (25 consultas/día, 150/mes)\n\n"
                    f"Usa /subscribe para suscribirte.\n"
                    f"Tu límite mensual se renueva el día 1."
                )
            return (
                f"⚠️ Has usado tus {self.daily_limit} consultas gratuitas de hoy.\n\n"
                f"Planes disponibles:\n"
                f"📦 *Basic* — €2.99/mes (10 consultas/día, 50/mes)\n"
                f"🚀 *Pro* — €9.99/mes (25 consultas/día, 150/mes)\n\n"
                f"Usa /subscribe para suscribirte.\n"
                f"Tu límite diario se renueva en 24 horas."
            )
        if self.plan_name == 'basic':
            if self._is_monthly_limit_hit:
                return (
                    f"⚠️ Has usado tus {self.monthly_limit} consultas de este mes (plan Basic).\n\n"
                    f"🚀 Pasa a *Pro* por €9.99/mes — 25 consultas/día, 150/mes!\n\n"
                    f"Usa /subscribe para hacer upgrade."
                )
            return (
                f"⚠️ Has usado tus {self.daily_limit} consultas de hoy (plan Basic).\n\n"
                f"🚀 Pasa a *Pro* por €9.99/mes — 25 consultas/día, 150/mes!\n\n"
                f"Usa /subscribe para hacer upgrade."
            )
        return (
            f"⚠️ Has alcanzado el límite de consultas (plan Pro).\n\n"
            f"Tu límite se renueva mañana."
        )


class SubscriptionService:
    """Сервис управления подписками и лимитами"""

    # Планы подписки
    PLANS = {
        'free': {
            'name': 'Free',
            'daily_limit': 5,
            'monthly_limit': 20,
            'price_monthly': 0,
        },
        'basic': {
            'name': 'Basic',
            'daily_limit': 10,
            'monthly_limit': 50,
            'price_monthly': 2.99,
        },
        'pro': {
            'name': 'Pro',
            'daily_limit': 25,
            'monthly_limit': 150,
            'price_monthly': 9.99,
        }
    }

    def __init__(self):
        self.supabase: Optional[Client] = None
        self._init_supabase()
        self._init_stripe()

    def _init_supabase(self):
        """Инициализация Supabase клиента"""
        try:
            supabase_key = getattr(settings, 'SUPABASE_SERVICE_KEY', None) or settings.SUPABASE_KEY
            self.supabase = create_client(
                settings.SUPABASE_URL,
                supabase_key
            )
            logger.info("✅ SubscriptionService: Supabase connected")
        except Exception as e:
            logger.error(f"❌ SubscriptionService: Supabase connection failed: {e}")

    def _init_stripe(self):
        """Инициализация Stripe"""
        stripe_key = os.getenv('STRIPE_SECRET_KEY')
        if stripe_key:
            stripe.api_key = stripe_key
            logger.info("✅ SubscriptionService: Stripe initialized")
        else:
            logger.warning("⚠️ SubscriptionService: STRIPE_SECRET_KEY not set")

    async def get_user_plan(self, telegram_id: int) -> UserPlan:
        """Получить план пользователя"""
        try:
            if not self.supabase:
                return self._default_free_plan()

            # Вызываем функцию в Supabase
            result = self.supabase.rpc(
                'get_user_plan',
                {'p_telegram_id': telegram_id}
            ).execute()

            if result.data and len(result.data) > 0:
                row = result.data[0]
                return UserPlan(
                    plan_name=row['plan_name'],
                    daily_limit=row['daily_limit'],
                    monthly_limit=row.get('monthly_limit'),
                    messages_today=row['messages_today'],
                    messages_this_month=row.get('messages_this_month', row['messages_today']),
                    messages_remaining=row['messages_remaining'],
                    is_premium=row['is_premium'],
                    expires_at=row['expires_at']
                )

            return self._default_free_plan()

        except Exception as e:
            error_msg = str(e)
            # Graceful degradation: if subscription tables don't exist yet
            if 'PGRST202' in error_msg or 'does not exist' in error_msg:
                logger.warning("Subscription tables not yet created - all users default to Free plan")
            else:
                logger.error(f"Error getting user plan: {e}")
            return self._default_free_plan()

    def _default_free_plan(self) -> UserPlan:
        """Дефолтный Free план"""
        return UserPlan(
            plan_name='free',
            daily_limit=5,
            monthly_limit=20,
            messages_today=0,
            messages_this_month=0,
            messages_remaining=5,
            is_premium=False,
            expires_at=None
        )

    async def can_send_message(self, telegram_id: int) -> tuple[bool, Optional[UserPlan]]:
        """
        Проверить может ли пользователь отправить сообщение

        Returns:
            (can_send, user_plan) - можно ли отправить и данные о плане
        """
        plan = await self.get_user_plan(telegram_id)
        return plan.can_send_message, plan

    async def increment_usage(self, telegram_id: int) -> int:
        """
        Инкрементировать счётчик использования

        Returns:
            Новое количество сообщений за день
        """
        try:
            if not self.supabase:
                return 0

            result = self.supabase.rpc(
                'increment_message_count',
                {'p_telegram_id': telegram_id}
            ).execute()

            return result.data if result.data else 0

        except Exception as e:
            error_msg = str(e)
            if 'PGRST202' in error_msg or 'does not exist' in error_msg:
                pass  # Tables not created yet, skip silently
            else:
                logger.error(f"Error incrementing usage: {e}")
            return 0

    # ============================================================
    # Stripe Integration
    # ============================================================

    async def create_checkout_session(
        self,
        telegram_id: int,
        plan: str = 'premium',
        billing_period: str = 'monthly'
    ) -> Optional[str]:
        """
        Создать Stripe Checkout Session

        Returns:
            URL для редиректа на оплату
        """
        try:
            # Получаем или создаём Stripe Customer
            customer_id = await self._get_or_create_stripe_customer(telegram_id)

            # Получаем Price ID из настроек
            price_id = os.getenv(f'STRIPE_PRICE_{plan.upper()}_{billing_period.upper()}')

            if not price_id:
                logger.error(f"Stripe Price ID not found for {plan}_{billing_period}")
                return None

            # Создаём Checkout Session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=os.getenv('STRIPE_SUCCESS_URL', 'https://t.me/tax_spaine_bot?start=success'),
                cancel_url=os.getenv('STRIPE_CANCEL_URL', 'https://t.me/tax_spaine_bot?start=cancel'),
                metadata={
                    'telegram_id': str(telegram_id),
                    'plan': plan,
                }
            )

            return session.url

        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            return None

    async def _get_or_create_stripe_customer(self, telegram_id: int) -> str:
        """Получить или создать Stripe Customer"""
        try:
            # Проверяем есть ли уже customer
            if self.supabase:
                result = self.supabase.table('user_subscriptions') \
                    .select('stripe_customer_id') \
                    .eq('user_id', self._get_user_id(telegram_id)) \
                    .execute()

                if result.data and result.data[0].get('stripe_customer_id'):
                    return result.data[0]['stripe_customer_id']

            # Создаём нового customer
            customer = stripe.Customer.create(
                metadata={'telegram_id': str(telegram_id)}
            )

            return customer.id

        except Exception as e:
            logger.error(f"Error getting/creating Stripe customer: {e}")
            raise

    def _get_user_id(self, telegram_id: int) -> Optional[str]:
        """Получить UUID пользователя по telegram_id"""
        try:
            if not self.supabase:
                return None

            result = self.supabase.table('users') \
                .select('id') \
                .eq('telegram_id', telegram_id) \
                .execute()

            if result.data:
                return result.data[0]['id']
            return None

        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
            return None

    async def handle_webhook(self, payload: bytes, sig_header: str) -> bool:
        """
        Обработать Stripe Webhook (с верификацией подписи)

        Args:
            payload: Тело запроса
            sig_header: Stripe-Signature header

        Returns:
            True если успешно обработано
        """
        try:
            webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            return await self.handle_event(event)

        except stripe.error.SignatureVerificationError:
            logger.error("Invalid Stripe webhook signature")
            return False
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return False

    async def handle_event(self, event) -> bool:
        """
        Обработать Stripe Event (уже верифицированный)

        Args:
            event: Stripe Event object

        Returns:
            True если успешно обработано
        """
        try:
            event_type = event['type']

            if event_type == 'checkout.session.completed':
                await self._handle_checkout_completed(event['data']['object'])

            elif event_type == 'customer.subscription.updated':
                await self._handle_subscription_updated(event['data']['object'])

            elif event_type == 'customer.subscription.deleted':
                await self._handle_subscription_deleted(event['data']['object'])

            elif event_type == 'invoice.payment_succeeded':
                await self._handle_payment_succeeded(event['data']['object'])

            elif event_type == 'invoice.payment_failed':
                await self._handle_payment_failed(event['data']['object'])

            else:
                logger.info(f"Unhandled Stripe event type: {event_type}")

            return True

        except Exception as e:
            logger.error(f"Error handling Stripe event: {e}")
            return False

    async def _handle_checkout_completed(self, session: Dict[str, Any]):
        """Обработка успешного checkout"""
        telegram_id = int(session['metadata']['telegram_id'])
        plan = session['metadata'].get('plan', 'premium')

        # Получаем подписку
        subscription = stripe.Subscription.retrieve(session['subscription'])

        # Обновляем в базе
        if self.supabase:
            self.supabase.rpc('update_subscription_from_stripe', {
                'p_telegram_id': telegram_id,
                'p_stripe_customer_id': session['customer'],
                'p_stripe_subscription_id': session['subscription'],
                'p_plan_name': plan,
                'p_status': 'active',
                'p_period_start': datetime.fromtimestamp(subscription['current_period_start']).isoformat(),
                'p_period_end': datetime.fromtimestamp(subscription['current_period_end']).isoformat()
            }).execute()

        logger.info(f"✅ Subscription created for telegram_id={telegram_id}, plan={plan}")

    async def _handle_subscription_updated(self, subscription: Dict[str, Any]):
        """Обработка обновления подписки"""
        customer = stripe.Customer.retrieve(subscription['customer'])
        telegram_id = int(customer['metadata'].get('telegram_id', 0))

        if telegram_id and self.supabase:
            status = subscription['status']
            self.supabase.rpc('update_subscription_from_stripe', {
                'p_telegram_id': telegram_id,
                'p_stripe_customer_id': subscription['customer'],
                'p_stripe_subscription_id': subscription['id'],
                'p_plan_name': 'premium',
                'p_status': status,
                'p_period_start': datetime.fromtimestamp(subscription['current_period_start']).isoformat(),
                'p_period_end': datetime.fromtimestamp(subscription['current_period_end']).isoformat()
            }).execute()

        logger.info(f"Subscription updated for telegram_id={telegram_id}")

    async def _handle_subscription_deleted(self, subscription: Dict[str, Any]):
        """Обработка отмены подписки"""
        customer = stripe.Customer.retrieve(subscription['customer'])
        telegram_id = int(customer['metadata'].get('telegram_id', 0))

        if telegram_id and self.supabase:
            # Возвращаем на Free план
            self.supabase.rpc('update_subscription_from_stripe', {
                'p_telegram_id': telegram_id,
                'p_stripe_customer_id': subscription['customer'],
                'p_stripe_subscription_id': subscription['id'],
                'p_plan_name': 'free',
                'p_status': 'cancelled',
                'p_period_start': None,
                'p_period_end': None
            }).execute()

        logger.info(f"Subscription cancelled for telegram_id={telegram_id}")

    async def _handle_payment_succeeded(self, invoice: Dict[str, Any]):
        """Обработка успешного платежа"""
        logger.info(f"Payment succeeded: {invoice['id']}")

    async def _handle_payment_failed(self, invoice: Dict[str, Any]):
        """Обработка неуспешного платежа"""
        logger.warning(f"Payment failed: {invoice['id']}")

    # ============================================================
    # Portal
    # ============================================================

    async def create_portal_session(self, telegram_id: int) -> Optional[str]:
        """
        Создать Stripe Customer Portal Session

        Returns:
            URL для управления подпиской
        """
        try:
            customer_id = await self._get_or_create_stripe_customer(telegram_id)

            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=os.getenv('STRIPE_PORTAL_RETURN_URL', 'https://t.me/tax_spaine_bot')
            )

            return session.url

        except Exception as e:
            logger.error(f"Error creating portal session: {e}")
            return None
