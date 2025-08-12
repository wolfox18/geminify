import os  # Импортируем модуль для работы с ОС
from dotenv import load_dotenv  # Импортируем функцию из новой библиотеки
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler, # Добавили для управления диалогами
    MessageHandler,
    filters, # Добавили для фильтрации сообщений (например, только текст)
    ContextTypes
)

# Импортируем нашу новую функцию для работы с Gemini
from gemini_integration import get_gemini_response

# Загружаем переменные из .env файла в окружение
load_dotenv()

# --- ВАШИ ДАННЫЕ (теперь читаются из окружения) ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Проверка, что токен был найден
if not BOT_TOKEN:
    print("Ошибка: Не найден токен для Telegram бота. Проверьте ваш .env файл.")
    exit()

# --- СОСТОЯНИЯ ДЛЯ ДИАЛОГА ---
# Определяем числовые константы для разных этапов диалога.
# Это помогает боту понять, какого ответа он сейчас ждет от пользователя.
WAITING_FOR_GEMINI_PROMPT = 1

# --- ОБРАБОТЧИКИ КОМАНД И КНОПОК ---

# Эта функция, как и раньше, вызывается по команде /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение и показывает две кнопки."""
    keyboard = [
        [InlineKeyboardButton("Простая кнопка", callback_data="simple_button_pressed")],
        # Новая кнопка, которая запустит диалог с Gemini
        [InlineKeyboardButton("✍️ Тестировать Gemini", callback_data="start_gemini_test")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Привет! Я бот. Нажми 'Простая кнопка' для обычного ответа или 'Тестировать Gemini', чтобы задать вопрос нейросети.",
        reply_markup=reply_markup
    )

# Эта функция вызывается при нажатии на "Простая кнопка"
async def simple_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие на простую кнопку."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Это ответ от простой кнопки!")

# НОВАЯ ФУНКЦИЯ: Запускает диалог с Gemini
async def start_gemini_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Вызывается при нажатии кнопки "Тестировать Gemini".
    Просит пользователя ввести свой вопрос.
    """
    query = update.callback_query
    await query.answer()
    # Редактируем сообщение, чтобы убрать кнопки и дать инструкцию
    await query.edit_message_text(text="Отлично! Теперь отправь мне свой вопрос или сообщение, и я перешлю его Gemini.")
    
    # Возвращаем боту состояние, в котором он будет ждать текстовое сообщение
    return WAITING_FOR_GEMINI_PROMPT

# НОВАЯ ФУНКЦИЯ: Обрабатывает сообщение для Gemini
async def handle_gemini_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Принимает текстовое сообщение от пользователя, отправляет его в Gemini,
    возвращает ответ и завершает диалог.
    """
    user_message = update.message.text
    
    # Сообщаем пользователю, что мы обрабатываем его запрос
    await update.message.reply_text("⏳ Минутку, отправляю ваш запрос в Gemini...")
    
    # Вызываем нашу функцию из модуля gemini_integration
    gemini_response = await get_gemini_response(user_message)
    
    # Отправляем ответ от Gemini пользователю
    await update.message.reply_text(f"🤖 **Ответ от Gemini:**\n\n{gemini_response}", parse_mode='Markdown')
    
    # Завершаем диалог
    return ConversationHandler.END

# НОВАЯ ФУНКЦИЯ: для отмены диалога
async def cancel_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущий диалог."""
    await update.message.reply_text("Действие отменено. Вы можете начать заново командой /start.")
    return ConversationHandler.END


# --- ЗАПУСК БОТА ---

def main() -> None:
    """Основная функция для запуска бота."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Создаем ConversationHandler для управления диалогом с Gemini
    gemini_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_gemini_dialog, pattern='^' + 'start_gemini_test' + '$')],
        states={
            WAITING_FOR_GEMINI_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gemini_message)],
        },
        fallbacks=[CommandHandler('cancel', cancel_dialog)],
    )

    # Регистрируем обработчики в приложении
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(simple_button_handler, pattern='^' + 'simple_button_pressed' + '$'))
    application.add_handler(gemini_conv_handler) # Регистрируем наш новый сложный обработчик диалога

    print("Бот запущен...")
    application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())