"""구글시트 양방향(내보내기/서명/가져오기) + 변경 감지 자동백업 검증 — 네트워크는 전부 mock."""
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
import engine as eng

# 아래 단계들의 save_local_state()가 상태 파일을 덮어쓰므로 시드를 먼저 확보
state0 = json.load(open("memento_state.json", encoding="utf-8"))

class FakeResp:
    def __init__(self, payload):
        self._p = json.dumps(payload).encode()
    def read(self):
        return self._p
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False

TOK = "22222222222222222222"

# ---------- 1) export: 키/감정/추격 컬럼 병합 ----------
st.session_state.trade_ledger = {
    TOK: {"date": "2026-07-01T12:00", "market": "Lakers vs Celtics — winner", "outcome": "Lakers",
          "status": "패(소멸)", "resolved": "lost", "pnl": -64.0, "category": "스포츠",
          "source": "지갑", "updated_at": "2026-07-01T13:00",
          "avg_buy_price": 80.0, "buy_cost": 64.0, "first_ts": 100.0, "latest_ts": 200.0},
}
st.session_state.trade_emotions = {TOK: {"emotion": 5, "chase": True, "updated_at": "x"}}
body, n = d._ledger_rows_for_export()
assert n == 1 and body[0] == d.GSHEET_LEDGER_HEADER, body[0]
row = dict(zip(body[0], body[1]))
assert row["키"] == TOK and row["감정(1-5)"] == "5" and row["추격"] == "Y" and row["카테고리"] == "스포츠", row
assert "first_ts" not in body[0] and len(body[1]) == len(d.GSHEET_LEDGER_FIELDS)
print("1) export 병합 OK")

# ---------- 2) 서명: 내용 바뀔 때만 달라짐 ----------
sig1, n1 = d.ledger_backup_signature()
assert sig1 and n1 == 1
st.session_state.trade_emotions = {TOK: {"emotion": 2, "chase": False, "updated_at": "y"}}
sig2, _ = d.ledger_backup_signature()
assert sig2 != sig1, "signature must change when emotion changes"
st.session_state.trade_ledger = {}
assert d.ledger_backup_signature() == ("", 0)
print("2) 변경 감지 서명 OK")

# ---------- 3) webapp 백업 POST 페이로드 ----------
st.session_state.trade_ledger = {TOK: dict(st.session_state.get("_keep", {})) or {
    "date": "2026-07-01T12:00", "market": "M", "outcome": "O", "status": "s", "resolved": "lost",
    "pnl": -1.0, "category": "c", "source": "지갑", "updated_at": "u"}}
st.session_state.gsheet_webapp_url = "https://script.google.com/macros/s/FAKE/exec"
st.session_state.gsheet_webapp_token = "tok123"
captured = {}
def fake_urlopen(req, timeout=None):
    captured["url"] = req.full_url
    captured["data"] = json.loads(req.data.decode()) if req.data else None
    return FakeResp({"ok": True, "written": 1})
with patch("urllib.request.urlopen", side_effect=fake_urlopen):
    r = d.backup_ledger_via_webapp()
assert r["ok"] and r["written"] == 1, r
assert captured["data"]["token"] == "tok123" and captured["data"]["rows"][0] == d.GSHEET_LEDGER_HEADER
print("3) webapp 백업 OK")

# ---------- 4) 시트 → 앱 가져오기 ----------
st.session_state.trade_ledger = {
    TOK: {"date": "d", "market": "M", "outcome": "O", "status": "s", "resolved": "lost",
          "pnl": -1.0, "category": "기타", "source": "지갑", "updated_at": "u"}}
st.session_state.trade_emotions = {}
sheet_rows = [d.GSHEET_LEDGER_HEADER,
              [TOK, "d", "M", "O", "s", "lost", "-1.0", "농구", "4", "y", "지갑", "u"],
              ["없는키", "d", "M2", "O2", "s", "", "0", "정치", "5", "", "지갑", "u"]]
