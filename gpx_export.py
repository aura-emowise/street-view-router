# gpx_export.py
def create_gpx(optimized_points, filename="route.gpx"):
    """
    Создаёт GPX-файл из списка оптимизированных точек.
    """
    header = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Street View Router" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Оптимальный маршрут</name>
    <trkseg>'''

    body = ""
    for i, (lat, lon) in enumerate(optimized_points):
        body += f'    <trkpt lat="{lat}" lon="{lon}"><name>{i+1}</name></trkpt>\n'

    footer = '''    </trkseg>
  </trk>
</gpx>'''

    with open(filename, "w", encoding="utf-8") as f:
        f.write(header + body + footer)

    return filename