# engine.py
"""
Robust HoroscopeEngine:
- loads .env/.cred as before (kept minimal here)
- builds prompt from templates/horoscope_prompt.txt (fallback)
- ALWAYS appends the structured JSON at the end of the prompt (defensive)
- attempts call with new or old OpenAI SDKs
- if the model asks for the JSON (or doesn't return JSON), retries once
  with an explicit injected prompt containing the structured JSON
- falls back to local deterministic narrative if no LLM available
"""

import os
import json
import re
from pathlib import Path

# optional dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _load_cred(path: str = ".cred"):
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

_creds = _load_cred()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or _creds.get("OPENAI_API_KEY")
ASTRO_MODEL = os.getenv("ASTRO_MODEL") or _creds.get("ASTRO_MODEL", "gpt-4o-mini")

# OpenAI import detection (new/old)
try:
    import openai as _openai_module
except Exception:
    _openai_module = None

try:
    from openai import OpenAI as OpenAIClient  # new SDK
    _has_new_client = True
except Exception:
    OpenAIClient = None
    _has_new_client = False

_has_old_style = bool(_openai_module and getattr(_openai_module, "ChatCompletion", None))

_openai_client = None
if _has_new_client and OPENAI_API_KEY:
    try:
        _openai_client = OpenAIClient(api_key=OPENAI_API_KEY)
    except Exception:
        try:
            _openai_client = OpenAIClient()
        except Exception:
            _openai_client = None
if _openai_module and OPENAI_API_KEY:
    try:
        setattr(_openai_module, "api_key", OPENAI_API_KEY)
    except Exception:
        pass

def _extract_json_from_text(text: str):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start:i+1]
                cleaned = re.sub(r",\s*}", "}", candidate)
                cleaned = re.sub(r",\s*]", "]", cleaned)
                cleaned = cleaned.strip("` \n\r\t")
                try:
                    return json.loads(cleaned)
                except Exception:
                    return None
    return None

def _resp_text_from_new(resp):
    try:
        choices = getattr(resp, "choices", None)
        if choices and len(choices) > 0:
            first = choices[0]
            msg = getattr(first, "message", None)
            if msg:
                c = getattr(msg, "content", None)
                if c:
                    return c
            try:
                return first["message"]["content"]
            except Exception:
                pass
    except Exception:
        pass
    return None

def _resp_text_from_old(resp):
    try:
        if isinstance(resp, dict):
            return resp["choices"][0]["message"]["content"]
        choices = getattr(resp, "choices", None)
        if choices and len(choices) > 0:
            first = choices[0]
            msg = getattr(first, "message", None)
            if msg:
                return getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
            try:
                return first["message"]["content"]
            except Exception:
                pass
    except Exception:
        pass
    return None

