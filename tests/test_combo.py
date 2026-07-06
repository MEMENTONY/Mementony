"""콤보(팔레이) 거래 지원 검증 — 붙여넣기 파싱, 원가 복원, 손실 이벤트 정산, 분석 제외 규칙."""
import sys, os, json
from pathlib import Path
TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(TESTS))
os.chdir(REPO)
from seed_state import seed
seed()

import streamlit as st
st.session_state.lang = "ko"
import data as d
import engine as eng

# 사용자가 실제로 겪은 케이스 그대로 (가격·수량 없이 금액만 있는 콤보 매수 3건 + 손실 이벤트 2건)
PASTE = """손실
예측 2개 콤보 Over 1.5 goals, 무승부

—
11시간 전

손실

예측 2개 콤보 Over 1.5 goals, France

—
11시간 전

매수
예측 2개 콤보 Over 1.5 goals, 무승부

-$67.00
13시간 전

매수
예측 2개 콤보 Over 1.5 goals, 무승부

-$67.00
13시간 전

매수

예측 2개 콤보 Over 1.5 goals, France

-$613.00
13시간 전
"""

# ---------- 1) 붙여넣기 파싱: 3건 전부 거래로 인식 (unparsed 0) ----------
rows, meta = d.parse_pasted_activity(PASTE)
assert meta["ok"] == 3 and meta["buy"] == 3, meta
assert not meta["unparsed"], meta["unparsed"]
assert len(meta["events"]) == 2, meta["events"]
for r in rows:
    assert r["combo"] is True and r["price"] == 100.0, r
    assert r["outcome"] == "콤보", r
amounts = sorted(r["amount"] for r in rows)
assert amounts == [67.0, 67.0, 613.0], amounts
ev_names = {e["name"] for e in meta["events"]}
assert "예측 2개 콤보 Over 1.5 goals, 무승부" in ev_names and "예측 2개 콤보 Over 1.5 goals, France" in ev_names, ev_names
print("1) 붙여넣기 파싱 OK")

# ---------- 2) 그룹핑 + 손실 이벤트 정산: 총 실현손익 -$747 ----------
groups = eng.group_auto_trades_for_pnl(rows)
assert len(groups) == 2, [g["market"] for g in groups]  # 무승부($67×2 합산) / France($613)
by_market = {g["market"]: g for g in groups}
draw = by_market["예측 2개 콤보 Over 1.5 goals, 무승부"]
france = by_market["예측 2개 콤보 Over 1.5 goals, France"]
assert draw["combo"] and draw["buy_cost"] == 134.0 and draw["fills"] == 2, draw
assert france["buy_cost"] == 613.0, france

linked = eng.link_settlement_events_to_trade_groups(groups, meta["events"])
total = 0.0
for g in linked:
    assert g.get("_adjusted"), g["market"]           # 손실 이벤트가 자동 연결됨
    assert g["adjusted_remaining_shares"] == 0, g    # 포지션 종료
    total += g["adjusted_realized_pnl"]
assert abs(total - (-747.0)) < 0.01, total
print("2) 손실 정산 -$747 OK")

# ---------- 3) 장부 반영 + combo 플래그 전파 ----------
st.session_state.profile = {"emotional_limit": 50.0}
st.session_state.auto_trades = []
st.session_state.activity_events = []
st.session_state.paste_trades = rows
st.session_state.paste_events = meta["events"]
st.session_state.trade_resolutions = {}
st.session_state.trade_emotions = {}
st.session_state.trade_ledger = {}
eng.update_trade_ledger()
led = st.session_state.trade_ledger
assert len(led) == 2, led.keys()
led_total = sum(v["pnl"] for v in led.values())
assert abs(led_total - (-747.0)) < 0.01, led_total
assert all(v.get("combo") is True for v in led.values()), led
print("3) 장부 반영 OK")

# ---------- 4) 분석: 고가 진입(합성 100¢) 제외, 과대베팅(원가)은 포함 ----------
ins = eng.behavior_insights()
assert ins["high_price"]["n"] == 0, ins["high_price"]          # 합성 가격은 고가 위반 아님
assert ins["oversized"]["n"] == 2, ins["oversized"]            # $134·$613 모두 감정한도($50) 초과
sim = eng.rule_simulation()
assert sim["rules"]["skip_high_price"]["affected"] == 0, sim["rules"]["skip_high_price"]
assert sim["rules"]["cap_size"]["affected"] == 2, sim["rules"]["cap_size"]
print("4) 분석 제외/포함 규칙 OK")

