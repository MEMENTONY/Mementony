"""자산 곡선(MDD)·일별 캘린더·주간 리포트 검증 + AppTest 렌더."""
import sys, os, json
from pathlib import Path
TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(TESTS))
os.chdir(REPO)
from seed_state import seed
seed()

from datetime import date, timedelta
import streamlit as st
st.session_state.lang = "ko"
from engine import equity_curve_data, calendar_heatmap_data, weekly_report

st.session_state.profile = {"emotional_limit": 50.0}

def row(pnl, day, market, price=60.0, cost=20.0, emotion=0, chase=False, cat="스포츠"):
    return ({"market": market, "outcome": "X", "pnl": pnl, "updated_at": "1",
             "date": f"{day}T12:00", "category": cat, "avg_buy_price": price, "buy_cost": cost,
             "first_ts": -1.0, "latest_ts": -1.0},
            {"emotion": emotion, "chase": chase})

# ---------- 1) 자산 곡선 + MDD ----------
# 일별: +30 → -50 → +10  ⇒ 누적 30 → -20 → -10, peak 30, MDD 50 (둘째 날)
LED, EMO = {}, {}
for i, (pnl, day) in enumerate([(30.0, "2026-06-01"), (-50.0, "2026-06-02"), (10.0, "2026-06-03")]):
    r, e = row(pnl, day, f"M{i}")
    LED[f"k{i}"] = r
    EMO[f"k{i}"] = e
eq = equity_curve_data(LED, EMO)
assert eq["days"] == 3 and eq["total"] == -10.0 and eq["peak"] == 30.0, eq
assert eq["mdd"] == 50.0 and eq["mdd_date"] == "2026-06-02", eq
assert eq["daily"][1] == {"date": "2026-06-02", "pnl": -50.0, "cum": -20.0}, eq["daily"]
assert equity_curve_data({}, {})["days"] == 0
print("1) 자산 곡선/MDD OK")

# ---------- 2) 캘린더 그리드 ----------
end = date(2026, 6, 4)  # 목요일
cal = calendar_heatmap_data(weeks=2, end=end, ledger=LED, emotions=EMO)
assert len(cal["grid"]) == 2 and all(len(w) == 7 for w in cal["grid"]), cal["start"]
assert cal["start"] == "2026-05-25", cal["start"]           # 지지난 월요일
cells = {c["date"]: c for w in cal["grid"] for c in w}
assert cells["2026-06-02"]["pnl"] == -50.0 and cells["2026-06-02"]["count"] == 1
assert cells["2026-05-26"]["pnl"] is None                    # 거래 없는 날
assert cells["2026-06-05"]["future"] is True                 # end 이후는 future
assert cal["scale"] >= 50.0                                  # 95퍼센타일 |일손익|
print("2) 캘린더 그리드 OK")

# ---------- 3) 주간 리포트 ----------
today = date(2026, 6, 10)  # 수요일 → 이번 주 6/8(월)~, 지난주 6/1(월)~6/7
LED2, EMO2 = {}, {}
data = [
    (-64.0, "2026-06-08", dict(price=85.0, cost=100.0, emotion=5, chase=True, cat="농구")),  # 이번 주: 감정적+위반
    (20.0, "2026-06-09", dict(cat="정치")),                                                   # 이번 주 승
    (30.0, "2026-06-02", dict(cat="농구")),                                                   # 지난주 승
    (-10.0, "2026-06-05", dict(cat="정치")),                                                  # 지난주 패
    (99.0, "2026-04-01", dict()),                                                             # 범위 밖
]
for i, (pnl, day, kw) in enumerate(data):
    r, e = row(pnl, day, f"W{i}", **kw)
    LED2[f"w{i}"] = r
    EMO2[f"w{i}"] = e
wr = weekly_report(now=today, ledger=LED2, emotions=EMO2)
assert wr["has_data"] and wr["this_start"] == "2026-06-08" and wr["last_start"] == "2026-06-01", wr
tw, lw = wr["this"], wr["last"]
assert tw["pnl"] == -44.0 and tw["n"] == 2 and tw["wins"] == 1 and tw["win_rate"] == 50.0, tw
assert tw["emotional_pnl"] == -64.0 and tw["emotional_n"] == 1, tw
assert tw["violation_pnl"] == -64.0 and tw["violation_n"] == 1, tw
assert tw["worst_category"] == "농구" and tw["worst_category_pnl"] == -64.0, tw
assert lw["pnl"] == 20.0 and lw["n"] == 2 and lw["win_rate"] == 50.0, lw
assert wr["delta_pnl"] == -64.0, wr["delta_pnl"]
assert not weekly_report(now=today, ledger={}, emotions={})["has_data"]
print("3) 주간 리포트 OK")

# ---------- 4) AppTest 렌더 ----------
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("streamlit_app.py", default_timeout=180).run()
assert not at.exception, f"EXCEPTION: {at.exception}"
all_md = "\n".join(m.value for m in at.markdown)
assert "자산 곡선" in all_md, "equity section missing"
assert "주간 리포트" in all_md, "weekly report missing"
print("4) AppTest 렌더 OK")
print("ALL REPORTS TESTS PASSED")
