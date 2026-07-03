"""rule_simulation 검증 — 규칙별 개별/결합 counterfactual + 일별 누적 + AppTest 렌더."""
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
from engine import rule_simulation, _mark_stopped_after_losses, _ledger_recs_for_analysis

st.session_state.profile = {"emotional_limit": 50.0}

def row(pnl, price, cost, first, latest, day, market):
    return {"market": market, "outcome": "X", "pnl": pnl, "updated_at": "1",
            "date": f"{day}T12:00", "avg_buy_price": price, "buy_cost": cost,
            "first_ts": first, "latest_ts": latest}

LEDGER = {
    "r1": row(-50.0, 85.0, 100.0, 500.0, 1000.0, "2026-07-01", "M1"),   # 고가 진입 + 과대베팅
    "r2": row(-30.0, 55.0, 20.0, 2000.0, 2500.0, "2026-07-01", "M2"),   # r1 손실 후 1000초 → 추격
    "r3": row(-20.0, 60.0, 30.0, 2600.0, 3000.0, "2026-07-01", "M3"),   # 2연패 후 진입 → 중단 대상 (+추격)
    "r4": row(40.0, 60.0, 20.0, 100000.0, 110000.0, "2026-07-02", "M4"),
}

# ---------- 1) 중단 표시 ----------
recs = _ledger_recs_for_analysis(LEDGER, {})
_mark_stopped_after_losses(recs)
stopped = {r["key"]: r["_stopped"] for r in recs}
assert stopped == {"r1": False, "r2": False, "r3": True, "r4": False}, stopped
chases = {r["key"]: r["_chase"] for r in recs}
assert chases == {"r1": False, "r2": True, "r3": True, "r4": False}, chases
print("1) 중단/추격 표시 OK")

# ---------- 2) 규칙별 개별 효과 ----------
sim = rule_simulation(LEDGER, {})
assert sim["n"] == 4 and sim["actual_total"] == -60.0, sim
R = sim["rules"]
assert R["skip_high_price"] == {"total": -10.0, "delta": 50.0, "affected": 1, "enabled": True}, R["skip_high_price"]
assert R["cap_size"]["total"] == -35.0 and R["cap_size"]["delta"] == 25.0 and R["cap_size"]["affected"] == 1, R["cap_size"]
assert R["no_chase"] == {"total": -10.0, "delta": 50.0, "affected": 2, "enabled": True}, R["no_chase"]
assert R["stop_after_losses"] == {"total": -40.0, "delta": 20.0, "affected": 1, "enabled": True}, R["stop_after_losses"]
print("2) 규칙별 개별 효과 OK")

# ---------- 3) 결합 + 일별 누적 ----------
C = sim["combined"]
assert C == {"total": 40.0, "delta": 100.0, "skipped": 3, "capped": 0}, C
assert sim["daily"] == [{"date": "2026-07-01", "actual": -100.0, "ruled": 0.0},
                        {"date": "2026-07-02", "actual": -60.0, "ruled": 40.0}], sim["daily"]
# 일부 규칙만: 사이즈 캡만 켬
sim2 = rule_simulation(LEDGER, {}, rules=("cap_size",))
assert sim2["combined"]["total"] == -35.0 and sim2["combined"]["capped"] == 1, sim2["combined"]
# 빈 장부 fail-soft
assert rule_simulation({}, {})["n"] == 0
print("3) 결합/일별/부분규칙 OK")

# ---------- 4) AppTest: 복기 탭에 시뮬레이터 렌더 ----------
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("streamlit_app.py", default_timeout=180).run()
assert not at.exception, f"EXCEPTION: {at.exception}"
all_md = "\n".join(m.value for m in at.markdown)
assert "규칙 시뮬레이터" in all_md, "simulator section missing"
assert "규칙 하나만 지켰다면" in all_md, "per-rule grid missing"
print("4) AppTest 렌더 OK")
print("ALL RULESIM TESTS PASSED")
