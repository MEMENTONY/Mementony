# data.py - auto-extracted from streamlit_app.py (behavior-preserving)
import hashlib
import json
import html
import os
import time
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from config import *
from state import *
from ui import *
from engine import *

def get_api_key():
    """Read Anthropic key safely from Streamlit secrets or local env. Never hard-code the key in app.py."""
    candidates = []
    try:
        candidates.append(st.secrets.get("ANTHROPIC_API_KEY", ""))
    except Exception:
        pass
    try:
        candidates.append(st.secrets.get("anthropic", {}).get("api_key", ""))
    except Exception:
        pass
    try:
        candidates.append(st.secrets.get("anthropic", {}).get("ANTHROPIC_API_KEY", ""))
    except Exception:
        pass
    candidates.append(os.getenv("ANTHROPIC_API_KEY", ""))

    for k in candidates:
        k = str(k).strip().strip('"').strip("'")
        if k.startswith("sk-ant-") or k.startswith("sk-"):
            return k
    return None

def build_prompt(market_name, outcome="", current_price=0, category="기타", sub="",
                 ai_context="", bookmaker_memo="", fair_price=None, edge=None,
                 market_class="", bookmaker_prob=None, bookmaker_source_memo="",
                 ai_extra_context="", report_mode="standard", resolution="", **_ignore):
    """Research-focused JSON prompt.

    Memento's deterministic engine already owns price/risk/stake. Claude is asked
    only for the things a language model can actually do well WITHOUT live internet:
    interpret the real Polymarket resolution rules, structure the user's pasted
    research, frame the edge, and produce an honest pre-bet checklist. It must never
    fabricate records, standings, injuries, or odds; unknown facts go to missing_data.
    The schema is flat and stable so the UI always renders clean cards/tables.
    """
    lang = "ko" if st.session_state.lang == "ko" else "en"
    category = str(category or "기타")
    sub = str(sub or "")
    market_name = str(market_name or "")
    outcome = str(outcome or "")
    resolution = str(resolution or "").strip()
    try:
        current_price_f = float(current_price or 0)
    except Exception:
        current_price_f = 0.0
    try:
        fair_price_f = float(fair_price) if fair_price is not None else None
    except Exception:
        fair_price_f = None
    try:
        edge_f = float(edge) if edge is not None else (fair_price_f - current_price_f if fair_price_f is not None else None)
    except Exception:
        edge_f = None

    cat = f"{category} {sub} {market_name}".lower()
    sporty = any(k in cat for k in ("e스포츠", "esport", "스포츠", "sport", "lol", "lck", "lpl", "mlb",
                                    "baseball", "nba", "nfl", "ufc", "tennis", "soccer", "football", "valorant", "cs2", "dota"))
    if sporty:
        focus = ("Sports/esports scouting: structure the user's notes into head-to-head, recent form, "
                 "standing, roster/injuries, and the style/matchup that decides this game.")
    else:
        focus = ("Event/market analysis: settlement criteria, timing risk, official source, the catalyst "
                 "or condition that actually decides YES, and liquidity/uncertainty.")

    memo = str(ai_context or ai_extra_context or "").strip()
    bkm = str(bookmaker_memo or bookmaker_source_memo or "").strip()
    if not bkm and bookmaker_prob not in (None, "", 0, 0.0):
        try:
            bkm = f"bookmaker implied {float(bookmaker_prob):.1f}%"
        except Exception:
            bkm = str(bookmaker_prob)

    evidence_parts = []
    if memo:
        evidence_parts.append(f"USER_NOTES (your only evidence for facts):<<<{memo}>>>")
    if bkm:
        evidence_parts.append(f"BOOKMAKER_INPUT:<<<{bkm}>>>")
    if resolution:
        evidence_parts.append(f"POLYMARKET_RESOLUTION_TEXT:<<<{resolution[:1400]}>>>")
    if memo or bkm:
        basis_rule = ("Base every factual claim ONLY on USER_NOTES / BOOKMAKER_INPUT above. "
                      "Anything not stated there is unknown — write '확인 필요' and add it to missing_data.")
    else:
        basis_rule = ("No research notes were provided. Do NOT invent any records, standings, form, injuries, "
                      "or odds. Set scouting fields to '확인 필요', confidence='low', and use data_basis to tell "
                      "the user plainly that this report is a framework only until they paste research.")
    evidence = ("\n" + "\n".join(evidence_parts)) if evidence_parts else ""

    fair_txt = f"{fair_price_f:.1f}¢" if fair_price_f is not None else "확인 필요"
    edge_txt = f"{edge_f:+.1f}¢" if edge_f is not None else "확인 필요"
    implied_txt = f"{current_price_f:.0f}%" if current_price_f else "확인 필요"
    price_txt = f"{current_price_f:.1f}¢" if current_price_f else "확인 필요"
    bookmaker_txt = bkm if bkm else "확인 필요"
    res_txt = "provided above — interpret it" if resolution else "확인 필요"
    lang_line = "Write every string value in natural Korean." if lang == "ko" else "Write every string value in English."
    mode_instruction = {
        "brief":    "Compact: summary 2 items, swing_factors 2, checklist 3, one short sentence per field.",
        "standard": "Standard: summary 3 items, swing_factors 3, checklist 4, concise sentences.",
        "detailed": "Detailed: summary 3 items, swing_factors 5, checklist 5, 2-3 sentence field values where useful.",
    }.get(str(report_mode or "standard"), "Standard length.")

    market_payload = {
        "name": market_name, "outcome": outcome, "category": category, "sub": sub,
        "market_class": market_class, "polymarket_price_cents": round(current_price_f, 1),
        "polymarket_implied_pct": round(current_price_f, 1),
        "user_fair_price": fair_txt, "user_edge": edge_txt, "bookmaker_view": bookmaker_txt,
    }

    return f"""You are Memento's research analyst for Polymarket bets. You have NO live internet access. Output ONE JSON object only — no markdown, no ``` fences, no text before or after. Every value is a flat string or an array of strings.

YOUR JOB (in priority order):
1. Interpret the resolution rules and name the single biggest settlement risk (this is your most valuable output).
2. Organize the user's pasted notes into a clean scouting picture — never add facts they did not give you.
3. Frame the edge using the known numbers (price, fair, bookmaker). The app already handles stake/risk/cap, so do NOT discuss bet sizing.
4. Tell the user exactly what to verify before entering.

HARD RULES:
- {basis_rule}
- Never fabricate records, standings, recent form, injuries, line-ups, or odds.
- Be calibrated: if evidence is thin, say so and keep confidence low. No false certainty.

MARKET={json.dumps(market_payload, ensure_ascii=False)}
FOCUS: {focus}{evidence}
REPORT_MODE: {report_mode}. {mode_instruction}

Return EXACTLY this JSON shape:
{{
"report_title":"short, specific title",
"stance":"favorable|neutral|risky",
"estimated_probability":"e.g. 58% (only if notes support it, else 확인 필요)",
"confidence":"high|medium|low",
"data_basis":"one honest sentence: what this report is actually based on",
"verdict":"1-2 sentence bottom line in plain language, context-based not math",
"summary":["key point","key point"],
"scouting":{{"head_to_head":"확인 필요","recent_form":"확인 필요","standing":"확인 필요","roster_news":"확인 필요","style_matchup":"확인 필요"}},
"odds":{{"polymarket":"{price_txt}","implied":"{implied_txt}","fair":"{fair_txt}","edge":"{edge_txt}","bookmaker":"{bookmaker_txt}","read":"short read on whether it looks cheap/expensive"}},
"resolution_read":"how this market settles and the main settlement risk ({res_txt})",
"swing_factors":["the variable that most decides the outcome"],
"checklist":["a concrete thing to verify before entering"],
"missing_data":["unknown items only; [] if none"]
}}

{lang_line}
"""

