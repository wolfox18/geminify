import os
import base64
import httpx
import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")
PLAYLIST_ID = os.getenv("SPOTIFY_PLAYLIST_ID")

# --- УПРАВЛЕНИЕ ТОКЕНОМ ДОСТУПА ---

def get_new_access_token():
    """Синхронная функция для получения токена."""
    # ... (код этой функции не меняется)
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_base64 = str(base64.b64encode(auth_string.encode('utf-8')), 'utf-8')
    url = "https://accounts.spotify.com/api/token"
    headers = {"Authorization": f"Basic {auth_base64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
    
    response = httpx.post(url, headers=headers, data=data)
    if response.status_code != 200:
        print(f"🔥 Ошибка обновления токена: {response.json()}")
        return None
    return response.json().get("access_token")

# --- АСИНХРОННЫЕ ФУНКЦИИ ПОИСКА ---

async def search_track_async(client: httpx.AsyncClient, track_name: str):
    """Асинхронно ищет ОДИН трек и возвращает СЛОВАРЬ {название, исполнитель, uri}."""
    url = "https://api.spotify.com/v1/search"
    params = {"q": track_name, "type": "track", "limit": 1}
    
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        items = response.json().get("tracks", {}).get("items", [])
        if items:
            track_info = items[0]
            # 👇 ИЗМЕНЕНИЕ: Возвращаем словарь вместо строки
            return {
                "name": track_info.get("name"),
                "artist": track_info["artists"][0].get("name") if track_info.get("artists") else "Неизвестен",
                "uri": track_info.get("uri")
            }
        else:
            print(f"❌ Не найден: {track_name}")
            return None
    except httpx.RequestError as e:
        print(f"🔥 Ошибка сети при поиске '{track_name}': {e}")
        return None

async def get_tracks_data_async(track_list: list[str]) -> list[dict]:
    """Асинхронно ищет ВСЕ треки и возвращает список словарей."""
    access_token = get_new_access_token()
    if not access_token: return []

    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient(headers=headers) as client:
        tasks = [search_track_async(client, name) for name in track_list]
        results = await asyncio.gather(*tasks)
    
    return [track_data for track_data in results if track_data and track_data.get("uri")]

# --- СИНХРОННЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ПЛЕЙЛИСТОМ ---

def clear_playlist(access_token):
    """Удаляет все треки из плейлиста."""
    # ... (код этой функции не меняется)
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    get_tracks_url = f"https://api.spotify.com/v1/playlists/{PLAYLIST_ID}/tracks"
    response = httpx.get(get_tracks_url, headers=headers, params={"fields": "items(track(uri))"})
    if response.status_code != 200: return False
    tracks_to_delete = response.json().get("items", [])
    if not tracks_to_delete: 
        print("Плейлист уже пуст.")
        return True
    uris_to_delete = [{"uri": item["track"]["uri"]} for item in tracks_to_delete]
    delete_url = f"https://api.spotify.com/v1/playlists/{PLAYLIST_ID}/tracks"
    with httpx.Client() as client:
        for i in range(0, len(uris_to_delete), 100):
            chunk = uris_to_delete[i:i + 100]
            request_body = json.dumps({"tracks": chunk})
            request = httpx.Request("DELETE", delete_url, headers=headers, content=request_body)
            delete_response = client.send(request)
            if delete_response.status_code not in [200, 201]: 
                print(f"🔥 Ошибка при удалении треков: {delete_response.text}")
                return False
    print(f"Плейлист очищен, удалено {len(uris_to_delete)} треков.")
    return True

def add_tracks_to_playlist(access_token, tracks_data: list[dict]):
    """Добавляет треки в плейлист и ЛОГИРУЕТ их названия."""
    if not tracks_data: return False
    
    # Извлекаем только URI для запроса к API
    track_uris = [track['uri'] for track in tracks_data]

    # 👇 ИЗМЕНЕНИЕ: Логируем то, что собираемся добавить
    print("\n--- Добавление треков в плейлист Spotify ---")
    for track in tracks_data:
        print(f"🎵 {track.get('artist')} - {track.get('name')}")
    print("-------------------------------------------\n")
    
    url = f"https://api.spotify.com/v1/playlists/{PLAYLIST_ID}/tracks"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    for i in range(0, len(track_uris), 100):
        chunk = track_uris[i:i + 100]
        response = httpx.post(url, headers=headers, json={"uris": chunk})
        if response.status_code not in [200, 201]: return False
    
    print(f"В плейлист добавлено {len(track_uris)} новых треков.")
    return True