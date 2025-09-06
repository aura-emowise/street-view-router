# route_logic.py
import re

def parse_route_file(file_content):
    """
    Парсит содержимое файла .txt и возвращает список точек (lat, lon)
    из отдельных точек и сегментов.
    Поддерживает формат:
      - Отдельная точка: 55.7558,37.6176
      - Сегмент: улица Ленина: 55.7558,37.6176-55.7600,37.6250
    """
    lines = file_content.splitlines()
    points = []
    segments = []
    errors = []

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue  # Пропускаем пустые строки и комментарии

        try:
            # Проверим, есть ли имя улицы (до двоеточия)
            if ':' in line:
                name_part, coord_part = line.split(':', 1)
                street_name = name_part.strip()
            else:
                street_name = f"Улица {len(segments)+1}"
                coord_part = line

            # Ищем координаты в формате lat1,lon1-lat2,lon2 или просто lat,lon
            if '-' in coord_part:
                # Это сегмент
                part1, part2 = coord_part.split('-', 1)
                lat1, lon1 = map(float, map(str.strip, part1.split(',')))
                lat2, lon2 = map(float, map(str.strip, part2.split(',')))
                points.append((lat1, lon1))
                points.append((lat2, lon2))
                segments.append({
                    "name": street_name,
                    "start": (lat1, lon1),
                    "end": (lat2, lon2)
                })
            else:
                # Это отдельная точка
                lat, lon = map(float, map(str.strip, coord_part.split(',')))
                points.append((lat, lon))
                segments.append({
                    "name": street_name,
                    "start": (lat, lon),
                    "end": None
                })
        except Exception as e:
            errors.append(f"Ошибка в строке {line_num}: '{line}'. Формат: 'lat,lon' или 'lat1,lon1-lat2,lon2'")

    if not points:
        return {"success": False, "error": "Файл не содержит корректных данных."}

    return {"success": True, "points": points, "segments": segments, "errors": errors}