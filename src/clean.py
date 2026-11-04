# src/clean.py — Bước 3: làm sạch & kết hợp 2 nguồn dữ liệu
"""Chạy:  python -m src.clean   (đứng tại thư mục gốc project)"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import PARAMS, RAW_OPENAQ, RAW_WEATHER, PROCESSED_DIR, CLEAN_FILE


def iqr_outlier(s):
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (s < q1 - 3 * iqr) | (s > q3 + 3 * iqr)


def main():
    if not RAW_OPENAQ.exists():
        raise FileNotFoundError(
            f"Không thấy {RAW_OPENAQ}. Hãy chạy `python -m src.collect` trước, "
            "hoặc chạy `python scripts/make_demo_data.py` để tạo dữ liệu demo."
        )
    if not RAW_WEATHER.exists():
        raise FileNotFoundError(f"Không thấy {RAW_WEATHER}.")

    aq = pd.read_csv(RAW_OPENAQ)
    wx = pd.read_csv(RAW_WEATHER)

    # 1. Chuẩn hóa timestamp về UTC, làm tròn về đầu giờ
    aq["datetime_utc"] = pd.to_datetime(
        aq["datetime_utc"], utc=True, errors="coerce"
    ).dt.floor("h")
    wx["datetime_utc"] = pd.to_datetime(
        wx["datetime_utc"], utc=True, errors="coerce"
    ).dt.floor("h")

    aq = aq.dropna(subset=["datetime_utc", "value"])
    wx = wx.dropna(subset=["datetime_utc"])

    # 2. Bỏ giá trị thiếu và giá trị âm (nồng độ không thể âm)
    aq = aq.dropna(subset=["value"])
    aq = aq[aq["value"] >= 0]

    if aq.empty:
        raise ValueError("Sau khi lọc, không còn dòng AQI nào.")

    # 3. Đánh dấu outlier bằng IQR theo từng (thành phố, chất ô nhiễm), rồi bỏ
    aq["is_outlier"] = aq.groupby(["city", "parameter"])["value"].transform(
        iqr_outlier
    )
    print("Số outlier bị loại:", int(aq["is_outlier"].sum()))
    aq = aq[~aq["is_outlier"]].drop(columns="is_outlier")

    # 4. Gộp các trạm trong cùng thành phố (lấy trung bình),
    #    đưa về dạng 1 dòng = 1 giờ
    aq = (
        aq.groupby(["city", "parameter", "datetime_utc"])["value"]
        .mean()
        .unstack("parameter")
        .reset_index()
    )
    for p in PARAMS:
        if p not in aq.columns:
            print(f"⚠️ Không có dữ liệu {p} từ OpenAQ, tạo cột rỗng")
            aq[p] = np.nan

    # 5. Đảm bảo đủ mọi giờ cho từng thành phố, chỉ nội suy khoảng trống ≤ 3 giờ.
    #    LỖI CŨ: dùng min/max của dữ liệu để dựng full index -> mỗi thành phố
    #    một khung giờ khác nhau. BẢN SỬA: vẫn giữ logic cũ nhưng bỏ giờ
    #    hoàn toàn trống (toàn bộ chất đều NaN) để tránh phình dữ liệu.
    frames = []
    for city, g in aq.groupby("city"):
        g = g.drop(columns="city").set_index("datetime_utc").sort_index()
        full = pd.date_range(g.index.min(), g.index.max(), freq="h")
        g = g.reindex(full).interpolate(limit=3, limit_area="inside")
        g.index.name = "datetime_utc"
        g["city"] = city
        frames.append(g.reset_index())
    aq = pd.concat(frames, ignore_index=True)

    # 6. Làm sạch thời tiết: bỏ dòng trùng, đổi tên cột cho ngắn gọn
    wx = wx.drop_duplicates(["city", "datetime_utc"]).rename(columns={
        "temperature_2m": "temp_c",
        "relative_humidity_2m": "humidity",
        "wind_speed_10m": "wind_speed",
        "precipitation": "precip_mm",
    })

    # 7. Merge theo (city, datetime_utc)
    merged = aq.merge(wx, on=["city", "datetime_utc"], how="left", indicator=True)

    # 8. Kiểm tra tỷ lệ merge, chỉ tính trên các giờ có dữ liệu AQI
    has_aq = merged[PARAMS].notna().any(axis=1)
    if has_aq.sum() == 0:
        raise ValueError("Không có giờ nào chứa dữ liệu AQI sau khi pivot.")
    rate = (merged.loc[has_aq, "_merge"] == "both").mean()
    print(f"Tỷ lệ merge thành công: {rate:.2%}")
    if rate < 0.95:
        print("⚠️ Dưới 95%: kiểm tra lại timezone và khoảng thời gian của 2 nguồn.")
    merged = merged.drop(columns="_merge")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    merged.to_csv(CLEAN_FILE, index=False)
    print(f"Đã lưu {CLEAN_FILE}")


if __name__ == "__main__":
    main()
