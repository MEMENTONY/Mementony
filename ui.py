# ui.py - auto-extracted from streamlit_app.py (behavior-preserving)
import json
import html
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from config import *
from state import *

def t(ko, en):
    return ko if st.session_state.lang == "ko" else en

def profile():
    p = st.session_state.profile
    if isinstance(p, dict) and p:
        merged = dict(DEFAULT_PROFILE)
        merged.update(p)
        return merged
    st.session_state.profile = dict(DEFAULT_PROFILE)
    return dict(DEFAULT_PROFILE)

def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))

def _display_money_value(v):
    try:
        amount = float(v or 0.0)
    except (TypeError, ValueError):
        amount = 0.0
    if st.session_state.get("display_currency", "USD") == "KRW":
        rate = max(float(st.session_state.get("usd_krw_rate", 1400.0) or 1400.0), 1.0)
        return amount * rate, "KRW"
    return amount, "USD"

def money(v):
    amount, currency = _display_money_value(v)
    sign = "-" if amount < 0 else ""
    if currency == "KRW":
        return f"{sign}₩{abs(amount):,.0f}"
    return f"{sign}${abs(amount):,.2f}"

def signed_money(v):
    amount, currency = _display_money_value(v)
    sign = "+" if amount >= 0 else "-"
    if currency == "KRW":
        return f"{sign}₩{abs(amount):,.0f}"
    return f"{sign}${abs(amount):,.2f}"

def signed_pct(v):
    return f"+{v:.1f}%" if v >= 0 else f"{v:.1f}%"

def cents(v):
    return f"{v:.1f}¢"

def stat(label, value, note="", tone=""):
    cls = " pos" if tone == "pos" else " neg" if tone == "neg" else ""
    return f"""<div class="stat"><div class="s-label">{label}</div><div class="s-value{cls}">{value}</div><div class="s-note">{note}</div></div>"""

def spec_row(key, val, state_text="", kind="i"):
    s = f'<span class="state {kind}">{state_text}</span>' if state_text else ""
    return f"""<div class="spec-row"><div class="spec-key">{key}</div><div class="spec-val">{val}</div><div>{s}</div></div>"""

def meter(label, value, kind, verdict, max_v=100, unit=""):
    """Meter with explicit colored verdict pill so good/bad is obvious."""
    color = {"g": "var(--green)", "w": "var(--amber)", "b": "var(--red)", "i": "var(--ink)"}.get(kind, "var(--ink)")
    width = clamp(value / max_v * 100 if max_v else 0)
    return f"""<div class="meter">
<div class="m-row">
  <span class="m-label">{label}</span>
  <span class="m-right"><span class="m-num {kind}">{value:.1f}{unit}</span><span class="state {kind}">{verdict}</span></span>
</div>
<div class="m-track"><div class="m-fill" style="width:{width:.1f}%;background:{color};"></div></div>
</div>"""

def line(text, kind="i"):
    return f'<div class="line"><span class="dot {kind}"></span><span>{text}</span></div>'

def verdict_dot(level):
    return {"good": "g", "warn": "w", "bad": "b"}.get(level, "i")

def grade_word(kind):
    return {"g": t("좋음", "Good"), "w": t("주의", "Caution"), "b": t("위험", "Risk"), "i": t("보통", "Neutral")}[kind]

def esc(v):
    # Collapse newlines/tabs to spaces so interpolated data can never introduce a blank line
    # that would break a single-line HTML block (Streamlit markdown renders such HTML as text).
    return html.escape(re.sub(r"[\r\n\t]+", " ", str(v or "")), quote=True)

_PILL_PALETTE = ("blue", "green", "red", "amber", "purple", "teal")

def outcome_pill(name):
    """Polymarket-style colored chip for a market outcome. Color is deterministic per
    outcome name (like team colors), so the same outcome always reads the same."""
    s = str(name or "").strip()
    if not s:
        return ""
    idx = sum(ord(c) for c in s) % len(_PILL_PALETTE)
    return f'<span class="pill {_PILL_PALETTE[idx]}">{esc(s)}</span>'

def cents_pill(v):
    """Small neutral price chip in cents (Polymarket-style)."""
    try:
        return f'<span class="price-pill">{cents(float(v or 0))}</span>'
    except (TypeError, ValueError):
        return ""

def self_check_scale():
    try:
        scale = int(st.session_state.get("self_check_scale", 5) or 5)
    except Exception:
        scale = 5
    return 10 if scale == 10 else 5

def self_check_scale_help():
    return t("1 = 매우 낮음 · 중간 = 보통 · 최대 = 매우 높음", "1 = very low · middle = normal · max = very high")

__all__ = [
    '_PILL_PALETTE',
    '_display_money_value',
    'cents',
    'cents_pill',
    'clamp',
    'esc',
    'outcome_pill',
    'grade_word',
    'line',
    'meter',
    'money',
    'profile',
    'self_check_scale',
    'self_check_scale_help',
    'signed_money',
    'signed_pct',
    'spec_row',
    'stat',
    't',
    'verdict_dot',
]
