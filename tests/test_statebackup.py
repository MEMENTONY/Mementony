"""전체 상태 백업/복원 검증 — 스냅샷/서명/webapp 왕복/부팅 복원/자동백업 (네트워크 mock)."""
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

class FakeResp:
    def __init__(self, payload):
        self._p = json.dumps(payload).encode()
    def read(self):
        return self._p
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False

class FakeRawResp:
    """비-JSON 응답(예: 배포 액세스 미설정 시 구글이 돌려주는 로그인/권한승인 HTML) 시뮬레이션."""
    def __init__(self, text):
        self._p = text.encode()
    def read(self):
        return self._p
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False

# ---------- 1) 스냅샷: raw 제외 + 데이터 포함 / 서명: _saved_at 무시 ----------
st.session_state.trade_resolutions = {"K": "won"}
st.session_state.trade_emotions = {"K": {"emotion": 3, "chase": False}}
st.session_state.cash = 123.45
st.session_state.wallet_raw = [{"huge": "x" * 1000}]
st.session_state.activity_raw = [{"huge": "y" * 1000}]
snap = json.loads(d.state_snapshot_json())
assert snap["trade_resolutions"] == {"K": "won"} and snap["cash"] == 123.45, snap.keys()
assert "wallet_raw" not in snap and "activity_raw" not in snap and snap["_schema"] == 1
sig1 = d.state_backup_signature()
import time as _t; _t.sleep(1.1)   # _saved_at이 초 단위로 달라져도
sig2 = d.state_backup_signature()
assert sig1 == sig2, "signature must ignore _saved_at"
st.session_state.cash = 999.0
assert d.state_backup_signature() != sig1, "signature must change on data change"
print("1) 스냅샷/서명 OK")

# ---------- 2) 백업 POST + 3) fetch 왕복 + 4) restore ----------
st.session_state.gsheet_webapp_url = "https://script.google.com/macros/s/FAKE/exec"
st.session_state.gsheet_webapp_token = "tok"
cap = {}
def fake_post(req, timeout=None):
    cap["data"] = json.loads(req.data.decode())
    return FakeResp({"ok": True, "chunks": 1})
with patch("urllib.request.urlopen", side_effect=fake_post):
    r = d.backup_state_via_webapp()
assert r["ok"], r
assert cap["data"]["token"] == "tok" and "saved_at" in cap["data"]
assert st.session_state["state_backup_last_at"] == cap["data"]["saved_at"]  # 영구 키 (유실 배너 판단)
posted_state = json.loads(cap["data"]["state"])
assert posted_state["cash"] == 999.0

def fake_get(req, timeout=None):
    cap["url"] = req.full_url
    return FakeResp({"ok": True, "state": cap["data"]["state"], "saved_at": cap["data"]["saved_at"]})
with patch("urllib.request.urlopen", side_effect=fake_get):
    data2, saved_at, err = d.fetch_state_from_webapp()
assert err == "" and data2["cash"] == 999.0 and saved_at == cap["data"]["saved_at"]
assert "action=read_state" in cap["url"] and "token=tok" in cap["url"]
# 스냅샷 없음(빈 state) → 오류 아님
with patch("urllib.request.urlopen", side_effect=lambda req, timeout=None: FakeResp({"ok": True, "state": "", "saved_at": ""})):
    d3, s3, e3 = d.fetch_state_from_webapp()
assert d3 is None and e3 == ""
# restore 적용 + 로컬 파일 재생성
st.session_state.cash = 0.0
st.session_state.trade_resolutions = {}
with patch("urllib.request.urlopen", side_effect=fake_get):
    rr = d.restore_state_from_webapp()
assert rr["ok"] and rr["restored"] > 0, rr
assert st.session_state.cash == 999.0 and st.session_state.trade_resolutions == {"K": "won"}
assert st.session_state["_local_state_status"] == "restored_from_sheet"
ondisk = json.load(open("memento_state.json", encoding="utf-8"))
assert ondisk["cash"] == 999.0
print("2~4) 백업/조회/복원 왕복 OK")

# ---------- 4b) 회귀: 비-JSON 응답(배포 액세스 미설정 등)을 거짓 성공 처리하지 않는다 ----------
with patch("urllib.request.urlopen", side_effect=lambda req, timeout=None: FakeRawResp("<html>Sign in - Google Accounts</html>")):
    r_html = d.backup_state_via_webapp()
assert not r_html["ok"] and "non_json_response" in r_html["error"], r_html
print("4b) 비-JSON 응답 → 거짓 성공 방지 OK")

# ---------- 5) AppTest: 재배포 시나리오 — 로컬 없음 + Secrets URL → 부팅 자동 복원 ----------
from streamlit.testing.v1 import AppTest
os.remove("memento_state.json")
SNAP = json.dumps({"cash": 777.0, "trade_resolutions": {"K": "lost"},
                   "trade_emotions": {"K": {"emotion": 5, "chase": True}},
                   "wallet_addr": "0x1234567890abcdef1234567890abcdef12345678",
                   "_saved_at": "2026-07-02T14:00:00"})
posts = []
def fake_net(req, timeout=None):
    if req.data:
        posts.append(json.loads(req.data.decode()))
        return FakeResp({"ok": True})
    return FakeResp({"ok": True, "state": SNAP, "saved_at": "2026-07-02T14:00:00"})
with patch("urllib.request.urlopen", side_effect=fake_net):
    at = AppTest.from_file("streamlit_app.py", default_timeout=180)
    at.secrets["gsheet_webapp_url"] = "https://script.google.com/macros/s/FAKE/exec"
    at.run()
assert not at.exception, f"EXCEPTION: {at.exception}"
assert at.session_state["cash"] == 777.0, at.session_state["cash"]
assert at.session_state["trade_resolutions"] == {"K": "lost"}
assert at.session_state["_state_restore_attempted"] is True
assert os.path.exists("memento_state.json"), "local file must be recreated"
print("5) 부팅 자동 복원 OK")

# ---------- 6) AppTest: 자동백업 켜면 상태 스냅샷도 백업 (1회 + 서명 저장) ----------
os.remove("memento_state.json")
posts.clear()
with patch("urllib.request.urlopen", side_effect=fake_net):
    at2 = AppTest.from_file("streamlit_app.py", default_timeout=180)
    at2.secrets["gsheet_webapp_url"] = "https://script.google.com/macros/s/FAKE/exec"
    at2.session_state["gsheet_autobackup"] = True
    at2.run()
assert not at2.exception, f"EXCEPTION: {at2.exception}"
state_posts = [p for p in posts if "state" in p]
assert len(state_posts) == 1, f"expected 1 state post, got {len(state_posts)}"
assert at2.session_state["_state_backup_sig"], "state signature not stored"
restored_again = json.loads(state_posts[0]["state"])
assert restored_again["cash"] == 777.0   # 복원된 값이 그대로 다시 백업됨
print("6) 상태 자동백업 OK")
print("ALL STATE-BACKUP TESTS PASSED")
