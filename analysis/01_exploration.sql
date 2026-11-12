-- Exploratory analysis of Delhi air quality and weather
-- Table: delhi_air_weather (hourly rows keyed on time, Asia/Kolkata local time)
-- Run these one at a time in Neon's SQL Editor.

-- 1. Overview: how much data do we have, and how bad is the air?
SELECT
    count(*)                              AS hours,
    min(time)                             AS first_hour,
    max(time)                             AS last_hour,
    round(avg(pm2_5)::numeric, 1)         AS avg_pm25,
    max(pm2_5)                            AS max_pm25
FROM delhi_air_weather;

-- 2. Pattern by hour of day: when is PM2.5 highest?
SELECT
    extract(hour FROM time)::int          AS hour_of_day,
    round(avg(pm2_5)::numeric, 1)         AS avg_pm25,
    round(avg(us_aqi)::numeric, 0)        AS avg_aqi
FROM delhi_air_weather
GROUP BY 1
ORDER BY 1;

-- 3. Daily summary with the weather that day
SELECT
    date_trunc('day', time)::date         AS day,
    round(avg(pm2_5)::numeric, 1)         AS avg_pm25,
    max(pm2_5)                            AS peak_pm25,
    round(avg(temperature_2m)::numeric, 1) AS avg_temp_c,
    round(avg(wind_speed_10m)::numeric, 1) AS avg_wind_kmh
FROM delhi_air_weather
GROUP BY 1
ORDER BY 1;

-- 4. Does wind clear the air? Average PM2.5 by wind speed band
SELECT
    CASE
        WHEN wind_speed_10m < 5  THEN '1: under 5 km/h'
        WHEN wind_speed_10m < 10 THEN '2: 5 to 10 km/h'
        WHEN wind_speed_10m < 20 THEN '3: 10 to 20 km/h'
        ELSE '4: 20 km/h or more'
    END                                   AS wind_band,
    count(*)                              AS hours,
    round(avg(pm2_5)::numeric, 1)         AS avg_pm25
FROM delhi_air_weather
WHERE wind_speed_10m IS NOT NULL AND pm2_5 IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- 5. Trend: daily average PM2.5 with a 7-day moving average (window function)
WITH daily AS (
    SELECT
        date_trunc('day', time)::date     AS day,
        avg(pm2_5)                        AS avg_pm25
    FROM delhi_air_weather
    GROUP BY 1
)
SELECT
    day,
    round(avg_pm25::numeric, 1)           AS avg_pm25,
    round(
        avg(avg_pm25) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)::numeric,
        1
    )                                     AS moving_avg_7d
FROM daily
ORDER BY day;

-- 6. Correlation of PM2.5 with each weather variable (-1 to 1)
SELECT
    round(corr(pm2_5, wind_speed_10m)::numeric, 2)        AS corr_wind,
    round(corr(pm2_5, temperature_2m)::numeric, 2)        AS corr_temperature,
    round(corr(pm2_5, relative_humidity_2m)::numeric, 2)  AS corr_humidity
FROM delhi_air_weather;