class HoroscopeEngine:
    def __init__(self, api_key_env="OPENAI_API_KEY"):
        self.api_key = os.getenv(api_key_env) or OPENAI_API_KEY
        self.model = os.getenv("ASTRO_MODEL") or ASTRO_MODEL

    def format_structured(self, rasi, nav, meta):
        payload = {
            "meta": meta,
            "rasi": {
                p: {
                    "lon": info.get("lon"),
                    "rasi": info.get("rasi"),
                    "deg": info.get("degree_in_sign") or info.get("deg"),
                } for p, info in rasi.get("planets", {}).items()
            },
            "asc": rasi.get("asc"),
            "navamsa": nav.get("navamsa")
        }
        return payload

    def _load_prompt_template(self, lang="ta"):
        template_path = Path("templates") / "horoscope_prompt.txt"
        if template_path.exists():
            try:
                return template_path.read_text(encoding="utf-8")
            except Exception:
                pass
        # fallback minimal template (Tamil-first)
        if lang and lang.startswith("ta"):
            return (
                "You are an experienced Vedic astrologer. Reply in JSON only with keys: "
                '{"headline":"","bullets":[],"narrative":"","yogas":[],"dasas":{}}.\n\n'
                "Please analyze the following chart. Input:\n{input}\n"
            )
        return (
            "You are an experienced Vedic astrologer. Reply in JSON only with keys: "
            '{"headline":"","bullets":[],"narrative":"","yogas":[],"dasas":{}}.\n\n'
            "Please analyze the following chart. Input:\n{input}\n"
        )

    def _build_prompt(self, structured, lang="ta"):
        template = self._load_prompt_template(lang=lang)
        s = json.dumps(structured, indent=2, ensure_ascii=False)
        # Replace common placeholders defensively
        if "{{ structured_data }}" in template:
            prompt = template.replace("{{ structured_data }}", s)
        elif "{input}" in template:
            prompt = template.replace("{input}", s)
        else:
            # Best-effort: append JSON explicitly so the model always receives the data
            prompt = template + "\n\nJSON_INPUT:\n" + s
        return prompt

    def _model_requests_json(self, text: str) -> bool:
        if not text:
            return False
        # typical phrasing models use when asking for the data
        ask_patterns = [
            r"please provide.*structured.*json",
            r"please provide.*json",
            r"please provide the chart json",
            r"send me the json",
            r"i need the json",
            r"provide the structured json",
        ]
        t = text.lower()
        for p in ask_patterns:
            if re.search(p, t):
                return True
        return False

    def _call_llm(self, messages):
        # Try new OpenAI client first
        if _openai_client:
            try:
                resp = _openai_client.chat.completions.create(model=self.model, messages=messages, max_tokens=1200)
                text = _resp_text_from_new(resp)
                return text
            except Exception:
                pass
        # Then try old-style openai module
        if _openai_module and getattr(_openai_module, "ChatCompletion", None):
            try:
                resp = _openai_module.ChatCompletion.create(model=self.model, messages=messages, max_tokens=1200)
                text = _resp_text_from_old(resp)
                return text
            except Exception:
                pass
        return None

    def generate_analysis(self, structured_payload, lang="ta"):
        """
        Generate analysis. If the model asks for the structured JSON, retry once with the JSON explicitly
        injected at the top of the prompt.
        """
        # Build initial prompt
        prompt = self._build_prompt(structured_payload, lang=lang)
        messages = [
            {"role": "system", "content": "You are an expert Vedic astrologer and write in a culturally sensitive manner."},
            {"role": "user", "content": prompt}
        ]

        text = self._call_llm(messages)
        parsed = _extract_json_from_text(text or "")

        # If parsed JSON found, return it
        if parsed:
            return parsed

        # If model explicitly asked for the JSON (or returned nothing usable), retry once with explicit injection
        if text and (self._model_requests_json(text) or parsed is None):
            injected_prompt = (
                "Proceed using the following structured JSON (do not ask for it again). "
                "Use it to produce JSON with keys: headline, bullets, narrative, yogas, dasas.\n\n"
                + json.dumps(structured_payload, indent=2, ensure_ascii=False)
            )
            messages_retry = [
                {"role": "system", "content": "You are an expert Vedic astrologer and write in a culturally sensitive manner."},
                {"role": "user", "content": injected_prompt}
            ]
            text2 = self._call_llm(messages_retry)
            parsed2 = _extract_json_from_text(text2 or "")
            if parsed2:
                return parsed2
            # If still nothing, return the LLM text as narrative (helpful feedback)
            return {"narrative": (text2 or text or "LLM produced no usable output.")}

        # If no LLM available or nothing useful, fallback
        return self._fallback_text(structured_payload)

    def _fallback_text(self, structured):
        rasi = structured.get("rasi", {})
        headline = "Basic horoscope overview (local fallback)"
        bullets = []
        for p, info in rasi.items():
            r = info.get("rasi")
            deg = info.get("deg")
            if deg is None:
                try:
                    deg = float(info.get("lon", 0)) % 30
                except Exception:
                    deg = 0.0
            bullets.append(f"{p}: sign {r}, {deg:.1f}°")
            if len(bullets) >= 6:
                break
        narrative = (
            headline + "\n\n" +
            "Key placements: " + "; ".join(bullets) + ".\n\n" +
            "This is an automated fallback reading."
        )
        return {"headline": headline, "bullets": bullets, "narrative": narrative, "yogas": [], "dasas": {}}
