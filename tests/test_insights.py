"""behavior_insights 계산 검증 (bare mode) + AppTest 부팅/렌더/위젯 저장 검증."""
import sys, os, json
from pathlib import Path
TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(TESTS))
os.chdir(REPO)
from seed_state import seed
seed()

# ---------- 1) bare-mode 계산 검증 ----------
import streamlit as st
from engine import behavior_insights

st.session_state.profile = {"emotional_limit": 50.0}
ledger = {
    "k1": {"market": "M1", "outcome": "A", "pnl": -50.0, "updated_at": "2",
           "avg_buy_price": 85.0, "buy_cost": 100.0, "first_ts": 500.0, "latest_ts": 1000.0},
    "k2": {"market": "M2", "outcome": "B", "pnl": -30.0, "updated_at": "2",
           "avg_buy_price": 55.0, "buy_cost": 20.0, "first_ts": 2000.0, "latest_ts": 2500.0},
    "k3": {"market": "M3", "outcome": "C", "pnl": 40.0, "updated_at": "2",
           "avg_buy_price": 60.0, "buy_cost": 20.0, "first_ts": 100000.0, "latest_ts": 110000.0},
}
emotions = {"k1": {"emotion": 5, "chase": False}, "k2": {"emotion": 4, "chase": False},
            "k3": {"emotion": 1, "chase": False}}
ins = behavior_insights(ledger, emotions, chase_window_min=60)
assert ins["n"] == 3 and ins["tagged"] == 3, ins
assert ins["tilt"] == {"n": 2, "pnl": -80.0}, ins["tilt"]
assert ins["calm"] == {"n": 1, "pnl": 40.0}, ins["calm"]
# k2: 첫 매수 2000, k1 손실 정산 1000 → 1000초(<=3600) 내 재진입 = 추격 자동감지
assert ins["chase"]["n"] == 1 and ins["chase"]["detected"] == 1 and ins["chase"]["pnl"] == -30.0, ins["chase"]
assert ins["high_price"]["n"] == 1 and ins["high_price"]["pnl"] == -50.0, ins["high_price"]
assert ins["oversized"]["n"] == 1 and ins["oversized"]["pnl"] == -50.0 and ins["oversized"]["limit"] == 50.0, ins["oversized"]
assert ins["violation"] == {"n": 1, "pnl": -50.0}, ins["violation"]   # k1 합집합 1건
assert ins["emotional"]["n"] == 2 and ins["emotional"]["pnl"] == -80.0, ins["emotional"]
assert ins["corr"] is not None and ins["corr"] < 0, ins["corr"]
# 빈 장부 fail-soft
assert behavior_insights({}, {})["n"] == 0
# 회귀: 단일 체결 손실(첫 매수시각=정산시각)이 자기 자신을 추격으로 잡으면 안 됨
solo = {"s1": {"market": "S", "outcome": "X", "pnl": -10.0, "updated_at": "1",
               "avg_buy_price": 50.0, "buy_cost": 10.0, "first_ts": 5000.0, "latest_ts": 5000.0}}
ins_solo = behavior_insights(solo, {})
assert ins_solo["chase"]["n"] == 0 and ins_solo["chase"]["detected"] == 0, ins_solo["chase"]
print("1) behavior_insights 계산 OK (자기추격 회귀 포함)")

# ---------- 2) AppTest: 시드 상태로 부팅 → 장부 확장 필드 + 인사이트 렌더 ----------
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("streamlit_app.py", default_timeout=180).run()
assert not at.exception, f"EXCEPTION: {at.exception}"
led = at.session_state["trade_ledger"]
assert led, "ledger empty"
row_b = led.get("22222222222222222222")
assert row_b and row_b["resolved"] == "lost" and abs(row_b["pnl"] - (-64.0)) < 0.01, row_b
assert row_b.get("avg_buy_price") == 80.0 and row_b.get("buy_cost") == 64.0, row_b
assert row_b.get("first_ts", -1) > 0 and row_b.get("latest_ts", -1) > 0, row_b
row_a = led.get("11111111111111111111")
assert row_a and abs(row_a["pnl"] - 10.0) < 0.01, row_a
all_md = "\n".join(m.value for m in at.markdown)
assert "행동 인사이트" in all_md, "insights section missing"
assert "감정적 거래 손익" in all_md, "emotional stat missing"
print("2) AppTest 부팅 + 장부 확장 + 인사이트 렌더 OK")

# ---------- 3) AppTest single-run: 손익박스 열고 감정 태그 저장 경로 ----------
# key: review_send_{key_prefix}_{idx}_{rid} / emo_{key_prefix}_{idx}, key_prefix="wallet_", idx=0(최신부터 정렬)
import importlib
import engine as eng
importlib.reload(eng)  # 세션 오염 방지용 아님, 함수만 사용
st.session_state.lang = "ko"
state = json.load(open("memento_state.json", encoding="utf-8"))
rows = eng.group_auto_trades_for_pnl(state["auto_trades"])
r0 = rows[0]  # 최신 = B (12:00)
rid0 = eng.make_review_id_from_trade_group(r0, "wallet")
at2 = AppTest.from_file("streamlit_app.py", default_timeout=180)
at2.session_state[f"review_send_wallet__0_{rid0}"] = True
at2.session_state["emo_wallet__0"] = 3  # 기존 5 → 3으로 변경되면 저장 로직이 실행됨
at2.run()
assert not at2.exception, f"EXCEPTION: {at2.exception}"
emo_map = at2.session_state["trade_emotions"]
assert emo_map.get(r0["key"], {}).get("emotion") == 3, emo_map
all_md2 = "\n".join(m.value for m in at2.markdown)
assert "손익 계산" in all_md2, "inline pnl box missing"
saved = json.load(open("memento_state.json", encoding="utf-8"))
assert saved["trade_emotions"].get(r0["key"], {}).get("emotion") == 3, "not persisted"
print("3) 감정 태그 위젯 저장 + 영구화 OK")
print("ALL INSIGHTS TESTS PASSED")
