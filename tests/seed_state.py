"""테스트용 시드: memento_state.json에 실데이터 모양의 지갑 거래/확정/감정/포트폴리오를 심는다."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

TOK_A = "11111111111111111111"
TOK_B = "22222222222222222222"

def trade(tx, d, name, outcome, side, price, shares, tok):
    return {"tx_id": tx, "d": d, "name": name, "outcome": outcome, "side": side,
            "price": price, "shares": shares, "amount": round(shares * price / 100, 2),
            "asset": tok, "token_id": tok}

def build_state():
    return {
        "lang": "ko",
        "cash": 500.0,
        "profile": {"assets": 1000.0, "start_capital": 1000.0, "emotional_limit": 50.0,
                    "max_pct": 3.0, "block_pct": 12.0, "start_when": "자동 시작", "freq": "", "cats": [],
                    "loss_reaction": "기본값"},
        "wallet_addr": "0x1234567890abcdef1234567890abcdef12345678",
        # 테스트는 네트워크를 쓰지 않아야 하므로 부팅 자동 동기화는 끈다 (앱 기본값은 True)
        "auto_sync_on_boot": False,
        "auto_trades": [
            # C: 전날 40¢ 매수 → 55¢ 매도 = +$7.50 (일별 누적 차트용 둘째 날)
            trade("t0a", "2026-06-30T10:00:00+09:00", "US CPI above 3% in June?", "No", "BUY", 40.0, 50.0, "66666666666666666666"),
            trade("t0b", "2026-06-30T11:00:00+09:00", "US CPI above 3% in June?", "No", "SELL", 55.0, 50.0, "66666666666666666666"),
            # A: 60¢ 100주 매수 → 70¢ 전량 매도 = 청산 완료 +$10
            trade("t1", "2026-07-01T10:00:00+09:00", "Will BTC hit 120k in July?", "Yes", "BUY", 60.0, 100.0, TOK_A),
            trade("t2", "2026-07-01T11:00:00+09:00", "Will BTC hit 120k in July?", "Yes", "SELL", 70.0, 100.0, TOK_A),
            # B: 80¢ 80주 매수 (고가 진입 + 감정한도 $50 초과 $64) → 수동 lost
            trade("t3", "2026-07-01T12:00:00+09:00", "Lakers vs Celtics — winner", "Lakers", "BUY", 80.0, 80.0, TOK_B),
        ],
        "activity_events": [],
        "trade_resolutions": {TOK_B: "lost"},
        "trade_emotions": {TOK_B: {"emotion": 5, "chase": True, "updated_at": "2026-07-01T13:00"}},
        "trade_ledger": {},
        "portfolio": [
            {"name": "Will BTC hit 120k in July?", "outcome": "Yes", "buy": 60.0, "shares": 120.0,
             "inv": 72.0, "cur": 66.0, "asset": "44444444444444444444"},
            {"name": "Fed cuts rates in September?", "outcome": "No", "buy": 35.0, "shares": 200.0,
             "inv": 70.0, "cur": 41.0, "asset": "55555555555555555555"},
        ],
        "reviews": [
            {"review_id": "rv1", "market": "Lakers vs Celtics — winner", "outcome": "Lakers",
             "status": "패(소멸)", "source": "지갑", "avg_buy_price": 80.0, "avg_sell_price": 0.0,
             "sold_shares": 0.0, "estimated_realized_pnl": -64.0, "remaining_shares": 0.0,
             "remaining_cost": 0.0, "latest_dt": "2026-07-01T12:00", "created_at": "2026-07-01T13:00"},
        ],
    }

def seed(path=None):
    """상태 파일을 시드로 덮어쓰고 시드 dict를 돌려준다."""
    target = Path(path) if path else REPO / "memento_state.json"
    state = build_state()
    with open(target, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    return state

if __name__ == "__main__":
    seed()
    print("seeded")
