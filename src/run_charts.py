import pandas as pd
from charts import line_aqi, bar_top_cities, scatter_wind_aqi, heatmap_hour_city, box_weather

# 1. Đọc dữ liệu từ file CSV 
# (Bạn hãy sửa lại đường dẫn 'aqi_weather_features.csv' cho đúng với vị trí file trên máy bạn)
df = pd.read_csv(r'D:\Tài liệu\Trực quan hóa dữ liệu\aqi-weather-project-fixed\aqi-weather-project\data\processed\aqi_weather_features.csv', parse_dates=['datetime_local'])

print("Đang tiến hành vẽ 5 biểu đồ... Vui lòng chờ.")

# 2. Gọi từng hàm và hiển thị biểu đồ (Plotly sẽ tự mở tab trên trình duyệt web)
fig1 = line_aqi(df)
fig1.show()

fig2 = bar_top_cities(df)
fig2.show()

fig3 = scatter_wind_aqi(df)
fig3.show()

fig4 = heatmap_hour_city(df)
fig4.show()

fig5 = box_weather(df)
fig5.show()

print("Hoàn thành! Bạn có thể tương tác (zoom, hover) trực tiếp trên các biểu đồ vừa mở.")