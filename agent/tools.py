from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests
from tavily import TavilyClient

from .config import (
	DEFAULT_CITY,
	OPENWEATHER_API_KEY,
	TAVILY_API_KEY,
)


# --- Web search tool (Tavily with simple interface) ---
def web_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
	if not TAVILY_API_KEY:
		raise RuntimeError("TAVILY_API_KEY is required for web search")
	client = TavilyClient(api_key=TAVILY_API_KEY)
	resp = client.search(query=query, max_results=max_results)
	# Normalize shape: list of {title, url, content}
	results = []
	for item in resp.get("results", []):
		results.append({
			"title": item.get("title"),
			"url": item.get("url"),
			"snippet": item.get("content"),
		})
	return results


# --- Weather tool (OpenWeather current weather + optional geocoding) ---
def _normalize_city_query(city: str) -> List[str]:
	"""Return possible query strings for OpenWeather geocoding.

	Examples:
	- "Napa, CA" -> ["Napa,CA,US", "Napa,CA", "Napa,US", "Napa"]
	- "Paris" -> ["Paris,FR", "Paris"]
	"""
	parts = [p.strip() for p in city.split(",") if p.strip()]
	queries: List[str] = []
	# Common default country
	default_country = "US"
	if len(parts) == 1:
		city_only = parts[0]
		# Try with default country first, then city only
		queries.extend([f"{city_only},{default_country}", city_only])
	elif len(parts) >= 2:
		c, region = parts[0], parts[1]
		# Try full with country
		queries.append(f"{c},{region},{default_country}")
		# Without country
		queries.append(f"{c},{region}")
		# City with default country
		queries.append(f"{c},{default_country}")
		# City only
		queries.append(c)
	return queries


def geocode_city(city: str) -> Optional[Dict[str, float]]:
	if not OPENWEATHER_API_KEY:
		raise RuntimeError("OPENWEATHER_API_KEY is required for weather")
	for query in _normalize_city_query(city):
		params = {"q": query, "limit": 1, "appid": OPENWEATHER_API_KEY}
		resp = requests.get("https://api.openweathermap.org/geo/1.0/direct", params=params, timeout=15)
		resp.raise_for_status()
		data = resp.json()
		if data:
			return {"lat": data[0]["lat"], "lon": data[0]["lon"]}
	return None


def current_weather(city: Optional[str] = None, units: str = "metric") -> Dict[str, Any]:
	if not OPENWEATHER_API_KEY:
		raise RuntimeError("OPENWEATHER_API_KEY is required for weather")
	city_query = (city or DEFAULT_CITY).strip()
	coords = geocode_city(city_query)
	if not coords:
		raise RuntimeError(f"Could not geocode city: {city_query}")
	params = {"lat": coords["lat"], "lon": coords["lon"], "units": units, "appid": OPENWEATHER_API_KEY}
	resp = requests.get("https://api.openweathermap.org/data/2.5/weather", params=params, timeout=15)
	resp.raise_for_status()
	data = resp.json()
	return {
		"city": city_query,
		"temperature": data.get("main", {}).get("temp"),
		"conditions": data.get("weather", [{}])[0].get("description"),
		"humidity": data.get("main", {}).get("humidity"),
		"wind_speed": data.get("wind", {}).get("speed"),
	}


__all__ = ["web_search", "current_weather"]


