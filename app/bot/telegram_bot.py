"""
Telegram Bot для AI налогового консультанта TuExpertoFiscal

Прямая интеграция через aiogram 3.x
Bot: @tax_spaine_bot
"""
import os
import re
import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BotCommand, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode, ChatAction

from app.config.settings import settings
from app.services.agent.tax_agent_service import TaxAgentService
from app.services.subscription_service import SubscriptionService
from app.prompts import (
    START_MESSAGE,
    HELP_MESSAGE,
    ABOUT_MESSAGE,
    CALENDAR_INTRO_MESSAGE,
    LOW_CONFIDENCE_WARNING_ES,
    LOW_CONFIDENCE_WARNING_RU
)

os.environ["TOKENIZERS_PARALLELISM"] = "false"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Router для обработки сообщений
router = Router()


def _subscribe_keyboard(is_russian: bool) -> InlineKeyboardMarkup:
    """Кнопка 'Подписаться' на всю ширину для бесплатных пользователей"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⭐ Подписаться — от €2.99/мес" if is_russian else "⭐ Suscribirse — desde €2.99/mes",
            callback_data="show_plans"
        )]
    ])

# Глобальные инстансы (инициализируются при старте)
agent: Optional[TaxAgentService] = None
subscription_service: Optional[SubscriptionService] = None


def _clean_markdown_for_telegram(text: str) -> str:
    """
    Очистить Markdown для Telegram

    Telegram Markdown поддерживает только:
    - *bold* (жирный)
    - _italic_ (курсив)
    - `code` (код)
    - [text](url) (ссылки)

    НЕ поддерживает:
    - ** для bold
    - __ для italic
    - *** для bold+italic
    - ### заголовки
    - ``` блоки кода
    """
    # Заменяем ** на * (bold)
    text = re.sub(r'\*\*([^\*]+)\*\*', r'*\1*', text)

    # Заменяем __ на _ (italic)
    text = re.sub(r'__([^_]+)__', r'_\1_', text)

    # Убираем ~~~ (strikethrough не поддерживается)
    text = re.sub(r'~~([^~]+)~~', r'\1', text)

    # Заменяем блоки кода ``` на простой код `
    text = re.sub(r'```[a-z]*\n(.*?)\n```', r'`\1`', text, flags=re.DOTALL)

    # Убираем заголовки ###
    text = re.sub(r'^#{1,6}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)

    # Убираем горизонтальные линии ---
    text = re.sub(r'^[-_*]{3,}$', '', text, flags=re.MULTILINE)

    # Убираем лишние пустые строки (больше 2 подряд)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ============================================================
# COMMAND HANDLERS
# ============================================================

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка команды /start"""
    await message.answer(START_MESSAGE, parse_mode=ParseMode.MARKDOWN)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработка команды /help"""
    await message.answer(HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN)


@router.message(Command("calendar"))
async def cmd_calendar(message: Message):
    """Обработка команды /calendar - ближайшие дедлайны"""
    await message.chat.do(ChatAction.TYPING)

    if agent:
        response = await agent.process_query(
            query="Cuáles son los próximos vencimientos fiscales?",
            user_id=str(message.from_user.id)
        )
        await message.answer(response.text, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer("⚠️ El servicio no está disponible en este momento.")


@router.message(Command("about"))
async def cmd_about(message: Message):
    """Обработка команды /about"""
    await message.answer(ABOUT_MESSAGE, parse_mode=ParseMode.MARKDOWN)


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    """Обработка команды /subscribe [basic|pro] - оформление подписки"""
    if not subscription_service:
        await message.answer("⚠️ El servicio de suscripción no está disponible.")
        return

    user = message.from_user
    current_plan = await subscription_service.get_user_plan(user.id)
    is_russian = any('\u0400' <= c <= '\u04FF' for c in (user.first_name or ''))

    # Проверяем аргумент: /subscribe basic или /subscribe pro
    args = message.text.split()
    chosen_plan = args[1].lower() if len(args) > 1 else None

    if chosen_plan in ('basic', 'pro'):
        # Пользователь выбрал план — создаём Stripe Checkout
        if current_plan.plan_name == chosen_plan:
            text = "✅ У вас уже этот план!" if is_russian else "✅ Ya tienes este plan!"
            await message.answer(text)
            return

        checkout_url = await subscription_service.create_checkout_session(
            telegram_id=user.id,
            plan=chosen_plan,
            billing_period='monthly'
        )

        if checkout_url:
            if is_russian:
                text = f"💳 Оформить *{chosen_plan.capitalize()}* — [перейти к оплате]({checkout_url})"
            else:
                text = f"💳 Suscribirse a *{chosen_plan.capitalize()}* — [ir al pago]({checkout_url})"
            await message.answer(text, parse_mode=ParseMode.MARKDOWN)
        else:
            text = (
                "⚠️ Оплата временно недоступна. Попробуйте позже."
                if is_russian else
                "⚠️ El pago no está disponible temporalmente. Inténtalo más tarde."
            )
            await message.answer(text)
        return

    if current_plan.plan_name == 'pro':
        # Уже Pro - показываем портал управления
        portal_url = await subscription_service.create_portal_session(user.id)
        if portal_url:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="⚙️ Управление подпиской" if is_russian else "⚙️ Gestionar suscripción",
                    url=portal_url
                )]
            ])
            text = (
                f"✅ *У вас активен план Pro*\n\n"
                f"Истекает: {current_plan.expires_at.strftime('%d/%m/%Y') if current_plan.expires_at else 'N/A'}"
            ) if is_russian else (
                f"✅ *Tienes el plan Pro activo*\n\n"
                f"Expira: {current_plan.expires_at.strftime('%d/%m/%Y') if current_plan.expires_at else 'N/A'}"
            )
            await message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        else:
            await message.answer("✅ Ya tienes el plan Pro activo.")
    else:
        # Free или Basic - показываем тарифы с кнопками
        if is_russian:
            text = (
                "🚀 *Тарифные планы TuExpertoFiscal*\n\n"
                "📦 *Free* — бесплатно\n"
                "  • 5 запросов/день, 20/месяц\n"
                "  • Калькулятор + Календарь\n"
                "  • История 7 дней\n\n"
                "⭐ *Basic* — €2.99/мес\n"
                "  • 10 запросов/день, 50/месяц\n"
                "  • Поиск в документах\n"
                "  • Напоминания о дедлайнах\n"
                "  • История 30 дней\n\n"
                "🚀 *Pro* — €9.99/мес\n"
                "  • 25 запросов/день, 150/месяц\n"
                "  • Все функции\n"
                "  • Приоритетные ответы\n"
                "  • Безлимитная история\n\n"
                f"Текущий план: *{current_plan.plan_name.capitalize()}*"
            )
        else:
            text = (
                "🚀 *Planes TuExpertoFiscal*\n\n"
                "📦 *Free* — gratis\n"
                "  • 5 consultas/día, 20/mes\n"
                "  • Calculadora + Calendario\n"
                "  • Historial 7 días\n\n"
                "⭐ *Basic* — €2.99/mes\n"
                "  • 10 consultas/día, 50/mes\n"
                "  • Búsqueda en documentos\n"
                "  • Recordatorios de plazos\n"
                "  • Historial 30 días\n\n"
                "🚀 *Pro* — €9.99/mes\n"
                "  • 25 consultas/día, 150/mes\n"
                "  • Todas las funciones\n"
                "  • Respuestas prioritarias\n"
                "  • Historial ilimitado\n\n"
                f"Plan actual: *{current_plan.plan_name.capitalize()}*"
            )

        # Inline-кнопки для оплаты
        buttons = []
        if current_plan.plan_name != 'basic':
            buttons.append([InlineKeyboardButton(
                text="⭐ Basic — €2.99/мес" if is_russian else "⭐ Basic — €2.99/mes",
                callback_data="subscribe:basic"
            )])
        buttons.append([InlineKeyboardButton(
            text="🚀 Pro — €9.99/мес" if is_russian else "🚀 Pro — €9.99/mes",
            callback_data="subscribe:pro"
        )])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.callback_query(F.data.startswith("subscribe:"))
async def callback_subscribe(callback: CallbackQuery):
    """Обработка нажатия кнопки подписки"""
    if not subscription_service:
        await callback.answer("⚠️ Servicio no disponible", show_alert=True)
        return

    chosen_plan = callback.data.split(":")[1]  # "basic" or "pro"
    user = callback.from_user
    is_russian = any('\u0400' <= c <= '\u04FF' for c in (user.first_name or ''))

    await callback.answer()  # убираем "часики" на кнопке

    checkout_url = await subscription_service.create_checkout_session(
        telegram_id=user.id,
        plan=chosen_plan,
        billing_period='monthly'
    )

    if checkout_url:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="💳 Перейти к оплате" if is_russian else "💳 Ir al pago",
                url=checkout_url
            )]
        ])
        if is_russian:
            text = f"Оформление подписки *{chosen_plan.capitalize()}*\n\nНажмите кнопку ниже для оплаты:"
        else:
            text = f"Suscripción *{chosen_plan.capitalize()}*\n\nPulsa el botón para pagar:"
        await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    else:
        text = (
            "⚠️ Оплата временно недоступна. Попробуйте позже."
            if is_russian else
            "⚠️ El pago no está disponible temporalmente. Inténtalo más tarde."
        )
        await callback.message.answer(text)


@router.callback_query(F.data == "show_plans")
async def callback_show_plans(callback: CallbackQuery):
    """Показать планы при нажатии кнопки 'Подписаться'"""
    if not subscription_service:
        await callback.answer("⚠️ Servicio no disponible", show_alert=True)
        return

    user = callback.from_user
    is_russian = any('\u0400' <= c <= '\u04FF' for c in (user.first_name or ''))
    current_plan = await subscription_service.get_user_plan(user.id)

    await callback.answer()

    # Показываем планы с кнопками оплаты
    if is_russian:
        text = (
            "⭐ *Basic* — €2.99/мес\n"
            "10 запросов/день, 50/месяц\n\n"
            "🚀 *Pro* — €9.99/мес\n"
            "25 запросов/день, 150/месяц"
        )
    else:
        text = (
            "⭐ *Basic* — €2.99/mes\n"
            "10 consultas/día, 50/mes\n\n"
            "🚀 *Pro* — €9.99/mes\n"
            "25 consultas/día, 150/mes"
        )

    buttons = []
    if current_plan.plan_name != 'basic':
        buttons.append([InlineKeyboardButton(
            text="⭐ Basic — €2.99/мес" if is_russian else "⭐ Basic — €2.99/mes",
            callback_data="subscribe:basic"
        )])
    buttons.append([InlineKeyboardButton(
        text="🚀 Pro — €9.99/мес" if is_russian else "🚀 Pro — €9.99/mes",
        callback_data="subscribe:pro"
    )])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Обработка команды /status - статус подписки и лимитов"""
    if not subscription_service:
        await message.answer("⚠️ El servicio no está disponible.")
        return

    user = message.from_user
    plan = await subscription_service.get_user_plan(user.id)
    is_russian = any('\u0400' <= c <= '\u04FF' for c in (user.first_name or ''))

    remaining = plan.messages_remaining if plan.messages_remaining is not None else 0
    remaining_text = "∞" if plan.daily_limit is None else str(remaining)

    if is_russian:
        daily_text = f"{plan.messages_today}/{plan.daily_limit}" if plan.daily_limit else "—"
        status_text = (
            f"👤 *Ваш аккаунт*\n\n"
            f"📦 План: *{plan.plan_name.capitalize()}*\n"
            f"📊 Запросов сегодня: {daily_text}\n"
        )
        if plan.monthly_limit is not None:
            status_text += f"📅 За месяц: {plan.messages_this_month}/{plan.monthly_limit}\n"
        status_text += f"⏳ Осталось: {remaining_text}\n"
        if plan.expires_at:
            status_text += f"📅 Действует до: {plan.expires_at.strftime('%d/%m/%Y')}\n"
        if plan.plan_name != 'pro':
            status_text += "\n💡 /subscribe — посмотреть тарифы"
    else:
        daily_text = f"{plan.messages_today}/{plan.daily_limit}" if plan.daily_limit else "—"
        status_text = (
            f"👤 *Tu cuenta*\n\n"
            f"📦 Plan: *{plan.plan_name.capitalize()}*\n"
            f"📊 Consultas hoy: {daily_text}\n"
        )
        if plan.monthly_limit is not None:
            status_text += f"📅 Este mes: {plan.messages_this_month}/{plan.monthly_limit}\n"
        status_text += f"⏳ Restantes: {remaining_text}\n"
        if plan.expires_at:
            status_text += f"📅 Válido hasta: {plan.expires_at.strftime('%d/%m/%Y')}\n"
        if plan.plan_name != 'pro':
            status_text += "\n💡 /subscribe — ver planes"

    await message.answer(status_text, parse_mode=ParseMode.MARKDOWN)


# ============================================================
# MESSAGE HANDLER
# ============================================================

@router.message(F.text)
async def handle_message(message: Message):
    """Обработка обычных текстовых сообщений - основная логика агента"""
    if not agent:
        await message.answer("⚠️ El servicio se está iniciando, por favor espera un momento...")
        return

    user = message.from_user
    query = message.text

    logger.info(f"Query from {user.id} ({user.username}): {query[:100]}")

    # Определяем язык пользователя
    is_russian = any('\u0400' <= c <= '\u04FF' for c in query) or any('\u0400' <= c <= '\u04FF' for c in (user.first_name or ''))

    # Проверяем лимиты подписки
    user_plan = None
    if subscription_service:
        can_send, user_plan = await subscription_service.can_send_message(user.id)
        if not can_send:
            if is_russian:
                await message.answer(user_plan.limit_message_ru, parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=_subscribe_keyboard(True))
            else:
                await message.answer(user_plan.limit_message_es, parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=_subscribe_keyboard(False))
            return

    # Отправляем статус-сообщение
    status_texts = {
        "search": "📚 Ищу в базе знаний..." if is_russian else "📚 Buscando en la base de conocimientos...",
        "tools": "🧮 Обрабатываю данные..." if is_russian else "🧮 Procesando datos...",
        "generate": "✍️ Готовлю ответ..." if is_russian else "✍️ Preparando la respuesta...",
    }
    status_msg = await message.answer(
        "🔍 Анализирую ваш вопрос..." if is_russian else "🔍 Analizando tu pregunta..."
    )

    async def update_status(step: str):
        text = status_texts.get(step)
        if text:
            try:
                await status_msg.edit_text(text)
            except Exception:
                pass

    try:
        # Инкрементируем счётчик использования
        if subscription_service:
            await subscription_service.increment_usage(user.id)

        # Обрабатываем запрос через агента
        response = await agent.process_query(
            query=query,
            user_id=str(user.id),
            progress_callback=update_status
        )

        # Удаляем статус-сообщение
        try:
            await status_msg.delete()
        except Exception:
            pass

        # Формируем ответ и очищаем Markdown для Telegram
        reply_text = _clean_markdown_for_telegram(response.text)

        # Добавляем метаданные (опционально)
        if response.confidence < 0.5:
            if any('\u0400' <= c <= '\u04FF' for c in query):
                reply_text += LOW_CONFIDENCE_WARNING_RU
            else:
                reply_text += LOW_CONFIDENCE_WARNING_ES

        # Кнопка подписки для free-пользователей
        show_subscribe = user_plan and user_plan.plan_name == 'free'
        reply_markup = _subscribe_keyboard(is_russian) if show_subscribe else None

        # Отправляем ответ (разбиваем на части если длинный)
        if len(reply_text) > 4000:
            parts = [reply_text[i:i+4000] for i in range(0, len(reply_text), 4000)]
            for i, part in enumerate(parts):
                markup = reply_markup if i == len(parts) - 1 else None
                await message.answer(part, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        else:
            try:
                await message.answer(reply_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            except Exception:
                await message.answer(reply_text, reply_markup=reply_markup)

        # Рекламный блок для free-пользователей
        if user_plan and user_plan.plan_name == 'free':
            ad_text = (
                "━━━━━━━━━━━━━━━\n"
                "📢 Здесь может быть Ваша реклама\n"
                "👉 @valencia\\_dvizh"
                if is_russian else
                "━━━━━━━━━━━━━━━\n"
                "📢 Aquí puede estar tu publicidad\n"
                "👉 @valencia\\_dvizh"
            )
            await message.answer(ad_text, parse_mode=ParseMode.MARKDOWN)

        logger.info(
            f"Response sent to {user.id}: "
            f"type={response.query_type}, "
            f"confidence={response.confidence:.2f}, "
            f"time={response.processing_time_ms:.0f}ms"
        )

    except Exception as e:
        logger.error(f"Error processing message from {user.id}: {e}")
        try:
            await status_msg.delete()
        except Exception:
            pass
        await message.answer(
            "Lo siento, ha ocurrido un error. Por favor, inténtalo de nuevo."
        )


# ============================================================
# BOT SETUP & START
# ============================================================

async def set_bot_commands(bot: Bot):
    """Установка команд бота в Telegram"""
    commands = [
        BotCommand(command="start", description="Iniciar el bot"),
        BotCommand(command="help", description="Mostrar ayuda"),
        BotCommand(command="calendar", description="Próximos vencimientos"),
        BotCommand(command="subscribe", description="Suscripción Premium"),
        BotCommand(command="status", description="Estado de tu cuenta"),
        BotCommand(command="about", description="Sobre el bot"),
    ]
    await bot.set_my_commands(commands)


async def main():
    """Запуск бота + Stripe webhook сервера"""
    global agent, subscription_service

    # Инициализация бота
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    bot = Bot(token=bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    # Инициализация сервиса подписок
    logger.info("💳 Initializing SubscriptionService...")
    subscription_service = SubscriptionService()
    logger.info("✅ SubscriptionService ready")

    # Инициализация агента
    logger.info("🤖 Initializing TaxAgentService...")
    agent = TaxAgentService()
    await agent.initialize()
    logger.info("✅ TaxAgentService ready")

    # Установка команд
    await set_bot_commands(bot)

    # Удаляем webhook (если был установлен через N8N или другой сервис)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Webhook cleared, switching to polling mode")

    # Запуск Stripe webhook сервера параллельно с ботом
    from app.api.stripe_webhook import run_webhook_server
    webhook_port = int(os.getenv("WEBHOOK_PORT", "8000"))
    logger.info(f"🔗 Starting Stripe webhook server on port {webhook_port}...")
    webhook_task = asyncio.create_task(run_webhook_server(port=webhook_port))

    # Запуск polling
    logger.info("🚀 Bot started! @tax_spaine_bot")
    logger.info("Press Ctrl+C to stop")

    try:
        await dp.start_polling(bot)
    finally:
        webhook_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
