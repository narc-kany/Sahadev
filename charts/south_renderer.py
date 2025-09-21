# charts/south_renderer.py
"""
Improved South-Indian rasi chart renderer.
- Produces high-contrast, legible SVG tuned for Streamlit.
- Shows zodiac glyphs, colored planet dots, two-column planet layout.
- Usage: draw_south_chart_svg(rasi_obj, size=900)
"""

import svgwrite
from typing import Dict, Tuple

# Unicode zodiac glyphs mapped to sign index 1..12 (Aries..Pisces)
ZODIAC_GLYPHS = [
    "\u2648", "\u2649", "\u264A", "\u264B", "\u264C", "\u264D",
    "\u264E", "\u264F", "\u2650", "\u2651", "\u2652", "\u2653"
]
SIGN_NAMES = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

# small color palette for planets (keeps contrast with white background)
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

def _wrap_lines(text: str, max_chars: int = 18):
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def _planet_label_lines(name: str, deg: float, show_deg: bool = True) -> Tuple[str]:
    if show_deg:
        return (f"{name} {_deg_min_str(deg)}",)
    return (name,)

def draw_south_chart_svg(rasi_obj: Dict,
                         size: int = 900,
                         bg_color: str = "#ffffff",
                         card_margin: int = 30,
                         stroke_color: str = "#222222",
                         text_color: str = "#111111",
                         font_family: str = "Segoe UI, Roboto, Arial, Helvetica, sans-serif",
                         show_degrees: bool = True,
                         title: str = None) -> str:
    """
    rasi_obj: {'planets': {'Sun': {'lon':..,'rasi':..,'degree_in_sign':..},...}, 'asc': <deg>}
    size: pixel width & height of SVG
    """
    dwg = svgwrite.Drawing(size=(size, size))
    dwg.viewbox(0, 0, size, size)

    # background card to stand out on dark theme
    dwg.add(dwg.rect((0,0),(size,size), fill=bg_color))

    # card inner area
    margin = card_margin
    inner_w = size - 2*margin
    inner_h = size - 2*margin

    # title area (optional)
    title_h = int(size * 0.06) if title else 0
    if title:
        dwg.add(dwg.text(title,
                         insert=(margin + 12, margin + int(title_h*0.6)),
                         font_size=int(size*0.03),
                         font_family=font_family,
                         fill=text_color,
                         font_weight="700"))

    grid_y0 = margin + title_h + 6
    grid_w = inner_w
    grid_h = inner_h - title_h - 10

    cols = 4
    rows = 3
    cell_w = grid_w / cols
    cell_h = grid_h / rows

    # Preferred sign layout for South Indian style (classical mapping)
    sign_layout = [
        (1, margin + 3*cell_w, grid_y0 + 0*cell_h),
        (2, margin + 2*cell_w, grid_y0 + 0*cell_h),
        (3, margin + 1*cell_w, grid_y0 + 0*cell_h),
        (4, margin + 0*cell_w, grid_y0 + 0*cell_h),
        (5, margin + 0*cell_w, grid_y0 + 1*cell_h),
        (6, margin + 0*cell_w, grid_y0 + 2*cell_h),
        (7, margin + 1*cell_w, grid_y0 + 2*cell_h),
        (8, margin + 2*cell_w, grid_y0 + 2*cell_h),
        (9, margin + 3*cell_w, grid_y0 + 2*cell_h),
        (10, margin + 3*cell_w, grid_y0 + 1*cell_h),
        (11, margin + 2*cell_w, grid_y0 + 1*cell_h),
        (12, margin + 1*cell_w, grid_y0 + 1*cell_h),
    ]

    # panel background and border (rounded)
    dwg.add(dwg.rect((margin-6, grid_y0-6), (grid_w+12, grid_h+12),
                     rx=6, ry=6, fill="#fff", stroke=stroke_color, stroke_width=2))

    font_base = max(12, int(size * 0.014))

    # Draw cells
    for sign, sx, sy in sign_layout:
        dwg.add(dwg.rect(insert=(sx, sy), size=(cell_w, cell_h),
                         stroke=stroke_color, stroke_width=1.6, fill="none"))

        # header row: glyph + name
        glyph = ZODIAC_GLYPHS[sign-1]
        header_x = sx + 8
        header_y = sy + font_base + 4
        # glyph
        dwg.add(dwg.text(glyph, insert=(header_x, header_y),
                         font_size=int(font_base*1.2), font_family=font_family, fill=text_color))
        # sign name (to the right)
        dwg.add(dwg.text(SIGN_NAMES[sign-1],
                         insert=(header_x + int(font_base*1.6), header_y),
                         font_size=int(font_base*1.05), font_family=font_family, fill=text_color, font_weight="700"))

    # Map planets to signs
    planets = rasi_obj.get("planets", {})
    sign_to_planets = {i: [] for i in range(1,13)}
    for p, info in planets.items():
        r = info.get("rasi")
        if not r:
            lon = info.get("lon", 0)
            r = int(lon // 30) + 1
        deg = info.get("degree_in_sign") or (info.get("lon", 0) % 30)
        sign_to_planets[r].append((p, deg))

    # inside each cell: two-column layout for planets
    for sign, sx, sy in sign_layout:
        items = sign_to_planets.get(sign, [])
        # starting y below header
        start_y = sy + int(font_base*1.8) + 8
        col_x_left = sx + 8
        col_x_right = sx + int(cell_w/2) + 6
        left = True
        y = start_y
        for i,(p,deg) in enumerate(items):
            # planet color dot
            color = PLANET_COLORS.get(p, "#333333")
            dot_r = max(3, int(size*0.0035))
            x_dot = col_x_left + (0 if left else (col_x_right - col_x_left))
            # text position (dot then label)
            txt_x = x_dot + dot_r + 6
            label = f"{p}"
            if show_degrees:
                label = f"{p} {_deg_min_str(deg)}"
            lines = _wrap_lines(label, max_chars=18)
            for li, line in enumerate(lines):
                tx = txt_x
                ty = y + li * int(font_base*1.05)
                # draw dot only on first line
                if li == 0:
                    dwg.add(dwg.circle(center=(x_dot, y+2), r=dot_r, fill=color, stroke="none"))
                dwg.add(dwg.text(line,
                                 insert=(tx, ty + int(font_base*0.6)),
                                 font_size=int(font_base*0.95),
                                 font_family=font_family,
                                 fill=text_color))
            # move to next slot
            if left:
                left = False
                # keep same y for right column
            else:
                left = True
                y += int(font_base*1.3) * max(1, len(lines))  # move down after filling both columns

    # draw ASC marker box (big and visible)
    asc = rasi_obj.get("asc")
    if asc is not None:
        asc_sign = int((asc // 30) % 12) + 1
        for sign, sx, sy in sign_layout:
            if sign == asc_sign:
                badge_r = int(cell_h * 0.07)
                cx = sx + cell_w - (badge_r + 10)
                cy = sy + (badge_r + 10)
                dwg.add(dwg.circle(center=(cx, cy), r=badge_r, fill="#111111", stroke="#fff", stroke_width=1))
                dwg.add(dwg.text("ASC", insert=(cx - badge_r*0.7, cy + int(badge_r*0.3)),
                                 font_size=int(font_base*0.8), font_family=font_family, fill="#fff", font_weight="700"))
                break

    # optional footer legend (small)
    legend_y = grid_y0 + grid_h + 6
    dwg.add(dwg.text("Legend:", insert=(margin+6, legend_y + 12), font_size=int(font_base*0.9), font_family=font_family, fill=text_color, font_weight="700"))
    lx = margin + 74
    for i,(pn,color) in enumerate(PLANET_COLORS.items()):
        # small dot + short label
        dwg.add(dwg.circle(center=(lx + i*80, legend_y + 8), r=4, fill=color))
        dwg.add(dwg.text(pn, insert=(lx + 10 + i*80, legend_y + 12), font_size=int(font_base*0.85), font_family=font_family, fill=text_color))

    return dwg.tostring()
