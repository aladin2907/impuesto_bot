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
from aiogram.types import Message, BotCommand
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
    """Обработка команды /subscribe - оформление подписки"""
    if not subscription_service:
        await message.answer("⚠️ El servicio de suscripción no está disponible.")
        return

    user = message.from_user
    plan = await subscription_service.get_user_plan(user.id)
    is_russian = any('\u0400' <= c <= '\u04FF' for c in (user.first_name or ''))

    if plan.plan_name == 'pro':
        # Уже Pro - показываем портал управления
        portal_url = await subscription_service.create_portal_session(user.id)
        if portal_url:
            text = (
                f"✅ *У вас активен план Pro*\n\n"
                f"Истекает: {plan.expires_at.strftime('%d/%m/%Y') if plan.expires_at else 'N/A'}\n\n"
                f"[Управление подпиской]({portal_url})"
            ) if is_russian else (
                f"✅ *Tienes el plan Pro activo*\n\n"
                f"Expira: {plan.expires_at.strftime('%d/%m/%Y') if plan.expires_at else 'N/A'}\n\n"
                f"[Gestionar suscripción]({portal_url})"
            )
            await message.answer(text, parse_mode=ParseMode.MARKDOWN)
        else:
            await message.answer("✅ Ya tienes el plan Pro activo.")
    else:
        # Free или Basic - показываем тарифы
        if is_russian:
            text = (
                "🚀 *Тарифные планы TuExpertoFiscal*\n\n"
                "📦 *Free* — бесплатно\n"
                "  • 5 запросов/день, 10/неделю\n"
                "  • Калькулятор + Календарь\n"
                "  • История 7 дней\n\n"
                "⭐ *Basic* — €2.99/мес\n"
                "  • 25 запросов в день\n"
                "  • Поиск в документах\n"
                "  • Напоминания о дедлайнах\n"
                "  • История 30 дней\n\n"
                "🚀 *Pro* — €9.99/мес\n"
                "  • Безлимитные запросы\n"
                "  • Все функции\n"
                "  • Приоритетные ответы\n"
                "  • Безлимитная история\n\n"
                f"Текущий план: *{plan.plan_name.capitalize()}*\n"
                "Используйте /subscribe basic или /subscribe pro"
            )
        else:
            text = (
                "🚀 *Planes TuExpertoFiscal*\n\n"
                "📦 *Free* — gratis\n"
                "  • 5 consultas/día, 10/semana\n"
                "  • Calculadora + Calendario\n"
                "  • Historial 7 días\n\n"
                "⭐ *Basic* — €2.99/mes\n"
                "  • 25 consultas/día\n"
                "  • Búsqueda en documentos\n"
                "  • Recordatorios de plazos\n"
                "  • Historial 30 días\n\n"
                "🚀 *Pro* — €9.99/mes\n"
                "  • Consultas ilimitadas\n"
                "  • Todas las funciones\n"
                "  • Respuestas prioritarias\n"
                "  • Historial ilimitado\n\n"
                f"Plan actual: *{plan.plan_name.capitalize()}*\n"
                "Usa /subscribe basic o /subscribe pro"
            )
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)


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
        daily_text = "Безлимит" if plan.daily_limit is None else f"{plan.messages_today}/{plan.daily_limit}"
        status_text = (
            f"👤 *Ваш аккаунт*\n\n"
            f"📦 План: *{plan.plan_name.capitalize()}*\n"
            f"📊 Запросов сегодня: {daily_text}\n"
        )
        if plan.weekly_limit is not None:
            status_text += f"📅 За неделю: {plan.messages_this_week}/{plan.weekly_limit}\n"
        status_text += f"⏳ Осталось: {remaining_text}\n"
        if plan.expires_at:
            status_text += f"📅 Действует до: {plan.expires_at.strftime('%d/%m/%Y')}\n"
        if plan.plan_name != 'pro':
            status_text += "\n💡 /subscribe — посмотреть тарифы"
    else:
        daily_text = "Ilimitado" if plan.daily_limit is None else f"{plan.messages_today}/{plan.daily_limit}"
        status_text = (
            f"👤 *Tu cuenta*\n\n"
            f"📦 Plan: *{plan.plan_name.capitalize()}*\n"
            f"📊 Consultas hoy: {daily_text}\n"
        )
        if plan.weekly_limit is not None:
            status_text += f"📅 Esta semana: {plan.messages_this_week}/{plan.weekly_limit}\n"
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

    # Проверяем лимиты подписки
    if subscription_service:
        can_send, plan = await subscription_service.can_send_message(user.id)
        if not can_send:
            # Определяем язык пользователя
            if any('\u0400' <= c <= '\u04FF' for c in query):
                await message.answer(plan.limit_message_ru, parse_mode=ParseMode.MARKDOWN)
            else:
                await message.answer(plan.limit_message_es, parse_mode=ParseMode.MARKDOWN)
            return

    # Показываем индикатор "печатает..."
    await message.chat.do(ChatAction.TYPING)

    try:
        # Инкрементируем счётчик использования
        if subscription_service:
            await subscription_service.increment_usage(user.id)

        # Обрабатываем запрос через агента
        response = await agent.process_query(
            query=query,
            user_id=str(user.id)
        )

        # Формируем ответ и очищаем Markdown для Telegram
        reply_text = _clean_markdown_for_telegram(response.text)

        # Добавляем метаданные (опционально)
        if response.confidence < 0.5:
            # Определяем язык для предупреждения
            if any('\u0400' <= c <= '\u04FF' for c in query):
                reply_text += LOW_CONFIDENCE_WARNING_RU
            else:
                reply_text += LOW_CONFIDENCE_WARNING_ES

        # Отправляем ответ (разбиваем на части если длинный)
        if len(reply_text) > 4000:
            # Telegram ограничивает сообщения до 4096 символов
            parts = [reply_text[i:i+4000] for i in range(0, len(reply_text), 4000)]
            for part in parts:
                await message.answer(part, parse_mode=ParseMode.MARKDOWN)
        else:
            try:
                await message.answer(reply_text, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                # Если Markdown не парсится, отправляем без форматирования
                await message.answer(reply_text)

        logger.info(
            f"Response sent to {user.id}: "
            f"type={response.query_type}, "
            f"confidence={response.confidence:.2f}, "
            f"time={response.processing_time_ms:.0f}ms"
        )

    except Exception as e:
        logger.error(f"Error processing message from {user.id}: {e}")
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
    """Запуск бота"""
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

    # Запуск polling
    logger.info("🚀 Bot started! @tax_spaine_bot")
    logger.info("Press Ctrl+C to stop")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
