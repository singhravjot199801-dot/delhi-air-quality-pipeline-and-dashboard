## 6. My findings (fill in, then copy into `docs/data-notes.md`)
- **Sources and columns: the two URLs from the first code block
      AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality" for Air Quality API
      WX_URL = "https://api.open-meteo.com/v1/forecast" for  Weather API
      Columns are the output of these two functions aq_df.head() and wx_df.head() **
- **Units: PM2.5 in µg/m³, temperature in °C, wind speed in km/h
      UNITS (air quality): {'time': 'iso8601', 'pm2_5': 'μg/m³', 'pm10': 'μg/m³', 'us_aqi': 'USAQI'}
      UNITS (weather): {'time': 'iso8601', 'temperature_2m': '°C', 'relative_humidity_2m': '%', 'wind_speed_10m': 'km/h'} **
- **Timezone handling: request included timezone=Asia/Kolkata, so timestamps are in Indian local time **
- **Missing values / gaps: non null values in the last 7 days for both air quality and weather
      aq rows: 182 | wx rows: 182 | merged rows: 182
      _merge
      both          182
      left_only       0
      right_only      0
      Name: count, dtype: int64 **
- **Odd values or spikes: check the output of .describe() function for both air quality and weather **
- **Forecast vs real readings: API includes future hours for today; filtered out
      Now (Delhi): 2026-11-11 13:27:27.338286
      Air quality range: 2026-11-04 00:00:00 -> 2026-11-11 23:00:00
      Weather range:     2026-11-04 00:00:00 -> 2026-11-11 23:00:00
      Duplicate timestamps (aq, wx): 0 0
      (182, 4) (182, 4) **
- **Cleaning decisions for Day 3: need to perform the below steps for day 3
       Drop rows after the current time
       Parse time as datetime
       Inner-merge on time
       Decide what to do with missing values (leave as null, or fill)
       Flag impossible values (like negative PM2.5) **