# src/config.py — cấu hình dùng chung cho cả dự án
from pathlib import Path

# Thư mục gốc project = thư mục cha của src/
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

CITIES = {
    "Hanoi":     {"lat": 21.0285, "lon": 105.8542, "tz": "Asia/Ho_Chi_Minh"},
    "HoChiMinh": {"lat": 10.8231, "lon": 106.6297, "tz": "Asia/Ho_Chi_Minh"},
    "Bangkok":   {"lat": 13.7563, "lon": 100.5018, "tz": "Asia/Bangkok"},
    "Singapore": {"lat": 1.3521,  "lon": 103.8198, "tz": "Asia/Singapore"},
    "Jakarta":   {"lat": -6.2088, "lon": 106.8456, "tz": "Asia/Jakarta"},
}

PARAMS = ["pm25", "pm10", "no2", "o3"]  # các chất ô nhiễm cần lấy

START_DATE, END_DATE = "2025-10-01", "2025-12-31"
START_UTC, END_UTC = "2025-10-01T00:00:00Z", "2025-12-31T23:59:59Z"

# File dữ liệu chuẩn của pipeline
RAW_OPENAQ = RAW_DIR / "openaq_hourly.csv"
RAW_WEATHER = RAW_DIR / "weather_hourly.csv"
CLEAN_FILE = PROCESSED_DIR / "aqi_weather_clean.csv"
FEATURES_FILE = PROCESSED_DIR / "aqi_weather_features.csv"
