"""부팅 스모크: 시드 상태·빈 상태 모두 AppTest 부팅이 무예외인지 확인."""
import sys, os
from pathlib import Path
TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(TESTS))
os.chdir(REPO)
from seed_state import seed

from streamlit.testing.v1 import AppTest

# 1) 시드 상태 부팅
seed()
at = AppTest.from_file("streamlit_app.py", default_timeout=180).run()
assert not at.exception, f"EXCEPTION(seeded): {at.exception}"
assert at.session_state["trade_ledger"], "seeded boot must build the ledger"
print("1) 시드 상태 부팅 OK ·", len(at.markdown), "markdown")

# 2) 빈 상태 부팅 (신규 사용자 / 재배포 직후 미복원)
os.remove(REPO / "memento_state.json")
at2 = AppTest.from_file("streamlit_app.py", default_timeout=180).run()
assert not at2.exception, f"EXCEPTION(empty): {at2.exception}"
print("2) 빈 상태 부팅 OK ·", len(at2.markdown), "markdown")
print("ALL BOOT TESTS PASSED")
