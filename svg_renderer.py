# ssvg_render.py
"""
Compatibility shim for older imports.
Redirects to new chart renderers in charts.north_renderer and charts.south_renderer.
Keep this file while you update other code; remove after cleanup.
"""

from charts.north_renderer import draw_north_chart_svg
from charts.south_renderer import draw_south_chart_svg

# Backwards-compatible API:
def render_rasi_svg(rasi_obj, style='north', **kwargs):
    """
    style: 'north' or 'south'
    kwargs passed to the new draw_* functions (size, bg_color, etc).
    """
    style = (style or 'north').lower()
    if style.startswith('n'):
        return draw_north_chart_svg(rasi_obj, **kwargs)
    return draw_south_chart_svg(rasi_obj, **kwargs)

def render_navamsa_svg(nav_obj, **kwargs):
    # If you added a dedicated nav renderer, call it; otherwise return a basic table SVG
    try:
        from charts.nav_renderer import draw_navamsa_svg
        return draw_navamsa_svg(nav_obj, **kwargs)
    except Exception:
        # simple fallback
        import svgwrite
        size = kwargs.get('size', 420)
        dwg = svgwrite.Drawing(size=(size, size))
        dwg.add(dwg.rect((0,0),(size,size), fill="#ffffff"))
        x, y = 12, 20
        dwg.add(dwg.text("Navamsa", insert=(x,y)))
        for i,(p,info) in enumerate(sorted(nav_obj.get('navamsa', {}).items())):
            dwg.add(dwg.text(f"{p}: {info.get('nav_sign')}", insert=(x, y + (i+1)*18)))
        return dwg.tostring()
