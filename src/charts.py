# src/charts.py — Bước 5: 5 đồ thị Plotly (mỗi hàm nhận DataFrame, trả về figure)
import pandas as pd
import plotly.express as px


def _need_cols(df, cols, name):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name}: thiếu cột {missing}")


def line_aqi(df):
    """1. Line chart: AQI trung bình trượt 24h theo thời gian."""
    _need_cols(df, ["datetime_local", "AQI_Rolling_24h", "city"], "line_aqi")
    d = df.dropna(subset=["AQI_Rolling_24h"]).sort_values("datetime_local")
    return px.line(
        d, x="datetime_local", y="AQI_Rolling_24h", color="city",
        title="AQI trung bình trượt 24 giờ theo thời gian",
        labels={"datetime_local": "Thời gian",
                "AQI_Rolling_24h": "AQI", "city": "Thành phố"},
    )


def bar_top_cities(df):
    """2. Bar chart: thành phố ô nhiễm nhất (AQI trung bình)."""
    _need_cols(df, ["city", "AQI"], "bar_top_cities")
    s = (
        df.groupby("city", as_index=False)["AQI"]
        .mean()
        .sort_values("AQI", ascending=False)
    )
    return px.bar(
        s, x="city", y="AQI", color="city",
        title="AQI trung bình theo thành phố",
        labels={"city": "Thành phố", "AQI": "AQI trung bình"},
    )


def scatter_wind_aqi(df):
    """3. Scatter: tốc độ gió vs AQI (lấy mẫu tối đa 5000 điểm cho nhẹ)."""
    _need_cols(df, ["wind_speed", "AQI", "city"], "scatter_wind_aqi")
    d = df.dropna(subset=["wind_speed", "AQI"])
    if len(d) > 5000:
        d = d.sample(5000, random_state=42)
    return px.scatter(
        d, x="wind_speed", y="AQI", color="city", opacity=0.4,
        title="Tốc độ gió và AQI",
        labels={"wind_speed": "Tốc độ gió (m/s)", "AQI": "AQI",
                "city": "Thành phố"},
    )


def heatmap_hour_city(df):
    """4. Heatmap: giờ trong ngày × thành phố, giá trị là AQI trung bình."""
    _need_cols(df, ["city", "Hour", "AQI"], "heatmap_hour_city")
    pv = df.pivot_table(index="city", columns="Hour", values="AQI", aggfunc="mean")
    # Sắp xếp cột giờ 0→23 cho đúng thứ tự (LỖI CŨ: cột lộn xộn)
    pv = pv.reindex(columns=sorted(pv.columns))
    return px.imshow(
        pv, aspect="auto", title="AQI theo giờ và thành phố",
        labels={"x": "Giờ", "y": "Thành phố", "color": "AQI"},
    )


def box_weather(df):
    """5. Box plot: AQI theo loại thời tiết."""
    _need_cols(df, ["Weather_Category", "AQI"], "box_weather")
    # Ép thứ tự Dry → Rainy cho dễ đọc (LỖI CŨ: thứ tự chữ cái)
    order = [c for c in ["Dry", "Rainy"] if c in df["Weather_Category"].unique()]
    d = df.copy()
    d["Weather_Category"] = pd.Categorical(
        d["Weather_Category"], categories=order, ordered=True
    )
    d = d.sort_values("Weather_Category")
    return px.box(
        d, x="Weather_Category", y="AQI", color="Weather_Category",
        title="Phân bố AQI theo loại thời tiết",
        labels={"Weather_Category": "Thời tiết", "AQI": "AQI"},
    )
