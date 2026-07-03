"""auto_resolve_trades / fetch_markets_by_token_ids 검증 — gamma-api를 mock으로."""
import sys, os, json
from unittest.mock import patch
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

TOK_B = "22222222222222222222"

class FakeResp:
    def __init__(self, payload):
        self._p = json.dumps(payload).encode()
    def read(self):
        return self._p
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False

GAMMA = [{
    "question": "Lakers vs Celtics — winner",
    "closed": True,
    "umaResolutionStatus": "resolved",
    "clobTokenIds": json.dumps([TOK_B, "33333333333333333333"]),
    "outcomePrices": json.dumps(["1", "0"]),
}]

# ---------- 1) fetch_markets_by_token_ids 파싱 ----------
with patch("urllib.request.urlopen", return_value=FakeResp(GAMMA)):
    v = d.fetch_markets_by_token_ids([TOK_B])
assert v[TOK_B]["verdict"] == "won" and v[TOK_B]["closed"] is True, v
assert v["33333333333333333333"]["verdict"] == "lost", v
# 미종료 마켓 → verdict ""
open_m = [dict(GAMMA[0], closed=False, umaResolutionStatus="")]
with patch("urllib.request.urlopen", return_value=FakeResp(open_m)):
    v2 = d.fetch_markets_by_token_ids([TOK_B])
assert v2[TOK_B]["verdict"] == "" and v2[TOK_B]["closed"] is False, v2
# 네트워크 오류 → 빈 dict (fail-soft)
with patch("urllib.request.urlopen", side_effect=OSError("down")):
    assert d.fetch_markets_by_token_ids([TOK_B]) == {}
print("1) gamma 파싱/판정 OK")

# ---------- 2) auto_resolve_trades: 미확정 보유 → won 확정 + 장부 갱신 ----------
state = json.load(open("memento_state.json", encoding="utf-8"))
st.session_state.auto_trades = state["auto_trades"]
st.session_state.paste_trades = []
st.session_state.activity_events = []
st.session_state.trade_resolutions = {}   # 미확정으로 시작
st.session_state.trade_emotions = {}
st.session_state.trade_ledger = {}
st.session_state.profile = {"emotional_limit": 50.0}
st.session_state.portfolio = []
st.session_state.cash = 0.0

with patch("urllib.request.urlopen", return_value=FakeResp(GAMMA)):
    r = d.auto_resolve_trades()
assert r["ok"] and r["won"] == 1 and r["lost"] == 0 and r["checked"] == 1, r
assert st.session_state.trade_resolutions.get(TOK_B) == "won", st.session_state.trade_resolutions
led = st.session_state.trade_ledger
# won: 80¢ 80주 → cur 0 + (80 - 64) = +16
assert abs(led[TOK_B]["pnl"] - 16.0) < 0.01 and led[TOK_B]["resolved"] == "won", led.get(TOK_B)

# ---------- 3) 수동 확정 보존 + 대상 없음 ----------
st.session_state.trade_resolutions = {TOK_B: "lost"}   # 수동 lost 가정
with patch("urllib.request.urlopen", return_value=FakeResp(GAMMA)):
    r2 = d.auto_resolve_trades()
assert r2["ok"] and r2["checked"] == 0, r2               # 이미 확정 → 후보 없음
assert st.session_state.trade_resolutions[TOK_B] == "lost"  # 덮어쓰지 않음

# ---------- 4) 네트워크 실패 → unknown, 아무것도 안 바꿈 ----------
st.session_state.trade_resolutions = {}
with patch("urllib.request.urlopen", side_effect=OSError("down")):
    r3 = d.auto_resolve_trades()
assert r3["ok"] and r3["unknown"] == 1 and r3["won"] == 0 and r3["lost"] == 0, r3
assert st.session_state.trade_resolutions == {}, st.session_state.trade_resolutions
print("2~4) auto_resolve_trades 판정/보존/fail-soft OK")
print("ALL AUTORESOLVE TESTS PASSED")
