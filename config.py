# config.py - auto-extracted from streamlit_app.py (behavior-preserving)
import json
import html
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

DEFAULT_PROFILE = {
    "assets": 1000.0,
    "start_capital": 1000.0,
    "start_when": "자동 시작",
    "freq": "",
    "cats": [],
    "emotional_limit": 50.0,
    "max_pct": 3.0,
    "block_pct": 12.0,
    "loss_reaction": "기본값",
}

DEFAULTS = {
    "lang": "ko",
    "display_currency": "USD",
    "usd_krw_rate": 1400.0,
    "profile": dict(DEFAULT_PROFILE),  # default risk profile; no onboarding gate
    "last_entry": None,
    "trade_log": [],
    "portfolio": [],
    "cash": 0.0,
    "deposits": 0.0,          # extra deposits after start capital
    "withdrawals": 0.0,       # withdrawals taken out of wallet
    "adj_month": 0.0,          # pre-app P&L adjustments
    "adj_year": 0.0,
    "url_rows": [],
    "explore_markets": [],
    "explore_raw": [],
    "explore_url": "https://polymarket.com/event/",
    "_explorer_active": "",
    "prefill_entry": {},
    "entry_url": "",
    "entry_markets": [],
    "entry_raw": {},
    "ai_extra_context": "",
    "_entry_active": "",
    "_entry_sel": None,
    "explore_ai_text": "", "explore_ai_error": "", "explore_ai_prompt": "", "explore_ai_pair": "",
    "ai_text": "", "ai_error": "", "ai_prompt": "", "ai_pair": "",
    "wallet_raw": [],
    "activity_raw": [],
    "activity_events": [],
    "api_sync_meta": {},
    "auto_trades": [],
    "wallet_addr": "",
    "imported_tx_ids": [],
    "portfolio_hidden_keys": [],
    "side_panel_mode": "panels",
    "side_panel_section": "today",
    "side_panel_trade_limit": 5,
    "today_anchor_mode": "next",
    "today_anchor_key": "",
    "today_anchor_label": "",
    "today_anchor_time": "",
    "today_anchor_set_at": "",
    "today_stop_loss_gross_only": False,
    "today_cash_adjustment": 0.0,
    "paste_trades": [],
    "paste_events": [],
    "paste_unparsed": [],
    "paste_meta": {"ok": 0, "buy": 0, "sell": 0, "events": [], "unparsed": []},
    "journal_mode": "wallet",
    "trade_qf": "all",
    "trade_qf_select": "all",
    "trade_start_date": None,
    "trade_end_date": None,
    "watchlist": [],
    "watching_market": {},
    "live_price_cache": {},
    "price_history_cache": {},
    "order_candidates": [],
    "explore_book_raw": {},
    "explore_history_raw": {},
    "habit_cache": {},
    "pnl_raw": {},
    "profile_pnl": {},
    "ai_pending": {},
    "ai_report_cache": {},
    "ai_last_market_key": "",
    "ai_report_mode": "standard",
    "_ai_memo_cache": "",
    "_ai_bk_cache": "",
    "dev_mode": False,
    "reviews": [],
    "review_notes": {},
    "entry_self_strategy": {},
    "entry_visible_sections": ["선택한 시장", "내 진입 전략 / 자가 판단"],
    "self_check_scale": 5,
    "day_locked_date": "",
    "trade_ledger": {},
    "trade_resolutions": {},
    "trade_emotions": {},
    "auto_sync_on_boot": True,
    "insight_chase_window": 60,
    "insight_high_price_cents": 80.0,
    "insight_stop_streak": 2,
    "state_backup_last_at": "",
    "gsheet_url": "",
    "gsheet_autobackup": False,
    "gsheet_webapp_url": "",
    "gsheet_webapp_token": "",
}

LOCAL_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memento_state.json")

PERSIST_KEYS = [
    "lang", "display_currency", "usd_krw_rate",
    "profile", "cash", "deposits", "withdrawals", "adj_month", "adj_year",
    "portfolio", "portfolio_hidden_keys", "wallet_addr", "wallet_raw", "pnl_raw",
    "activity_raw", "activity_events", "api_sync_meta", "auto_trades", "imported_tx_ids",
    "paste_trades", "paste_events", "paste_unparsed", "paste_meta", "journal_mode",
    "trade_log", "watchlist", "watching_market", "order_candidates",
    "reviews", "review_notes", "entry_self_strategy", "self_check_scale",
    "side_panel_mode", "side_panel_section", "side_panel_trade_limit",
    "today_start_cash", "today_stop_loss_amount", "today_goal_mode", "today_goal_pct",
    "today_goal_amount", "today_anchor_mode", "today_anchor_key", "today_anchor_label",
    "today_anchor_time", "today_anchor_set_at", "today_stop_loss_gross_only",
    "today_cash_adjustment",
    "day_locked_date",
    "trade_ledger",
    "trade_resolutions",
    "trade_emotions",
    "auto_sync_on_boot",
    "insight_chase_window",
    "insight_high_price_cents",
    "insight_stop_streak",
    "state_backup_last_at",
    "gsheet_url",
    "gsheet_autobackup",
    "gsheet_webapp_url",
    "gsheet_webapp_token",
]

GAME_RE = re.compile(r"\b(game|map)\s*[1-5]\b", re.I)

PROP_KW = (
    "first blood", "first tower", "first dragon", "first baron", "kills", "towers",
    "tower", "dragon", "baron", "handicap", "spread", "total", "over/under", "o/u",
    "correct score", "map score", "series score", "exact score", "duration",
    "objectives", "inhibitor", "first to", "player props",
)

MAIN_KW = (
    "moneyline", "match winner", "match-winner", "series winner", "series-winner",
    "overall winner", "event winner", "to win", "will win", "match result", "series result",
)

_PMHIST_RANGES = {
    "1H": ("1h", 1),
    "6H": ("6h", 5),
    "1D": ("1d", 15),
    "1W": ("1w", 60),
    "1M": ("1m", 180),
    "MAX": ("max", 720),
}

KST = timezone(timedelta(hours=9))

QF_DEF = [("today", "오늘", "Today"), ("yday", "어제", "Yesterday"),
          ("d7", "최근 7일", "Last 7d"), ("month", "이번 달", "This month"),
          ("all", "전체", "All"), ("custom", "직접 선택", "Custom")]

QF_LABEL = {code: (ko, en) for code, ko, en in QF_DEF}

MIN_SHARES = 1.0   # 이 미만 수량은 dust로 간주

MIN_VALUE = 1.0    # 평가금 $1 미만은 숨김

__all__ = [
    'DEFAULTS',
    'DEFAULT_PROFILE',
    'GAME_RE',
    'KST',
    'LOCAL_STATE_PATH',
    'MAIN_KW',
    'MIN_SHARES',
    'MIN_VALUE',
    'PERSIST_KEYS',
    'PROP_KW',
    'QF_DEF',
    'QF_LABEL',
    '_PMHIST_RANGES',
]
