# app.py
import streamlit as st
import pydeck as pdk
import polyline
import os
from dotenv import load_dotenv
import numpy as np
from sklearn.cluster import KMeans

load_dotenv()
MAPBOX_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN")
if not MAPBOX_TOKEN:
    st.error("❌ MAPBOX_ACCESS_TOKEN не найден в .env")
    st.stop()

st.set_page_config(page_title="Street View Маршрутизатор", layout="wide")
st.title("📹 Оптимизатор маршрутов для съёмки улиц")

st.markdown("""
Загрузите `.txt` файл с улицами в формате:  
`название улицы: широта1,долгота1-широта2,долгота2`

Поддержка до 500+ координат.
""")

uploaded_file = st.file_uploader("Загрузите список улиц (.txt)", type=["txt"])

def cluster_points(points, max_points_per_cluster=12):
    if len(points) <= max_points_per_cluster:
        return [points]
    n_clusters = (len(points) + max_points_per_cluster - 1) // max_points_per_cluster
    kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(points)
    labels = kmeans.labels_
    clusters = [[] for _ in range(n_clusters)]
    for i, label in enumerate(labels):
        clusters[label].append(points[i])
    return clusters

def parse_route_file(content):
    lines = content.splitlines()
    points = []
    segments = []
    errors = []
    import re
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"): continue
        try:
            if ':' in line:
                name_part, coord_part = line.split(':', 1)
                street_name = name_part.strip()
            else:
                street_name = f"Улица {len(segments)+1}"
                coord_part = line
            match = re.search(r'(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\s*-\s*(-?\d+\.?\d*),\s*(-?\d+\.?\d*)', coord_part)
            if not match: continue
            lat1, lon1, lat2, lon2 = map(float, match.groups())
            points.append((lat1, lon1))
            points.append((lat2, lon2))
            segments.append({"name": street_name, "start": (lat1, lon1), "end": (lat2, lon2)})
        except Exception as e:
            errors.append(f"Ошибка в строке {line_num}: {str(e)}")
    if not points: return {"success": False, "error": "Нет данных."}
    return {"success": True, "points": points, "segments": segments, "errors": errors}

def optimize_route(points):
    if not MAPBOX_TOKEN: return {"success": False, "error": "Токен не найден"}
    coordinates = ';'.join([f"{lon},{lat}" for lat, lon in points])
    url = f"https://api.mapbox.com/optimized-trips/v1/mapbox/driving/{coordinates}"
    import requests
    params = {"access_token": MAPBOX_TOKEN, "steps": "true", "geometries": "polyline6"}
    try:
        response = requests.get(url, params=params).json()
        if response.get("code") != "Ok": return {"success": False, "error": "Ошибка API"}
        route = response["trips"][0]
        waypoints = response["waypoints"]
        geometry = route["geometry"]
        distance = route["distance"] / 1000
        duration = route["duration"] / 60
        return {
            "success": True,
            "optimized_points": [(wp["location"][1], wp["location"][0]) for wp in waypoints],
            "polyline": geometry,
            "distance_km": round(distance, 2),
            "duration_min": round(duration, 1)
        }
    except Exception as e:
        return {"success": False, "error": f"Ошибка: {str(e)}"}

def create_gpx(optimized_points, filename="route.gpx"):
    header = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Street View Router">
  <trk><name>Маршрут</name><trkseg>'''
    body = ''.join([f'<trkpt lat="{lat}" lon="{lon}"><name>{i+1}</name></trkpt>\n' for i, (lat, lon) in enumerate(optimized_points)])
    footer = '''</trkseg></trk></gpx>'''
    with open(filename, "w", encoding="utf-8") as f: f.write(header + body + footer)
    return filename

if uploaded_file is not None:
    try:
        content = uploaded_file.read().decode("utf-8")
    except Exception as e:
        st.error(f"Ошибка чтения: {e}")
    else:
        parsed = parse_route_file(content)
        if not parsed["success"]: st.error(parsed["error"])
        else:
            points = parsed["points"]
            st.info(f"✅ Найдено {len(points)//2} улиц ({len(points)} координат)")
            clusters = cluster_points(points, 12)
            all_optimized = []
            all_polylines = []
            total_distance = 0.0
            total_duration = 0.0
            for i, cluster in enumerate(clusters):
                with st.spinner(f"Оптимизация группы {i+1}/{len(clusters)}..."):
                    result = optimize_route(cluster)
                    if result["success"]:
                        all_optimized.extend(result["optimized_points"])
                        total_distance += result["distance_km"]
                        total_duration += result["duration_min"]
                        try:
                            decoded = polyline.decode(result["polyline"])
                            path = [[lon, lat] for lat, lon in decoded]
                            all_polylines.append({"path": path})
                        except: pass
                    else:
                        st.warning(f"Ошибка в группе {i+1}: {result['error']}")
            if all_optimized:
                st.success("✅ Все группы оптимизированы!")
                st.metric("Общее расстояние", f"{total_distance:.2f} км")
                if all_polylines:
                    view_state = pdk.ViewState(
                        latitude=np.mean([p[0] for p in all_optimized]),
                        longitude=np.mean([p[1] for p in all_optimized]),
                        zoom=10
                    )
                    r = pdk.Deck(
                        layers=[
                            pdk.Layer("PathLayer", data=all_polylines, get_path="path", get_color=[255,0,0], width_min_pixels=3),
                            pdk.Layer("ScatterplotLayer", data=[{"lon": lon, "lat": lat} for lat, lon in all_optimized], get_position=["lon","lat"], get_radius=50, get_fill_color=[0,128,255])
                        ],
                        initial_view_state=view_state,
                        map_style=f"mapbox://styles/mapbox/light-v10?access_token={MAPBOX_TOKEN}",
                        api_keys={"mapbox": MAPBOX_TOKEN}
                    )
                    st.pydeck_chart(r)
                all_points = all_optimized
                if len(all_points) > 1:
                    origin = f"{all_points[0][0]},{all_points[0][1]}"
                    destination = f"{all_points[-1][0]},{all_points[-1][1]}"
                    google_waypoints = "|".join([f"{lat},{lon}" for lat, lon in all_points[1:-1]])
                    yandex_points = "~".join([f"{lat},{lon}" for lat, lon in all_points])
                    google_url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={google_waypoints}"
                    yandex_url = f"https://yandex.ru/maps/?rtext={yandex_points}&rtt=1"
                    st.markdown(f'<a href="{google_url}" target="_blank" style="background:#4285F4; color:white; padding:10px; border-radius:5px; text-decoration:none;">🌍 Google Maps</a>', unsafe_allow_html=True)
                    st.markdown(f'<a href="{yandex_url}" target="_blank" style="background:#FFCC00; color:black; padding:10px; border-radius:5px; text-decoration:none;">🟡 Яндекс.Карты</a>', unsafe_allow_html=True)
                    gpx_file = create_gpx(all_optimized)
                    with open(gpx_file, "r", encoding="utf-8") as f:
                        st.download_button("💾 Скачать маршрут (.gpx)", f.read(), "route.gpx", "application/gpx+xml")