# ---------- 5) API 경로(normalize_activity): 수량·가격 없는 체결도 원가로 복원 ----------
api_raw = [{"type": "TRADE", "side": "BUY", "usdcSize": 67.0, "timestamp": 1751500000,
            "title": "2-leg combo: Over 1.5 goals + Draw", "outcome": "", "asset": "99999999999999999999"}]
api_rows = d.normalize_activity(api_raw)
assert len(api_rows) == 1 and api_rows[0]["combo"] is True, api_rows
assert api_rows[0]["shares"] == 67.0 and api_rows[0]["price"] == 100.0 and api_rows[0]["amount"] == 67.0, api_rows[0]
# 일반 거래는 combo 플래그가 붙지 않는다
normal = d.normalize_activity([{"type": "TRADE", "side": "BUY", "price": 0.6, "size": 50.0,
                                "usdcSize": 30.0, "timestamp": 1751500000, "title": "N", "asset": "88888888888888888888"}])
assert normal[0]["combo"] is False, normal[0]
print("5) API 경로 복원 OK")

# ---------- 6) 제목이 두 줄로 끊긴 콤보(짧은 제목 + 레그 줄) 병합 ----------
PASTE2 = """매수
예측 2개 콤보
Over 1.5 goals, 무승부
-$10.00
1시간 전
"""
rows2, meta2 = d.parse_pasted_activity(PASTE2)
assert meta2["ok"] == 1, meta2
assert rows2[0]["name"] == "예측 2개 콤보 — Over 1.5 goals, 무승부", rows2[0]["name"]
print("6) 두 줄 제목 병합 OK")

# ---------- 7) 콤보 보유 포지션(매도·정산 없음) 수동 '패' 확정 = -원가 ----------
held = [{"tx_id": "h1", "d": "2026-07-05T05:59:00+09:00",
         "name": "Paraguay vs. France: O/U 1.5 AND Will France win", "outcome": "Yes",
         "side": "BUY", "price": 77.9, "shares": 787.09, "amount": 613.0,
         "asset": "COMBO_nonnumeric", "token_id": "COMBO_nonnumeric", "combo": True}]
hg = eng.group_auto_trades_for_pnl(held)[0]
assert hg["status"] == "보유 중" and hg["remaining_shares"] == 787.09, hg
st.session_state.trade_resolutions = {}
assert eng.resolve_trade_row(hg)["realized_final"] == 0.0            # 미확정 → $0
st.session_state.trade_resolutions = {hg["key"]: "lost"}
resh = eng.resolve_trade_row(hg)
assert resh["realized_final"] == -613.0 and resh["remaining_final"] == 0.0, resh
# 콤보 held는 auto_resolve 대상이 아님(비숫자 토큰)
st.session_state.auto_trades = held
st.session_state.paste_trades = []
st.session_state.trade_resolutions = {}
ar = d.auto_resolve_trades()
assert ar["ok"] and ar["checked"] == 0, ar                          # 조회 대상 0 (콤보 토큰 제외)
print("7) 콤보 보유분 수동 패 확정 OK")

# ---------- 8) AppTest: 미확정 보유 포지션에 '승/패 확정 필요' 힌트 노출 ----------
seed()
import json as _json
_state = _json.load(open("memento_state.json", encoding="utf-8"))
_state["auto_trades"] = held
_state["paste_trades"] = []
_state["activity_events"] = []
_state["trade_resolutions"] = {}
_state["wallet_addr"] = "0x1234567890abcdef1234567890abcdef12345678"
_state["auto_sync_on_boot"] = False
with open("memento_state.json", "w", encoding="utf-8") as f:
    _json.dump(_state, f, ensure_ascii=False)
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("streamlit_app.py", default_timeout=180).run()
assert not at.exception, f"EXCEPTION: {at.exception}"
all_md = "\n".join(m.value for m in at.markdown)
assert "콤보는 자동 확정 불가" in all_md, "combo resolve hint missing"
print("8) 미확정 보유 힌트 노출 OK")
print("ALL COMBO TESTS PASSED")
