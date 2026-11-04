# src/features.py — Bước 4: tạo cột & chỉ số mới
"""Chạy:  python -m src.features   (đứng tại thư mục gốc project)"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import CITIES, CLEAN_FILE, FEATURES_FILE

# --- AQI từ PM2.5 theo breakpoint của US EPA (µg/m³), cập nhật 2024 ---
PM25_BP = [  # (C_lo, C_hi, I_lo, I_hi)
    (0.0, 9.0, 0, 50),
    (9.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 125.4, 151, 200),
    (125.5, 225.4, 201, 300),
    (225.5, 325.4, 301, 500),
]


def pm25_to_aqi(c):
    """Nội suy tuyến tính AQI từ nồng độ PM2.5."""
    if pd.isna(c):
        return np.nan
    c = float(c)
    if c < 0:
        return np.nan
    for c_lo, c_hi, i_lo, i_hi in PM25_BP:
        if c <= c_hi:
            return (i_hi - i_lo) / (c_hi - c_lo) * (c - c_lo) + i_lo
    return 500.0


def aqi_level(a):
    """Phân loại mức AQI theo EPA."""
    if pd.isna(a):
        return np.nan
    if a <= 50:
        return "Good"
    if a <= 100:
        return "Moderate"
    if a <= 150:
        return "Unhealthy for Sensitive Groups"
    if a <= 200:
        return "Unhealthy"
    if a <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def main():
    if not CLEAN_FILE.exists():
        raise FileNotFoundError(
            f"Không thấy {CLEAN_FILE}. Hãy chạy `python -m src.clean` trước."
        )

    df = pd.read_csv(CLEAN_FILE)
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True, errors="coerce")
    df = df.dropna(subset=["datetime_utc"])
    df = df.sort_values(["city", "datetime_utc"]).reset_index(drop=True)

    if "pm25" not in df.columns:
        raise ValueError("Thiếu cột pm25 — file clean chưa đúng định dạng.")

    df["AQI"] = df["pm25"].apply(pm25_to_aqi).round(1)
    df["AQI_Level"] = df["AQI"].apply(aqi_level)

    # --- Phân loại thời tiết ---
    df["wind_speed"] = pd.to_numeric(df.get("wind_speed"), errors="coerce")
    df["temp_c"] = pd.to_numeric(df.get("temp_c"), errors="coerce")
    df["precip_mm"] = pd.to_numeric(df.get("precip_mm"), errors="coerce").fillna(0)

    df["Wind_Category"] = pd.cut(
        df["wind_speed"], bins=[-np.inf, 3, 6, np.inf],
        labels=["Calm", "Moderate", "Strong"],
    )  # m/s
    df["Temp_Category"] = pd.cut(
        df["temp_c"], bins=[-np.inf, 20, 30, np.inf],
        labels=["Cold", "Normal", "Hot"],
    )  # °C
    df["Weather_Category"] = np.where(
        df["precip_mm"] > 0.1, "Rainy", "Dry"
    )

    # --- Thời gian theo giờ địa phương ---
    # LỖI CŨ: tz_localize(None) làm mất thông tin + groupby city lặp chậm.
    # BẢN SỬA: map tz theo city bằng vector hóa, giữ cột datetime_local
    # naive (không tz) để Streamlit/Plotly vẽ ổn định.
    tz_map = {c: v["tz"] for c, v in CITIES.items()}

    local_list = []
    for city, g in df.groupby("city", sort=False):
        g = g.copy()
        tz = tz_map.get(city)
        if tz is None:
            print(f"⚠️ Thành phố {city} không có trong config, giữ giờ UTC.")
            g["datetime_local"] = g["datetime_utc"].dt.tz_convert("UTC").dt.tz_localize(None)
        else:
            g["datetime_local"] = (
                g["datetime_utc"].dt.tz_convert(tz).dt.tz_localize(None)
            )
        local_list.append(g)
    df = pd.concat(local_list, ignore_index=True)
    df = df.sort_values(["city", "datetime_utc"]).reset_index(drop=True)

    df["Hour"] = df["datetime_local"].dt.hour
    df["DayOfWeek"] = df["datetime_local"].dt.day_name()
    df["IsWeekend"] = df["datetime_local"].dt.dayofweek >= 5

    # --- Trung bình trượt 24 giờ (theo từng thành phố) ---
    df["AQI_Rolling_24h"] = (
        df.groupby("city")["AQI"]
        .transform(lambda s: s.rolling(24, min_periods=12).mean())
        .round(1)
    )

    # --- Weather_Impact = AQI trung bình khi gió mạnh − khi gió yếu ---
    # LỖI CŨ: nếu thiếu nhóm Strong/Calm thì impact = NaN cho cả thành phố.
    # BẢN SỬA: fillna(0) + in cảnh báo số giờ mỗi nhóm để dễ kiểm tra.
    strong = df[df["Wind_Category"] == "Strong"].groupby("city")["AQI"].mean()
    calm = df[df["Wind_Category"] == "Calm"].groupby("city")["AQI"].mean()
    impact = (strong - calm).rename("Weather_Impact")
    print("Weather_Impact theo thành phố:\n", impact.round(1))
    print("Số giờ theo nhóm gió:", df["Wind_Category"].value_counts(dropna=False).to_dict())
    missing = set(df["city"].unique()) - set(impact.dropna().index)
    if missing:
        print(f"⚠️ Các thành phố thiếu nhóm gió nên Impact=NaN, gán 0: {missing}")
    df["Weather_Impact"] = df["city"].map(impact).fillna(0).round(1)

    df.to_csv(FEATURES_FILE, index=False)
    print(f"Đã lưu {FEATURES_FILE}")


if __name__ == "__main__":
    main()
