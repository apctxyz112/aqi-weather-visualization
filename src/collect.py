# src/collect.py — Bước 2: thu thập dữ liệu từ OpenAQ và Open-Meteo
"""Chạy:  python -m src.collect   (đứng tại thư mục gốc project)"""
import os
import sys
import time

import pandas as pd
import requests
from dotenv import load_dotenv

# Cho phép chạy cả 2 cách:  python -m src.collect  và  python src/collect.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import CITIES, PARAMS, START_UTC, END_UTC, START_DATE, END_DATE, RAW_DIR

load_dotenv()  # đọc key từ file .env, KHÔNG viết key thẳng vào code
OPENAQ_KEY = os.getenv("OPENAQ_API_KEY")
OPENAQ_URL = "https://api.openaq.org/v3"
HEADERS = {"X-API-Key": OPENAQ_KEY} if OPENAQ_KEY else {}


def _check_key():
    if not OPENAQ_KEY:
        raise RuntimeError(
            "Thiếu OPENAQ_API_KEY. Hãy copy file .env.example thành .env "
            "rồi điền key của bạn vào."
        )


def get_sensors(lat, lon, radius_m=25000, max_locations=15):
    r = requests.get(
        f"{OPENAQ_URL}/locations",
        headers=HEADERS,
        timeout=30,
        params={
            "coordinates": f"{lat},{lon}",
            "radius": radius_m,
            "limit": max_locations,
        },
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("results", [])
    if not results:
        print("  ⚠️ Không tìm thấy trạm OpenAQ nào trong bán kính đã cho.")
        return []
    sensors = []
    for loc in results:
        loc_sensors = loc.get("sensors", []) or []
        names = [
            (s.get("parameter") or {}).get("name")
            for s in loc_sensors
        ]
        print(f"  {loc.get('name')}: {names}")  # in ra để kiểm tra
        for s in loc_sensors:
            pname = (s.get("parameter") or {}).get("name")
            if pname in PARAMS and "id" in s:
                sensors.append({
                    "sensor_id": s["id"],
                    "parameter": pname,
                    "location": loc.get("name", "unknown"),
                })
    return sensors


def get_hourly(sensor_id):
    """Lấy dữ liệu trung bình theo giờ của 1 cảm biến, lặp qua các trang."""
    rows, page = [], 1
    while True:
        r = requests.get(
            f"{OPENAQ_URL}/sensors/{sensor_id}/hours",
            headers=HEADERS,
            timeout=60,
            params={
                "datetime_from": START_UTC,
                "datetime_to": END_UTC,
                "limit": 1000,
                "page": page,
            },
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        rows.extend(results)
        if len(results) < 1000:  # trang cuối
            break
        page += 1
        time.sleep(1)  # tránh vượt giới hạn số request
    return rows


def hours_to_df(rows, city, sensor):
    """Chuyển kết quả JSON thành DataFrame phẳng."""
    if not rows:
        return pd.DataFrame(
            columns=["city", "location", "parameter", "datetime_utc", "value"]
        )
    records = []
    for x in rows:
        try:
            period = x.get("period", {})
            dt_from = (period.get("datetimeFrom") or {})
            records.append({
                "city": city,
                "location": sensor["location"],
                "parameter": sensor["parameter"],
                "datetime_utc": dt_from.get("utc"),
                "value": x.get("value"),
            })
        except Exception:
            continue
    return pd.DataFrame(records)


def get_weather(lat, lon):
    """Thời tiết theo giờ (UTC) từ Open-Meteo Archive. Miễn phí, không cần key."""
    r = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        timeout=60,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "hourly": "temperature_2m,relative_humidity_2m,"
                    "wind_speed_10m,precipitation",
            "wind_speed_unit": "ms",
            "timezone": "UTC",
        },
    )
    r.raise_for_status()
    payload = r.json().get("hourly")
    if not payload:
        raise RuntimeError(f"Open-Meteo không trả dữ liệu hourly: {r.text[:200]}")
    return pd.DataFrame(payload).rename(columns={"time": "datetime_utc"})


def main():
    _check_key()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    aq_frames, wx_frames = [], []

    for city, info in CITIES.items():
        print(f"Đang thu thập: {city}")
        sensors = get_sensors(info["lat"], info["lon"])
        if not sensors:
            print(f"  ⚠️ Bỏ qua {city} (không có sensor).")
        for s in sensors:
            try:
                rows = get_hourly(s["sensor_id"])
                df_one = hours_to_df(rows, city, s)
                if not df_one.empty:
                    aq_frames.append(df_one)
            except requests.HTTPError as e:
                print(f"  ⚠️ Lỗi sensor {s['sensor_id']} ({s['parameter']}): {e}")
            time.sleep(1)
        try:
            wx = get_weather(info["lat"], info["lon"])
            wx.insert(0, "city", city)
            wx_frames.append(wx)
        except Exception as e:
            print(f"  ⚠️ Lỗi thời tiết {city}: {e}")

    if not aq_frames:
        raise RuntimeError(
            "Không thu được dòng AQI nào. Kiểm tra lại API key, "
            "khoảng thời gian và kết nối mạng."
        )
    if not wx_frames:
        raise RuntimeError("Không thu được dữ liệu thời tiết nào.")

    pd.concat(aq_frames, ignore_index=True).to_csv(
        RAW_DIR / "openaq_hourly.csv", index=False
    )
    pd.concat(wx_frames, ignore_index=True).to_csv(
        RAW_DIR / "weather_hourly.csv", index=False
    )
    print(f"Xong! Đã lưu vào {RAW_DIR}/")


if __name__ == "__main__":
    main()
