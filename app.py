# app.py — Bước 6: dashboard Streamlit
"""Chạy:  streamlit run app.py   (đứng tại thư mục gốc project)"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.charts import line_aqi, bar_top_cities, scatter_wind_aqi, heatmap_hour_city, box_weather
from src.config import CITIES, FEATURES_FILE

st.set_page_config(page_title="AQI & Thời tiết", layout="wide")


@st.cache_data  # chỉ đọc file một lần, các lần sau lấy từ cache
def load_data():
    # LỖI CŨ: đường dẫn tương đối "data/processed/..." vỡ khi chạy từ thư mục khác.
    # BẢN SỬA: đường dẫn tuyệt đối từ config.
    if not FEATURES_FILE.exists():
        return None
    df = pd.read_csv(FEATURES_FILE, parse_dates=["datetime_local"])
    return df.dropna(subset=["AQI"])


df = load_data()

if df is None or df.empty:
    st.title("Chất lượng không khí (AQI) và tác động của thời tiết")
    st.error(
        "Chưa có dữ liệu để hiển thị.\n\n"
        "Cách tạo dữ liệu:\n"
        "1. Dữ liệu demo (nhanh, không cần API key): "
        "`python scripts/make_demo_data.py`, rồi chạy tiếp "
        "`python -m src.clean` và `python -m src.features`.\n"
        "2. Dữ liệu thật: điền key vào file `.env`, rồi chạy "
        "`python -m src.collect`, `python -m src.clean`, `python -m src.features`."
    )
    st.stop()

# ---------- Sidebar: slicer ----------
st.sidebar.header("Bộ lọc")
all_cities = sorted(df["city"].unique())
sel_cities = st.sidebar.multiselect("Thành phố", all_cities, default=all_cities)

weather_opts = sorted(df["Weather_Category"].dropna().unique().tolist()) or ["Rainy", "Dry"]
sel_weather = st.sidebar.multiselect("Loại thời tiết", weather_opts, default=weather_opts)

# LỖI CŨ: date_input crash khi df rỗng / min>max. BẢN SỬA: kiểm tra biên hợp lệ.
dmin = df["datetime_local"].min()
dmax = df["datetime_local"].max()
dates = st.sidebar.date_input(
    "Khoảng thời gian",
    value=(dmin.date(), dmax.date()),
    min_value=dmin.date(),
    max_value=dmax.date(),
)

if not (isinstance(dates, (tuple, list)) and len(dates) == 2):
    st.info("Hãy chọn đủ ngày bắt đầu và kết thúc.")
    st.stop()

if not sel_cities or not sel_weather:
    st.warning("Hãy chọn ít nhất 1 thành phố và 1 loại thời tiết.")
    st.stop()

# ---------- Lọc dữ liệu ----------
t0 = pd.Timestamp(dates[0])
t1 = pd.Timestamp(dates[1]) + pd.Timedelta(days=1)
mask = (
    df["city"].isin(sel_cities)
    & df["Weather_Category"].isin(sel_weather)
    & df["datetime_local"].between(t0, t1, inclusive="left")
)
f = df[mask].copy()

if f.empty:
    st.warning("Không có dữ liệu với bộ lọc hiện tại.")
    st.stop()

st.title("Chất lượng không khí (AQI) và tác động của thời tiết")
tab1, tab2, tab3 = st.tabs(["Tổng quan", "Phân tích AQI", "Tác động thời tiết"])

# ---------- Tab 1: Tổng quan ----------
with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("AQI trung bình", f"{f['AQI'].mean():.0f}")
    c2.metric("AQI cao nhất", f"{f['AQI'].max():.0f}")
    c3.metric("Tỷ lệ giờ AQI > 100", f"{(f['AQI'] > 100).mean():.1%}")

    st.plotly_chart(line_aqi(f), use_container_width=True)

    geo = f.groupby("city", as_index=False)["AQI"].mean()
    # LỖI CŨ: KeyError nếu city trong data không có trong CITIES.
    # BẢN SỬA: dùng .get + bỏ dòng thiếu tọa độ.
    geo["lat"] = geo["city"].map(lambda c: (CITIES.get(c) or {}).get("lat"))
    geo["lon"] = geo["city"].map(lambda c: (CITIES.get(c) or {}).get("lon"))
    geo = geo.dropna(subset=["lat", "lon"])
    if not geo.empty:
        st.plotly_chart(
            px.scatter_geo(
                geo, lat="lat", lon="lon", size="AQI", color="AQI",
                hover_name="city", projection="natural earth",
                title="Bản đồ AQI trung bình theo thành phố",
            ),
            use_container_width=True,
        )
    else:
        st.info("Không đủ tọa độ để vẽ bản đồ.")

# ---------- Tab 2: Phân tích AQI ----------
with tab2:
    st.plotly_chart(heatmap_hour_city(f), use_container_width=True)
    st.plotly_chart(bar_top_cities(f), use_container_width=True)

# ---------- Tab 3: Tác động thời tiết ----------
with tab3:
    st.plotly_chart(scatter_wind_aqi(f), use_container_width=True)
    st.plotly_chart(box_weather(f), use_container_width=True)
