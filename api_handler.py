# api_handler.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()

MAPBOX_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN")

def optimize_route(points):
    """
    Отправляет точки в Mapbox Optimization API и возвращает оптимизированный маршрут.
    """
    if not MAPBOX_TOKEN:
        return {"success": False, "error": "API-ключ Mapbox не найден."}

    # Подготавливаем координаты: lon,lat (важно для Mapbox)
    coordinates = ';'.join([f"{lon},{lat}" for lat, lon in points])
    url = f"https://api.mapbox.com/optimized-trips/v1/mapbox/driving/{coordinates}"

    params = {
        "access_token": MAPBOX_TOKEN,
        "steps": "true",
        "geometries": "polyline6"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if response.status_code != 200:
            error_msg = data.get("message", "Неизвестная ошибка")
            return {"success": False, "error": f"Mapbox API ошибка: {error_msg}"}

        if data.get("code") != "Ok":
            return {"success": False, "error": f"Ошибка маршрута: {data.get('message', 'Неизвестно')}"}

        # Извлекаем маршрут
        route = data["trips"][0]
        waypoints = data["waypoints"]
        geometry = route["geometry"]  # polyline6
        distance = route["distance"] / 1000  # км
        duration = route["duration"] / 60  # минуты

        return {
            "success": True,
            "optimized_points": [(wp["location"][1], wp["location"][0]) for wp in waypoints],  # lat, lon
            "polyline": geometry,
            "distance_km": round(distance, 2),
            "duration_min": round(duration, 1)
        }

    except Exception as e:
        return {"success": False, "error": f"Ошибка подключения к API: {str(e)}"}