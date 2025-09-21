# astrology.py
"""
Astrology helpers using Swiss Ephemeris (pyswisseph).
Provides ChartCalculator that computes planet positions, ascendant,
rasi chart and navamsa chart.
"""

try:
    import swisseph as swe
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "Missing dependency 'pyswisseph' (swisseph). Install it with:\n\n"
        "  pip install pyswisseph\n\n"
        "If pip fails on Windows, try installing via conda:\n\n"
        "  conda install -c conda-forge pyswisseph\n\n"
        "Make sure you are using the same Python interpreter/virtualenv as Streamlit/VS Code."
    ) from e

from datetime import timezone
import math

class ChartCalculator:
    def __init__(self, dt, lat, lon, tz_name, ayanamsa='Lahiri', house_system='Placidus'):
        """
        dt: timezone-aware datetime (preferred). If naive, ensure you made it timezone-aware before.
        lat, lon: float
        tz_name: string label (saved in metadata)
        """
        self.dt = dt
        self.lat = lat
        self.lon = lon
        self.tz_name = tz_name
        self.ayanamsa = ayanamsa
        self.house_system = house_system

        # Set sidereal mode to Lahiri by default (customize if needed)
        try:
            swe.set_sid_mode(swe.SIDM_LAHIRI)
        except Exception:
            # Not fatal: if attribute missing in some wrappers, continue.
            pass

    def _julian_day(self):
        """
        Compute Julian Day (UT) using swisseph API:
        swe.julday(year, month, day, hour_decimal)
        We convert self.dt to UTC and supply integer year/month/day and fractional hour.
        """
        # ensure dt is timezone-aware; convert to UTC
        if self.dt.tzinfo is None:
            # best-effort: assume dt is already UTC-like — but it's safer to pass tz-aware datetime
            dt_utc = self.dt.replace(tzinfo=timezone.utc)
        else:
            dt_utc = self.dt.astimezone(timezone.utc)

        year = dt_utc.year
        month = dt_utc.month
        day = dt_utc.day

        # fractional hour as decimal (hours + minutes/60 + seconds/3600 + micros)
        hour_decimal = (
            dt_utc.hour
            + dt_utc.minute / 60.0
            + dt_utc.second / 3600.0
            + dt_utc.microsecond / 3_600_000_000.0
        )

        # Call julday with separate hour parameter to avoid passing float day
        jd = swe.julday(year, month, day, hour_decimal)
        return jd

    def planet_positions(self):
        """
        Return dictionary of planet longitudes (0-360) and raw info.
        """
        jd = self._julian_day()
        bodies = {
            'Sun': swe.SUN,
            'Moon': swe.MOON,
            'Mercury': swe.MERCURY,
            'Venus': swe.VENUS,
            'Mars': swe.MARS,
            'Jupiter': swe.JUPITER,
            'Saturn': swe.SATURN,
            # use mean node for Rahu; you can switch to TRUE_NODE if preferred
            'Rahu': swe.MEAN_NODE,
        }
        planets = {}
        for name, code in bodies.items():
            # calc_ut returns (longitude, latitude, distance) in many wrappers
            res = swe.calc_ut(jd, code)
            # res may be list, tuple or nested; handle common shapes
            # pyswisseph usually returns a tuple of arrays: (lon, lat, dist), but APIs vary by version
            try:
                lon = float(res[0])
            except Exception:
                # fallback if returned as nested structure
                try:
                    lon = float(res[0][0])
                except Exception:
                    lon = 0.0
            lon = lon % 360.0
            planets[name] = {'lon': lon}
        return planets

    def ascendant(self):
        """
        Compute Ascendant (Lagna) using swe.houses or swe.houses_ex depending on wrapper.
        We'll first try swe.houses(jd, lat, lon) which commonly returns (ascmc, houses)
        """
        jd = self._julian_day()
        # try the common API
        try:
            ascmc = swe.houses(jd, self.lat, self.lon)
            # many bindings return a tuple: (cusps, ascmc) or (ascmc, cusps) depending on version;
            # attempt to extract the ascendant robustly:
            if isinstance(ascmc, tuple) and len(ascmc) >= 2:
                # look for a numeric asc value among returned structures
                for part in ascmc:
                    if isinstance(part, (list, tuple)):
                        # find a float-looking item
                        for item in part:
                            if isinstance(item, (int, float)):
                                asc = float(item)
                                return asc % 360.0
                # fallback: use first element's first numeric
                try:
                    asc = float(ascmc[0][0])
                    return asc % 360.0
                except Exception:
                    pass
            # If houses returned a single array with asc as first element
            if isinstance(ascmc, (list, tuple)) and len(ascmc) >= 1 and isinstance(ascmc[0], (int, float)):
                return float(ascmc[0]) % 360.0
        except Exception:
            pass

        # fallback: use swe.houses_ex if available
        try:
            ascmc = swe.houses_ex(jd, self.lat, self.lon)
            # typical structure: (cusps, ascmc)
            # try to get asc from ascmc[0]
            if isinstance(ascmc, tuple) and len(ascmc) >= 2:
                asc = ascmc[0][0] if isinstance(ascmc[0], (list, tuple)) else ascmc[0]
                return float(asc) % 360.0
        except Exception:
            pass

        # As an ultimate fallback, return 0.0
        return 0.0

    def get_rasi_chart(self):
        """
        Build rasi chart structure with each planet's rasi (1..12) and degree within sign.
        """
        planets = self.planet_positions()
        asc = self.ascendant()
        for p, info in planets.items():
            lon = info.get('lon', 0.0)
            rasi = int(lon // 30) + 1
            deg_in_sign = lon % 30
            info.update({'rasi': rasi, 'degree_in_sign': deg_in_sign})
        return {'planets': planets, 'asc': asc}

    def get_navamsa_chart(self):
        """
        Compute navamsa sign for each planet. Basic algorithm:
        - navamsa index within a sign = floor((degree_in_sign) / (30/9))
        - convert to absolute navamsa sign by (sign_index-1)*9 + nav_index then map mod 12 +1
        """
        rasi = self.get_rasi_chart()
        nav = {}
        for p, info in rasi['planets'].items():
            lon = info.get('lon', 0.0)
            # navamsa partition size:
            part = 30.0 / 9.0
            nav_index = int((lon % 30) // part)
            nav_sign = ((int(lon // 30) * 9) + nav_index) % 12 + 1
            nav[p] = {'lon': lon, 'nav_sign': nav_sign}
        return {'navamsa': nav}

    def metadata(self):
        return {'datetime': self.dt.isoformat(), 'lat': self.lat, 'lon': self.lon, 'tz': self.tz_name}
