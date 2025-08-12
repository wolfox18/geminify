import os
import re
import random
import json
from dotenv import load_dotenv
from functools import wraps # Импортируем wraps для создания декоратора
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Импортируем наши модули
import gemini_integration
import spotify_integration

# Загружаем переменные окружения
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PLAYLIST_ID = os.getenv("SPOTIFY_PLAYLIST_ID")

# --- Загрузка списка разрешенных пользователей ---
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_IDS", "")
ALLOWED_IDS = [int(user_id) for user_id in ALLOWED_IDS_STR.split(',') if user_id]

if not BOT_TOKEN or not ALLOWED_IDS:
    raise ValueError("Не найдены переменные окружения BOT_TOKEN или ALLOWED_TELEGRAM_IDS. Проверьте .env файл.")

# --- Декоратор для проверки прав доступа ---
def allowed_users_only(func):
    """
    Декоратор, который проверяет, есть ли user_id в списке разрешенных.
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_IDS:
            print(f"🚫 Неавторизованный доступ от пользователя с ID: {user_id}")
            await update.message.reply_text("⛔ У вас нет доступа к этому боту.")
            return
        # Если проверка пройдена, выполняем исходную функцию
        return await func(update, context, *args, **kwargs)
    return wrapped

# Состояния для диалогов
(PROMPT_TEST_STATE, PLAYLIST_UPDATE_STATE) = range(2)

# --- Основные функции бота  ---

@allowed_users_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение и главные кнопки."""
    # ... (код функции не меняется)
    keyboard = [
        [InlineKeyboardButton("🧪 Тестировать промпт", callback_data="prompt_test")],
        [InlineKeyboardButton("🎶 Изменить плейлист Geminify", callback_data="playlist_update")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Привет! Я твой бот для создания плейлистов. Выбери действие:",
        reply_markup=reply_markup
    )
    
async def ask_for_query(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str) -> int:
    """Общая функция, чтобы спросить у пользователя его запрос."""
    # Проверка доступа для кнопок
    user_id = update.effective_user.id
    if user_id not in ALLOWED_IDS:
        print(f"🚫 Неавторизованный доступ (нажатие кнопки) от пользователя с ID: {user_id}")
        await context.bot.answer_callback_query(callback_query_id=update.callback_query.id, text="⛔ У вас нет доступа.", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    await query.answer()
    text = "✍️ Введи свой запрос для Gemini, и я его протестирую."
    next_state = PROMPT_TEST_STATE
    if mode == "playlist":
        text = "🎵 Опиши, какой плейлист ты хочешь, и я создам его для тебя в Spotify."
        next_state = PLAYLIST_UPDATE_STATE
    await query.edit_message_text(text=text)
    return next_state

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущий диалог и возвращает к главному меню."""
    if update.message:
        await update.message.reply_text("Действие отменено.")
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Действие отменено.")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выбери действие:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🧪 Тестировать промпт", callback_data="prompt_test")],
            [InlineKeyboardButton("🎶 Изменить плейлист Geminify", callback_data="playlist_update")]
        ])
    )
    return ConversationHandler.END

# --- Логика тестирования промпта ---

async def handle_prompt_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает запрос для теста, вызывает Gemini и выводит ответ."""
    user_message = update.message.text
    await update.message.reply_text("⏳ Отправляю запрос в Gemini...")
    
    gemini_response = await gemini_integration.get_gemini_response(user_message)
    
    await update.message.reply_text(f"🤖 **Ответ от Gemini:**\n\n{gemini_response}", parse_mode='Markdown')
    
    # Возвращаем пользователя в главное меню
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выбери следующее действие:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🧪 Тестировать промпт", callback_data="prompt_test")],
            [InlineKeyboardButton("🎶 Изменить плейлист Geminify", callback_data="playlist_update")]
        ])
    )
    return ConversationHandler.END

# --- Логика обновления плейлиста ---

def parse_gemini_tracks(text: str) -> list[str]:
    """Извлекает названия треков из нумерованного списка от Gemini."""
    # Ищем строки, которые начинаются с цифры, точки и пробела
    tracks = re.findall(r'^\d+\.\s*(.+)', text, re.MULTILINE)
    return [track.strip() for track in tracks]

# В файле main_bot.py

