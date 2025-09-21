# charts/north_renderer.py
"""
Clean, robust North-Indian rasi chart renderer.
Replaces previous buggy code that referenced an undefined `s`.
Returns a legible SVG string (use st.components.v1.html(svg, height=...)).
"""

import svgwrite
from typing import Dict

# Unicode zodiac glyphs Aries..Pisces
ZODIAC_GLYPHS = [
    "\u2648", "\u2649", "\u264A", "\u264B", "\u264C", "\u264D",
    "\u264E", "\u264F", "\u2650", "\u2651", "\u2652", "\u2653"
]
SIGN_NAMES = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

PLANET_COLORS = {
    "Sun": "#E4572E",
    "Moon": "#4C78A8",
    "Mercury": "#2E8B57",
    "Venus": "#FF7F0E",
    "Mars": "#D62728",
    "Jupiter": "#8C564B",
    "Saturn": "#6A5ACD",
    "Rahu": "#7F7F7F",
    "Ketu": "#2B2B2B"
}

def _deg_min_str(deg_float: float) -> str:
    d = int(deg_float)
    m = int(round((deg_float - d) * 60))
    return f"{d}°{m:02d}'"

def _wrap_lines(text: str, max_chars: int = 16):
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def draw_north_chart_svg(rasi_obj: Dict,
                         size: int = 900,
                         bg_color: str = "#ffffff",
                         stroke_color: str = "#222222",
                         text_color: str = "#111111",
                         font_family: str = "Segoe UI, Roboto, Arial, Helvetica, sans-serif",
                         show_degrees: bool = True,
                         title: str = None) -> str:
    """
    rasi_obj: {'planets': {'Sun': {'lon':..,'rasi':..,'degree_in_sign':..},...}, 'asc': <deg>}
    size: canvas size in px
    Returns SVG string.
    """
    dwg = svgwrite.Drawing(size=(size, size))
    dwg.viewbox(0, 0, size, size)
    dwg.add(dwg.rect((0,0),(size,size), fill=bg_color))

    margin = int(size * 0.06)
    inner_w = size - 2*margin
    inner_h = size - 2*margin
    title_h = int(size * 0.06) if title else 0
    if title:
        dwg.add(dwg.text(title, insert=(margin + 10, margin + int(title_h*0.6)),
                         font_size=int(size*0.03), font_family=font_family, fill=text_color, font_weight="700"))

    grid_y0 = margin + title_h + 6
    grid_w = inner_w
    grid_h = inner_h - title_h - 10

    # Build a stable 3x3 grid and map the 12 rasis to positions in a readable North Indian arrangement.
    cols = 3
    rows = 3
    cell_w = grid_w / cols
    cell_h = grid_h / rows

    # Use a canonical ordered layout (12 houses). Each entry: (sign_index, x, y)
    # These coordinates are chosen to give a classic north-chart look while staying simple.
    ordered_layout = [
        (1, margin + cell_w, grid_y0 + 0*cell_h),      # Aries (top-center)
        (2, margin + 2*cell_w, grid_y0 + 0*cell_h),    # Taurus (top-right)
        (3, margin + 2*cell_w, grid_y0 + 0.5*cell_h),  # Gemini (upper-right inner)
        (4, margin + 2*cell_w, grid_y0 + 1.5*cell_h),  # Cancer (lower-right inner)
        (5, margin + 2*cell_w, grid_y0 + 2*cell_h),    # Leo (bottom-right)
        (6, margin + cell_w, grid_y0 + 2*cell_h),      # Virgo (bottom-center)
        (7, margin + 0*cell_w, grid_y0 + 2*cell_h),    # Libra (bottom-left)
        (8, margin + 0*cell_w, grid_y0 + 1.5*cell_h),  # Scorpio (lower-left inner)
        (9, margin + 0*cell_w, grid_y0 + 0.5*cell_h),  # Sagittarius (upper-left inner)
        (10, margin + 0*cell_w, grid_y0 + 0*cell_h),   # Capricorn (top-left)
        (11, margin + cell_w * 1.02, grid_y0 + 0.5*cell_h),  # Aquarius (mid-right-ish)
        (12, margin + cell_w * 1.02, grid_y0 + 1.5*cell_h),  # Pisces (mid-left-ish)
    ]

    house_w = int(cell_w * 0.94)
    house_h = int(cell_h * 0.9)
    font_base = max(12, int(size * 0.014))

    # Draw boxes and headers
    for sign, x, y in ordered_layout:
        x = float(x)
        y = float(y)
        dwg.add(dwg.rect(insert=(x, y), size=(house_w, house_h),
                         stroke=stroke_color, stroke_width=1.6, fill="none"))
        glyph = ZODIAC_GLYPHS[sign-1]
        header_x = x + 8
        header_y = y + font_base + 4
        dwg.add(dwg.text(glyph, insert=(header_x, header_y),
                         font_size=int(font_base*1.2), font_family=font_family, fill=text_color))
        dwg.add(dwg.text(SIGN_NAMES[sign-1], insert=(header_x + int(font_base*1.6), header_y),
                         font_size=int(font_base*1.0), font_family=font_family, fill=text_color, font_weight="700"))

    # Map planets to signs
    planets = rasi_obj.get("planets", {})
    sign_to_planets = {i: [] for i in range(1,13)}
    for p, info in planets.items():
        lon = info.get("lon", 0)
        r = info.get("rasi") or int(lon // 30) + 1
        deg = info.get("degree_in_sign") or (lon % 30)
        sign_to_planets[r].append((p, deg))

    # Place planets inside houses (two-column layout)
    for sign, x, y in ordered_layout:
        x = float(x)
        y = float(y)
        items = sign_to_planets.get(sign, [])
        start_y = y + int(font_base*1.9) + 6
        left_x = x + 8
        right_x = x + int(house_w/2) + 6
        left = True
        line_y = start_y
        for (p, deg) in items:
            label = f"{p}" + (f" {_deg_min_str(deg)}" if show_degrees else "")
            lines = _wrap_lines(label, max_chars=18)
            dot_r = max(3, int(size*0.0035))
            col_x = left_x if left else right_x
            # dot
            dwg.add(dwg.circle(center=(col_x, line_y + 2), r=dot_r, fill=PLANET_COLORS.get(p, "#333333")))
            for li, line in enumerate(lines):
                dwg.add(dwg.text(line, insert=(col_x + dot_r + 6, line_y + int(font_base*0.6) + li*int(font_base*1.05)),
                                 font_size=int(font_base*0.95), font_family=font_family, fill=text_color))
            if left:
                left = False
            else:
                left = True
                line_y += int(font_base*1.3) * max(1, len(lines))

    # ASC marker
    asc = rasi_obj.get("asc")
    if asc is not None:
        asc_sign = int((asc // 30) % 12) + 1
        for sign, x, y in ordered_layout:
            if sign == asc_sign:
                badge_r = int(min(house_w, house_h) * 0.07)
                cx = x + house_w - (badge_r + 10)
                cy = y + (badge_r + 10)
                dwg.add(dwg.circle(center=(cx, cy), r=badge_r, fill="#111111", stroke="#ffffff", stroke_width=1.2))
                dwg.add(dwg.text("ASC", insert=(cx - badge_r*0.7, cy + int(badge_r*0.28)),
                                 font_size=int(font_base*0.8), font_family=font_family, fill="#fff", font_weight="700"))
                break

    # Optional legend
    legend_y = grid_y0 + grid_h + 6
    dwg.add(dwg.text("Legend:", insert=(margin+6, legend_y + 12), font_size=int(font_base*0.9), font_family=font_family, fill=text_color, font_weight="700"))
    lx = margin + 74
    for i,(pn,color) in enumerate(PLANET_COLORS.items()):
        dwg.add(dwg.circle(center=(lx + i*78, legend_y + 8), r=4, fill=color))
        dwg.add(dwg.text(pn, insert=(lx + 10 + i*78, legend_y + 12), font_size=int(font_base*0.85), font_family=font_family, fill=text_color))

    return dwg.tostring()
