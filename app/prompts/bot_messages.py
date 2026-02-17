"""
Сообщения Telegram бота

Тексты для команд и уведомлений
"""

# Команда /start
START_MESSAGE = """¡Hola! 👋 Soy *TuExpertoFiscal*, tu asesor fiscal inteligente para España.

Puedo ayudarte con:
• 📅 Plazos y calendario fiscal (modelos 303, 130, etc.)
• 🧮 Cálculos de impuestos (IRPF, IVA, cuotas de autónomo)
• 📚 Consultas sobre legislación fiscal
• 💡 Consejos prácticos de la comunidad
• 📰 Novedades fiscales

*Hazme cualquier pregunta* sobre impuestos en España en español, ruso, ucraniano o inglés.

_Ejemplo:_ "¿Cuándo hay que presentar el modelo 303?"
_Пример:_ "Сколько стоит cuota de autónomo?"

Usa /help para ver todos los comandos disponibles.
"""

# Команда /help
HELP_MESSAGE = """🤖 *Cómo usar TuExpertoFiscal*

*Comandos disponibles:*
/start - Mensaje de bienvenida
/help - Esta ayuda
/calendar - Ver próximos plazos fiscales
/about - Información sobre el bot

*Tipos de consultas que puedo responder:*

📅 *Calendario fiscal*
_"¿Cuándo presentar IVA del Q3?"_
_"Когда подавать modelo 303?"_

🧮 *Cálculos*
_"Calcular IRPF para 50.000€"_
_"Сколько IVA на 1500 евро?"_

📚 *Legislación*
_"¿Qué dice la ley sobre deducciones?"_

💡 *Consejos prácticos*
_"¿Cómo abrir autónomo en Valencia?"_
_"Как организовать учёт?"_

*Idiomas soportados:*
Español 🇪🇸 | Русский 🇷🇺 | English 🇬🇧 | Українська 🇺🇦

Simplemente escríbeme tu pregunta en cualquier idioma.
"""

# Команда /about
ABOUT_MESSAGE = """ℹ️ *Sobre TuExpertoFiscal*

Soy un asistente fiscal inteligente especializado en impuestos de España, creado con tecnología de IA avanzada.

*Mis fuentes de información:*
• 📱 Comunidad de Telegram (IT Autonomos Spain, Chat for Nomads)
• 📄 Documentación oficial de la Agencia Tributaria
• 📰 Noticias fiscales actualizadas
• 📅 Calendario fiscal oficial

*Tecnología:*
• LLM: OpenAI GPT-4.1
• Base de datos: Supabase + pgvector
• Embeddings: Multilingual-E5-Large + OpenAI
• Framework: aiogram 3.x

*Importante:*
⚠️ Proporciono información general. Para casos específicos, consulta siempre a un asesor fiscal profesional.

*Desarrollado por:* AI Tax Consultant Team
*Versión:* 2.0
*Última actualización:* Febrero 2026

¿Tienes alguna pregunta fiscal? ¡Pregúntame!
"""

# Введение для команды /calendar
CALENDAR_INTRO_MESSAGE = """📅 *Próximos vencimientos fiscales*

Aquí están los plazos más cercanos:
"""

# Предупреждения о низкой уверенности
LOW_CONFIDENCE_WARNING_ES = """
⚠️ _La confianza de esta respuesta es baja. Te recomiendo consultar a un profesional._
"""

LOW_CONFIDENCE_WARNING_RU = """
⚠️ _Уверенность в этом ответе низкая. Рекомендую проконсультироваться с профессионалом._
"""
