# SAHADEV — Vedic Horoscope Streamlit App

A Streamlit-based Vedic horoscope prototype that:
- computes planetary positions using Swiss Ephemeris (`pyswisseph`)
- renders North & South Indian rasi charts as SVGs
- detects basic yogas & provides Vimshottari dasa placeholders (integrates with `pyjhora` or `VedicAstro` if installed)
- generates human-friendly horoscope text via an LLM (OpenAI-compatible code provided)

## Quickstart

1. Create and activate virtualenv:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
