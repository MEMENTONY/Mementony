"""거래일지 수정 3종 검증 — HTML 노출 방지(html_block) · 활동 페이지네이션 · 자가치유 중복제거.
네트워크는 전부 mock."""
import sys, os, json, re, urllib.parse
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
import ui
import data as d
import views as v

# ---------- 1) html_block: 마크다운이 코드블록/HTML 종료로 오해할 줄이 없어야 함 ----------
raw = '''<div class="pf-card">
  <div class="pf-card-head">
    <div>
      <div class="pf-title">T1 vs FURIA</div>

    </div>
    <div style="text-align:right;min-width:96px;">
      <div style="font-size:22px;">+$17.59</div>
    </div>
  </div>
</div>'''
cleaned = ui.html_block(raw)
lines = cleaned.splitlines()
assert all(l.strip() for l in lines), "빈/공백 줄이 남으면 HTML 블록이 끊긴다"
assert all(not l.startswith(" ") for l in lines), "4칸 들여쓰기가 남으면 코드블록으로 노출된다"
assert "+$17.59" in cleaned and cleaned.count("<div") == cleaned.count("</div>")
print("1) html_block 정리 OK")

# ---------- 2) 거래 카드 렌더: 넘어가는 마크다운에 위험한 줄이 없어야 함 ----------
st.session_state.trade_resolutions = {}
st.session_state.trade_emotions = {}
rows_trades = [
    # 미확정 힌트 없는(= 예전엔 공백 줄이 생겨 깨지던) 청산 완료 거래
    {"tx_id": "a1", "d": "2026-07-06T17:38:00+09:00", "name": "LoL: T1 vs FURIA Esports - Game 3 Winner",
     "outcome": "T1", "side": "BUY", "price": 95.1, "shares": 370.0, "amount": 352.03, "asset": "tokA", "token_id": "tokA"},
    {"tx_id": "a2", "d": "2026-07-06T17:40:00+09:00", "name": "LoL: T1 vs FURIA Esports - Game 3 Winner",
     "outcome": "T1", "side": "SELL", "price": 99.9, "shares": 370.0, "amount": 369.62, "asset": "tokA", "token_id": "tokA"},
    # 미확정 보유(힌트 있는 경로)도 함께 검사
    {"tx_id": "b1", "d": "2026-07-06T14:13:00+09:00", "name": "LoL: BLG vs LYON - Game 3 Winner",
     "outcome": "Bilibili Gaming", "side": "BUY", "price": 86.4, "shares": 300.0, "amount": 259.08, "asset": "tokB", "token_id": "tokB"},
]
captured = []
_orig_markdown = st.markdown
def _spy_markdown(body, *a, **k):
    captured.append(str(body))
    return None
with patch.object(v.st, "markdown", side_effect=_spy_markdown), \
     patch.object(v.st, "columns", wraps=v.st.columns):
    v.render_trade_pnl_summary(rows_trades, "테스트", key_prefix="wallet_")
cards = [b for b in captured if "pf-card" in b]
assert cards, "거래 카드가 렌더되지 않음"
for body in cards:
    for ln in body.splitlines():
        assert ln.strip(), f"공백 줄 발견 — HTML 노출 재발: {body[:80]}"
        assert not ln.startswith("    "), f"4칸 들여쓰기 발견 — 코드블록 노출 재발: {ln!r}"
print(f"2) 거래 카드 {len(cards)}건 마크다운 안전 OK")

# ---------- 3) 페이지네이션: offset을 넘겨가며 오래된 거래까지 수집 ----------
TOTAL = 620  # 한 페이지(500) 초과
FEED = [{"type": "TRADE", "side": "BUY", "price": 0.5, "size": 10.0, "usdcSize": 5.0,
         "timestamp": 1751500000 - i, "title": f"Market {i}", "outcome": "Yes",
         "asset": f"tok{i}", "transactionHash": f"0x{i:04d}"} for i in range(TOTAL)]

class FakeResp:
    def __init__(self, payload):
        self._p = json.dumps(payload).encode()
    def read(self):
        return self._p
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False

offsets = []
def router(req, timeout=None):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(req.full_url).query)
    off, lim = int(q["offset"][0]), int(q["limit"][0])
    offsets.append(off)
    return FakeResp(FEED[off:off + lim])

d.fetch_wallet_activity.clear()
d.fetch_wallet_activity_all.clear()
with patch("urllib.request.urlopen", side_effect=router):
    got = d.fetch_wallet_activity_all("0xwallet", max_rows=1000)
assert len(got) == TOTAL, f"{len(got)} != {TOTAL}"
assert offsets == [0, 500], offsets  # 두 번째 페이지까지 요청, 짧은 페이지에서 중단
rows = d.normalize_activity(got)
assert len(rows) == TOTAL
print("3) 활동 페이지네이션 OK")

# ---------- 4) max_rows 상한 준수 ----------
offsets.clear()
d.fetch_wallet_activity.clear()
d.fetch_wallet_activity_all.clear()
with patch("urllib.request.urlopen", side_effect=router):
    got_cap = d.fetch_wallet_activity_all("0xwallet", max_rows=510)
