"""sync_wallet_full 단일 파이프라인 검증 — 포지션+가치+활동+장부+자동확정 (전부 mock) + 부팅 자동 동기화."""
import sys, os, json
from pathlib import Path
from unittest.mock import patch
TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(TESTS))
os.chdir(REPO)
import seed_state
seed_state.seed()

import streamlit as st
st.session_state.lang = "ko"
import views as v

ADDR = "0x1234567890abcdef1234567890abcdef12345678"
TOK_NEW = "88888888888888888888"

POSITIONS = [{"title": "P1 market", "outcome": "Yes", "avgPrice": 0.4, "size": 10.0,
              "initialValue": 4.0, "currentValue": 5.0, "curPrice": 0.5, "asset": "77777777777777777777"}]
ACTIVITY = [{"type": "TRADE", "side": "BUY", "price": 0.6, "size": 50.0, "usdcSize": 30.0,
             "timestamp": 1751500000, "title": "New market Q", "outcome": "Up",
             "asset": TOK_NEW, "transactionHash": "0xabc"}]
GAMMA = [{"question": "New market Q", "closed": True, "umaResolutionStatus": "resolved",
          "clobTokenIds": json.dumps([TOK_NEW]), "outcomePrices": json.dumps(["1"])}]

class FakeResp:
    def __init__(self, payload):
        self._p = json.dumps(payload).encode()
    def read(self):
        return self._p
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False

calls = []
def router(req, timeout=None):
    url = req.full_url
    calls.append(url)
    if "positions" in url:
        return FakeResp(POSITIONS)
    if "value" in url:
        return FakeResp({"value": 123.0})
    if "activity" in url:
        return FakeResp(ACTIVITY)
    if "gamma-api" in url:
        return FakeResp(GAMMA)
    return FakeResp({})

def reset_session():
    st.session_state.profile = {"emotional_limit": 50.0}
    st.session_state.portfolio = []
    st.session_state.cash = 0.0
    st.session_state.auto_trades = []
    st.session_state.paste_trades = []
    st.session_state.imported_tx_ids = []
    st.session_state.activity_events = []
    st.session_state.trade_resolutions = {}
    st.session_state.trade_emotions = {}
    st.session_state.trade_ledger = {}

# ---------- 1) 전체 파이프라인: 포지션 + 활동 + 장부 + 자동확정 ----------
reset_session()
with patch("urllib.request.urlopen", side_effect=router):
    r = v.sync_wallet_full(ADDR, limit=100, force=False)
assert r["ok"], r
assert r["positions"] == 1 and st.session_state.portfolio[0]["name"] == "P1 market", st.session_state.portfolio
assert st.session_state.portfolio[0]["cur"] == 50.0 and st.session_state.portfolio[0]["buy"] == 40.0
assert r["found"] == 1 and r["added"] == 1, r
assert r["resolved_won"] == 1 and r["resolved_lost"] == 0, r
assert st.session_state.trade_resolutions.get(TOK_NEW) == "won"
led = st.session_state.trade_ledger.get(TOK_NEW)
assert led and led["resolved"] == "won" and abs(led["pnl"] - 20.0) < 0.01, led  # 0 + (50주 − $30)
assert st.session_state.api_sync_meta["positions"] == 1
print("1) 전체 파이프라인 OK")

# ---------- 2) 잘못된 주소 → 네트워크 호출 없음 ----------
calls.clear()
with patch("urllib.request.urlopen", side_effect=router):
    r2 = v.sync_wallet_full("0xshort")
assert not r2["ok"] and r2["error"] == "bad_address" and calls == [], (r2, calls)
print("2) 주소 검증 OK")

# ---------- 3) 포지션 실패 + 활동 성공 → 부분 성공 ----------
reset_session()
def router_pos_fail(req, timeout=None):
    if "positions" in req.full_url:
        raise OSError("positions down")
    return router(req, timeout)
with patch("urllib.request.urlopen", side_effect=router_pos_fail):
    r3 = v.sync_wallet_full(ADDR, limit=100, force=True, resolve=False)
assert r3["ok"] and r3["positions"] == 0 and "positions" in r3["partial"], r3
assert r3["found"] == 1 and r3["resolved_won"] == 0, r3
assert st.session_state.api_sync_meta["status"] == "partial"
print("3) 부분 성공(fail-soft) OK")

# ---------- 4) AppTest: 부팅 자동 동기화 (auto_sync_on_boot=True) ----------
from streamlit.testing.v1 import AppTest
stt = seed_state.build_state()
stt["auto_sync_on_boot"] = True   # 시드 기본은 False(테스트 격리) — 이 테스트만 켠다
with open("memento_state.json", "w", encoding="utf-8") as f:
    json.dump(stt, f, ensure_ascii=False)
with patch("urllib.request.urlopen", side_effect=router):
    at = AppTest.from_file("streamlit_app.py", default_timeout=180).run()
assert not at.exception, f"EXCEPTION: {at.exception}"
assert at.session_state["_wallet_autosynced"] is True
assert len(at.session_state["portfolio"]) == 1 and at.session_state["portfolio"][0]["name"] == "P1 market"
assert at.session_state["trade_resolutions"].get(TOK_NEW) == "won"      # 부팅에서 자동확정까지
assert at.session_state["trade_resolutions"].get(seed_state.TOK_B) == "lost"  # 기존 수동 확정 보존
print("4) 부팅 자동 동기화 + 자동확정 OK")

# ---------- 5) AppTest: 자동 동기화 OFF면 네트워크 안 탐 ----------
seed_state.seed()   # auto_sync_on_boot=False
calls.clear()
with patch("urllib.request.urlopen", side_effect=router):
    at2 = AppTest.from_file("streamlit_app.py", default_timeout=180).run()
assert not at2.exception, f"EXCEPTION: {at2.exception}"
assert calls == [], f"network must not be touched when off: {calls[:2]}"
print("5) 자동 동기화 OFF 격리 OK")
print("ALL SYNC TESTS PASSED")
