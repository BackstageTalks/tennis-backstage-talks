import requests
import os

API_KEY = os.getenv("TENNIS_API_KEY")
BASE_URL = "https://tennis-api.com/api/v1"

def get_recent_matches(tour="ATP", limit=100):
    url = f"{BASE_URL}/matches?tour={tour}&limit={limit}"
    headers = {"x-rapidapi-key": API_KEY}

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()
