"""天气数据路由 - Open-Meteo 天气/AQI + 高德城市搜索代理"""

from typing import Optional

import httpx
from fastapi import APIRouter, Query

from config import AMAP_WEB_SERVICE_KEY

router = APIRouter(prefix="/api/weather", tags=["weather"])

# WMO weather_code -> 中文映射
WMO_WEATHER_TEXT = {
    0: "晴",
    1: "大部晴朗",
    2: "局部多云",
    3: "多云",
    45: "雾",
    48: "沉积雾凇",
    51: "小毛毛雨",
    53: "中毛毛雨",
    55: "大毛毛雨",
    56: "冻毛毛雨(轻)",
    57: "冻毛毛雨(重)",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨(轻)",
    67: "冻雨(重)",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "大阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴大冰雹",
}


def _aqi_level(aqi: Optional[int]) -> str:
    """US AQI -> 中文等级"""
    if aqi is None:
        return "未知"
    if aqi <= 50:
        return "优"
    if aqi <= 100:
        return "良"
    if aqi <= 150:
        return "轻度污染"
    if aqi <= 200:
        return "中度污染"
    if aqi <= 300:
        return "重度污染"
    return "严重污染"


@router.get("")
async def get_weather(
    lat: float = Query(29.56, description="纬度(WGS84)"),
    lon: float = Query(106.55, description="经度(WGS84)"),
):
    """获取指定坐标的实时天气与空气质量(数据源: Open-Meteo)"""
    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "shortwave_radiation",
            "soil_moisture_0_to_1cm",
        ]),
        "timezone": "Asia/Shanghai",
    }

    aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aqi_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "us_aqi,pm2_5,pm10",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            weather_resp, aqi_resp = await client.get(weather_url, params=weather_params), None
            try:
                aqi_resp = await client.get(aqi_url, params=aqi_params)
            except Exception:
                pass

        if weather_resp.status_code != 200:
            return {"error": "天气数据获取失败"}

        w = weather_resp.json().get("current", {})

        weather_code = w.get("weather_code")
        weather_text = WMO_WEATHER_TEXT.get(weather_code, "未知")

        aqi_val = None
        pm2_5 = None
        pm10 = None
        if aqi_resp and aqi_resp.status_code == 200:
            aq = aqi_resp.json().get("current", {})
            aqi_val = aq.get("us_aqi")
            pm2_5 = aq.get("pm2_5")
            pm10 = aq.get("pm10")

        return {
            "temperature": w.get("temperature_2m"),
            "apparent_temperature": w.get("apparent_temperature"),
            "humidity": w.get("relative_humidity_2m"),
            "precipitation": w.get("precipitation"),
            "weather_code": weather_code,
            "weather_text": weather_text,
            "wind_speed": w.get("wind_speed_10m"),
            "wind_direction": w.get("wind_direction_10m"),
            "radiation": w.get("shortwave_radiation"),
            "soil_moisture": w.get("soil_moisture_0_to_1cm"),
            "aqi": aqi_val,
            "aqi_level": _aqi_level(aqi_val),
            "pm2_5": pm2_5,
            "pm10": pm10,
            "time": w.get("time"),
        }

    except httpx.TimeoutException:
        return {"error": "请求超时，请稍后重试"}
    except Exception as e:
        return {"error": f"获取天气数据失败: {str(e)}"}


@router.get("/cities")
async def search_cities(
    keywords: str = Query(..., description="城市/区县搜索关键词"),
):
    """代理高德行政区搜索(key 不暴露给前端)"""
    url = "https://restapi.amap.com/v3/config/district"
    params = {
        "keywords": keywords,
        "subdistrict": 1,
        "extensions": "base",
        "key": AMAP_WEB_SERVICE_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)

        if resp.status_code != 200:
            return {"error": "高德接口请求失败", "cities": []}

        data = resp.json()
        if data.get("status") != "1":
            return {"error": data.get("info", "未知错误"), "cities": []}

        districts = data.get("districts", [])
        result = []
        for d in districts:
            # 展开子级
            subs = d.get("districts", [])
            if subs:
                for sub in subs:
                    center = sub.get("center", "")
                    if center:
                        lng, lat = center.split(",")
                        result.append({
                            "name": f"{d.get('name')} - {sub.get('name')}",
                            "adcode": sub.get("adcode"),
                            "lng": float(lng),
                            "lat": float(lat),
                        })
            else:
                center = d.get("center", "")
                if center:
                    lng, lat = center.split(",")
                    result.append({
                        "name": d.get("name"),
                        "adcode": d.get("adcode"),
                        "lng": float(lng),
                        "lat": float(lat),
                    })

        return {"cities": result}

    except httpx.TimeoutException:
        return {"error": "请求超时", "cities": []}
    except Exception as e:
        return {"error": str(e), "cities": []}
