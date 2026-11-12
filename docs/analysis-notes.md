Findings for the 6 SQL Queries are as follows :

Starting with these three, since they give the most to work with-

Query 2 -
 SELECT
    extract(hour FROM time)::int          AS hour_of_day,
    round(avg(pm2_5)::numeric, 1)         AS avg_pm25,
    round(avg(us_aqi)::numeric, 0)        AS avg_aqi
FROM delhi_air_weather
GROUP BY 1
ORDER BY 1;

Result : 
#	hour_of_day	avg_pm25	avg_aqi
1	0		92.0		159
2	1		89.6		159
3	2		87.4		159
4	3		85.6		159
5	4		84.3		158
6	5		81.3		158
7	6		84.4		158
8	7		87.2		158
9	8		79.5		158
10	9		69.6		159
11	10		61.5		159
12	11		56.6		159
13	12		53.3		158
14	13		52.8		158
15	14		52.8		158
16	15		53.4		161
17	16		56.3		166
18	17		69.3		171
19	18		77.9		172
20	19		85.1		171
21	20		89.8		167
22	21		93.2		162
23	22		95.4		160
24	23		95.1    	160


Findings: 
What the numbers actually show

-A daily cycle. PM2.5 is lowest at 13:00 to 14:00 (about 53 µg/m³) and highest at 22:00 to 23:00 (about 95 µg/m³), roughly 80% higher.

-Two rises. There’s a smaller bump around 6 to 7 AM (about 87), then a drop through the morning, then a steady climb from about 16:00 into the night.

-Even the cleanest hour is high. The midday low of about 53 is still around 3.5 times the WHO’s 24-hour guideline of 15 µg/m³.

Common explanations for this shape are that midday heating mixes pollution into a deeper layer of air and winds pick up, while the evening and night rise comes from traffic and cooler, calmer air trapping emissions. Those are hypotheses, and my data can’t prove them. Query 4 (wind) will test part of it, since if windy hours have clearly lower PM2.5, that supports the mixing idea. 

Conclusion of this finding : Average PM2.5 follows a daily cycle, bottoming out at about 53 µg/m³ around 13:00 to 14:00 and peaking at about 95 µg/m³ around 22:00 to 23:00 (mid-September to mid-November, Delhi local time).

Query 4- 

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

Result :

#	wind_band		hours	avg_pm25
1	1: under 5 km/h		692	85.9
2	2: 5 to 10 km/h		613	71.5
3	3: 10 to 20 km/h	147	52.2

Findings:
-There’s no 20+ km/h band because no hours in my data reached that wind speed, so I can’t say anything about stronger winds.

-The windiest group has only 147 hours (about 10% of my data), so that 52.2 is less certain than the other two.

-This is a correlation, not proof that wind clears the air. Wind and time of day are tangled together. Afternoons tend to be both windier and my cleanest hours (about 53 at 13:00 to 14:00), so part of the wind effect may just be the time-of-day effect.

Conclusion of this finding: Average PM2.5 falls as wind speed rises: about 86 µg/m³ in calm conditions (under 5 km/h), 72 at 5 to 10 km/h, and 52 at 10 to 20 km/h, roughly 39% lower than in calm air (mid-September to mid-November; no hours above 20 km/h).


Query 6-

SELECT
    round(corr(pm2_5, wind_speed_10m)::numeric, 2)        AS corr_wind,
    round(corr(pm2_5, temperature_2m)::numeric, 2)        AS corr_temperature,
    round(corr(pm2_5, relative_humidity_2m)::numeric, 2)  AS corr_humidity
FROM delhi_air_weather;

Result-

#	corr_wind	corr_temperature	corr_humidity
1	-0.34	        -0.40			0.11

Findings: 

Weather variable	Correlation with PM2.5		What it means
Temperature		-0.40				Cooler hours tend to have higher PM2.5 (the strongest of the three).
Wind speed		-0.34				Windier hours tend to have lower PM2.5, which matches my query 4 result.
Humidity		0.11				Almost no linear relationship.


Weather explains only part of the story. Squaring a correlation gives the share of variation it accounts for, so temperature alone covers about 16% and wind about 12%. Humidity covers about 1%. The rest comes from other things, such as emissions, crop burning, and the previous hours’ pollution.

Temperature is probably standing in for other things. It’s lower at night and lower as autumn turns to winter, and both of those also bring higher PM2.5. So the -0.40 likely reflects time of day and season as much as temperature itself. 

Correlation measures straight-line relationships only, so a weak number doesn’t rule out a more complex pattern.

Conclusion of this finding: PM2.5 shows moderate negative correlations with temperature (-0.40) and wind speed (-0.34) and almost none with humidity (0.11), so weather alone explains only a modest share of the variation (mid-September to mid-November; correlation, not causation).




