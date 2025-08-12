import requests
import base64
import os
from dotenv import load_dotenv

# Загружаем переменные из .env, чтобы получить ID и Secret клиента
load_dotenv()
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
# Этот Redirect URI должен точно совпадать с тем, что в настройках приложения Spotify
REDIRECT_URI = "https://www.google.com/"


def get_refresh_token():
    """Обменивает одноразовый код на постоянный Refresh Token."""
    one_time_code = input("Пожалуйста, вставьте ваш ONE_TIME_CODE из адресной строки браузера:\n> ")
    if not one_time_code:
        print("🛑 Код не был введён. Выход.")
        return

    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_base64 = str(base64.b64encode(auth_string.encode('utf-8')), 'utf-8')

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": one_time_code,
        "redirect_uri": REDIRECT_URI
    }

    try:
        result = requests.post(url, headers=headers, data=data)
        result.raise_for_status()
        json_result = result.json()
        refresh_token = json_result.get("refresh_token")

        print("\n✅ УСПЕШНО!")
        print("Сохраните этот Refresh Token в ваш .env файл как SPOTIFY_REFRESH_TOKEN")
        print("="*50)
        print(refresh_token)
        print("="*50)

    except requests.exceptions.RequestException as e:
        print(f"🔥 Произошла ошибка при запросе: {e}")
        print(f"Ответ от сервера: {result.text if 'result' in locals() else 'нет ответа'}")


def create_playlist():
    """Создаёт приватный плейлист 'Geminify' и выводит его ID."""
    refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")
    if not refresh_token:
        print("🛑 Сначала получите Refresh Token и добавьте его в .env файл.")
        return
        
    # Сначала получим свежий Access Token
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_base64 = str(base64.b64encode(auth_string.encode('utf-8')), 'utf-8')
    url_token = "https://accounts.spotify.com/api/token"
    headers_token = {"Authorization": f"Basic {auth_base64}", "Content-Type": "application/x-www-form-urlencoded"}
    data_token = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    
    result = requests.post(url_token, headers=headers_token, data=data_token)
    if result.status_code != 200:
        print("🔥 Не удалось обновить Access Token для создания плейлиста.")
        return
        
    access_token = result.json().get("access_token")

    # Получим User ID
    user_info_result = requests.get("https://api.spotify.com/v1/me", headers={"Authorization": f"Bearer {access_token}"})
    if user_info_result.status_code != 200:
        print("🔥 Не удалось получить User ID.")
        return
    user_id = user_info_result.json().get("id")

    # Создадим плейлист
    url_playlist = f"https://api.spotify.com/v1/users/{user_id}/playlists"
    headers_playlist = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data_playlist = {
        "name": "Geminify",
        "description": "Make AI playlist great again!",
        "public": False
    }

    try:
        result = requests.post(url_playlist, headers=headers_playlist, json=data_playlist)
        result.raise_for_status()
        playlist_id = result.json().get("id")
        
        print("\n✅ УСПЕШНО!")
        print("Плейлист 'Geminify Playlist' создан.")
        print("Сохраните этот ID в ваш .env файл как SPOTIFY_PLAYLIST_ID")
        print("="*50)
        print(playlist_id)
        print("="*50)

    except requests.exceptions.RequestException as e:
        print(f"🔥 Произошла ошибка при создании плейлиста: {e}")
        print(f"Ответ от сервера: {result.text if 'result' in locals() else 'нет ответа'}")


if __name__ == "__main__":
    print("--- Утилита для настройки проекта ---")
    choice = input("Что вы хотите сделать?\n1 - Получить Refresh Token\n2 - Создать плейлист 'Geminify'\nВведите номер: ")
    if choice == "1":
        get_refresh_token()
    elif choice == "2":
        create_playlist()
    else:
        print("Неверный выбор.")