async def handle_playlist_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Полный цикл обновления плейлиста с динамическим вероятностным фильтром."""
    user_message = update.message.text
    await update.message.reply_text("✨ Начинаю магию... Это может занять до минуты.\n\n1️⃣ / 5️⃣ Получаю плейлист от Gemini...")
    
    gemini_response = await gemini_integration.get_gemini_response(user_message)
    tracks = parse_gemini_tracks(gemini_response)
    
    if not tracks:
        await update.message.reply_text("🤷‍♂️ Gemini не вернул список песен. Попробуй другой запрос.")
        return await cancel(update, context)

    # --- Динамический вероятностный фильтр ---
    
    # Загружаем конфиг фильтрации
    try:
        with open('prompt_config.json', 'r', encoding='utf-8') as f:
            # 👇 ВОТ ИСПРАВЛЕНИЕ: Сначала загружаем ВЕСЬ файл, потом получаем нужную часть
            full_config = json.load(f)
            config = full_config.get('filter_config', {})
    except (FileNotFoundError, json.JSONDecodeError):
        config = {} # В случае ошибки используем значения по умолчанию
        
    initial_prob = config.get('initial_filter_probability', 80) / 100.0
    decay_rate = config.get('filter_decay_rate', 0.9)
    
    print("\n--- Динамическая фильтрация плейлиста от Gemini ---")
    filtered_tracks = []
    for i, track in enumerate(tracks):
        # Рассчитываем вероятность фильтрации для текущей песни
        current_filter_prob = initial_prob * (decay_rate ** i)
        
        # Решаем, добавлять ли трек
        if random.random() > current_filter_prob:
            status = "✅ Выбран"
            filtered_tracks.append(track)
        else:
            status = f"❌ Отфильтрован (шанс удаления {current_filter_prob:.1%})"
        
        # Печатаем результат для каждого трека
        print(f"{i+1}. {track} -> {status}")
    print("--------------------------------------------------\n")
            
    if not filtered_tracks:
        await update.message.reply_text("🤷‍♂️ После вероятностного отбора не осталось ни одного трека. Попробуй еще раз!")
        return await cancel(update, context)
    
    # ... остальная часть функции без изменений ...
    await update.message.reply_text(f"2️⃣ / 5️⃣ Gemini предложил {len(tracks)} треков. После отбора осталось {len(filtered_tracks)}. Ищу их в Spotify...")
    tracks_data = await spotify_integration.get_tracks_data_async(filtered_tracks)
    
    if not tracks_data:
        await update.message.reply_text("🤷‍♂️ Не удалось найти ни одного из отобранных треков в Spotify.")
        return await cancel(update, context)
    
    # tracks_data.reverse()
    
    access_token = spotify_integration.get_new_access_token()
    if not access_token:
        await update.message.reply_text("🔥 Не удалось получить токен доступа Spotify. Проверь логи.")
        return await cancel(update, context)
        
    await update.message.reply_text("3️⃣ / 5️⃣ Очищаю старый плейлист...")
    if not spotify_integration.clear_playlist(access_token):
        await update.message.reply_text("🔥 Не удалось очистить плейлист. Проверь логи.")
        return await cancel(update, context)
        
    await update.message.reply_text(f"4️⃣ / 5️⃣ Добавляю {len(tracks_data)} новых треков...")
    if not spotify_integration.add_tracks_to_playlist(access_token, tracks_data):
        await update.message.reply_text("🔥 Не удалось добавить треки в плейлист. Проверь логи.")
        return await cancel(update, context)
        
    playlist_url = f"https://open.spotify.com/playlist/{PLAYLIST_ID}"
    await update.message.reply_text(f"✅ 5️⃣ / 5️⃣ Готово! Твой новый плейлист здесь: {playlist_url}")
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Хочешь создать еще один? Выбери действие:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🧪 Тестировать промпт", callback_data="prompt_test")],
            [InlineKeyboardButton("🎶 Изменить плейлист Geminify", callback_data="playlist_update")]
        ])
    )
    return ConversationHandler.END

def main() -> None:
    """Основная функция для запуска бота."""
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start), # Декоратор сработает здесь
            CallbackQueryHandler(lambda u, c: ask_for_query(u, c, "test"), pattern='^prompt_test$'),
            CallbackQueryHandler(lambda u, c: ask_for_query(u, c, "playlist"), pattern='^playlist_update$')
        ],
        states={
            PROMPT_TEST_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt_test)],
            PLAYLIST_UPDATE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_playlist_update)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True 
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start)) # Добавляем и обычный /start с проверкой

    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()