assert len(got_cap) == 510 and offsets == [0, 500], (len(got_cap), offsets)
print("4) max_rows 상한 OK")

# ---------- 5) 자가치유 중복제거: 목록만 남고 거래가 유실돼도 다시 인식 ----------
st.session_state.auto_trades = []
st.session_state.imported_tx_ids = [r["tx_id"] for r in d.normalize_activity(FEED[:5])]  # 유실 상황 재현
items = d.normalize_activity(FEED[:5])
added = d.merge_activity_into_log(items)
assert added == 5, f"유실된 기존 거래가 다시 인식돼야 함: {added}"
# 같은 걸 또 병합하면 0건 (tx_id 기준 중복제거)
assert d.merge_activity_into_log(items) == 0
assert len(st.session_state.auto_trades) == 5
print("5) 자가치유 중복제거 OK")

# ---------- 6) tx_id 없는 옛 행은 내용 지문으로 중복 차단 ----------
legacy = dict(items[0]); legacy.pop("tx_id")
st.session_state.auto_trades = [legacy]
st.session_state.imported_tx_ids = []
assert d.merge_activity_into_log([items[0]]) == 0, "내용이 같은 옛 행과 중복되면 추가 금지"
assert d.merge_activity_into_log([items[1]]) == 1
print("6) 레거시 내용 지문 중복제거 OK")

# ---------- 7) 이벤트 오분류 수정: 시장 제목의 'Winner' 단어로 SPLIT이 정산 이벤트가 되면 안 됨 ----------
api_rows = [
    {"type": "SPLIT", "title": "LoL: T1 vs FURIA - Game 3 Winner", "usdcSize": 50.0, "timestamp": 1751500000},
    {"type": "MERGE", "title": "Will X win the election?", "usdcSize": 10.0, "timestamp": 1751500001},
    {"type": "REDEEM", "title": "Some market", "usdcSize": 99.0, "timestamp": 1751500002},
]
evs = d.normalize_activity_events(api_rows)
assert len(evs) == 1 and evs[0]["type"] == "REDEEM", evs
print("7) 정산 이벤트 분류(제목 키워드 무시 · REDEEM만) OK")

# ---------- 8) '확인 필요(매도>매수)' 행도 수동 확정 가능 (회수금−매수금 기준) ----------
import engine as eng
oversold = [
    {"tx_id": "o1", "d": "2026-07-01T10:00:00+09:00", "name": "Oversold market", "outcome": "Yes",
     "side": "BUY", "price": 50.0, "shares": 10.0, "amount": 5.0, "asset": "tokO", "token_id": "tokO"},
    {"tx_id": "o2", "d": "2026-07-01T11:00:00+09:00", "name": "Oversold market", "outcome": "Yes",
     "side": "SELL", "price": 60.0, "shares": 30.0, "amount": 18.0, "asset": "tokO", "token_id": "tokO"},
]
og = eng.group_auto_trades_for_pnl(oversold)[0]
assert og["realized_pnl"] is None and og["remaining_shares"] == 0.0, og  # 매도>매수 → 확인 필요
st.session_state.trade_resolutions = {}
assert eng.resolve_trade_row(og)["realized_final"] is None               # 미확정이면 그대로 '확인 필요'
st.session_state.trade_resolutions = {og["key"]: "lost"}
r_lost = eng.resolve_trade_row(og)
assert abs(r_lost["realized_final"] - 13.0) < 0.01, r_lost               # 회수 18 − 매수 5 = +13
print("8) 매도>매수 행 수동 확정 폴백 OK")

# ---------- 9) AppTest: AI 탭 삭제 + 확정취소 버튼 + 전체 markdown HTML 안전성 ----------
from seed_state import seed as _seed
_seed()
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("streamlit_app.py", default_timeout=180).run()
assert not at.exception, f"EXCEPTION: {at.exception}"
_all_md = "\n".join(str(m.value) for m in at.markdown)
assert "AI 리서치" not in _all_md, "AI research tab must be removed"
_btns = [b.label for b in at.button]
assert any("확정 취소" in x for x in _btns), _btns                       # 수동 lost 표시된 거래에 취소 버튼
for m in at.markdown:
    s = str(m.value)
    head = s.lstrip()[:8].lower()
    if not s.lstrip().startswith("<") or head.startswith(("<style", "<script", "<pre")):
        continue  # 마크다운 문서/스타일 블록은 빈 줄 허용
    for i, ln in enumerate(s.splitlines()[1:], 2):
        assert ln.strip(), f"HTML 블록 안 공백 줄(태그 노출 재발): line {i} of {s[:80]!r}"
        assert not ln.startswith("    "), f"HTML 블록 안 4칸 들여쓰기: {ln[:60]!r}"
print("9) AI 탭 삭제 + 확정취소 버튼 + 전체 HTML 안전성 OK")

print("ALL JOURNAL-FIX TESTS PASSED")
