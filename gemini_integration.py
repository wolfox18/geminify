import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import asyncio

# Загружаем ключи из .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("Не найден ключ API для Gemini. Проверьте ваш .env файл.")

# Настраиваем API-клиент один раз при запуске
genai.configure(api_key=GEMINI_API_KEY)


# --- ОСНОВНАЯ ФУНКЦИЯ ---

async def get_gemini_response(user_prompt: str) -> str:
    """
    Отправляет запрос в API Gemini, используя конфигурацию из файла prompt_config.json.
    Читает конфигурацию при каждом вызове.
    """
    try:
        # Шаг 1: Читаем конфигурацию из файла
        with open('prompt_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Шаг 2: Инициализируем модель с параметрами из файла
        model = genai.GenerativeModel(
            # 👇 ВОТ ИЗМЕНЕНИЕ: читаем имя модели из конфига
            model_name=config["model_name"], 
            generation_config=config["generation_config"],
            safety_settings=config["safety_settings"]
        )

        # Шаг 3: Собираем полный промпт
        full_prompt = f"{config['system_prompt']}\n\nЗАПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_prompt}"

        # Шаг 4: Отправляем запрос в API
        response = await asyncio.to_thread(
            model.generate_content,
            full_prompt
        )
        return response.text

    except FileNotFoundError:
        error_message = "Ошибка: Файл конфигурации prompt_config.json не найден."
        print(error_message)
        return error_message
    except json.JSONDecodeError:
        error_message = "Ошибка: Не удалось прочитать prompt_config.json. Проверьте синтаксис JSON."
        print(error_message)
        return error_message
    except KeyError as e:
        error_message = f"Ошибка: в файле prompt_config.json отсутствует обязательный ключ: {e}."
        print(error_message)
        return error_message
    except Exception as e:
        error_message = f"Произошла ошибка при запросе к Gemini API: {e}"
        print(error_message)
        return f"К сожалению, не удалось получить ответ от нейросети. 😔\n\n**Техническая информация:**\n`{e}`"