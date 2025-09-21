# streamlit_app.py (updated)
import streamlit as st
from datetime import datetime
from astrology import ChartCalculator
from charts.north_renderer import draw_north_chart_svg
from charts.south_renderer import draw_south_chart_svg
from engine import HoroscopeEngine
from yogas import analyze_chart_for_yogas_and_dasas
from utils import geocode_place, ensure_tzaware

st.set_page_config(page_title="Sahadev a Vedic Horoscope", layout="centered")

st.title("Sahadev a Vedic Horoscope (North & South Indian)")

with st.form("birth_form"):
    col1, col2 = st.columns(2)
    with col1:
        dob = st.date_input("Date of birth", datetime(1996, 10, 15))
        tob = st.time_input("Time of birth", datetime(1996, 10, 15, 17, 55).time())
        place = st.text_input("Place of birth (city, country)", "Chennai, India")
    with col2:
        tz = st.text_input("Timezone (e.g. Asia/Kolkata)", "Asia/Kolkata")
        ayanamsa = st.selectbox("Ayanamsa", ["Lahiri", "Raman", "Fagan-Allen"])
        house_system = st.selectbox("House system", ["Placidus", "WholeSign"])
        chart_style = st.selectbox("Chart style", ["NorthIndian", "SouthIndian"])
        llm_lang = st.selectbox("LLM language", ["ta (Tamil)", "en (English)"])
    submit = st.form_submit_button("Generate Horoscope")

if submit:
    loc = geocode_place(place)
    if not loc:
        st.error("Could not geocode place. Enter 'lat,lon' or a different place name.")
    else:
        dt_naive = datetime.combine(dob, tob)
        dt = ensure_tzaware(dt_naive, tz)
        calc = ChartCalculator(dt, loc["lat"], loc["lon"], tz, ayanamsa=ayanamsa, house_system=house_system)
        rasi = calc.get_rasi_chart()
        nav = calc.get_navamsa_chart()

        # Render chart: increase size and ensure white background for contrast
        if chart_style == "NorthIndian":
            svg = draw_north_chart_svg(rasi, size=1000, bg_color="#ffffff", text_color="#111111", title="Rasi Chart (North Indian)")
        else:
            svg = draw_south_chart_svg(rasi, size=1000, bg_color="#ffffff", text_color="#111111", title="Rasi Chart (South Indian)")

        st.header("Rasi Chart")
        st.components.v1.html(svg, height=1000, scrolling=True)

        st.header("Navamsa Overview")
        st.code(nav)

        # Yogas & Dasas (heuristic or library if installed)
        analysis_yogas = analyze_chart_for_yogas_and_dasas(rasi, nav, birth_dt=dt)

        st.subheader("Detected Yogas & Dasas (preliminary)")
        st.json(analysis_yogas)

        # LLM analysis
        engine = HoroscopeEngine()
        structured = engine.format_structured(rasi, nav, calc.metadata())

        # Merge heuristic yogas/dasas into the structured payload so LLM sees them
        structured["yogas"] = analysis_yogas.get("yogas", [])
        structured["dasas"] = analysis_yogas.get("dasas", {})

        with st.expander("Structured payload sent to LLM"):
            st.json(structured)

        # choose lang code for engine: 'ta' or 'en'
        lang_code = "ta" if llm_lang.startswith("ta") else "en"

        with st.spinner("Generating horoscope (LLM)..."):
            result = engine.generate_analysis(structured, lang=lang_code)

        st.subheader("Horoscope")
        # If engine returned parsed JSON (headline/bullets/narrative), render them
        if isinstance(result, dict):
            if result.get("headline"):
                st.markdown(f"**{result['headline']}**")
            if result.get("bullets"):
                for b in result["bullets"]:
                    st.write("- " + b)
            # If narrative is present as string, show it
            if result.get("narrative"):
                st.write(result["narrative"])
            # Show yogas/dasas inferred by LLM if present
            if result.get("yogas"):
                st.markdown("**Yogas (from LLM):**")
                for y in result["yogas"]:
                    st.write("- " + y)
            if result.get("dasas"):
                st.markdown("**Dasas (from LLM):**")
                st.json(result["dasas"])
        else:
            # Fallback: show raw text
            st.write(result)

        # If the LLM returned a minimal response or asked for data, show the raw response to help debug
        if isinstance(result, dict) and not any(k in result for k in ("headline", "bullets", "narrative")):
            st.warning("LLM returned no structured analysis. Showing raw output for debugging.")
            st.write(result)
