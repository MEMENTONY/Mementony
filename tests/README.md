# tests — Memento 테스트 스위트

**반드시 python 3.12 + streamlit 1.58.0** (PEP 701 f-string, AppTest 동작이 버전에 민감).
네트워크는 전부 mock — 폴리마켓/구글시트에 실제 요청을 보내지 않는다.

## 실행

각 파일은 **독립 프로세스로** 실행해야 한다 (bare-mode `st.session_state`가 전역이라 한 프로세스에서 여러 파일을 돌리면 서로 오염됨). CI(`.github/workflows/tests.yml`)도 같은 방식.

```bash
pip install -r requirements.txt
for f in tests/test_*.py; do python "$f" || break; done
```

## 파일

| 파일 | 검증 내용 |
|---|---|
| `test_boot.py` | 시드/빈 상태 AppTest 부팅 무예외 |
| `test_insights.py` | behavior_insights 계산(감정×손익·추격 자기제외·규칙위반), 감정 태그 위젯 저장/영구화 |
| `test_autoresolve.py` | gamma-api 파싱/판정, 수동 확정 보존, 네트워크 실패 fail-soft |
| `test_gsheet.py` | 장부 내보내기(키·감정 병합)·지문·webapp 백업·시트→앱 가져오기·수동 카테고리 보존·변경감지 자동백업 |
| `test_statebackup.py` | 전체 상태 스냅샷/서명/백업·복원 왕복, 재배포 시나리오 부팅 자동 복원, 상태 자동백업 |
| `test_rulesim.py` | 규칙 시뮬레이터 — 중단/추격 표시, 규칙별·결합 counterfactual, 일별 누적 |
| `test_journal_fixes.py` | 거래 카드 HTML 노출 방지(html_block·빈 줄/4칸 들여쓰기 금지), 활동 페이지네이션(offset·상한), 자가치유 중복제거(유실 재인식·레거시 내용 지문) |

`seed_state.py`는 시드 헬퍼(테스트가 각자 호출). 테스트가 리포 루트의 `memento_state.json`을 덮어쓰므로(gitignore됨) 실데이터가 있는 환경에서는 백업 후 실행할 것.

## 주의 (streamlit 1.58 AppTest)

- **2회차 run 버그**(`_widget_state` AttributeError) — 위젯 상호작용은 single-run으로: `at.session_state`에 위젯 key를 미리 심고 첫 run에서 원하는 상태를 렌더.
- 위젯 검증 예시는 `test_insights.py` 3번 참고.