def fake_doget(req, timeout=None):
    captured["get_url"] = req.full_url
    return FakeResp({"ok": True, "rows": sheet_rows})
with patch("urllib.request.urlopen", side_effect=fake_doget):
    ri = d.restore_ledger_from_webapp()
assert ri["ok"] and ri["categories"] == 1 and ri["tags"] == 1 and ri["rows"] == 2, ri
assert "action=read" in captured["get_url"] and "token=tok123" in captured["get_url"]
led = st.session_state.trade_ledger[TOK]
assert led["category"] == "농구" and led["category_src"] == "manual", led
emo = st.session_state.trade_emotions[TOK]
assert emo["emotion"] == 4 and emo["chase"] is True, emo
# 같은 내용 다시 가져오면 변경 0
with patch("urllib.request.urlopen", side_effect=fake_doget):
    ri2 = d.restore_ledger_from_webapp()
assert ri2["ok"] and ri2["categories"] == 0 and ri2["tags"] == 0, ri2
# 키 컬럼 없는 시트 → 에러
bad = [["날짜", "시장"], ["d", "M"]]
with patch("urllib.request.urlopen", side_effect=lambda req, timeout=None: FakeResp({"ok": True, "rows": bad})):
    ri3 = d.restore_ledger_from_webapp()
assert not ri3["ok"] and ri3["error"] == "no_key_column", ri3
# 토큰 거부 응답 → 에러 전달
with patch("urllib.request.urlopen", side_effect=lambda req, timeout=None: FakeResp({"ok": False, "error": "bad token"})):
    ri4 = d.restore_ledger_from_webapp()
assert not ri4["ok"] and "bad token" in ri4["error"], ri4
print("4) 시트→앱 가져오기 OK")

# ---------- 5) update_trade_ledger가 수동 카테고리 보존 ----------
st.session_state.auto_trades = state0["auto_trades"]
st.session_state.paste_trades = []
st.session_state.activity_events = []
st.session_state.trade_resolutions = {TOK: "lost"}
st.session_state.trade_ledger = {
    TOK: {"date": "d", "market": "Lakers vs Celtics — winner", "outcome": "Lakers", "status": "s",
          "resolved": "lost", "pnl": -64.0, "category": "농구", "category_src": "manual",
          "source": "지갑", "updated_at": "u"}}
eng.update_trade_ledger()
led2 = st.session_state.trade_ledger[TOK]
assert led2["category"] == "농구" and led2.get("category_src") == "manual", led2
print("5) 수동 카테고리 보존 OK")

# ---------- 6) AppTest: 변경 감지 자동백업 (첫 로드 1회 + 서명 저장) ----------
from streamlit.testing.v1 import AppTest
calls = {"post": 0, "state_post": 0}
def fake_backup_urlopen(req, timeout=None):
    if req.data:
        _pl = json.loads(req.data.decode())
        if "rows" in _pl:          # 장부 백업
            calls["post"] += 1
            calls["rows"] = _pl["rows"]
        elif "state" in _pl:       # 전체 상태 스냅샷 백업 (별도 테스트에서 검증)
            calls["state_post"] += 1
    return FakeResp({"ok": True, "written": 2})
with patch("urllib.request.urlopen", side_effect=fake_backup_urlopen):
    at = AppTest.from_file("streamlit_app.py", default_timeout=180)
    at.session_state["gsheet_autobackup"] = True
    at.session_state["gsheet_webapp_url"] = "https://script.google.com/macros/s/FAKE/exec"
    at.run()
assert not at.exception, f"EXCEPTION: {at.exception}"
assert calls["post"] == 1, calls          # 장부 백업은 정확히 1회
assert calls["state_post"] == 1, calls    # 상태 스냅샷 백업도 1회
assert calls["rows"][0] == d.GSHEET_LEDGER_HEADER
assert at.session_state["_gsheet_backup_sig"], "signature not stored"
print("6) 변경 감지 자동백업 OK")
print("ALL GSHEET TESTS PASSED")
