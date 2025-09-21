# utils.py
from geopy.geocoders import Nominatim
import pytz
from datetime import datetime

def geocode_place(place: str):
    # allow lat,lon direct
    try:
        parts = [p.strip() for p in place.split(",")]
        if len(parts) >= 2 and all([p.replace(".","",1).replace("-","",1).isdigit() for p in parts[:2]]):
            return {"lat": float(parts[0]), "lon": float(parts[1])}
    except Exception:
        pass
    geolocator = Nominatim(user_agent="sahadedv-geocoder")
    try:
        loc = geolocator.geocode(place, timeout=10)
        if loc:
            return {"lat": loc.latitude, "lon": loc.longitude}
    except Exception:
        return None

def ensure_tzaware(dt_naive: datetime, tz_name: str):
    tz = pytz.timezone(tz_name)
    return tz.localize(dt_naive)
