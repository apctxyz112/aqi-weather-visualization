# Dự án AQI & Thời tiết — Chất lượng không khí 5 thành phố Đông Nam Á

Dashboard Streamlit phân tích mối quan hệ giữa chất lượng không khí (AQI từ PM2.5)
và thời tiết (nhiệt độ, gió, mưa) tại Hà Nội, TP.HCM, Bangkok, Singapore, Jakarta,
giai đoạn 01/10/2025 – 31/12/2025.

## 1. Cấu trúc project

```text
aqi-weather-project/
├── app.py                  # Dashboard Streamlit (bước 6)
├── requirements.txt        # Thư viện cần cài
├── .env.example            # Mẫu file chứa API key (copy thành .env)
├── src/
│   ├── config.py           # Cấu hình: tọa độ, chất ô nhiễm, đường dẫn file
│   ├── collect.py          # B2: tải dữ liệu OpenAQ + Open-Meteo
│   ├── clean.py            # B3: làm sạch, nội suy, merge 2 nguồn
│   ├── features.py         # B4: tính AQI, phân loại thời tiết/gió/nhiệt
│   └── charts.py           # B5: 5 hàm vẽ biểu đồ Plotly
├── scripts/
│   └── make_demo_data.py   # Sinh dữ liệu demo (không cần API key)
├── notebooks/
│   └── 01_eda.ipynb        # Notebook phân tích khám phá
└── data/
    ├── raw/                # openaq_hourly.csv, weather_hourly.csv
    └── processed/          # aqi_weather_clean.csv, aqi_weather_features.csv
```

## 2. Cài đặt (làm 1 lần)

Yêu cầu: **Python 3.10 trở lên**. Kiểm tra bằng `python --version`.

```bash
cd aqi-weather-project

# 2a. Tạo môi trường ảo (khuyên dùng)
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

# 2b. Cài thư viện
pip install -r requirements.txt
```

## 3. Cách chạy NHANH (không cần API key) — khuyên dùng để chấm bài

```bash
cd aqi-weather-project
# (nhớ bật .venv nếu đã tạo ở bước 2)

python scripts/make_demo_data.py   # sinh dữ liệu demo vào data/raw/
python -m src.clean                # làm sạch → data/processed/aqi_weather_clean.csv
python -m src.features             # tạo đặc trưng → data/processed/aqi_weather_features.csv
streamlit run app.py               # mở dashboard trên trình duyệt
```

Lệnh cuối sẽ in ra một địa chỉ, thường là `http://localhost:8501` — mở bằng trình duyệt.
Nhấn `Ctrl+C` trong terminal để tắt app.

> Bản bàn giao này đã kèm sẵn dữ liệu demo trong `data/` nên bạn có thể
> chạy ngay `streamlit run app.py` mà không cần chạy 3 lệnh đầu.

## 4. Cách chạy với DỮ LIỆU THẬT (cần API key OpenAQ)

1. Đăng ký key miễn phí tại [https://explore.openaq.org/](https://explore.openaq.org/) (Create account → API key).
2. Copy file mẫu rồi điền key:

   ```bash
   copy .env.example .env        # Windows
   # cp .env.example .env        # macOS / Linux
   ```

   Mở `.env` và thay `your_openaq_api_key_here` bằng key thật.
3. Chạy pipeline:

   ```bash
   python -m src.collect    # tải dữ liệu (mất vài phút, cần mạng)
   python -m src.clean
   python -m src.features
   streamlit run app.py
   ```

   (Open-Meteo không cần key. Nếu OpenAQ hết quota, app vẫn chạy với dữ liệu demo.)

## 5. Mô tả từng bước pipeline

| Bước          | File                | Vào → Ra                            | Việc làm                                                                                                                     |
| --------------- | ------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 2. Thu thập    | `src/collect.py`  | API → `data/raw/*.csv`             | Tìm sensor OpenAQ quanh mỗi thành phố, tải AQI giờ + thời tiết Open-Meteo                                              |
| 3. Làm sạch   | `src/clean.py`    | raw → `aqi_weather_clean.csv`      | Bỏ giá trị âm/thiếu, loại outlier IQR, gộp trạm, nội suy lỗ ≤ 3 giờ, merge theo (city, giờ UTC)                   |
| 4. Đặc trưng | `src/features.py` | clean → `aqi_weather_features.csv` | AQI từ PM2.5 (chuẩn US EPA 2024), nhóm gió/nhiệt/mưa-nắng, giờ địa phương, trung bình trượt 24h, Weather_Impact |
| 5. Biểu đồ   | `src/charts.py`   | DataFrame → figure                   | 5 hàm: line 24h, bar top cities, scatter gió–AQI, heatmap giờ×thành phố, box mưa–nắng                                |
| 6. Dashboard    | `app.py`          | features CSV → web                   | Sidebar lọc thành phố/thời tiết/ngày + 3 tab: Tổng quan, Phân tích AQI, Tác động thời tiết                       |