def call_claude(prompt, mode="standard"):
    key = get_api_key()
    if not key:
        return None, "no_key"
    max_tokens = {"brief": 700, "standard": 1500, "detailed": 2200}.get(str(mode or "standard"), 1500)
    try:
        payload = json.dumps({"model": "claude-sonnet-4-6", "max_tokens": max_tokens,
                              "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=payload,
                                     headers={"Content-Type": "application/json", "x-api-key": key,
                                              "anthropic-version": "2023-06-01"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
            return data["content"][0]["text"], None
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "ignore")[:500]
        except Exception:
            body = ""
        return None, f"http_{e.code}: {body}"
    except Exception as e:
        return None, str(e)

def safe_json_parse(text):
    """Parse Claude JSON robustly. Returns None on failure without raising."""
    if not text:
        return None
    import re as _re
    s = str(text).strip()
    m = _re.search(r"```(?:json)?\s*(\{.*\})\s*```", s, _re.S)
    if m:
        s = m.group(1)
    a, b = s.find("{"), s.rfind("}")
    if a == -1 or b == -1 or b <= a:
        return None
    frag = s[a:b + 1]
    attempts = [
        frag,
        frag.replace("\n", " "),
        _re.sub(r",\s*}", "}", _re.sub(r",\s*]", "]", frag)),
        frag.replace("\\", ""),
    ]
    for attempt in attempts:
        try:
            return json.loads(attempt)
        except Exception:
            continue
    return None

def _ai_get(d, *keys, default=""):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", [], {}):
            return v
    return default

def extract_slug(url):
    """Return the last usable path segment. Supports localized Polymarket URLs like /ko/sports/mlb/<slug>."""
    try:
        path = urllib.parse.urlparse(str(url or "").strip()).path.strip("/")
    except Exception:
        return ""
    parts = [p for p in path.split("/") if p]
    return parts[-1] if parts else ""

@st.cache_data(ttl=60, show_spinner=False)
def fetch_gamma(slug):
    api = f"https://gamma-api.polymarket.com/events?slug={urllib.parse.quote(slug)}"
    req = urllib.request.Request(api, headers={"User-Agent": "Memento/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))

def parse_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return []
    return []

def classify_market_type(question, outcome="", is_binary=False):
    """Classify markets for URL-loaded Polymarket events.

    MAIN = full match / moneyline / series winner.
    GAME = specific game/map winner.
    PROP = markets the user does not want in the entry flow.
    Important: many Polymarket main moneyline markets are just binary team-vs-team
    questions without the word "moneyline". Those are promoted to MAIN when
    they are not props and not game/map-specific.
    """
    s = f"{question or ''} {outcome or ''}".lower()
    if any(k in s for k in PROP_KW):
        return "prop"
    if GAME_RE.search(s):
        return "p2_game"
    if any(k in s for k in MAIN_KW):
        return "p1_main"
    if is_binary:
        return "p1_main"
    return "other"

def is_prop_market(q, outcome=""):
    return classify_market_type(q, outcome, False) == "prop"

def is_relevant_market(q, outcome="", event_title=""):
    s = f"{event_title or ''} {q or ''}"
    return classify_market_type(s, outcome, False) in ("p1_main", "p2_game")

def _event_resolution(event, market):
    return (market.get("rules") or market.get("description") or market.get("resolutionSource") or
            event.get("rules") or event.get("description") or event.get("resolutionSource") or "")

def _event_volume(event, market):
    return market.get("volume") or market.get("volumeNum") or event.get("volume") or event.get("volumeNum") or ""

def _event_liquidity(event, market):
    return market.get("liquidity") or market.get("liquidityNum") or event.get("liquidity") or event.get("liquidityNum") or ""

def _event_end_date(event, market):
    return market.get("endDate") or market.get("endDateIso") or event.get("endDate") or event.get("endDateIso") or ""

def extract_markets(payload, category=""):
    """Extract MAIN + GAME winner markets.

    Return order:
    1) MAIN full match / moneyline / series winner, including binary non-prop non-game markets
    2) GAME/MAP winner
    Props are excluded. Game markets never replace main markets.
    """
    events = payload if isinstance(payload, list) else payload.get("events", []) if isinstance(payload, dict) else []
    if not isinstance(events, list):
        return []
    p1, p2, binary_other = [], [], []
    seen = set()
    for event in events:
        if not isinstance(event, dict):
            continue
        event_title = event.get("title") or event.get("slug") or ""
        for m in event.get("markets", []) or []:
            if not isinstance(m, dict):
                continue
            q = m.get("question") or m.get("title") or m.get("slug") or event_title or "Unknown"
            outs = parse_list(m.get("outcomes"))
            prices = parse_list(m.get("outcomePrices"))
            tokens = parse_list(m.get("clobTokenIds"))
            if not outs:
                continue
            is_bin = len(outs) == 2
            cls = classify_market_type(f"{event_title} {q}", "", is_bin)
            if cls == "prop":
                continue
            for i, o in enumerate(outs):
                price = None
                if i < len(prices):
                    try:
                        price = round(float(prices[i]) * 100, 2)
                    except Exception:
                        price = None
                row = {
                    t("시장", "Market"): q,
                    t("선택지", "Outcome"): o,
                    t("현재가 (¢)", "Price (¢)"): price,
                    "token_id": tokens[i] if i < len(tokens) else "",
                    "volume": _event_volume(event, m),
                    "liquidity": _event_liquidity(event, m),
                    "endDate": _event_end_date(event, m),
                    "resolution": _event_resolution(event, m),
                    "event_title": event_title,
                    "market_class": cls,
                    "_binary": is_bin,
                }
                key = (row[t("시장", "Market")], row[t("선택지", "Outcome")], row.get("token_id"))
                if key in seen:
                    continue
                seen.add(key)
                if cls == "p1_main":
                    p1.append(row)
                elif cls == "p2_game":
                    p2.append(row)
                elif is_bin:
                    binary_other.append(row)
    if not p1 and binary_other:
        for r in binary_other:
            r["market_class"] = "p1_main"
        p1 = binary_other
    return p1 + p2

def _escape(v):
    return html.escape(str(v or ""))

def _as_cents(v):
    try:
        f = float(v)
        return f * 100 if 0 <= f <= 1 else f
    except Exception:
        return None

@st.cache_data(ttl=45, show_spinner=False)
def fetch_clob_price(token_id):
    """Read-only CLOB quote. Public endpoint; no trading/auth."""
    token_id = str(token_id or "").strip()
    if not token_id:
        return {"bid": None, "ask": None, "spread": None, "raw": {}}

    out = {"bid": None, "ask": None, "spread": None, "raw": {}}

    def _get(path, params):
        url = "https://clob.polymarket.com" + path + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Memento/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))

    try:
        bid_raw = _get("/price", {"token_id": token_id, "side": "BUY"})
        out["raw"]["bid"] = bid_raw
        out["bid"] = _as_cents(bid_raw.get("price") if isinstance(bid_raw, dict) else None)
    except Exception as e:
        out["raw"]["bid_error"] = str(e)

    try:
        ask_raw = _get("/price", {"token_id": token_id, "side": "SELL"})
        out["raw"]["ask"] = ask_raw
        out["ask"] = _as_cents(ask_raw.get("price") if isinstance(ask_raw, dict) else None)
    except Exception as e:
        out["raw"]["ask_error"] = str(e)

    try:
        sp_raw = _get("/spread", {"token_id": token_id})
        out["raw"]["spread"] = sp_raw
        out["spread"] = _as_cents(sp_raw.get("spread") if isinstance(sp_raw, dict) else None)
    except Exception as e:
        out["raw"]["spread_error"] = str(e)

    if out["spread"] is None and out["bid"] is not None and out["ask"] is not None:
        out["spread"] = out["ask"] - out["bid"]
    return out

@st.cache_data(ttl=45, show_spinner=False)
def fetch_clob_book(token_id):
    """Read-only CLOB orderbook. Fails soft."""
    token_id = str(token_id or "").strip()
    if not token_id:
        return {}
    try:
        url = "https://clob.polymarket.com/book?" + urllib.parse.urlencode({"token_id": token_id})
        req = urllib.request.Request(url, headers={"User-Agent": "Memento/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=15, show_spinner=False)
def fetch_live_token_price(token_id):
    """Return live bid/ask/mid/spread in cents. Fails soft and never calls Claude."""
    token_id = str(token_id or "").strip()
    if not token_id:
        return None
    # First try the existing quote endpoints. They are more stable than raw book shape.
    try:
        q = fetch_clob_price(token_id)
        bid, ask, spread = q.get("bid"), q.get("ask"), q.get("spread")
        mid = round((float(bid) + float(ask)) / 2, 2) if bid is not None and ask is not None else (bid if bid is not None else ask)
        if mid is not None:
            return {"bid": bid, "ask": ask, "mid": mid, "spread": spread, "source": "price"}
    except Exception:
        pass
    # Fallback to book. The JSON shape can differ, so parse defensively.
    try:
        book = fetch_clob_book(token_id)
        bids = book.get("bids") or [] if isinstance(book, dict) else []
        asks = book.get("asks") or [] if isinstance(book, dict) else []
        def _price(x):
            if isinstance(x, dict):
                return _as_cents(x.get("price"))
            if isinstance(x, (list, tuple)) and x:
                return _as_cents(x[0])
            return None
        bid_prices = [p for p in (_price(x) for x in bids) if p is not None]
        ask_prices = [p for p in (_price(x) for x in asks) if p is not None]
        bid = max(bid_prices) if bid_prices else None
        ask = min(ask_prices) if ask_prices else None
        mid = round((bid + ask) / 2, 2) if bid is not None and ask is not None else (bid if bid is not None else ask)
        spread = round(ask - bid, 2) if bid is not None and ask is not None else None
        return {"bid": bid, "ask": ask, "mid": mid, "spread": spread, "source": "book"} if mid is not None else None
    except Exception:
        return None

@st.cache_data(ttl=30, show_spinner=False)
def fetch_price_history(token_id, rng="1D"):
    """Polymarket CLOB price history -> list[{t,p}] (t=unix sec, p=cents). Fails soft."""
    token_id = str(token_id or "").strip()
    if not token_id:
        return []
    interval, fidelity = _PMHIST_RANGES.get(str(rng).upper(), ("1d", 15))
    attempts = [
        ("https://clob.polymarket.com/prices-history", {"market": token_id, "interval": interval, "fidelity": fidelity}),
        ("https://clob.polymarket.com/prices-history", {"market": token_id, "fidelity": fidelity}),
    ]
    for base, params in attempts:
        try:
            url = base + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers={"User-Agent": "Memento/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as r:
                d = json.loads(r.read().decode("utf-8"))
            hist = d.get("history") if isinstance(d, dict) else d
            if not isinstance(hist, list):
                hist = []
            out = []
            for p in hist:
                if not isinstance(p, dict):
                    continue
                pc = _as_cents(p.get("p", p.get("price", p.get("value"))))
                if pc is None:
                    continue
                out.append({"t": p.get("t", p.get("timestamp", len(out))), "p": round(pc, 2)})
            if out:
                return out
        except Exception:
            continue
    return []

def evaluate_live_price(entry_result, live_price):
    """Deterministic live re-evaluation. Does not call Claude."""
    entry_result = entry_result if isinstance(entry_result, dict) else {}
    fair = float(entry_result.get("fair_price") or st.session_state.get("watching_market", {}).get("fair_price") or 0)
    entry_p = float(entry_result.get("current_price") or st.session_state.get("watching_market", {}).get("entry_price") or 0)
    target = float(entry_result.get("target_price") or 999)
    edge = fair - float(live_price)
    move = float(live_price) - entry_p
    if live_price >= target:
        status, kind = t("익절 구간", "Take-profit zone"), "w"
    elif fair and live_price >= fair:
        status, kind = t("비쌈 — 진입 불리", "Expensive — worse entry"), "b"
    elif edge >= 8:
        status, kind = t("저평가 — 진입 유리", "Cheap — better entry"), "g"
    elif edge >= 3:
        status, kind = t("약간 저평가", "Slightly cheap"), "w"
    else:
        status, kind = t("적정", "Fair"), "i"
    return {"edge": edge, "move": move, "status": status, "kind": kind, "implied": live_price, "fair": fair}

def _first_present(obj, keys, default=""):
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj.get(k) not in (None, ""):
                return obj.get(k)
        for v in obj.values():
            got = _first_present(v, keys, None)
            if got not in (None, ""):
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = _first_present(v, keys, None)
            if got not in (None, ""):
                return got
    return default

def _history_points(raw):
    if isinstance(raw, dict):
        for key in ("history", "prices", "data"):
            val = raw.get(key)
            if isinstance(val, list):
                return val
    return raw if isinstance(raw, list) else []

def history_summary(raw):
    pts = _history_points(raw)
    vals = []
    for p in pts:
        if isinstance(p, dict):
            val = p.get("p", p.get("price", p.get("value")))
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            val = p[1]
        else:
            val = p
        cv = _as_cents(val)
        if cv is not None:
            vals.append(cv)
    if len(vals) >= 2:
        return {"start": vals[0], "last": vals[-1], "change": vals[-1] - vals[0], "points": len(vals)}
    return {"start": None, "last": None, "change": None, "points": len(vals)}

def book_summary(raw):
    bids = raw.get("bids", []) if isinstance(raw, dict) else []
    asks = raw.get("asks", []) if isinstance(raw, dict) else []
    def _level_value(level):
        if isinstance(level, dict):
            price = _as_cents(level.get("price")) or 0
            size = _safe_float(level.get("size"), 0)
            return price, size
        if isinstance(level, (list, tuple)) and len(level) >= 2:
            return _as_cents(level[0]) or 0, _safe_float(level[1], 0)
        return 0, 0
    bid_depth = sum(_level_value(x)[1] for x in bids[:5])
    ask_depth = sum(_level_value(x)[1] for x in asks[:5])
    return {"bids": len(bids), "asks": len(asks), "bid_depth5": bid_depth, "ask_depth5": ask_depth}

def build_order_candidate(row, clob=None, bankroll=None):
    clob = clob or {}
    bankroll = bankroll or effective_bankroll()
    price = row_get(row, "현재가 (¢)", "Price (¢)", 52.0)
    try:
        price = float(price)
    except Exception:
        price = 52.0
    bid = clob.get("bid")
    spread = clob.get("spread")
    limit_price = bid if isinstance(bid, (int, float)) and bid > 0 else price
    max_amt = min(bankroll * profile().get("max_pct", 3) / 100, profile().get("emotional_limit", 50))
    shares = max_amt / (limit_price / 100) if limit_price > 0 else 0
    kind = "g"
    note = t("후보 생성 가능", "Candidate ready")
    if isinstance(spread, (int, float)) and spread >= 5:
        kind, note = "w", t("스프레드 넓음 — 원본 호가 확인", "Wide spread — confirm orderbook")
    if price >= 85:
        kind, note = "w", t("고가 구간 — 신규 주문 후보는 보수적으로", "High-price zone — conservative sizing")
    if price >= 95:
        kind, note = "b", t("상환 스캘핑 구간 — 자동 주문 금지", "Redemption-scap zone — no automation")
    return {"limit_price": limit_price, "max_amount": max_amt, "shares": shares, "kind": kind, "note": note}

def row_get(row, ko, en=None, default=""):
    if not isinstance(row, dict):
        return default
    if ko in row:
        return row.get(ko, default)
    if en and en in row:
        return row.get(en, default)
    lookup = ("시장", "Market") if ko == "시장" else ("선택지", "Outcome") if ko == "선택지" else ("현재가 (¢)", "Price (¢)")
    for k in lookup:
        if k in row:
            return row.get(k, default)
    return row.get(ko, default)

@st.cache_data(ttl=30, show_spinner=False)
def fetch_wallet_positions(addr):
    """Public Polymarket data API — read-only, no login required."""
    api = f"https://data-api.polymarket.com/positions?user={urllib.parse.quote(addr)}&sizeThreshold=0.5&limit=100"
    req = urllib.request.Request(api, headers={"User-Agent": "Memento/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))

@st.cache_data(ttl=60, show_spinner=False)
def fetch_wallet_value(addr):
    api = f"https://data-api.polymarket.com/value?user={urllib.parse.quote(addr)}"
    req = urllib.request.Request(api, headers={"User-Agent": "Memento/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))

def _find_first_number(obj, keys):
    if isinstance(obj, dict):
        lower = {str(k).lower(): v for k, v in obj.items()}
        for k in keys:
            if k.lower() in lower:
                val = _safe_float(lower[k.lower()], None)
                if val is not None:
                    return val
        for v in obj.values():
            got = _find_first_number(v, keys)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = _find_first_number(v, keys)
            if got is not None:
                return got
    return None

def calc_profile_pnl(portfolio, cash, raw_positions=None, raw_value=None):
    raw_positions = raw_positions if isinstance(raw_positions, list) else []
    pos_value_local = sum(_safe_float(p.get("shares"), 0) * (_safe_float(p.get("cur"), 0) / 100) for p in portfolio)
    pos_cost_local = sum(_safe_float(p.get("inv"), 0) for p in portfolio)
    value_api = _find_first_number(raw_value, ["value", "positionValue", "positionsValue", "totalValue", "currentValue"])
    pos_value = value_api if value_api is not None and value_api >= 0 else pos_value_local
    raw_initial = sum(_safe_float(it.get("initialValue"), 0) for it in raw_positions)
    raw_current = sum(_safe_float(it.get("currentValue"), 0) for it in raw_positions)
    raw_realized = sum(_safe_float(it.get("realizedPnl"), 0) for it in raw_positions)
    raw_cash = sum(0 for it in raw_positions)
    raw_percent = _find_first_number(raw_positions, ["percentPnl", "percentRealizedPnl", "percentCashPnl"])
    cost = raw_initial if raw_initial > 0 else pos_cost_local
    if raw_current > 0 and value_api is None:
        pos_value = raw_current
    unrealized = pos_value - cost if cost else pos_value - pos_cost_local
    unrealized_pct = unrealized / cost * 100 if cost else 0
    wallet_assets = cash + pos_value
    deposits = _safe_float(st.session_state.deposits, 0)
    withdrawals = _safe_float(st.session_state.withdrawals, 0)
    # Manual cash/deposit/withdrawal inputs are the source of truth for profile-like P&L.
    # Deposit and withdrawal are both entered as positive total amounts.
    net_profit = wallet_assets + withdrawals - deposits
    adjusted_roi = net_profit / deposits * 100 if deposits else None
    _, month_pnl, year_pnl = period_pnl()
    status_kind = "g" if net_profit >= 0 else "b"
    status_text = t("누적 이익 중", "Net profitable") if net_profit >= 0 else t("누적 손실 중", "Net loss")
    return {"position_value": pos_value, "position_cost": cost, "cash": cash, "wallet_assets": wallet_assets,
            "unrealized": unrealized, "unrealized_pct": unrealized_pct,
            "realized_pnl": raw_realized, "percent_pnl": raw_percent if raw_percent is not None else unrealized_pct,
            "deposits": deposits, "withdrawals": withdrawals,
            "adjusted_profit": net_profit, "net_profit": net_profit, "adjusted_roi": adjusted_roi,
            "month_pnl": month_pnl, "year_pnl": year_pnl, "status_kind": status_kind, "status_text": status_text,
            "source_note": t("수동 현금·입금·출금 + 공개 포지션 API 기준", "Manual cash/deposit/withdrawal + public position API")}

@st.cache_data(ttl=60, show_spinner=False)
def fetch_wallet_activity(addr, limit=100, offset=0):
    """Read-only Polymarket activity feed for a wallet. Used for automatic trade history import."""
    qs = urllib.parse.urlencode({
        "user": addr,
        "limit": int(limit),
        "offset": int(offset),
        "sortBy": "TIMESTAMP",
        "sortDirection": "DESC",
    })
    api = f"https://data-api.polymarket.com/activity?{qs}"
    req = urllib.request.Request(api, headers={"User-Agent": "Memento/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

ACTIVITY_PAGE_SIZE = 500  # data-api /activity의 요청당 최대치

@st.cache_data(ttl=60, show_spinner=False)
def fetch_wallet_activity_all(addr, max_rows=1000):
    """활동내역을 offset 페이지네이션으로 max_rows까지 전부 수집한다.
    예전에는 최근 1페이지(최대 300건)만 가져와서, 그보다 오래된 '기존 거래'가
    거래일지에 영영 인식되지 않았다. 페이지가 짧게 오면(마지막 페이지) 멈춘다."""
    out, offset = [], 0
    max_rows = max(int(max_rows or ACTIVITY_PAGE_SIZE), 1)
    while offset < max_rows:
        n = min(ACTIVITY_PAGE_SIZE, max_rows - offset)
        batch = fetch_wallet_activity(addr, limit=n, offset=offset)
        if not isinstance(batch, list) or not batch:
            break
        out.extend(batch)
        if len(batch) < n:
            break
        offset += n
    return out

def _activity_time_value(it):
    if not isinstance(it, dict):
        return None
    return (it.get("timestamp") or it.get("createdAt") or it.get("created_at") or
            it.get("date") or it.get("time") or it.get("updatedAt"))

def _activity_dt(v):
    if isinstance(v, str) and v.strip():
        s = v.strip()
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                # Public APIs usually emit naive createdAt values in UTC.
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone(timedelta(hours=9))).isoformat()
        except Exception:
            pass

    ts = _safe_float(v, 0)
    if ts <= 0:
        return datetime.now(timezone(timedelta(hours=9))).isoformat()
    if ts > 10_000_000_000:  # milliseconds
        ts = ts / 1000
    # Polymarket timestamps are UTC; display in Korea time for journal grouping.
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(timezone(timedelta(hours=9))).isoformat()

def _activity_action(it):
    if not isinstance(it, dict):
        return ""
    side = str(it.get("side") or "").upper()
    typ = str(it.get("type") or it.get("activityType") or it.get("eventType") or "").upper()
    if side in ("BUY", "SELL"):
        return side
    if typ in ("BUY", "BOUGHT"):
        return "BUY"
    if typ in ("SELL", "SOLD"):
        return "SELL"
    blob = " ".join(str(it.get(k, "")) for k in ("type", "activityType", "eventType", "side", "action", "label")).lower()
    if "buy" in blob or "bought" in blob or "매수" in blob:
        return "BUY"
    if "sell" in blob or "sold" in blob or "매도" in blob:
        return "SELL"
    return ""

def _activity_asset(it):
    if not isinstance(it, dict):
        return ""
    for k in ("asset", "assetId", "token_id", "tokenId", "clobTokenId", "conditionId", "market", "marketId"):
        v = it.get(k)
        if v:
            return str(v)
    title = it.get("title") or it.get("slug") or it.get("eventSlug") or ""
    outcome = it.get("outcome") or ""
    return f"{title}|{outcome}" if title or outcome else ""

def normalize_activity(raw):
    """Convert raw Polymarket activity rows into a simple journal-like table."""
    rows = []
    if not isinstance(raw, list):
        return rows
    for it in raw:
        if not isinstance(it, dict):
            continue
        typ = str(it.get("type", "TRADE")).upper()
        side = _activity_action(it)
        # Keep trade-like rows first. Other activity can stay in raw debug.
        if side not in ("BUY", "SELL"):
            continue
        price_raw = _safe_float(it.get("price") or it.get("pricePerShare") or it.get("avgPrice"), 0)
        price_c = price_raw * 100 if 0 < price_raw <= 1 else price_raw
        size = _safe_float(it.get("size") or it.get("shares") or it.get("outcomeTokens"), 0)
        usdc = _safe_float(it.get("usdcSize") or it.get("usdValue") or it.get("amount"), 0)
        amount = usdc if usdc > 0 else size * (price_c / 100 if price_c else 0)
        combo = False
        if size <= 0 and price_c <= 0 and usdc > 0:
            # 콤보(팔레이) 등 수량·가격 없이 금액만 오는 체결 — 원가(금액) 기준으로 복원.
            # 원가·패배 손익은 정확하고 승리는 상환 이벤트 금액으로 정산된다. (combo 플래그로 가격 분석 제외)
            size, price_c, combo = usdc, 100.0, True
        tx_base = it.get("transactionHash") or it.get("transaction_hash") or it.get("hash") or ""
        asset = _activity_asset(it)
        tx_id = "|".join([str(tx_base), str(asset), str(_activity_time_value(it) or ""), side, str(size), str(price_raw)])
        rows.append({
            "tx_id": tx_id,
            "d": _activity_dt(_activity_time_value(it)),
            "name": it.get("title") or it.get("slug") or it.get("eventSlug") or "Polymarket trade",
            "outcome": it.get("outcome", ""),
            "side": side,
            "price": round(price_c, 2),
            "shares": round(size, 4),
            "amount": round(amount, 2),
            "asset": str(asset),
            "token_id": str(asset),
            "combo": combo,
        })
    return rows

def normalize_activity_events(raw):
    """Extract settlement/redemption/loss-like API activity rows for realized P&L matching."""
    events = []
    if not isinstance(raw, list):
        return events
    for idx, it in enumerate(raw):
        if not isinstance(it, dict):
            continue
        typ = str(it.get("type") or it.get("activityType") or it.get("eventType") or "").upper()
        side = str(it.get("side") or "").upper()
        blob = " ".join(str(it.get(k, "")) for k in ("type", "activityType", "eventType", "title", "slug", "eventSlug", "outcome", "status", "result")).lower()
        is_event = (
            side not in ("BUY", "SELL")
            and any(k in blob for k in ("redeem", "redemption", "settle", "settled", "claim", "claimed", "loss", "lost", "won", "win", "profit"))
        )
        if not is_event and typ not in ("REDEEM", "REDEMPTION", "SETTLE", "SETTLED", "CLAIM", "CLAIMED", "LOSS", "PROFIT"):
            continue

        amt = (
            it.get("usdcSize")
            or it.get("usdValue")
            or it.get("amount")
            or it.get("payout")
            or it.get("proceeds")
            or it.get("value")
            or ""
        )
        amount = ""
        if amt != "":
            amount = money(_safe_float(amt, 0.0))

        events.append({
            "name": it.get("title") or it.get("slug") or it.get("eventSlug") or t("알 수 없는 시장", "Unknown market"),
            "outcome": it.get("outcome", ""),
            "price": _as_cents(it.get("price")) if it.get("price") is not None else None,
            "shares": _safe_float(it.get("size") or it.get("shares"), 0.0) or None,
            "amount": amount,
            "result": typ.title() if typ else t("정산", "Settled"),
            "type": typ,
            "label": it.get("status") or it.get("result") or "",
            "d": _activity_dt(_activity_time_value(it)),
            "tx_id": it.get("transactionHash") or it.get("transaction_hash") or f"activity-event-{idx}",
        })
    return events

def _trade_content_sig(tr):
    """tx_id가 없거나 형식이 바뀐 옛 행도 같은 체결로 알아보는 내용 지문."""
    return "|".join([
        str(tr.get("d", "")), str(tr.get("name", "")), str(tr.get("outcome", "")),
        str(tr.get("side", "")).upper(),
        f"{_safe_float(tr.get('shares'), 0):.4f}", f"{_safe_float(tr.get('price'), 0):.2f}",
        f"{_safe_float(tr.get('amount'), 0):.2f}",
    ])

def merge_activity_into_log(items):
    """Merge API trades into auto_trades without duplicating existing rows.

    중복 판정은 '지금 실제로 존재하는' auto_trades 행 기준이다. 예전처럼 imported_tx_ids
    목록에만 의존하면, 목록만 남고 거래 행이 유실된 경우(부분 복원·초기화 꼬임 등)
    기존 거래가 다시는 인식되지 않는 버그가 있었다. tx_id가 없는 옛 행은 내용 지문으로
    중복을 막는다. imported_tx_ids는 하위호환용 미러로 계속 채워 둔다."""
    trades = st.session_state.get("auto_trades")
    if not isinstance(trades, list):
        trades = []
    st.session_state.auto_trades = trades
    seen_tx = {str(tr.get("tx_id")) for tr in trades if isinstance(tr, dict) and tr.get("tx_id")}
    legacy_sigs = {_trade_content_sig(tr) for tr in trades if isinstance(tr, dict) and not tr.get("tx_id")}
    added = 0
    for it in items:
        tx = str(it.get("tx_id") or "")
        if tx and tx in seen_tx:
            continue
        if not tx or legacy_sigs:
            if _trade_content_sig(it) in legacy_sigs:
                continue
        trades.append(it)
        if tx:
            seen_tx.add(tx)
        added += 1
    st.session_state.imported_tx_ids = sorted(seen_tx)
    return added

def summarize_activity(items):
    # Summarize imported activity for pattern review. Does not calculate realized P&L.
    now = datetime.now()
    today = now.date().isoformat()
    week_start = (now - timedelta(days=now.weekday())).date()
    month_key = now.strftime("%Y-%m")
    out = {
        "count": 0, "buy_count": 0, "sell_count": 0, "today_count": 0,
        "week_count": 0, "month_count": 0, "total_amount": 0.0,
        "top_market": "-", "top_market_count": 0, "market_count": 0,
        "repeat_markets": [], "heavy_markets": [], "insights": []
    }
    if not items:
        out["insights"].append(("i", t("불러온 거래내역이 없습니다.", "No imported activity yet.")))
        return out

    market_stats = {}
    for tr in items:
        name = str(tr.get("name") or "Unknown")
        side = str(tr.get("side") or "").upper()
        amount = _safe_float(tr.get("amount"), 0)
        out["count"] += 1
        out["total_amount"] += amount
        if side == "BUY":
            out["buy_count"] += 1
        elif side == "SELL":
            out["sell_count"] += 1
        d = str(tr.get("d") or "")[:10]
        if d == today:
            out["today_count"] += 1
        try:
            dd = datetime.fromisoformat(str(tr.get("d"))).date()
            if dd >= week_start:
                out["week_count"] += 1
            if str(tr.get("d"))[:7] == month_key:
                out["month_count"] += 1
        except Exception:
            pass
        stt = market_stats.setdefault(name, {"count": 0, "buy": 0, "sell": 0, "amount": 0.0})
        stt["count"] += 1
        stt["amount"] += amount
        if side == "BUY": stt["buy"] += 1
        if side == "SELL": stt["sell"] += 1

    out["market_count"] = len(market_stats)
    ranked = sorted(market_stats.items(), key=lambda x: (x[1]["count"], x[1]["amount"]), reverse=True)
    if ranked:
        out["top_market"], top = ranked[0]
        out["top_market_count"] = top["count"]
    out["repeat_markets"] = [(n, v) for n, v in ranked if v["count"] >= 3]
    out["heavy_markets"] = [(n, v) for n, v in ranked if v["amount"] >= max(out["total_amount"] * 0.35, 50)]

    buy_ratio = out["buy_count"] / out["count"] * 100 if out["count"] else 0
    if out["today_count"] >= 10:
        out["insights"].append(("b", t(f"오늘 거래 {out['today_count']}건 — 거래 빈도가 높습니다. 감정적 재진입 여부를 점검하세요.",
                                        f"{out['today_count']} trades today — high frequency. Check for emotional re-entry.")))
    elif out["today_count"] >= 5:
        out["insights"].append(("w", t(f"오늘 거래 {out['today_count']}건 — 잦은 진입 구간입니다.",
                                        f"{out['today_count']} trades today — frequent trading zone.")))
    else:
        out["insights"].append(("g", t(f"오늘 거래 {out['today_count']}건 — 빈도는 과하지 않습니다.",
                                        f"{out['today_count']} trades today — frequency is not excessive.")))
    if buy_ratio >= 75 and out["count"] >= 5:
        out["insights"].append(("w", t(f"BUY 비율 {buy_ratio:.0f}% — 매수 중심입니다. 익절/축소 계획이 있는지 확인하세요.",
                                        f"BUY ratio {buy_ratio:.0f}% — buy-heavy. Check whether you have exit/reduction rules.")))
    if out["repeat_markets"]:
        names = ", ".join(n[:34] + ("…" if len(n) > 34 else "") for n, _ in out["repeat_markets"][:3])
        out["insights"].append(("w", t(f"같은 시장 반복 거래 감지: {names}. 물타기/추격매수인지 복기하세요.",
                                        f"Repeated market activity: {names}. Review whether it was averaging down or chasing.")))
    if out["heavy_markets"]:
        n, v = out["heavy_markets"][0]
        out["insights"].append(("w", t(f"거래금액 집중: {n[:48]} · {money(v['amount'])}. 한 시장에 노출이 몰렸는지 확인하세요.",
                                        f"Concentrated turnover: {n[:48]} · {money(v['amount'])}. Check if exposure is clustered.")))
    return out

def activity_market_table(items):
    # Market-level activity summary table, intentionally no realized P&L pairing.
    agg = {}
    for tr in items:
        name = str(tr.get("name") or "Unknown")
        side = str(tr.get("side") or "").upper()
        a = agg.setdefault(name, {"market": name, "count": 0, "buy": 0, "sell": 0, "amount": 0.0, "last": ""})
        a["count"] += 1
        a["amount"] += _safe_float(tr.get("amount"), 0)
        if side == "BUY": a["buy"] += 1
        if side == "SELL": a["sell"] += 1
        d = str(tr.get("d") or "")[:16]
        if d > a["last"]:
            a["last"] = d
    return sorted(agg.values(), key=lambda x: (x["count"], x["amount"]), reverse=True)

def parse_pasted_activity(text):
    """Parse plain copied Polymarket Activity text into normalized trade rows.

    Supports current mobile/web clipboard shapes where the action label can appear
    before the "icon for ..." line. BUY/SELL rows become auto_trades-shaped rows.
    Settlement/loss/profit/redemption rows become recognized events and are never
    counted in estimated P&L.
    """
    rows, events, unparsed = [], [], []
    src = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not src.strip():
        return rows, {"ok": 0, "buy": 0, "sell": 0, "events": events, "unparsed": unparsed}

    label_map = {
        "매수": "BUY", "buy": "BUY", "bought": "BUY",
        "매도": "SELL", "sell": "SELL", "sold": "SELL",
        "상환": "EVENT", "정산": "EVENT", "손실": "EVENT", "수익": "EVENT",
        "redeem": "EVENT", "redeemed": "EVENT", "redemption": "EVENT",
        "settle": "EVENT", "settled": "EVENT", "loss": "EVENT", "lost": "EVENT",
        "profit": "EVENT", "won": "EVENT", "win": "EVENT",
    }
    event_label_ko = {
        "상환": t("상환", "Redeemed"), "정산": t("정산", "Settled"),
        "손실": t("손실", "Loss"), "수익": t("수익", "Profit"),
        "redeem": t("상환", "Redeemed"), "redeemed": t("상환", "Redeemed"),
        "redemption": t("상환", "Redeemed"), "settle": t("정산", "Settled"),
        "settled": t("정산", "Settled"), "loss": t("손실", "Loss"),
        "lost": t("손실", "Loss"), "profit": t("수익", "Profit"),
        "won": t("수익", "Profit"), "win": t("수익", "Profit"),
    }

    def _clean_line(s):
        return str(s or "").strip()

    def _clean_title(s):
        s = _clean_line(s)
        m = re.fullmatch(r"\[([^\]]+)\]\(https?://[^)\s]+\)", s)
        return m.group(1).strip() if m else s

    raw_lines = [_clean_line(x) for x in src.split("\n")]
    lines = [ln for ln in raw_lines if ln]

    def _label_of(line):
        key = _clean_line(line).lower()
        return label_map.get(key)

    blocks, current = [], None
    for ln in lines:
        act = _label_of(ln)
        if act:
            if current:
                blocks.append(current)
            current = {"label_raw": ln, "action": act, "lines": []}
            continue
        if current is None:
            current = {"label_raw": "", "action": None, "lines": []}
        current["lines"].append(ln)
    if current:
        blocks.append(current)

    if not any(any(x.lower().startswith("icon for ") for x in b.get("lines", [])) for b in blocks):
        link_re = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
        links = list(link_re.finditer(src))
        if links:
            blocks = []
            for i, m in enumerate(links):
                pre = src[(links[i - 1].end() if i > 0 else 0):m.start()]
                pre_lines = [x.strip() for x in pre.splitlines() if x.strip()]
                label_raw = pre_lines[-1] if pre_lines and _label_of(pre_lines[-1]) else ""
                body = src[m.end():(links[i + 1].start() if i + 1 < len(links) else len(src))]
                body_lines = [x.strip() for x in body.splitlines() if x.strip()]
                if not label_raw and body_lines and _label_of(body_lines[-1]):
                    label_raw = body_lines[-1]
                    body_lines = body_lines[:-1]
                blocks.append({"label_raw": label_raw, "action": _label_of(label_raw), "lines": [f"icon for {m.group(1).strip()}"] + body_lines})

    now_kst = datetime.now(KST)
    price_re = re.compile(r"^\s*(.+?)\s+([\d,]+(?:\.\d+)?)\s*(?:¢|cents?|c)\s*$", re.IGNORECASE)
    shares_re = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:주|shares?)\b", re.IGNORECASE)
    amount_re = re.compile(r"^([+\-]?)\$\s*([\d,]+(?:\.\d+)?)\s*$")
    rel_re = re.compile(r"(?:약\s*)?(\d+)\s*(분|시간|시|일|주|개월|달|min|minute|minutes|hour|hours|day|days|week|weeks|month|months)\s*(?:전|ago)?", re.IGNORECASE)

    def _num(s, default=None):
        try:
            return float(str(s).replace(",", ""))
        except Exception:
            return default

    def _dt_from_blob(blob):
        low = blob.lower()
        if "어제" in blob or "yesterday" in low:
            return (now_kst - timedelta(days=1)).replace(tzinfo=None).isoformat()
        rm = rel_re.search(blob)
        if rm:
            n, unit = int(rm.group(1)), rm.group(2).lower()
            if unit in ("분", "min", "minute", "minutes"):
                delta = timedelta(minutes=n)
            elif unit in ("시간", "시", "hour", "hours"):
                delta = timedelta(hours=n)
            elif unit in ("일", "day", "days"):
                delta = timedelta(days=n)
            elif unit in ("주", "week", "weeks"):
                delta = timedelta(weeks=n)
            else:
                delta = timedelta(days=30 * n)
            return (now_kst - delta).replace(tzinfo=None).isoformat()
        return now_kst.replace(tzinfo=None).isoformat()

    for idx, b in enumerate(blocks):
        blines = list(b.get("lines", []))
        label_raw = str(b.get("label_raw") or "").strip()
        action = b.get("action") or _label_of(label_raw)
        blob = "\n".join([label_raw] + blines)
        low = blob.lower()

        if action is None:
            if re.search(r"\b(sold|sell)\b|매도", low):
                action = "SELL"
            elif re.search(r"\b(bought|buy)\b|매수", low):
                action = "BUY"
            elif re.search(r"상환|정산|손실|수익|redeem|settle|loss|lost|profit|won", low):
                action = "EVENT"

        title = ""
        content_lines = []
        for ln in blines:
            if ln.lower().startswith("icon for "):
                title = _clean_title(ln[9:].strip())
            else:
                content_lines.append(ln)
        if not title and content_lines:
            title = _clean_title(content_lines[0].strip())

        def _is_meta_line(ln):
            return bool(amount_re.match(ln) or re.fullmatch(r"[-—–]", ln)
                        or rel_re.search(ln) or price_re.match(ln) or shares_re.search(ln))

        # 콤보(팔레이) 제목이 "예측 2개 콤보"처럼 짧게 끊기고 레그 목록이 다음 줄로 밀린 경우 제목에 합친다.
        if re.fullmatch(r"(?:예측\s*\d+\s*개?\s*콤보|\d+\s*-?\s*(?:leg|pick|prediction)s?\s*combo)", title, re.IGNORECASE):
            _rest = [ln for ln in content_lines if _clean_title(ln) != title]
            if _rest and not _is_meta_line(_rest[0]):
                title = f"{title} — {_clean_title(_rest[0])}"

        outcome, price = "", None
        for ln in content_lines:
            pm = price_re.match(ln)
            if pm:
                outcome = pm.group(1).strip()
                price = _num(pm.group(2))
                break

        shares = None
        sm = shares_re.search(blob)
        if sm:
            shares = _num(sm.group(1))

        shown = ""
        if re.search(r"^\s*[-—–]\s*$", blob, re.MULTILINE):
            shown = "-"
        for ln in content_lines + [label_raw]:
            am = amount_re.match(ln.strip())
            if am:
                shown = f"{am.group(1)}${am.group(2)}"
                break

        # 콤보(팔레이) 매수/매도 행은 UI에 가격·수량 없이 금액만 나온다.
        # 금액을 원가로 복원(수량=금액, 가격=100¢): 원가·패배 손익은 정확하고,
        # 승리는 '수익/상환' 이벤트 금액이 정산 연결로 반영된다. combo 플래그로
        # 가격 기반 분석(80¢+ 고가 진입)에서는 제외된다.
        combo_flag = False
        combo_like = bool(re.search(r"예측\s*\d+\s*개?\s*콤보|(?:\d+\s*-?\s*(?:leg|pick|prediction)s?\s*)?combo", title or "", re.IGNORECASE))
        if (action in ("BUY", "SELL") and combo_like
                and (price is None or shares is None or shares <= 0)
                and shown and shown != "-"):
            _amt_val = _num(shown.replace("$", "").replace("+", ""))
            if _amt_val is not None and abs(_amt_val) > 0:
                shares = round(abs(_amt_val), 4)
                price = 100.0
                if not outcome:
                    outcome = t("콤보", "Combo")
                combo_flag = True

        d_iso = _dt_from_blob(blob)
        if action == "EVENT":
            raw_key = label_raw.lower()
            result = event_label_ko.get(raw_key, t("정산", "Settled"))
            events.append({
                "name": title or t("알 수 없는 시장", "Unknown market"),
                "outcome": outcome,
                "price": round(price, 2) if price is not None else None,
                "shares": round(shares, 4) if shares is not None else None,
                "amount": shown,
                "result": result,
                "d": d_iso,
            })
            continue

        is_trade = (action in ("BUY", "SELL")) and (price is not None) and (shares is not None) and shares > 0 and bool(outcome)
        if not is_trade:
            missing = []
            if not title:
                missing.append(t("시장", "market"))
            if action not in ("BUY", "SELL"):
                missing.append(t("매수/매도", "buy/sell"))
            if not outcome or price is None:
                missing.append(t("선택지·가격", "outcome/price"))
            if shares is None or shares <= 0:
                missing.append(t("수량", "shares"))
            unparsed.append((title or t("알 수 없는 행", "Unknown row"), t("확인 필요: ", "verify: ") + ", ".join(missing)))
            continue

        key = f"{title}|{outcome}"
        rows.append({
            "tx_id": f"paste|{idx}|{title}|{outcome}|{action}|{price}|{shares}|{d_iso}",
            "d": d_iso,
            "name": title or "Polymarket trade",
            "outcome": outcome,
            "side": action,
            "price": round(price, 2),
            "shares": round(shares, 4),
            "amount": round(shares * price / 100.0, 2),
            "asset": key,
            "token_id": key,
            "src": "paste",
            "shown_pnl": shown,
            "combo": combo_flag,
        })

    rows = sort_trades_newest_first(rows) if "sort_trades_newest_first" in globals() else rows
    events = sorted(events, key=lambda x: parse_trade_datetime(x) or datetime.min.replace(tzinfo=KST), reverse=True) if "parse_trade_datetime" in globals() else events
    buy = sum(1 for r in rows if r["side"] == "BUY")
    sell = sum(1 for r in rows if r["side"] == "SELL")
    return rows, {"ok": len(rows), "buy": buy, "sell": sell, "events": events, "unparsed": unparsed}

def habit_report(trades):
    """Higher-level trading habit report from imported activity. It does not calculate realized P&L."""
    sm = summarize_activity(trades)
    insights = list(sm.get("insights", []))
    if not trades:
        return {**sm, "habit_level": "i", "habit_title": t("거래 습관 데이터 없음", "No habit data"), "habit_insights": insights}

    by_day = {}
    last_by_market = {}
    fast_reentries = 0
    chase_like = 0
    for tr in sorted(trades, key=_trade_ts):
        dkey = str(tr.get("d") or "")[:10]
        by_day[dkey] = by_day.get(dkey, 0) + 1
        name = str(tr.get("name") or "Unknown")
        side = str(tr.get("side") or "").upper()
        dt = _trade_ts(tr)
        px = _safe_float(tr.get("price"), 0)
        if side == "BUY" and px >= 80:
            chase_like += 1
        prev = last_by_market.get(name)
        if prev and side == "BUY" and prev.get("side") == "BUY":
            gap_min = (dt - prev.get("dt", dt)).total_seconds() / 60
            if 0 <= gap_min <= 180:
                fast_reentries += 1
        last_by_market[name] = {"dt": dt, "side": side}

    max_day = max(by_day.values()) if by_day else 0
    if max_day >= 15 or fast_reentries >= 3:
        level, title = "b", t("과열 거래 가능성 높음", "High chance of overtrading")
    elif max_day >= 8 or fast_reentries >= 1 or chase_like >= 2:
        level, title = "w", t("거래 습관 주의", "Trading habit caution")
    else:
        level, title = "g", t("거래 빈도 관리 가능", "Trading frequency manageable")

    insights.append((level, t(f"최대 하루 거래 {max_day}건 · 빠른 재진입 {fast_reentries}회 · 80¢ 이상 매수 {chase_like}회",
                              f"Max daily trades {max_day} · fast re-entries {fast_reentries} · buys above 80¢ {chase_like}")))
    if fast_reentries:
        insights.append(("w", t("짧은 시간 안의 같은 시장 재매수가 감지됐습니다. 손실 복구/추격매수인지 복기하세요.",
                                "Repeated buys in the same market within a short time were detected. Review whether it was chasing or loss recovery.")))
    if chase_like:
        insights.append(("w", t("80¢ 이상 고가 매수가 있습니다. 작은 추가수익을 위해 큰 금액을 위험에 둔 거래인지 확인하세요.",
                                "Some buys were above 80¢. Check whether you risked too much for limited upside.")))
    return {**sm, "habit_level": level, "habit_title": title, "habit_insights": insights}

# ---------------------------------------------------------------------------
# 승/패 자동 확정 — 폴리마켓 마켓 결과(gamma-api)로 미확정 보유 거래를 자동 판정.
# 수동 확정(trade_resolutions 기존 값)은 절대 덮어쓰지 않으며, 전부 fail-soft.
# ---------------------------------------------------------------------------

def fetch_markets_by_token_ids(token_ids, chunk=15):
    """gamma-api에서 CLOB 토큰 id들로 마켓 종료/결과를 조회해 {token_id: 판정}으로 돌려준다.
    판정 verdict: 'won'/'lost'(마켓 종료·가격 확정) 또는 ''(미종료/판정불가).
    네트워크/파싱 오류가 난 배치는 조용히 건너뛴다(응답에 없는 토큰 = 판정불가)."""
    out = {}
    ids = [str(x).strip() for x in (token_ids or []) if str(x).strip()]
    step = max(int(chunk or 1), 1)
    for i in range(0, len(ids), step):
        batch = ids[i:i + step]
        try:
            qs = urllib.parse.urlencode({"clob_token_ids": ",".join(batch), "limit": len(batch)})
            api = f"https://gamma-api.polymarket.com/markets?{qs}"
            req = urllib.request.Request(api, headers={"User-Agent": "Memento/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except Exception:
            continue
        if isinstance(payload, list):
            markets = payload
        elif isinstance(payload, dict):
            markets = payload.get("markets") if isinstance(payload.get("markets"), list) else []
        else:
            markets = []
        for m in markets:
            if not isinstance(m, dict):
                continue
            toks = [str(x) for x in parse_list(m.get("clobTokenIds"))]
            prices = parse_list(m.get("outcomePrices"))
            closed = bool(m.get("closed")) or str(m.get("umaResolutionStatus", "") or "").lower() == "resolved"
            for pos, tok in enumerate(toks):
                verdict = ""
                if closed and pos < len(prices):
                    p = safe_trade_float(prices[pos], -1.0)
                    if p >= 0.99:
                        verdict = "won"
                    elif 0.0 <= p <= 0.01:
                        verdict = "lost"
                out[tok] = {"closed": closed, "verdict": verdict,
                            "question": str(m.get("question", "") or "")}
    return out

def auto_resolve_trades():
    """잔여 보유가 있는 미확정 거래그룹을 폴리마켓 결과로 자동 승/패 확정한다.
    이미 확정된 key(수동 포함)는 건드리지 않고, 확정되면 장부 갱신 + 저장까지 수행. Fail-soft."""
    try:
        res = dict(st.session_state.get("trade_resolutions") or {})
        candidates = {}
        for trades in (st.session_state.get("auto_trades") or [], st.session_state.get("paste_trades") or []):
            if not trades:
                continue
            for r in group_auto_trades_for_pnl(trades):
                key = str(r.get("key") or "")
                tok = str(r.get("token_id") or "").strip()
                if not key or key in res:
                    continue
                if safe_trade_float(r.get("remaining_shares"), 0.0) <= 1e-6:
                    continue
                if not (tok.isdigit() and len(tok) >= 10):
                    continue  # 실제 CLOB 토큰 id가 있어야 결과 조회 가능 (붙여넣기 거래 등은 수동 확정)
                candidates[key] = tok
        if not candidates:
            return {"ok": True, "checked": 0, "won": 0, "lost": 0, "open": 0, "unknown": 0, "error": ""}
        verdicts = fetch_markets_by_token_ids(sorted(set(candidates.values())))
        won = lost = still_open = unknown = 0
        for key, tok in candidates.items():
            v = verdicts.get(tok)
            if not v:
                unknown += 1
            elif v["verdict"] == "won":
                res[key] = "won"
                won += 1
            elif v["verdict"] == "lost":
                res[key] = "lost"
                lost += 1
            else:
                still_open += 1
        if won or lost:
            st.session_state.trade_resolutions = res
            update_trade_ledger()
            save_local_state()
        return {"ok": True, "checked": len(candidates), "won": won, "lost": lost,
                "open": still_open, "unknown": unknown, "error": ""}
    except Exception as e:
        return {"ok": False, "checked": 0, "won": 0, "lost": 0, "open": 0, "unknown": 0,
                "error": f"{type(e).__name__}: {e}"}

# ---------------------------------------------------------------------------
# Google Sheets backup — mirror the durable trade ledger to a Google Sheet.
# One-way (app -> sheet), service-account auth via Streamlit Secrets.
# gspread/google-auth are imported lazily and every entry point is fail-soft, so
# a missing library / secret / sheet / network can NEVER break the app boot.
# ---------------------------------------------------------------------------
GSHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
# '키'는 시트→앱 가져오기의 매칭 기준. 감정(1-5)·추격(Y)은 시트에서 고쳐서 앱으로 되가져올 수 있는 편집 가능 컬럼.
GSHEET_LEDGER_HEADER = ["키", "날짜", "시장", "선택", "상태", "결과", "손익USD", "카테고리", "감정(1-5)", "추격", "출처", "갱신시각"]
GSHEET_LEDGER_FIELDS = ["key", "date", "market", "outcome", "status", "resolved", "pnl", "category", "emotion", "chase", "source", "updated_at"]

def _gsheet_service_account_info():
    """Service-account dict from Streamlit Secrets (key: gcp_service_account), or None."""
    try:
        sa = st.secrets.get("gcp_service_account", None)
    except Exception:
        return None
    if not sa:
        return None
    try:
        return dict(sa)
    except Exception:
        return None

def gsheet_target_url():
    """Target spreadsheet URL/key: prefer the in-app setting, fall back to secrets."""
    u = str(st.session_state.get("gsheet_url", "") or "").strip()
    if u:
        return u
    try:
        return str(st.secrets.get("gsheet_url", "") or "").strip()
    except Exception:
        return ""

def gsheet_status():
    """Readiness snapshot for the Settings UI. Never raises."""
    lib = True
    try:
        import gspread  # noqa: F401
        from google.oauth2.service_account import Credentials  # noqa: F401
    except Exception:
        lib = False
    sa = _gsheet_service_account_info()
    email = ""
    if sa:
        try:
            email = str(sa.get("client_email", "") or "")
        except Exception:
            email = ""
    url = gsheet_target_url()
    return {"lib": lib, "creds": bool(sa), "email": email, "url": url,
            "has_url": bool(url), "ready": bool(lib and sa and url)}

def _gsheet_open_worksheet():
    """Authorize and open (or create) the 'ledger' worksheet of the target sheet. Raises on failure."""
    import gspread
    from google.oauth2.service_account import Credentials
    sa = _gsheet_service_account_info()
    creds = Credentials.from_service_account_info(sa, scopes=GSHEET_SCOPES)
    gc = gspread.authorize(creds)
    url = gsheet_target_url()
    sh = gc.open_by_url(url) if url.startswith("http") else gc.open_by_key(url)
    try:
        ws = sh.worksheet("ledger")
    except Exception:
        ws = sh.add_worksheet(title="ledger", rows=200, cols=len(GSHEET_LEDGER_HEADER))
    return ws

def backup_ledger_to_gsheet(force=False):
    """Mirror st.session_state.trade_ledger into the Google Sheet (full overwrite = idempotent,
    dedup-free). Returns {"ok","error","written"}. Any failure -> ok False with a reason string."""
    s = gsheet_status()
    if not s["lib"]:
        return {"ok": False, "error": "no_lib", "written": 0}
    if not s["creds"]:
        return {"ok": False, "error": "no_creds", "written": 0}
    if not s["has_url"]:
        return {"ok": False, "error": "no_url", "written": 0}
    body, n = _ledger_rows_for_export()
    if n == 0 and not force:
        return {"ok": False, "error": "empty_ledger", "written": 0}
    try:
        ws = _gsheet_open_worksheet()
        ws.clear()
        ws.append_rows(body, value_input_option="RAW")
        st.session_state["_gsheet_last_backup"] = datetime.now(KST).isoformat(timespec="minutes")
        st.session_state["_gsheet_last_count"] = n
        return {"ok": True, "error": "", "written": n}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "written": 0}

def _ledger_rows_for_export():
    """장부를 표(헤더+행, 최신순)로 만든다. 두 백업 방식·CSV 다운로드·시트 가져오기가 같은 포맷을 쓴다.
    '키'는 가져오기 매칭 기준, 감정(1-5)·추격(Y)은 trade_emotions에서 key로 조인해 채운다."""
    ledger = st.session_state.get("trade_ledger") or {}
    if not isinstance(ledger, dict):
        ledger = {}
    emotions = st.session_state.get("trade_emotions") or {}
    if not isinstance(emotions, dict):
        emotions = {}
    items = sorted(((str(k), v) for k, v in ledger.items() if isinstance(v, dict)),
                   key=lambda kv: str(kv[1].get("date", "")), reverse=True)
    body = [list(GSHEET_LEDGER_HEADER)]
    for k, rec in items:
        tag = emotions.get(k)
        tag = tag if isinstance(tag, dict) else {}
        emo = int(_safe_float(tag.get("emotion"), 0))
        merged = dict(rec)
        merged["key"] = k
        merged["emotion"] = emo if 1 <= emo <= 5 else ""
        merged["chase"] = "Y" if tag.get("chase") else ""
        body.append([str(merged.get(f, "")) for f in GSHEET_LEDGER_FIELDS])
    return body, len(items)

def ledger_backup_signature():
    """백업 내용의 지문(md5)과 행 수. 장부 내용이 실제로 바뀌었을 때만 자동백업을 쏘기 위한 값."""
    try:
        body, n = _ledger_rows_for_export()
        if not n:
            return "", 0
        return hashlib.md5(json.dumps(body, ensure_ascii=False).encode("utf-8")).hexdigest(), n
    except Exception:
        return "", 0

def gsheet_webapp_endpoint():
    """Apps Script 웹앱 URL: 앱 내 설정값 우선, 없으면 Streamlit Secrets(gsheet_webapp_url).
    Secrets에 넣어두면 재배포로 로컬 상태가 초기화돼도 부팅 복원이 가능하다."""
    u = str(st.session_state.get("gsheet_webapp_url", "") or "").strip()
    if u:
        return u
    try:
        return str(st.secrets.get("gsheet_webapp_url", "") or "").strip()
    except Exception:
        return ""

def gsheet_webapp_secret():
    """웹앱 공유 토큰: 앱 내 설정값 우선, 없으면 Streamlit Secrets(gsheet_webapp_token)."""
    tok = str(st.session_state.get("gsheet_webapp_token", "") or "").strip()
    if tok:
        return tok
    try:
        return str(st.secrets.get("gsheet_webapp_token", "") or "").strip()
    except Exception:
        return ""

def backup_ledger_via_webapp(force=False):
    """Push the ledger to the user's own Google Sheet through their Apps Script web app URL
    (no service account / Google Cloud). POSTs {"rows":[...], "token":...}. Fail-soft."""
    url = gsheet_webapp_endpoint()
    if not url:
        return {"ok": False, "error": "no_url", "written": 0}
    body, n = _ledger_rows_for_export()
    if n == 0 and not force:
        return {"ok": False, "error": "empty_ledger", "written": 0}
    try:
        payload = {"rows": body}
        token = gsheet_webapp_secret()
        if token:
            payload["token"] = token
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=25) as resp:
            txt = resp.read().decode("utf-8", "ignore")
        try:
            j = json.loads(txt)
            ok_resp = bool(j.get("ok", True))
            written = int(j.get("written", n))
        except Exception:
            # 구글이 JSON 대신 로그인/권한승인 HTML 등을 돌려주면 여기로 온다 — 스크립트가
            # 실제로 실행됐다고 볼 근거가 없으므로 절대 성공 처리하지 않는다(배포 액세스 설정 확인 필요).
            ok_resp, written = False, 0
            txt = f"non_json_response (check Apps Script deployment access = Anyone): {txt[:120]}"
        if not ok_resp:
            return {"ok": False, "error": f"webapp: {txt[:180]}", "written": 0}
        st.session_state["_gsheet_last_backup"] = datetime.now(KST).isoformat(timespec="minutes")
        st.session_state["_gsheet_last_count"] = written
        return {"ok": True, "error": "", "written": written}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "written": 0}

def restore_ledger_from_webapp():
    """양방향의 '시트→앱' 방향: Apps Script doGet으로 ledger 탭을 되읽어 편집 가능한 컬럼만 반영한다.
    반영 대상 — 카테고리 → trade_ledger(수동 표시로 보존됨), 감정(1-5)·추격(Y) → trade_emotions.
    행 매칭은 '키' 컬럼으로만 하고, 시트에서 지운 감정 기록은 앱에서 지우지 않는다(merge-only). Fail-soft."""
    url = gsheet_webapp_endpoint()
    if not url:
        return {"ok": False, "error": "no_url", "rows": 0, "categories": 0, "tags": 0}
    try:
        params = {"action": "read"}
        token = gsheet_webapp_secret()
        if token:
            params["token"] = token
        sep = "&" if "?" in url else "?"
        req = urllib.request.Request(url + sep + urllib.parse.urlencode(params),
                                     headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            j = json.loads(resp.read().decode("utf-8", "ignore"))
        if not (isinstance(j, dict) and j.get("ok")):
            err = str((j or {}).get("error", "bad response"))[:140] if isinstance(j, dict) else "bad response"
            return {"ok": False, "error": f"webapp: {err}", "rows": 0, "categories": 0, "tags": 0}
        rows = j.get("rows") or []
        if not (isinstance(rows, list) and len(rows) >= 2 and isinstance(rows[0], list)):
            return {"ok": False, "error": "empty_sheet", "rows": 0, "categories": 0, "tags": 0}
        header = [str(h).strip() for h in rows[0]]

        def col(name):
            try:
                return header.index(name)
            except ValueError:
                return -1

        i_key, i_cat, i_emo, i_chase = col("키"), col("카테고리"), col("감정(1-5)"), col("추격")
        if i_key < 0:
            return {"ok": False, "error": "no_key_column", "rows": len(rows) - 1, "categories": 0, "tags": 0}
        ledger = dict(st.session_state.get("trade_ledger") or {})
        emotions = dict(st.session_state.get("trade_emotions") or {})
        now_iso = datetime.now(KST).isoformat(timespec="minutes")
        cat_n = tag_n = 0
        for raw in rows[1:]:
            if not isinstance(raw, list):
                continue

            def cell(i):
                return str(raw[i]).strip() if 0 <= i < len(raw) else ""

            k = cell(i_key)
            if not k or k not in ledger or not isinstance(ledger.get(k), dict):
                continue
            cat = cell(i_cat)
            if cat and cat != str(ledger[k].get("category", "")):
                rec = dict(ledger[k])
                rec["category"] = cat
                rec["category_src"] = "manual"  # update_trade_ledger 재생성 때 자동 분류로 덮지 않음
                rec["updated_at"] = now_iso
                ledger[k] = rec
                cat_n += 1
            emo_raw = cell(i_emo)
            emo = int(_safe_float(emo_raw, 0)) if emo_raw else 0
            emo = emo if 1 <= emo <= 5 else 0
            chase = cell(i_chase).upper() in ("Y", "YES", "1", "TRUE", "O", "예") if i_chase >= 0 else False
            old = emotions.get(k) if isinstance(emotions.get(k), dict) else {}
            old_emo = int(_safe_float((old or {}).get("emotion"), 0))
            old_chase = bool((old or {}).get("chase"))
            if (emo or chase) and (emo != old_emo or chase != old_chase):
                emotions[k] = {"emotion": emo, "chase": chase, "updated_at": now_iso}
                tag_n += 1
        if cat_n or tag_n:
            st.session_state.trade_ledger = ledger
            st.session_state.trade_emotions = emotions
            save_local_state()
        return {"ok": True, "error": "", "rows": len(rows) - 1, "categories": cat_n, "tags": tag_n}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "rows": 0, "categories": 0, "tags": 0}

def gsheet_active_method():
    """Which backup method is configured. Apps Script (webapp) is preferred when set."""
    if gsheet_webapp_endpoint():
        return "webapp"
    if gsheet_status()["ready"]:
        return "service_account"
    return ""

# ---------------------------------------------------------------------------
# 전체 상태 백업/복원 — Streamlit Cloud는 재배포·재부팅 때 로컬 파일(memento_state.json)이
# 사라진다. 장부 외의 모든 기록(승/패 확정·감정 태그·복기 노트·현금 입력 등)을 시트의
# 'state' 탭에 스냅샷으로 저장하고, 부팅 시 로컬이 비어 있으면 자동 복원한다. 전부 fail-soft.
# ---------------------------------------------------------------------------
STATE_SNAPSHOT_EXCLUDE = ("wallet_raw", "pnl_raw", "activity_raw")  # 재조회 가능한 raw 덤프 — 부피 절감

def state_snapshot_json():
    """복원용 전체 상태 스냅샷(JSON 문자열). local_state_payload에서 raw 덤프만 제외."""
    try:
        data = local_state_payload()
        for k in STATE_SNAPSHOT_EXCLUDE:
            data.pop(k, None)
        data["_schema"] = 1
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return ""

def state_backup_signature():
    """상태 스냅샷 지문(md5). 매 실행 바뀌는 _saved_at은 빼고 계산해 '실제 변경'만 감지."""
    try:
        data = local_state_payload()
        for k in STATE_SNAPSHOT_EXCLUDE:
            data.pop(k, None)
        data.pop("_saved_at", None)
        return hashlib.md5(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    except Exception:
        return ""

def backup_state_via_webapp():
    """전체 상태 스냅샷을 웹앱 doPost({"state": ...})로 시트 'state' 탭에 저장. Fail-soft."""
    url = gsheet_webapp_endpoint()
    if not url:
        return {"ok": False, "error": "no_url"}
    snap = state_snapshot_json()
    if not snap:
        return {"ok": False, "error": "empty_state"}
    try:
        payload = {"state": snap, "saved_at": datetime.now(KST).isoformat(timespec="seconds")}
        token = gsheet_webapp_secret()
        if token:
            payload["token"] = token
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=25) as resp:
            txt = resp.read().decode("utf-8", "ignore")
        try:
            ok_resp = bool(json.loads(txt).get("ok", True))
        except Exception:
            # 비-JSON 응답(로그인/권한승인 HTML 등)은 스크립트 미실행으로 간주 — 성공 처리 금지.
            ok_resp = False
            txt = f"non_json_response (check Apps Script deployment access = Anyone): {txt[:120]}"
        if not ok_resp:
            return {"ok": False, "error": f"webapp: {txt[:180]}"}
        st.session_state["_gsheet_state_last_backup"] = payload["saved_at"]
        st.session_state["state_backup_last_at"] = payload["saved_at"]  # 영구 저장 → 유실 위험 배너 판단용
        return {"ok": True, "error": ""}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def fetch_state_from_webapp():
    """시트 'state' 탭의 스냅샷을 읽어 (dict, saved_at, error)로 돌려준다.
    스냅샷이 아직 없으면 (None, "", "") — 오류가 아니다."""
    url = gsheet_webapp_endpoint()
    if not url:
        return None, "", "no_url"
    try:
        params = {"action": "read_state"}
        token = gsheet_webapp_secret()
        if token:
            params["token"] = token
        sep = "&" if "?" in url else "?"
        req = urllib.request.Request(url + sep + urllib.parse.urlencode(params),
                                     headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            j = json.loads(resp.read().decode("utf-8", "ignore"))
        if not (isinstance(j, dict) and j.get("ok")):
            return None, "", str((j or {}).get("error", "bad response"))[:140] if isinstance(j, dict) else "bad response"
        raw = str(j.get("state", "") or "")
        if not raw.strip():
            return None, "", ""
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None, "", "bad_snapshot"
        return data, str(j.get("saved_at", "") or data.get("_saved_at", "") or ""), ""
    except Exception as e:
        return None, "", f"{type(e).__name__}: {e}"

def restore_state_from_webapp():
    """시트 스냅샷을 세션에 적용하고 로컬 파일을 재생성한다. PERSIST_KEYS에 있는 키만 적용.
    호출한 쪽에서 '언제 복원할지'(부팅 시 로컬 비었을 때 / 수동 확인 후)를 결정한다. Fail-soft."""
    data, saved_at, err = fetch_state_from_webapp()
    if err:
        return {"ok": False, "restored": 0, "saved_at": "", "error": err}
    if data is None:
        return {"ok": False, "restored": 0, "saved_at": "", "error": "no_snapshot"}
    applied = 0
    for k in PERSIST_KEYS:
        if k in data:
            st.session_state[k] = data[k]
            applied += 1
    save_local_state()  # 로컬 파일 재생성 (내부에서 status를 'saved'로 만들므로 그 뒤에 표시)
    st.session_state["_local_state_status"] = "restored_from_sheet"
    st.session_state["_local_state_saved_at"] = saved_at
    return {"ok": True, "restored": applied, "saved_at": saved_at, "error": ""}

def maybe_backup_state(min_interval_sec=120):
    """자동 상태 백업: 내용이 실제로 바뀌었고 최소 간격이 지났을 때만 웹앱으로 백업.
    같은 내용으로 실패했으면 내용이 바뀔 때까지 재시도하지 않는다. 결과 dict. Fail-soft."""
    try:
        if not gsheet_webapp_endpoint():
            return {"ok": False, "skipped": "no_url"}
        sig = state_backup_signature()
        if not sig:
            return {"ok": False, "skipped": "empty"}
        if sig == str(st.session_state.get("_state_backup_sig", "")):
            return {"ok": True, "skipped": "unchanged"}
        if sig == str(st.session_state.get("_state_backup_fail_sig", "")):
            return {"ok": False, "skipped": "failed_before"}
        now = time.time()
        if now - float(st.session_state.get("_state_backup_last_ts", 0) or 0) < max(min_interval_sec, 0):
            return {"ok": True, "skipped": "throttled"}
        r = backup_state_via_webapp()
        st.session_state["_state_backup_last_ts"] = now
        if r.get("ok"):
            st.session_state["_state_backup_sig"] = sig
            st.session_state.pop("_state_backup_fail_sig", None)
        else:
            st.session_state["_state_backup_fail_sig"] = sig
        return r
    except Exception as e:
        return {"ok": False, "error": str(e)}

def backup_ledger(force=False):
    """Single entry point: dispatch to whichever backup method is configured."""
    m = gsheet_active_method()
    if m == "webapp":
        r = backup_ledger_via_webapp(force); r["method"] = "webapp"; return r
    if m == "service_account":
        r = backup_ledger_to_gsheet(force); r["method"] = "service_account"; return r
    return {"ok": False, "error": "not_configured", "written": 0, "method": ""}

__all__ = [
    '_ledger_rows_for_export',
    'auto_resolve_trades',
    'fetch_markets_by_token_ids',
    'ledger_backup_signature',
    'restore_ledger_from_webapp',
    'gsheet_webapp_endpoint',
    'gsheet_webapp_secret',
    'STATE_SNAPSHOT_EXCLUDE',
    'state_snapshot_json',
    'state_backup_signature',
    'backup_state_via_webapp',
    'fetch_state_from_webapp',
    'restore_state_from_webapp',
    'maybe_backup_state',
    'backup_ledger',
    'backup_ledger_via_webapp',
    'gsheet_active_method',
    'GSHEET_LEDGER_FIELDS',
    'GSHEET_LEDGER_HEADER',
    'GSHEET_SCOPES',
    '_gsheet_open_worksheet',
    '_gsheet_service_account_info',
    'backup_ledger_to_gsheet',
    'gsheet_status',
    'gsheet_target_url',
    '_activity_action',
    '_activity_asset',
    '_activity_dt',
    '_activity_time_value',
    '_ai_get',
    '_as_cents',
    '_escape',
    '_event_end_date',
    '_event_liquidity',
    '_event_resolution',
    '_event_volume',
    '_find_first_number',
    '_first_present',
    '_history_points',
    'activity_market_table',
    'book_summary',
    'build_order_candidate',
    'build_prompt',
    'calc_profile_pnl',
    'call_claude',
    'classify_market_type',
    'evaluate_live_price',
    'extract_markets',
    'extract_slug',
    'fetch_clob_book',
    'fetch_clob_price',
    'fetch_gamma',
    'fetch_live_token_price',
    'fetch_price_history',
    'fetch_wallet_activity',
    'fetch_wallet_activity_all',
    'ACTIVITY_PAGE_SIZE',
    '_trade_content_sig',
    'fetch_wallet_positions',
    'fetch_wallet_value',
    'get_api_key',
    'habit_report',
    'history_summary',
    'is_prop_market',
    'is_relevant_market',
    'merge_activity_into_log',
    'normalize_activity',
    'normalize_activity_events',
    'parse_list',
    'parse_pasted_activity',
    'row_get',
    'safe_json_parse',
    'summarize_activity',
]
