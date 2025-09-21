# yogas.py
"""
Heuristic yoga detectors and a self-contained Vimshottari dasa calculator.
- Provides analyze_chart_for_yogas_and_dasas(rasi, nav, birth_dt=None)
- Does NOT require pyjhora; but if you later install pyjhora, we can prefer it.
Note: These are heuristics and meant for quick UI feedback. For production, use pyjhora/VedicAstro.
"""

from datetime import datetime, timedelta
import math

# Vimshottari sequence & durations (years)
VIM_ORDER = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']
VIM_YEARS = {'Ketu':7, 'Venus':20, 'Sun':6, 'Moon':10, 'Mars':7, 'Rahu':18, 'Jupiter':16, 'Saturn':19, 'Mercury':17}

def _deg_to_nak_index(lon):
    """
    Map absolute longitude (0-360) -> nakshatra index 0..26 and the intra-nak fraction.
    Each nakshatra = 13.333333... degrees (360/27).
    Returns: (nak_index, fraction_into_nak) where fraction in [0,1)
    """
    span = 360.0 / 27.0  # 13.333...
    idx = int(lon // span) % 27
    fraction = (lon % span) / span
    return idx, fraction

def compute_vimshottari_dasa_heuristic(moon_lon, birth_dt=None):
    """
    Compute a simple Vimshottari Mahadasha timeline starting from birth.
    - moon_lon: Moon longitude in degrees (0..360)
    - birth_dt: datetime object (optional) used to compute absolute calendar spans
    Returns a dict with 'current' mahadasha name, remaining years (float),
    and a short upcoming list of mahadashas with start/end years (approx).
    """
    nak_idx, frac = _deg_to_nak_index(moon_lon)
    # starting lord is based on nak index mapping repeating VIM_ORDER across 27 nakshatras
    start_lord = VIM_ORDER[nak_idx % len(VIM_ORDER)]
    # remaining fraction of the mahadasha at birth = 1 - frac (because dasha runs from start of nak)
    remaining_fraction = 1.0 - frac
    # compute remaining years of current mahadasha
    full_years = VIM_YEARS[start_lord]
    remaining_years = full_years * remaining_fraction

    # Build upcoming mahadasha sequence (names + durations)
    sequence = []
    # find index in order
    start_index = VIM_ORDER.index(start_lord)
    # Use birth_dt if provided, else compute relative years
    if birth_dt is None:
        birth_dt = datetime.utcnow()
        use_dates = False
    else:
        use_dates = True

    cur_start = birth_dt
    # current mahadasha started earlier; compute its end
    cur_end = cur_start + timedelta(days=remaining_years * 365.25)
    sequence.append({"name": start_lord, "start": cur_start.isoformat(), "end": cur_end.isoformat(), "duration_years": remaining_years})

    # next mahadashas (cover next ~6)
    idx = (start_index + 1) % len(VIM_ORDER)
    running_start = cur_end
    for i in range(1, 7):
        lord = VIM_ORDER[idx]
        dur = VIM_YEARS[lord]
        running_end = running_start + timedelta(days=dur * 365.25)
        sequence.append({"name": lord, "start": running_start.isoformat(), "end": running_end.isoformat(), "duration_years": dur})
        running_start = running_end
        idx = (idx + 1) % len(VIM_ORDER)

    return {
        "current": f"{start_lord} Mahadasha (approx)",
        "remaining_years": round(remaining_years, 3),
        "sequence": sequence
    }

# Simple angular helpers
def _angle_distance(a, b):
    """Smallest distance between two angles (degrees)"""
    d = abs((a - b + 180) % 360 - 180)
    return d

def detect_common_yogas(rasi):
    """
    Conservative, readable heuristics for a few classical yogas.
    Returns a list of strings (yoga names). Avoids overclaiming.
    """
    out = []
    p = rasi.get("planets", {})

    # Gajakesari: strong Jupiter-Moon relationship (conjunction or trine within orb)
    if "Jupiter" in p and "Moon" in p:
        d = _angle_distance(p["Jupiter"]["lon"], p["Moon"]["lon"])
        if d <= 6 or abs(d - 120) <= 6 or abs(d - 240) <= 6:
            out.append("Gajakesari Yoga (heuristic)")

    # Chandra-Mangal: Moon-Mars close conjunction or strong aspect
    if "Moon" in p and "Mars" in p:
        d = _angle_distance(p["Moon"]["lon"], p["Mars"]["lon"])
        if d <= 3:
            out.append("Chandra-Mangal Yoga (heuristic)")

    # Mahalakshmi heuristic: Venus in trikona (1,5,9) plus benefic placements (simple)
    if "Venus" in p:
        v_sign = p["Venus"].get("rasi")
        if v_sign in (1,5,9):
            out.append("Mahalakshmi Yoga (heuristic)")

    # Raja-yoga family (simple): strong lords in kendras/trikonas
    for lord in ("Sun","Moon","Mercury","Venus","Jupiter","Mars","Saturn"):
        if lord in p:
            s = p[lord].get("rasi")
            if s in (1,4,7,10):  # kendra
                out.append(f"Possible Raja-yoga influence ({lord} in kendra)")

    # Neechabhanga (simple): planet debilitated but with cancellation by exalted trine/associate
    # We'll only provide a very safe placeholder detection: if a planet is <5 deg in a sign (debilitation)
    for name,info in p.items():
        deg = info.get("degree_in_sign") or (info.get("lon",0) % 30)
        if deg is not None and deg < 2.0:
            out.append(f"Possible Neecha (weak) placement: {name} (~{deg:.2f}°) — may require detailed inspection")

    # dedupe
    seen = set()
    filtered = []
    for s in out:
        if s not in seen:
            filtered.append(s)
            seen.add(s)
    return filtered

def analyze_chart_for_yogas_and_dasas(rasi, nav=None, birth_dt=None):
    """
    Public helper: returns {'yogas': [...], 'dasas': {...}}
    - rasi: required (output of ChartCalculator.get_rasi_chart())
    - nav: optional
    - birth_dt: optional datetime; if provided, dasha sequence will contain ISO dates
    """
    yogas = detect_common_yogas(rasi)
    # find Moon lon (required)
    moon = rasi.get("planets", {}).get("Moon")
    if moon:
        dasas = compute_vimshottari_dasa_heuristic(moon.get("lon", 0), birth_dt=birth_dt)
    else:
        dasas = {"current": "Unknown (no Moon position)", "sequence": []}
    return {"yogas": yogas, "dasas": dasas}
