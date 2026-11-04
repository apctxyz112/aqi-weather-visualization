# scripts/make_demo_data.py — tạo dữ liệu demo để chạy thử pipeline không cần API key
"""Chạy:  python scripts/make_demo_data.py   (đứng tại thư mục gốc project)

Sinh 2 file data/raw/openaq_hourly.csv và data/raw/weather_hourly.csv
với định dạng GIỐNG HỆT dữ liệu thật từ collect.py.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import CITIES, PARAMS, START_DATE, END_DATE, RAW_DIR

RNG = np.random.default_rng(42)

# Nền ô nhiễm đặc trưng mỗi thành phố (µg/m³ cho pm25)
BASE_PM25 = {
    "Hanoi": 45.0,
    "HoChiMinh": 28.0,
    "Bangkok": 32.0,
    "Singapore": 15.0,
    "Jakarta": 38.0,
}


def make_weather(city, hours):
    n = len(hours)
    doy = hours.dayofyear.to_numpy()
    hod = hours.hour.to_numpy()
    # Nhiệt độ: dao động ngày + mùa
    temp = 28 + 4 * np.sin((hod - 9) / 24 * 2 * np.pi) + RNG.normal(0, 1.2, n)
    if city in ("Hanoi",):
        temp -= 6 * np.sin((doy - 280) / 92 * np.pi).clip(min=0)  # se lạnh cuối năm
    humidity = (75 - 1.2 * (temp - 25) + RNG.normal(0, 5, n)).clip(30, 100)
    wind = (3.8 + 1.8 * np.sin(hod / 24 * 2 * np.pi + 1) + RNG.normal(0, 1.2, n)).clip(0.2, 12)
    # Mưa: ~12% số giờ có mưa, mưa to ngẫu nhiên
    rain_flag = RNG.random(n) < 0.12
    precip = np.where(rain_flag, RNG.exponential(2.5, n).round(1), 0.0)
    return pd.DataFrame({
        "city": city,
        "datetime_utc": hours.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "temperature_2m": temp.round(1),
        "relative_humidity_2m": humidity.round(0),
        "wind_speed_10m": wind.round(1),
        "precipitation": precip,
    })


def make_pollutants(city, hours, weather):
    hod = hours.hour.to_numpy()
    n = len(hours)
    # PM2.5: cao điểm sáng/tối (giờ cao điểm), giảm khi mưa/gió mạnh
    diurnal = 10 * np.exp(-((hod - 8) ** 2) / 8) + 12 * np.exp(-((hod - 19) ** 2) / 10)
    washout = 1 - 0.45 * (weather["precipitation"] > 0.1).to_numpy()  # mưa rửa bụi
    wind_clean = 1 - 0.08 * (weather["wind_speed_10m"].to_numpy() - 3).clip(min=0)
    base = BASE_PM25.get(city, 30.0)
    pm25 = (base + diurnal) * washout * wind_clean + RNG.normal(0, 5, n)
    pm25 = pm25.clip(3, 250).round(1)

    pm10 = (pm25 * 1.6 + RNG.normal(0, 6, n)).clip(5, 350).round(1)
    no2 = (25 + 12 * np.exp(-((hod - 8) ** 2) / 6) + RNG.normal(0, 5, n)).clip(2, 150).round(1)
    o3 = (35 + 25 * np.exp(-((hod - 14) ** 2) / 12) + RNG.normal(0, 5, n)).clip(2, 200).round(1)
    return {"pm25": pm25, "pm10": pm10, "no2": no2, "o3": o3}


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    hours = pd.date_range(f"{START_DATE}T00:00:00Z", f"{END_DATE}T23:00:00Z", freq="h", tz="UTC")

    aq_frames, wx_frames = [], []
    for city in CITIES:
        wx = make_weather(city, hours)
        wx_frames.append(wx)
        pollutants = make_pollutants(city, hours, wx)
        for p in PARAMS:
            aq_frames.append(pd.DataFrame({
                "city": city,
                "location": f"{city}-demo-station-1",
                "parameter": p,
                "datetime_utc": wx["datetime_utc"],
                "value": pollutants[p],
            }))

    aq = pd.concat(aq_frames, ignore_index=True)
    wx_all = pd.concat(wx_frames, ignore_index=True)

    # Giả lập thiếu dữ liệu 2%: xóa ngẫu nhiên để test nội suy
    drop_idx = RNG.choice(aq.index.to_numpy(), size=int(len(aq) * 0.02), replace=False)
    aq = aq.drop(index=drop_idx).reset_index(drop=True)

    aq.to_csv(RAW_DIR / "openaq_hourly.csv", index=False)
    wx_all.to_csv(RAW_DIR / "weather_hourly.csv", index=False)
    print(f"Đã tạo dữ liệu demo: {len(aq)} dòng AQI, {len(wx_all)} dòng thời tiết.")
    print(f"Lưu tại {RAW_DIR}/")


if __name__ == "__main__":
    main()
