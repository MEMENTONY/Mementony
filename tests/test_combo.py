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

# ---------- 7) 지갑(API) 경로: 손실 이벤트도 표시에 연결돼야 종료로 인식된다 ----------
# streamlit_app.py 지갑 거래내역 카드가 group_auto_trades_for_pnl 결과에 activity_events를
# 반드시 연결해야 한다는 회귀 가드. events를 넘기지 않으면 콤보 손실이 '보유 중'으로 남는다.
T = 1751500000
api_buys = [
    {"type": "TRADE", "side": "BUY", "usdcSize": 67.0, "timestamp": T,
     "title": "2-leg combo: Over 1.5 goals, Draw", "outcome": "Draw", "asset": "7001", "transactionHash": "0xd1"},
    {"type": "TRADE", "side": "BUY", "usdcSize": 67.0, "timestamp": T + 1,
     "title": "2-leg combo: Over 1.5 goals, Draw", "outcome": "Draw", "asset": "7001", "transactionHash": "0xd2"},
    {"type": "TRADE", "side": "BUY", "usdcSize": 613.0, "timestamp": T + 2,
     "title": "2-leg combo: Over 1.5 goals, France", "outcome": "France", "asset": "7002", "transactionHash": "0xf1"},
]
api_loss = [
    {"type": "LOSS", "title": "2-leg combo: Over 1.5 goals, Draw", "outcome": "Draw", "timestamp": T + 7200, "transactionHash": "0xd3"},
    {"type": "LOSS", "title": "2-leg combo: Over 1.5 goals, France", "outcome": "France", "timestamp": T + 7201, "transactionHash": "0xf2"},
]
wallet_trades = d.normalize_activity(api_buys)
wallet_events = d.normalize_activity_events(api_loss)
assert len(wallet_events) == 2, wallet_events
assert all(e["shares"] is None and e["amount"] == "" for e in wallet_events), wallet_events  # 패배는 상환금이 없다

# 옛 버그 재현: events 미전달 → 콤보 손실이 종료로 인식되지 않고 '보유 중'
buggy = eng.group_auto_trades_for_pnl(wallet_trades)
assert all(not g.get("_adjusted") and eng._display_remaining_shares(g) > 0 for g in buggy), buggy

# 수정된 표시 경로: events 연결 → 손실 정산·종료로 인식
fixed = eng.link_settlement_events_to_trade_groups(eng.group_auto_trades_for_pnl(wallet_trades), wallet_events)
assert all(g.get("_adjusted") and g["adjusted_remaining_shares"] == 0 for g in fixed), fixed
assert abs(sum(g["adjusted_realized_pnl"] for g in fixed) - (-747.0)) < 0.01, [g["adjusted_realized_pnl"] for g in fixed]
print("7) 지갑 경로 손실 이벤트 연결 OK")

# ---------- 8) 지갑 경로: 자동확정 안 되는 팔레이는 수동 '패' 확정으로 장부에 손실 반영 ----------
# API가 실가격·수량을 준 팔레이는 combo 플래그도 안 붙고 gamma-api 자동확정도 안 돼 '보유 중'으로
# 남는다(사용자 실제 케이스). 카드에서 수동 '패' 확정하면 −원가가 장부·분석에 잡혀야 한다.
api_open = [
    {"type": "TRADE", "side": "BUY", "price": 0.111, "size": 603.6, "usdcSize": 67.0, "timestamp": T,
     "title": "Paraguay vs. France: O/U 1.5 AND draw?", "outcome": "Yes", "asset": "11111111111111", "transactionHash": "0xo1"},
    {"type": "TRADE", "side": "BUY", "price": 0.111, "size": 603.6, "usdcSize": 67.0, "timestamp": T + 1,
     "title": "Paraguay vs. France: O/U 1.5 AND draw?", "outcome": "Yes", "asset": "11111111111111", "transactionHash": "0xo2"},
    {"type": "TRADE", "side": "BUY", "price": 0.779, "size": 787.09, "usdcSize": 613.0, "timestamp": T + 2,
     "title": "Paraguay vs. France: O/U 1.5 AND France win?", "outcome": "Yes", "asset": "22222222222222", "transactionHash": "0xo3"},
]
open_trades = d.normalize_activity(api_open)
open_groups = eng.group_auto_trades_for_pnl(open_trades)
assert all(not g["combo"] for g in open_groups), open_groups           # 실가격이 있어 콤보 아님
assert all("보유" in g["status"] for g in open_groups), [g["status"] for g in open_groups]  # 미청산
# 카드에서 '패' 확정 (trade_resolutions[key]='lost')
st.session_state.auto_trades = open_trades
st.session_state.activity_events = []
st.session_state.paste_trades = []
st.session_state.paste_events = []
st.session_state.trade_emotions = {}
st.session_state.trade_ledger = {}
st.session_state.trade_resolutions = {g["key"]: "lost" for g in open_groups}
# resolve_trade_row가 수동 패를 −잔여원가로 계산
for g in open_groups:
    assert eng.resolve_trade_row(g)["resolved"] == "lost", g
eng.update_trade_ledger()
led2 = st.session_state.trade_ledger
assert len(led2) == 2, led2.keys()
assert all(v["resolved"] == "lost" for v in led2.values()), led2
assert abs(sum(v["pnl"] for v in led2.values()) - (-747.0)) < 0.01, [v["pnl"] for v in led2.values()]
print("8) 지갑 팔레이 수동 패 확정 → 장부 −$747 OK")
print("ALL COMBO TESTS PASSED")
