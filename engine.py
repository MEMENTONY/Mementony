# engine.py - auto-extracted from streamlit_app.py (behavior-preserving)
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

from config import *
from state import *
from ui import *

def price_zone(price):
    if price >= 99: return t("99¢ 매수 금지", "Do not buy at 99¢"), "b", -32, t("99¢는 사는 가격이 아니라 파는 가격입니다.", "99¢ is a selling price, not a buying price.")
    if price >= 95: return t("상환 스캘핑", "Redemption scalping"), "b", -24, t("95~98¢는 거의 상환 스캘핑입니다. 고액 신규 매수 금지에 가깝습니다.", "95–98¢ is near-redemption scalping. Avoid large new buys.")
    if price >= 90: return t("신규매수 비추천", "New buys discouraged"), "b", -18, t("90~95¢는 신규 매수 비추천 구간입니다.", "90–95¢ is a discouraged range for new buys.")
    if price >= 85: return t("매우 신중", "Be very cautious"), "w", -10, t("85~90¢는 신규 진입을 매우 신중하게 봐야 합니다.", "85–90¢ requires extra caution.")
    if price >= 80: return t("익절 고려", "Take-profit zone"), "w", -6, t("80~85¢는 신규 매수보다 익절 고려 구간입니다.", "80–85¢ favors taking profit over new buys.")
    if 2 <= price <= 5: return t("초저가 Bounce", "Deep-value bounce"), "w", -12, t("2~5¢ Bounce Trade는 소액 전용입니다.", "2–5¢ bounce trades are small-size only.")
    if price < 2: return t("복권형", "Lottery ticket"), "b", -20, t("2¢ 미만은 거의 복권형 가격입니다.", "Below 2¢ is essentially a lottery ticket.")
    if price <= 20: return t("고변동", "High volatility"), "w", -4, t("저가 구간은 변동성이 큽니다. 소액만 적합합니다.", "Low prices are volatile. Small size only.")
    return t("정상 구간", "Normal range"), "g", 0, t("가격 구간 자체는 과도한 위험 신호가 크지 않습니다.", "No major risk signal from price alone.")

def purpose_options():
    return [t("경기승리 / 만기 보유", "Win bet / hold to expiry"),
            t("경기 시작 전 가격 상승 노림", "Pre-game price rise"),
            t("반반 경기 쏠림 이용 / 중간 익절", "Crowd-tilt / mid take-profit"),
            t("역배 / Bounce Trade", "Underdog / bounce trade"),
            t("99¢ 상환 스캘핑", "99¢ redemption scalp"),
            t("뉴스/이벤트 선반영", "News/event front-run")]

def purpose_rule(p):
    table = [
        (1.00, 0,  t("실제 승률 추정이 핵심인 기본 승리 베팅입니다.", "Standard win bet; true win-rate matters most.")),
        (0.70, -6, t("시장 심리와 타이밍이 중요합니다. 익절 기준을 먼저 정해야 합니다.", "Sentiment & timing; set a take-profit rule first.")),
        (0.60, -8, t("경기력이 아니라 시장 쏠림을 노리는 거래입니다.", "Targets crowd tilt, not team strength.")),
        (0.35, -13, t("역배와 bounce는 소액 전용입니다. 손실 제한이 핵심입니다.", "Underdog/bounce is small-size only.")),
        (0.20, -25, t("작은 수익을 위해 큰 금액을 위험에 노출하는 구조입니다.", "Risks a lot for very little.")),
        (0.50, -12, t("조건문과 resolution 기준 확인이 중요합니다.", "Check resolution criteria carefully.")),
    ]
    opts = purpose_options()
    try: return table[opts.index(p)]
    except ValueError: return (1.0, 0, t("일반 베팅으로 계산합니다.", "Calculated as a standard bet."))

def market_type_options():
    return ["Match Moneyline", "Game Winner", "Correct Score",
            t("정치 선거", "Political election"), t("뉴스/이벤트", "News / event"),
            t("99¢ 상환 스캘핑", "99¢ redemption scalp"), "2~5¢ Bounce Trade"]

def market_type_rule(m):
    table = [
        (1.00, 0,  t("가장 기본적인 시장입니다.", "The most standard market.")),
        (0.50, -10, t("단판 시장은 변동성이 커서 추천 금액을 50% 줄입니다.", "Single-game markets cut suggested size by 50%.")),
        (0.25, -25, t("Correct Score는 맞히기 어렵습니다.", "Correct Score is hard to hit.")),
        (0.50, -12, t("결과 기준과 이의제기 가능성을 확인해야 합니다.", "Verify result criteria & dispute risk.")),
        (0.50, -12, t("조건문과 resolution 기준 확인이 필수입니다.", "Resolution wording check is mandatory.")),
        (0.20, -25, t("고가 상환 스캘핑은 고액 금지입니다.", "No large size for redemption scalps.")),
        (0.20, -18, t("초저가 bounce는 소액 전용입니다.", "Deep-value bounce is small-size only.")),
    ]
    opts = market_type_options()
    try: return table[opts.index(m)]
    except ValueError: return (1.0, 0, t("일반 시장으로 계산합니다.", "Standard market."))

def size_thresholds():
    p = profile()
    g = max(p["max_pct"], 0.5)
    return g, g * 1.5, g * 2.5, max(p["block_pct"], g * 1.6)

def size_rule(pct):
    g, c1, c2, blk = size_thresholds()
    if pct >= 50: return t("시스템 실패", "System failure"), "b", -100, t("계좌 생존 리스크입니다. 50% 이상 노출은 절대 금지입니다.", "Account-survival risk. Never expose 50%+.")
    if pct >= blk: return t("진입 금지", "Entry blocked"), "b", -85, t(f"내 기준 진입 금지선({blk:.0f}%)을 넘었습니다.", f"Above your no-entry line ({blk:.0f}%).")
    if pct >= c2: return t("매우 위험", "Very risky"), "b", -38, t(f"내 적정 비율({g:.0f}%)의 2.5배가 넘는 포지션입니다.", f"Over 2.5× your comfort ratio ({g:.0f}%).")
    if pct >= c1: return t("위험", "Risky"), "w", -20, t(f"내 적정 비율({g:.0f}%)을 크게 넘었습니다.", f"Well above your comfort ratio ({g:.0f}%).")
    if pct > g: return t("주의", "Caution"), "w", -8, t(f"내 적정 비율({g:.0f}%)을 약간 넘었습니다.", f"Slightly above your comfort ratio ({g:.0f}%).")
    return t("정상", "Normal"), "g", 5, t(f"내 적정 비율({g:.0f}%) 이내입니다.", f"Within your comfort ratio ({g:.0f}%).")

def exposure_rule(pct):
    g, c1, c2, blk = size_thresholds()
    if pct >= blk: return t("중복 노출 금지", "Stacked exposure blocked"), "b", -60, t(f"같은 경기·방향 총 노출이 진입 금지선({blk:.0f}%)을 넘었습니다.", f"Same-game/side exposure above your no-entry line ({blk:.0f}%).")
    if pct >= c2: return t("중복 노출 위험", "Stacked exposure risky"), "b", -35, t("같은 경기·방향 총 노출이 큽니다.", "Stacked exposure is large.")
    if pct >= c1: return t("중복 노출 주의", "Stacked exposure caution"), "w", -12, t("같은 경기·방향 노출이 쌓이고 있습니다.", "Exposure is stacking up.")
    return t("정상", "Normal"), "g", 0, t("중복 노출은 관리 가능한 범위입니다.", "Stacked exposure is manageable.")

def confidence_options():
    return [t("관찰용", "Watching"), t("낮은 확신", "Low conviction"), t("중간 확신", "Medium"),
            t("높은 확신", "High conviction"), t("초고확신", "Very high")]

def confidence_caps():
    el = profile()["emotional_limit"]
    return [el * .3, el * .5, el * 1.0, el * 1.4, el * 1.4]

def portfolio_caps(bankroll):
    g = profile()["max_pct"] / 100
    return [bankroll * g * .3, bankroll * g * .5, bankroll * g * 1.0, bankroll * g * 1.3, bankroll * g * 1.5]

def effective_bankroll():
    pos_value = sum((p.get("shares", 0) or 0) * ((p.get("cur", 0) or 0) / 100) for p in st.session_state.portfolio)
    total = st.session_state.cash + pos_value
    return total if total > 0 else profile()["assets"]

def calculate_entry(d):
    prof = profile()
    current_price, fair_price = d["current_price"], d["fair_price"]
    stake, bankroll = d["stake"], d["bankroll"]
    edge = fair_price - current_price
    position_pct = stake / bankroll * 100 if bankroll else 0

    zone_label, zone_kind, zone_pen, zone_note = price_zone(current_price)
    p_mult, p_pen, p_note = purpose_rule(d["purpose"])
    m_mult, m_pen, m_note = market_type_rule(d["market_type"])
    size_label, size_kind, size_pen, size_note = size_rule(position_pct)

    el = prof["emotional_limit"]
    try:
        ci = confidence_options().index(d["confidence"])
    except ValueError:
        ci = 2
    base_cap = min(confidence_caps()[ci], portfolio_caps(bankroll)[ci], el)
    rec_cap = base_cap * p_mult * m_mult
    if d["fomo_count"] >= 1:
        rec_cap *= 0.5

    # --- Loss-adaptive shrink: the more you've lost today (and on a losing streak),
    # the smaller the cap -- so you cannot up-size a bet to "win it back". ---
    loss_adapt = max(0.0, min(1.0, d.get("loss_adapt_factor", 1.0)))
    rec_cap *= loss_adapt

    # --- Kelly stake sizing (fractional, conservative) ---
    # For a binary YES share bought at current_price cents, the full-Kelly fraction
    # of bankroll is edge / (100 - price); it is naturally bounded to [0, 1] because
    # fair_price <= 100. We scale it down by confidence (never above 1/2 Kelly) and
    # never suggest more than the existing risk cap -- Kelly proposes, guardrails dispose.
    kelly_upside = 100.0 - current_price
    kelly_full = max(0.0, min(1.0, edge / kelly_upside)) if kelly_upside > 0 else 0.0
    kelly_fraction = [0.10, 0.15, 0.25, 0.40, 0.50][ci]
    kelly_stake_raw = kelly_full * kelly_fraction * bankroll
    kelly_stake = min(kelly_stake_raw, rec_cap) if kelly_stake_raw > 0 else 0.0
    if kelly_full <= 0:
        kelly_kind, kelly_label, kelly_note = "i", t("엣지 없음", "No edge"), t(
            "적정가가 현재가 이하라 켈리 기준 베팅액은 0입니다.",
            "Fair price is at or below market, so Kelly suggests no bet.")
    elif stake > kelly_stake * 1.5:
        kelly_kind, kelly_label, kelly_note = "w", t("켈리 초과", "Above Kelly"), t(
            f"투자금이 켈리 추천({money(kelly_stake)})의 1.5배를 넘습니다 — 변동성이 큽니다.",
            f"Stake is over 1.5x the Kelly size ({money(kelly_stake)}) — higher variance.")
    elif stake < kelly_stake * 0.5:
        kelly_kind, kelly_label, kelly_note = "i", t("켈리 미만", "Below Kelly"), t(
            f"켈리 추천({money(kelly_stake)})보다 보수적입니다 — 안전하지만 성장은 더딥니다.",
            f"More conservative than Kelly ({money(kelly_stake)}) — safe but slower growth.")
    else:
        kelly_kind, kelly_label, kelly_note = "g", t("켈리 부합", "Near Kelly"), t(
            f"투자금이 켈리 추천({money(kelly_stake)})과 비슷합니다.",
            f"Stake is near the Kelly size ({money(kelly_stake)}).")

    sys_amt, warn_amt = el * 4, el * 2
    if stake >= sys_amt: cap_label, cap_kind, cap_pen = t(f"감정 한도 4배 초과 — 시스템 실패", "4× emotional cap — system failure"), "b", -90
    elif stake >= warn_amt: cap_label, cap_kind, cap_pen = t(f"감정 한도 2배 초과 — 강한 경고", "2× emotional cap — strong warning"), "b", -50
    elif stake > rec_cap * 1.2: cap_label, cap_kind, cap_pen = t("추천 상한선 초과", "Above suggested cap"), "b", -32
    elif stake > rec_cap: cap_label, cap_kind, cap_pen = t("상한선 소폭 초과", "Slightly above cap"), "w", -12
    else: cap_label, cap_kind, cap_pen = t("상한선 이내", "Within cap"), "g", 0

    dup_total = d["duplicate_ml"] + d["duplicate_game"] + d["duplicate_side"] + stake
    dup_pct = dup_total / bankroll * 100 if bankroll else 0
    exp_label, exp_kind, exp_pen, exp_note = exposure_rule(dup_pct)

    if d["fomo_count"] >= 3:
        fomo_label, fomo_kind, fomo_pen = t("감정 진입 금지", "Emotional — blocked"), "b", -75
        fomo_note = t("감정 체크 3개 이상입니다. 신규 진입 금지로 봐야 합니다.", "3+ emotion checks. Treat as no-entry.")
    elif d["fomo_count"] >= 1:
        fomo_label, fomo_kind, fomo_pen = t("감정 위험", "Emotional risk"), "w", -20
        fomo_note = t("감정 체크가 있습니다. 추천 금액을 50% 줄였습니다.", "Emotion checks present. Size halved.")
    else:
        fomo_label, fomo_kind, fomo_pen = t("정상", "Normal"), "g", 0
        fomo_note = t("감정 체크가 없습니다.", "No emotion checks.")

    if d["previous_good_price"] > 0:
        gap = current_price - d["previous_good_price"]
        if gap >= 30: chase = (t("FOMO 추격", "FOMO chase"), "b", -25, t("처음 봤던 가격보다 30¢ 이상 올랐습니다.", "Up 30¢+ since first sighting."))
        elif gap >= 15: chase = (t("추격 위험", "Chase risk"), "w", -13, t("처음 봤던 가격보다 많이 올랐습니다.", "Up a lot since first sighting."))
        elif gap >= 5: chase = (t("조금 상승", "Slightly up"), "w", -5, t("처음 봤던 가격보다 조금 올랐습니다.", "Slightly up since first sighting."))
        else: chase = (t("추격 아님", "Not a chase"), "g", 5, t("추격 위험은 크지 않습니다.", "Chase risk is small."))
    else:
        chase = (t("미입력", "Not entered"), "i", 0, t("처음 봤던 저평가 가격을 입력하지 않았습니다.", "First-seen price not provided."))
    chase_label, chase_kind, chase_pen, chase_note = chase

    bk = d["bookmaker_prob"]
    my_vs_poly = fair_price - current_price
    book_vs_poly = bk - current_price if bk > 0 else 0
    my_vs_book = fair_price - bk if bk > 0 else 0
    if bk <= 0: book = (t("북메이커 미입력", "No bookmaker input"), "i", 0, t("북메이커 승률을 입력하면 공식 배당과의 괴리를 볼 수 있습니다.", "Enter a bookmaker probability to compare."))
    elif my_vs_book >= 10: book = (t("과신 재검토", "Re-check overconfidence"), "b", -12, t("내 적정가가 북메이커보다 10%p 이상 높습니다.", "Your fair price is 10pp+ above the book."))
    elif book_vs_poly >= 5: book = (t("외부배당도 저평가", "Cheap vs books too"), "g", 6, t("북메이커 기준으로도 가격이 싸 보입니다.", "Cheap even vs bookmakers."))
    elif book_vs_poly <= -5: book = (t("외부배당 기준 비쌈", "Expensive vs books"), "w", -8, t("북메이커 기준으로는 비싼 편입니다.", "Expensive vs bookmakers."))
    else: book = (t("큰 차이 없음", "No big gap"), "i", 0, t("북메이커와 큰 차이가 없습니다.", "No large gap vs books."))
    book_label, book_kind, book_pen, book_note = book

    value_score = clamp(50 + edge * 2.2 + zone_pen + p_pen + m_pen + chase_pen + book_pen)
    final_score = clamp(value_score + size_pen + exp_pen + fomo_pen + cap_pen)

    g, c1, c2, blk = size_thresholds()
    hard_stop = None
    if d.get("day_locked"): hard_stop = t("오늘 베팅 잠금 — 신규 진입 차단", "Day locked — no new entries")
    elif d.get("loss_limit_hit"): hard_stop = t("오늘 손실 한도 도달 — 신규 진입 금지", "Daily loss limit hit — stop for today")
    elif d.get("tilt_level") == "stop": hard_stop = t(f"연속 손실 {int(d.get('tilt_streak', 3))}회 — 쿨다운 필요", f"{int(d.get('tilt_streak', 3))} losses in a row — cool down")
    elif position_pct >= 50: hard_stop = t("시스템 실패 — 계좌 생존 리스크", "System failure — survival risk")
    elif stake >= sys_amt: hard_stop = t("시스템 실패 — 감정 한도 4배", "System failure — 4× emotional cap")
    elif position_pct >= blk: hard_stop = t(f"진입 금지 — 내 한도 {blk:.0f}% 초과", f"Entry blocked — over your {blk:.0f}% line")
    elif dup_pct >= blk: hard_stop = t(f"진입 금지 — 중복 노출 {blk:.0f}% 초과", f"Entry blocked — stacked over {blk:.0f}%")
    elif d["fomo_count"] >= 3: hard_stop = t("진입 금지 — 감정 배팅 위험", "Entry blocked — emotional betting")

    if hard_stop: decision, level = hard_stop, "bad"
    elif final_score >= 75: decision, level = t("진입 적절", "Good entry"), "good"
    elif final_score >= 60: decision, level = t("소액 진입 가능", "Small entry OK"), "warn"
    elif final_score >= 45: decision, level = t("관망 우선", "Wait and watch"), "warn"
    else: decision, level = t("진입 부적절", "Poor entry"), "bad"

    shares = stake / (current_price / 100)
    win_profit = shares - stake
    target_profit = shares * (d["target_price"] / 100) - stake
    stop_loss_amt = stake - shares * (d["stop_price"] / 100)
    rr = target_profit / stop_loss_amt if stop_loss_amt > 0 else 0

    if target_profit > 0 and stop_loss_amt > 0:
        if stop_loss_amt > target_profit: rr_text, rr_kind = t(f"손절 손실이 목표 수익보다 약 {stop_loss_amt/target_profit:.1f}배 큽니다.", f"Stop-loss ≈ {stop_loss_amt/target_profit:.1f}× the target."), "b"
        elif target_profit >= stop_loss_amt * 1.5: rr_text, rr_kind = t(f"목표 수익이 손절 손실보다 약 {target_profit/stop_loss_amt:.1f}배 큽니다.", f"Target ≈ {target_profit/stop_loss_amt:.1f}× the stop."), "g"
        else: rr_text, rr_kind = t(f"손익비 {rr:.2f}:1 — 큰 우위는 아닙니다.", f"R:R {rr:.2f}:1 — not a big edge."), "w"
    else:
        rr_text, rr_kind = t("목표가 또는 손절가를 다시 확인하세요.", "Re-check target or stop."), "w"

    current_value = shares * (current_price / 100)
    additional_to_100 = shares - current_value
    high_warn = ""
    if current_price >= 90:
        high_warn = t(f"현재부터 100¢까지 추가수익은 {money(additional_to_100)}뿐입니다. 틀리면 {money(current_value)}를 잃을 수 있습니다.",
                      f"Only {money(additional_to_100)} left to 100¢, but a miss costs {money(current_value)}.")
    if current_price >= 97:
        high_warn += t(" 97~99¢ 고액 매수는 작은 수익을 위해 큰 금액을 위험에 노출합니다.", " Large buys at 97–99¢ risk a lot for little.")

    if edge >= 10: edge_reason = ("g", t(f"가격 메리트 좋음 — 적정가가 현재가보다 {edge:.1f}¢ 높습니다.", f"Good value — fair price {edge:.1f}¢ above market."))
    elif edge >= 5: edge_reason = ("w", t(f"가격 메리트 약간 — edge {edge:.1f}¢.", f"Some value — edge {edge:.1f}¢."))
    elif edge < 0: edge_reason = ("b", t(f"가격 메리트 없음 — 현재가가 {abs(edge):.1f}¢ 더 비쌉니다.", f"No value — market {abs(edge):.1f}¢ above fair."))
    else: edge_reason = ("w", t(f"가격 메리트 작음 — edge {edge:.1f}¢.", f"Thin value — edge {edge:.1f}¢."))

    reasons = [edge_reason,
               (size_kind, t(f"포지션 크기 — 총자산의 {position_pct:.1f}% · {size_label}", f"Size — {position_pct:.1f}% of portfolio · {size_label}")),
               (cap_kind, t(f"추천 상한선 {money(rec_cap)} · 투자금 {money(stake)} — {cap_label}", f"Cap {money(rec_cap)} · stake {money(stake)} — {cap_label}")),
               (zone_kind, t(f"가격 구간 — {zone_label}. {zone_note}", f"Price zone — {zone_label}. {zone_note}"))]

    _tlevel = d.get("tilt_level", "ok")
    _tstreak = int(d.get("tilt_streak", 0) or 0)
    if _tlevel == "stop":
        tilt_kind, tilt_note = "b", t(f"최근 {_tstreak}연속 손실 — 지금은 쉬어야 할 때입니다.", f"{_tstreak} losses in a row — time to step away.")
    elif _tlevel == "warn":
        tilt_kind, tilt_note = "w", t(f"최근 {_tstreak}연속 손실 — 추격 베팅을 조심하세요.", f"{_tstreak} losses in a row — beware loss-chasing.")
    else:
        tilt_kind, tilt_note = "i", ""

    if loss_adapt < 0.999:
        adapt_kind, adapt_note = "w", t(f"오늘 손실로 추천 상한이 {(1 - loss_adapt) * 100:.0f}% 축소됨 — 만회용 큰 베팅을 막습니다.", f"Cap cut {(1 - loss_adapt) * 100:.0f}% after today's losses — blocks revenge sizing.")
    else:
        adapt_kind, adapt_note = "i", ""

    return {**d, "edge": edge, "position_pct": position_pct,
            "duplicate_total": dup_total, "duplicate_pct": dup_pct, "rec_cap": rec_cap,
            "value_score": round(value_score, 1), "final_score": round(final_score, 1),
            "decision": decision, "level": level, "shares": shares,
            "win_profit": win_profit, "target_profit": target_profit,
            "stop_loss_amt": stop_loss_amt, "rr": rr, "rr_text": rr_text, "rr_kind": rr_kind,
            "current_value": current_value, "additional_to_100": additional_to_100,
            "high_warn": high_warn,
            "zone_label": zone_label, "zone_kind": zone_kind, "zone_note": zone_note,
            "purpose_note": p_note, "market_type_note": m_note,
            "size_label": size_label, "size_kind": size_kind, "size_note": size_note,
            "cap_label": cap_label, "cap_kind": cap_kind,
            "exp_label": exp_label, "exp_kind": exp_kind, "exp_note": exp_note,
            "fomo_label": fomo_label, "fomo_kind": fomo_kind, "fomo_note": fomo_note,
            "chase_label": chase_label, "chase_kind": chase_kind, "chase_note": chase_note,
            "book_label": book_label, "book_kind": book_kind, "book_note": book_note,
            "my_vs_poly": my_vs_poly, "book_vs_poly": book_vs_poly, "my_vs_book": my_vs_book,
            "kelly_full": kelly_full, "kelly_fraction": kelly_fraction,
            "kelly_stake": kelly_stake, "kelly_stake_raw": kelly_stake_raw,
            "kelly_label": kelly_label, "kelly_kind": kelly_kind, "kelly_note": kelly_note,
            "tilt_kind": tilt_kind, "tilt_note": tilt_note,
            "adapt_kind": adapt_kind, "adapt_note": adapt_note, "loss_adapt": loss_adapt,
            "reasons": reasons}

def partial_rows(shares, price_cent, investment):
    pdec = price_cent / 100
    rows, need = [], None
    if shares > 0 and pdec > 0:
        need = investment / (shares * pdec) * 100
    for ratio in [25, 50, 70, 80, 90, 100]:
        ss = shares * ratio / 100
        rec = ss * pdec
        rem = shares - ss
        rows.append({
            t("매도 비율", "Sell %"): f"{ratio}%",
            t("매도 수량", "Shares sold"): round(ss, 2),
            t("회수금", "Recovered"): money(rec),
            t("원금 대비 확정손익", "Locked P&L"): signed_money(rec - investment),
            t("남은 수량", "Shares left"): round(rem, 2),
            t("남은 평가금", "Remaining value"): money(rem * pdec),
            t("100¢ 추가수익", "Extra at 100¢"): signed_money(rem * (1 - pdec)),
        })
    return rows, need

def infer_market_category(url="", name=""):
    s = f"{url or ''} {name or ''}".lower()
    if any(x in s for x in ["/sports/", "mlb", "nba", "nfl", "nhl", "soccer", "ufc", "tennis", "baseball", "basketball"]):
        return t("일반 스포츠", "Sports")
    if any(x in s for x in ["lol", "lck", "lpl", "valorant", "cs2", "dota", "esports"]):
        return t("e스포츠", "Esports")
    if any(x in s for x in ["election", "politic", "president", "mayor", "선거"]):
        return t("정치", "Politics")
    if any(x in s for x in ["crypto", "bitcoin", "btc", "ethereum", "eth", "solana", "sol"]):
        return t("크립토", "Crypto")
    if any(x in s for x in ["news", "event"]):
        return t("뉴스·이벤트", "News / events")
    return t("기타", "Other")

def infer_market_subcategory(url="", name=""):
    s = f"{url or ''} {name or ''}".lower()
    if "mlb" in s or "baseball" in s:
        return t("야구", "Baseball")
    if "nba" in s or "basketball" in s:
        return t("농구", "Basketball")
    if "nfl" in s or "football" in s:
        return t("미식축구", "Football")
    if "soccer" in s:
        return t("축구", "Soccer")
    if "tennis" in s:
        return t("테니스", "Tennis")
    if "ufc" in s or "mma" in s:
        return "UFC/MMA"
    if "lol" in s or "lck" in s or "lpl" in s:
        return "LoL"
    return t("기타", "Other")

def _safe_float(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default

def safe_trade_float(x, default=0.0):
    try:
        if x is None or x == "":
            return float(default)
        return float(x)
    except Exception:
        return float(default)

def _norm_price_cent(p):
    p = safe_trade_float(p)
    return round(p * 100, 2) if 0 < p <= 1 else round(p, 2)

def parse_trade_datetime(tr):
    """Return a KST datetime from normalized auto_trades or raw-like activity rows."""
    if not isinstance(tr, dict):
        return None
    raw = tr.get("d") or tr.get("timestamp") or tr.get("createdAt") or tr.get("created_at") or tr.get("date")
    if raw is None:
        return None
    try:
        n = float(raw)
        if n > 1e12:  # milliseconds
            n /= 1000.0
        if n > 1e9:   # seconds epoch
            return datetime.fromtimestamp(n, tz=timezone.utc).astimezone(KST)
    except (TypeError, ValueError):
        pass
    try:
        s0 = str(raw).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s0)
        if dt.tzinfo is None:
            # normalize_activity already stores KST-like ISO without tz; treat it as KST.
            dt = dt.replace(tzinfo=KST)
        return dt.astimezone(KST)
    except Exception:
        return None

def sort_trades_newest_first(trades):
    """Newest first; rows with unknown datetime go last."""
    def _key(tr):
        dt = parse_trade_datetime(tr)
        if dt is None:
            return (1, 0.0)
        return (0, -dt.timestamp())
    return sorted(list(trades or []), key=_key)

def filter_trades_by_date(auto_trades, start_date, end_date):
    """Filter imported activity by KST date range and return newest first."""
    keep, unknown = [], 0
    has_range = bool(start_date or end_date)
    for tr in auto_trades or []:
        dt = parse_trade_datetime(tr)
        if dt is None:
            if has_range:
                unknown += 1
                continue
            keep.append(tr)
            continue
        d0 = dt.date()
        if start_date and d0 < start_date:
            continue
        if end_date and d0 > end_date:
            continue
        keep.append(tr)
    return sort_trades_newest_first(keep), unknown

def _trade_preset(qf, today):
    if qf == "today":
        return today, today
    if qf == "yday":
        yday = today - timedelta(days=1)
        return yday, yday
    if qf == "d7":
        return today - timedelta(days=6), today
    if qf == "month":
        return today.replace(day=1), today
    return None, None

def group_auto_trades_for_pnl(auto_trades):
    """Group fill-level trades by market/outcome/token and estimate weighted average P&L."""
    groups = {}
    for tr in sort_trades_newest_first(auto_trades or []):
        if not isinstance(tr, dict):
            continue
        title = tr.get("title") or tr.get("market") or tr.get("name") or tr.get("slug") or "Unknown"
        outcome = tr.get("outcome") or tr.get("side_outcome") or ""
        tok = tr.get("token_id") or tr.get("asset") or tr.get("assetId") or ""
        key = str(tok).strip() if tok else f"{title}|{outcome}"
        side = str(tr.get("side") or tr.get("type") or "").upper()
        price = _norm_price_cent(tr.get("price"))
        size = safe_trade_float(tr.get("size") or tr.get("shares"))
        usdc = tr.get("usdcSize", tr.get("usdValue", tr.get("amount", None)))
        cash = safe_trade_float(usdc) if usdc is not None else size * (price / 100)
        if size <= 0 and cash <= 0:
            continue
        g = groups.setdefault(key, {
            "market": title, "outcome": outcome, "token_id": tok,
            "bought_shares": 0.0, "sold_shares": 0.0,
            "buy_cost": 0.0, "sell_proceeds": 0.0, "fills": 0,
            "latest_dt": None, "first_dt": None,
        })
        g["fills"] += 1
        dt = parse_trade_datetime(tr)
        if dt is not None and (g["latest_dt"] is None or dt > g["latest_dt"]):
            g["latest_dt"] = dt
        if dt is not None and (g["first_dt"] is None or dt < g["first_dt"]):
            g["first_dt"] = dt
        if side.startswith("B"):
            g["bought_shares"] += size
            g["buy_cost"] += cash
        elif side.startswith("S"):
            g["sold_shares"] += size
            g["sell_proceeds"] += cash
    rows = []
    for key, g in groups.items():
        bs, ss = g["bought_shares"], g["sold_shares"]
        avg_buy = (g["buy_cost"] / bs) if bs > 0 else 0.0
        avg_sell = (g["sell_proceeds"] / ss) if ss > 0 else 0.0
        oversold = ss > bs + 1e-6
        matched_buy_cost = avg_buy * min(ss, bs)
        realized = g["sell_proceeds"] - matched_buy_cost
        remaining = max(bs - ss, 0.0)
        remaining_cost = avg_buy * remaining
        if oversold:
            status = t("확인 필요(매도>매수)", "Verify (sold>bought)")
        elif remaining > 1e-6 and ss > 0:
            status = t("일부 청산", "Partly closed")
        elif remaining > 1e-6:
            status = t("보유 중", "Open")
        else:
            status = t("청산 완료", "Closed")
        latest_dt = g.get("latest_dt")
        first_dt = g.get("first_dt")
        rows.append({
            "key": key, "market": g["market"], "outcome": g["outcome"], "token_id": g["token_id"],
            "first_dt": first_dt.isoformat(timespec="minutes") if first_dt else "",
            "_first_ts": first_dt.timestamp() if first_dt else -1,
            "avg_buy_price": round(avg_buy * 100, 2) if avg_buy <= 1 and avg_buy > 0 else round(avg_buy, 2),
            "avg_sell_price": round(avg_sell * 100, 2) if avg_sell <= 1 and avg_sell > 0 else round(avg_sell, 2),
            "bought_shares": round(bs, 2), "sold_shares": round(ss, 2),
            "buy_cost": round(g["buy_cost"], 2), "sell_proceeds": round(g["sell_proceeds"], 2),
            "realized_pnl": None if oversold else round(realized, 2),
            "remaining_shares": round(remaining, 2), "remaining_cost": round(remaining_cost, 2),
            "status": status, "fills": g["fills"],
            "latest_dt": latest_dt.isoformat(timespec="minutes") if latest_dt else "",
            "_latest_ts": latest_dt.timestamp() if latest_dt else -1,
        })
    return sorted(rows, key=lambda r: (r.get("_latest_ts", -1), abs(r.get("realized_pnl") or 0), r.get("buy_cost", 0)), reverse=True)

def _norm_trade_text(v):
    '''Normalize market/outcome text for settlement-event matching.'''
    s = str(v or "")
    s = re.sub(r"\[([^\]]+)\]\(https?://[^)\s]+\)", r"\1", s)
    s = re.sub(r"^icon\s+for\s+", "", s, flags=re.I).strip()
    s = re.sub(r"\s+", " ", s.strip().lower())
    return "".join(ch for ch in s if ch.isalnum())

def _parse_event_amount(v):
    '''Return signed USD amount from '+$1.23', '$1.23', '-$1.23'; None for '-' / unknown.'''
    s = str(v or "").strip()
    if not s or s == "-":
        return None
    m = re.search(r"([+\-]?)\s*\$\s*([\d,]+(?:\.\d+)?)", s)
    if not m:
        return None
    amt = safe_trade_float(m.group(2).replace(",", ""), 0.0)
    return -amt if m.group(1) == "-" else amt

def _event_kind(ev):
    raw = f"{ev.get('result', '')} {ev.get('type', '')} {ev.get('label', '')}".lower()
    if any(k in raw for k in ("손실", "loss", "lost")):
        return "loss"
    if any(k in raw for k in ("상환", "수익", "redeem", "redemption", "claim", "claimed", "profit", "won", "win")):
        return "redeem"
    if any(k in raw for k in ("정산", "settle", "settled")):
        return "settled"
    return "event"

def _match_event_to_group(ev, rows):
    '''Find the best open group for one recognized settlement/loss event.'''
    ev_market = _norm_trade_text(ev.get("name"))
    ev_outcome = _norm_trade_text(ev.get("outcome"))
    ev_shares = safe_trade_float(ev.get("shares"), 0.0)
    candidates = []
    for r in rows:
        remaining = safe_trade_float(r.get("remaining_shares"), 0.0)
        if remaining <= 1e-6 and not r.get("_adjusted"):
            continue
        r_market = _norm_trade_text(r.get("market"))
        r_outcome = _norm_trade_text(r.get("outcome"))
        if not ev_market or not r_market:
            continue
        market_match = (ev_market == r_market) or (ev_market in r_market) or (r_market in ev_market)
        outcome_match = (not ev_outcome) or (not r_outcome) or ev_outcome == r_outcome or ev_outcome in r_outcome or r_outcome in ev_outcome
        if not (market_match and outcome_match):
            continue
        score = 100 if ev_market == r_market else 70
        if ev_outcome and r_outcome and ev_outcome == r_outcome:
            score += 30
        if ev_shares > 0:
            share_basis = max(remaining, safe_trade_float(r.get("bought_shares"), 0.0))
            tolerance = max(0.25, share_basis * 0.03)
            remaining_tolerance = max(0.25, remaining * 0.03)
            diff = min(abs(ev_shares - share_basis), abs(ev_shares - remaining))
            if (remaining > 0 and abs(ev_shares - remaining) <= remaining_tolerance) or diff <= tolerance or remaining <= 1e-6:
                score += 50
            else:
                score -= min(45, diff)
        candidates.append((score, r))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best = candidates[0]
    if len(candidates) > 1 and best_score == candidates[1][0]:
        return None
    return best if best_score >= 80 else None

def link_settlement_events_to_trade_groups(rows, events):
    '''Attach recognized settlement/loss/redemption events to matching open trade groups.'''
    rows = [dict(r) for r in (rows or [])]
    events = events or []
    for ev in events:
        if isinstance(ev, dict):
            ev.pop("_linked_to", None)
            ev.pop("_linked_note", None)

    def _event_link_sort(ev):
        kind = _event_kind(ev) if isinstance(ev, dict) else "event"
        amount = _parse_event_amount(ev.get("amount")) if isinstance(ev, dict) else None
        dt = parse_trade_datetime(ev) if isinstance(ev, dict) else None
        # Cash settlement/redeem rows should establish recovered value before
        # dust loss rows from the same settled market are applied.
        priority = 0 if amount is not None and kind in ("redeem", "settled") else 1 if kind == "loss" else 2
        return (priority, -(dt.timestamp() if dt else 0.0))

    for ev in sorted([x for x in events if isinstance(x, dict)], key=_event_link_sort):
        if not isinstance(ev, dict):
            continue
        kind = _event_kind(ev)
        if kind not in ("loss", "redeem", "settled"):
            continue
        match = _match_event_to_group(ev, rows)
        if not match:
            continue
        event_amount = _parse_event_amount(ev.get("amount"))
        buy_cost = safe_trade_float(match.get("buy_cost"), 0.0)
        base_proceeds = safe_trade_float(match.get("sell_proceeds"), 0.0)
        current_effective = safe_trade_float(match.get("adjusted_effective_proceeds"), base_proceeds)
        if kind == "loss":
            note = t("손실 이벤트 자동 연결됨", "Loss event auto-linked")
            effective_proceeds = current_effective
        elif kind == "redeem":
            note = t("상환/수익 이벤트 자동 연결됨", "Redemption/profit event auto-linked")
            effective_proceeds = current_effective + (event_amount or 0.0)
        else:
            note = t("정산 이벤트 자동 연결됨", "Settlement event auto-linked")
            effective_proceeds = current_effective + (event_amount or 0.0)

        raw_event_shares = ev.get("shares")
        event_shares = safe_trade_float(raw_event_shares, 0.0)
        current_closed = safe_trade_float(match.get("adjusted_sold_shares"), safe_trade_float(match.get("sold_shares"), 0.0))
        current_remaining = safe_trade_float(match.get("adjusted_remaining_shares"), safe_trade_float(match.get("remaining_shares"), 0.0))
        if raw_event_shares is None:
            # Redemption rows often omit shares; they still settle the remaining position.
            event_close_shares = current_remaining
        elif event_shares <= 0:
            # Polymarket can emit a 0.0-share loss row for sub-1-share dust after redemption.
            # Link it for audit visibility, but never let it close or overwrite the real payout.
            event_close_shares = 0.0
            if kind == "loss":
                note = t("1주 미만 잔여 손실 이벤트 자동 연결됨", "Sub-1-share dust loss auto-linked")
        else:
            event_close_shares = min(current_remaining, event_shares)
        adjusted_sold_shares = current_closed + max(event_close_shares, 0.0)
        adjusted_remaining_shares = max(current_remaining - max(event_close_shares, 0.0), 0.0)
        adjusted_avg_exit = (effective_proceeds / adjusted_sold_shares * 100.0) if adjusted_sold_shares > 0 else 0.0
        adjusted_pnl = effective_proceeds - buy_cost
        event_dt = parse_trade_datetime(ev)
        latest_dt = parse_trade_datetime({"d": match.get("latest_dt")}) if match.get("latest_dt") else None
        display_latest_dt = match.get("latest_dt", "")
        latest_ts = safe_trade_float(match.get("_latest_ts"), -1.0)
        if event_dt is not None and (latest_dt is None or event_dt > latest_dt):
            display_latest_dt = event_dt.isoformat(timespec="minutes")
            latest_ts = event_dt.timestamp()
        linked_kinds = set(str(match.get("linked_event_type", "") or "").split("+")) - {""}
        linked_kinds.add(kind)
        if "redeem" in linked_kinds or (effective_proceeds > base_proceeds and effective_proceeds > 0):
            status = t("상환/수익 정산됨", "Redeemed / settled")
        elif "settled" in linked_kinds:
            status = t("정산됨", "Settled")
        else:
            status = t("손실 정산됨", "Settled as loss")
        prior_note = str(match.get("linked_event_note", "") or "")
        linked_note = f"{prior_note} · {note}" if prior_note and note not in prior_note else (prior_note or note)
        prior_amount = match.get("linked_event_amount")
        linked_amount = (safe_trade_float(prior_amount, 0.0) if prior_amount is not None else 0.0) + (event_amount or 0.0)
        prior_shares = safe_trade_float(match.get("linked_event_shares"), 0.0)
        linked_shares = prior_shares + max(event_close_shares, 0.0)
        match.update({
            "_adjusted": True,
            "linked_event_type": "+".join(sorted(linked_kinds)),
            "linked_event_amount": round(linked_amount, 2) if linked_amount else None,
            "linked_event_shares": round(linked_shares, 4) if linked_shares else None,
            "linked_event_time": display_latest_dt,
            "linked_event_note": linked_note,
            "latest_dt": display_latest_dt,
            "_latest_ts": latest_ts,
            "adjusted_status": status,
            "adjusted_realized_pnl": None if adjusted_pnl is None else round(adjusted_pnl, 2),
            "adjusted_effective_proceeds": round(effective_proceeds, 2),
            "adjusted_sold_shares": round(adjusted_sold_shares, 2),
            "adjusted_avg_exit_price": round(adjusted_avg_exit, 2),
            "adjusted_remaining_shares": round(adjusted_remaining_shares, 4),
            "adjusted_remaining_cost": 0.0 if adjusted_remaining_shares <= 1e-6 else round(safe_trade_float(match.get("remaining_cost"), 0.0) * (adjusted_remaining_shares / max(safe_trade_float(match.get("remaining_shares"), 0.0), adjusted_remaining_shares)), 2),
        })
        ev["_linked_to"] = match.get("key")
        ev["_linked_note"] = note
    return rows

def _display_realized(r):
    if r.get("_adjusted"):
        return r.get("adjusted_realized_pnl")
    return r.get("realized_pnl")

def _display_remaining_shares(r):
    return safe_trade_float(r.get("adjusted_remaining_shares"), 0.0) if r.get("_adjusted") else safe_trade_float(r.get("remaining_shares"), 0.0)

def _display_remaining_cost(r):
    return safe_trade_float(r.get("adjusted_remaining_cost"), 0.0) if r.get("_adjusted") else safe_trade_float(r.get("remaining_cost"), 0.0)

def _display_sold_shares(r):
    return safe_trade_float(r.get("adjusted_sold_shares"), 0.0) if r.get("_adjusted") else safe_trade_float(r.get("sold_shares"), 0.0)

def _display_exit_price(r):
    return safe_trade_float(r.get("adjusted_avg_exit_price"), 0.0) if r.get("_adjusted") else safe_trade_float(r.get("avg_sell_price"), 0.0)

def summarize_selected_trade_groups(rows, selected_keys):
    sel = [r for r in rows if r["key"] in selected_keys] or rows
    buy_cost = sum(safe_trade_float(r.get("buy_cost"), 0) for r in sel)
    proceeds = sum(safe_trade_float(r.get("adjusted_effective_proceeds", r.get("sell_proceeds")), 0) for r in sel)
    realized_vals = [_display_realized(r) for r in sel]
    realized = sum(safe_trade_float(v, 0) for v in realized_vals if v is not None)
    remaining = sum(_display_remaining_shares(r) for r in sel)
    remaining_cost = sum(_display_remaining_cost(r) for r in sel)
    any_unverified = any(v is None for v in realized_vals)
    return {"buy_cost": buy_cost, "sell_proceeds": proceeds, "realized_pnl": realized,
            "remaining_shares": remaining, "remaining_cost": remaining_cost, "unverified": any_unverified}

def _safe_review_id_part(v):
    s = re.sub(r"\s+", "_", str(v or "").strip().lower())
    s = re.sub(r"[^0-9a-zA-Z가-힣_\-.]+", "", s)
    return s[:80] or "item"

def _review_widget_key(prefix, review_id):
    return f"{prefix}_{_safe_review_id_part(review_id)}"

def make_review_id_from_trade_group(r, source="paste"):
    base = "|".join([
        str(source or "trade"), str(r.get("key", "")), str(r.get("market", "")),
        str(r.get("outcome", "")), str(r.get("token_id", "")),
        str(r.get("avg_buy_price", "")), str(r.get("avg_sell_price", "")),
        str(r.get("latest_dt", "")),
    ])
    return _safe_review_id_part(base)

def build_review_item_from_trade_group(r, source="paste"):
    rid = make_review_id_from_trade_group(r, source)
    pnl = _display_realized(r)
    return {
        "review_id": rid,
        "source": source,
        "market": r.get("market", ""),
        "outcome": r.get("outcome", ""),
        "token_id": r.get("token_id", ""),
        "avg_buy_price": r.get("avg_buy_price", 0.0),
        "avg_sell_price": r.get("avg_sell_price", 0.0),
        "bought_shares": r.get("bought_shares", 0.0),
        "sold_shares": r.get("sold_shares", 0.0),
        "buy_cost": r.get("buy_cost", 0.0),
        "sell_proceeds": r.get("adjusted_effective_proceeds", r.get("sell_proceeds", 0.0)),
        "estimated_realized_pnl": pnl,
        "remaining_shares": _display_remaining_shares(r),
        "remaining_cost": _display_remaining_cost(r),
        "status": r.get("adjusted_status") or r.get("status", ""),
        "linked_event_type": r.get("linked_event_type", ""),
        "linked_event_note": r.get("linked_event_note", ""),
        "linked_event_amount": r.get("linked_event_amount"),
        "linked_event_shares": r.get("linked_event_shares"),
        "linked_event_time": r.get("linked_event_time", ""),
        "latest_dt": r.get("latest_dt", ""),
        "created_at": datetime.now(KST).isoformat(timespec="seconds"),
    }

def add_review_items_from_trade_groups(selected_rows, source="paste"):
    existing = st.session_state.get("reviews", [])
    existing_ids = {str(x.get("review_id")) for x in existing if isinstance(x, dict)}
    added = 0
    for r in selected_rows or []:
        item = build_review_item_from_trade_group(r, source)
        if item["review_id"] in existing_ids:
            continue
        existing.append(item)
        existing_ids.add(item["review_id"])
        added += 1
    st.session_state.reviews = existing
    return added

def _norm_key(v):
    return "".join(ch.lower() for ch in str(v or "") if ch.isalnum())

def _trade_ts(tr):
    # Always return a consistent timezone-aware (KST) datetime so sorting and
    # "now - then" math never mix naive/aware values (which raises TypeError).
    dt = parse_trade_datetime(tr) if isinstance(tr, dict) else None
    return dt or datetime.min.replace(tzinfo=KST)

def link_position_to_trades(p, trades):
    """Connect one open position to imported activity using token/asset first, then market+outcome fallback."""
    if not trades:
        return {"matched_trades": 0, "buy_trades": 0, "sell_trades": 0, "buy_amount": 0.0,
                "sell_amount": 0.0, "last_trade": "", "last_buy": "", "recent_add": False,
                "repeat_entry": False, "avg_activity_price": 0.0, "match_note": t("거래내역 없음", "No imported activity")}

    pos_asset = str(p.get("asset") or p.get("token_id") or p.get("conditionId") or "").strip()
    pos_name = _norm_key(p.get("name"))
    pos_out = _norm_key(p.get("outcome"))
    matched = []
    for tr in trades:
        tr_asset = str(tr.get("asset") or tr.get("token_id") or "").strip()
        asset_match = pos_asset and tr_asset and pos_asset == tr_asset
        text_match = pos_name and pos_name in _norm_key(tr.get("name")) and (not pos_out or pos_out in _norm_key(tr.get("outcome")))
        if asset_match or text_match:
            matched.append(tr)

    matched = sorted(matched, key=_trade_ts)
    buys = [x for x in matched if str(x.get("side", "")).upper() == "BUY"]
    sells = [x for x in matched if str(x.get("side", "")).upper() == "SELL"]
    buy_amount = sum(_safe_float(x.get("amount"), 0) for x in buys)
    sell_amount = sum(_safe_float(x.get("amount"), 0) for x in sells)
    buy_shares = sum(_safe_float(x.get("shares"), 0) for x in buys)
    avg_px = (buy_amount / buy_shares * 100) if buy_shares else 0
    last_trade = matched[-1]["d"][:16] if matched else ""
    last_buy_dt = _trade_ts(buys[-1]) if buys else None
    recent_add = bool(last_buy_dt and (datetime.now(KST) - last_buy_dt).total_seconds() <= 60 * 60 * 24)
    repeat_entry = len(buys) >= 3
    note = t(f"연결 거래 {len(matched)}건 · 매수 {len(buys)}회 / 매도 {len(sells)}회",
             f"Linked {len(matched)} fills · {len(buys)} buys / {len(sells)} sells")
    if recent_add:
        note += t(" · 최근 24시간 추가매수", " · added in last 24h")
    if repeat_entry:
        note += t(" · 반복 진입 주의", " · repeated entry")
    return {"matched_trades": len(matched), "buy_trades": len(buys), "sell_trades": len(sells),
            "buy_amount": buy_amount, "sell_amount": sell_amount, "last_trade": last_trade,
            "last_buy": last_buy_dt.isoformat()[:16] if last_buy_dt else "", "recent_add": recent_add,
            "repeat_entry": repeat_entry, "avg_activity_price": avg_px, "match_note": note}

def is_open_position(it):
    """현재 실제 보유 중인 포지션인지 판단"""
    try:
        size = float(it.get("size", 0))
        cur = float(it.get("curPrice", 0))
        val = float(it.get("currentValue", size * cur))
    except Exception:
        return False
    if it.get("redeemable") is True:
        return False
    if size < MIN_SHARES or val < MIN_VALUE:
        return False
    if cur <= 0.001 or cur >= 0.999:
        return False
    return True

def period_pnl():
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    w = m = y = 0.0
    for tr in st.session_state.trade_log:
        try:
            dt = datetime.fromisoformat(tr["d"])
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
        except Exception:
            continue
        p = tr.get("profit", 0.0)
        if dt >= week_start: w += p
        if dt.year == now.year and dt.month == now.month: m += p
        if dt.year == now.year: y += p
    return w, m + st.session_state.adj_month, y + st.session_state.adj_year

def portfolio_health(portfolio, cash):
    """Analyze current holdings using only existing portfolio rows. No extra manual inputs."""
    g, c1, c2, blk = size_thresholds()
    pos_value = sum((p.get("shares", 0) or 0) * ((p.get("cur", 0) or 0) / 100) for p in portfolio)
    pos_cost = sum((p.get("inv", 0) or 0) for p in portfolio)
    total_assets = cash + pos_value
    unrealized = pos_value - pos_cost
    unrealized_pct = unrealized / pos_cost * 100 if pos_cost else 0
    exposure_pct = pos_value / total_assets * 100 if total_assets else 0
    cash_pct = cash / total_assets * 100 if total_assets else 0

    rows, values = [], []
    for p in portfolio:
        sh = p.get("shares", 0) or 0
        cur = p.get("cur", 0) or 0
        inv = p.get("inv", 0) or 0
        val = sh * cur / 100
        pnl = val - inv
        roi = pnl / inv * 100 if inv else 0
        pct = val / total_assets * 100 if total_assets else 0
        values.append({"name": p.get("name", ""), "val": val, "pct": pct, "cur": cur, "roi": roi, "pnl": pnl})

    if not portfolio:
        return {"title": t("분석할 보유 포지션이 없습니다", "No holdings to analyze"), "kind": "i",
                "summary": t("지갑에서 포지션을 불러오거나 직접 추가하면 자동 분석이 표시됩니다.", "Import or add positions to see analysis."),
                "lines": [], "exposure_pct": 0, "cash_pct": 100, "unrealized": 0, "unrealized_pct": 0}

    biggest = max(values, key=lambda x: x["val"]) if values else {"name": "", "pct": 0, "val": 0, "cur": 0, "roi": 0}
    losers = [x for x in values if x["roi"] <= -8]
    high_price = [x for x in values if x["cur"] >= 85]
    lottery = [x for x in values if x["cur"] <= 5]

    kind = "g"
    title = t("보유 상황 양호", "Holdings look controlled")
    summary = t("현재 포지션 규모가 개인 리스크 기준 안에서 관리 가능한 편입니다.", "Current position sizes look manageable within your risk profile.")

    if biggest["pct"] >= blk:
        kind, title = "b", t("단일 포지션 과대", "Single position too large")
        summary = t(f"가장 큰 포지션이 총자산의 {biggest['pct']:.1f}%입니다. 내 진입 금지선 {blk:.0f}%를 넘었습니다.",
                    f"Largest position is {biggest['pct']:.1f}% of assets, above your no-entry line {blk:.0f}%.")
    elif exposure_pct >= min(blk * 2, 50):
        kind, title = "b", t("전체 노출 과대", "Total exposure too high")
        summary = t(f"보유 포지션 평가금이 총자산의 {exposure_pct:.1f}%입니다. 신규 진입보다 축소·관망이 우선입니다.",
                    f"Open positions are {exposure_pct:.1f}% of assets. Reduce/watch before adding.")
    elif biggest["pct"] >= c1 or len(losers) >= 2 or high_price:
        kind, title = "w", t("주의 필요", "Needs caution")
        summary = t("일부 포지션의 크기·가격대·손실률을 점검해야 합니다.", "Review size, price zone, or loss rate on some positions.")

    rows.append((kind, summary))
    rows.append(("w" if biggest["pct"] >= c1 else "g",
                 t(f"최대 포지션: {biggest['name']} · {money(biggest['val'])} · 총자산의 {biggest['pct']:.1f}%",
                   f"Largest: {biggest['name']} · {money(biggest['val'])} · {biggest['pct']:.1f}% of assets")))
    rows.append(("g" if unrealized >= 0 else "b",
                 t(f"보유 포지션 손익: {signed_money(unrealized)} ({signed_pct(unrealized_pct)})",
                   f"Unrealized P&L: {signed_money(unrealized)} ({signed_pct(unrealized_pct)})")))
    rows.append(("w" if high_price else "g",
                 t(f"85¢ 이상 고가 포지션: {len(high_price)}개 — 고가 구간은 신규매수보다 익절/축소 판단이 우선입니다.",
                   f"High-price positions 85¢+: {len(high_price)} — prefer take-profit/reduce checks over new buys.")))
    rows.append(("w" if lottery else "g",
                 t(f"5¢ 이하 복권형 포지션: {len(lottery)}개 — 추가매수 금지 원칙이 좋습니다.",
                   f"Lottery-like positions ≤5¢: {len(lottery)} — no-add rule is safer.")))

    return {"title": title, "kind": kind, "summary": summary, "lines": rows,
            "exposure_pct": exposure_pct, "cash_pct": cash_pct,
            "unrealized": unrealized, "unrealized_pct": unrealized_pct}

def analyze_portfolio_position(p, bankroll):
    """Analyze one open holding using current portfolio data only."""
    name = p.get("name", "") or "Polymarket position"
    outcome = p.get("outcome", "") or ""
    sh = _safe_float(p.get("shares"), 0)
    buy = _safe_float(p.get("buy"), 0)
    cur = _safe_float(p.get("cur"), 0)
    inv = _safe_float(p.get("inv"), 0)
    val = sh * cur / 100 if cur else 0
    pnl = val - inv
    roi = pnl / inv * 100 if inv else 0
    pct = val / bankroll * 100 if bankroll else 0

    zone_label, zone_kind, _, zone_note = price_zone(cur)
    size_label, size_kind, _, size_note = size_rule(pct)
    g, c1, c2, blk = size_thresholds()

    if pct >= blk:
        title, kind = t("과대 노출 — 축소 우선", "Oversized — reduce first"), "b"
        summary = t("이 포지션은 내 진입 금지선보다 큽니다. 추가매수보다 일부 축소가 우선입니다.",
                    "This holding is above your no-entry line. Reducing comes before adding.")
    elif roi >= 30 and cur >= 80:
        title, kind = t("수익 구간 — 부분매도 검토", "Profit zone — consider partial sell"), "w"
        summary = t("수익률이 크고 가격도 높은 편입니다. 원금 회수 또는 일부 익절을 검토할 만합니다.",
                    "Profit is strong and price is high. Consider recovering principal or taking partial profit.")
    elif roi <= -35:
        title, kind = t("손실 확대 — 추가매수 금지", "Large loss — no adding"), "b"
        summary = t("손실률이 큽니다. 복구 배팅보다 손절·홀딩 기준을 다시 확인하세요.",
                    "Loss is large. Re-check stop/hold rules instead of chasing.")
    elif cur >= 90:
        title, kind = t("고가 구간 — 신규매수 비추천", "High price — new buys discouraged"), "w"
        summary = t("현재가는 고가 구간입니다. 홀딩은 가능해도 추가 진입은 보수적으로 봐야 합니다.",
                    "Price is high. Holding may be fine, but adding should be conservative.")
    elif cur <= 5:
        title, kind = t("복권형 구간 — 소액 원칙", "Lottery zone — small only"), "w"
        summary = t("초저가 포지션입니다. 추가매수보다 최대 손실을 제한하는 게 중요합니다.",
                    "Very low-price holding. Limit max loss rather than adding.")
    elif pct >= c1:
        title, kind = t("크기 주의 — 비중 점검", "Size caution — review exposure"), "w"
        summary = t("가격 자체보다 포지션 크기가 커지고 있습니다. 다음 진입 전에 전체 노출을 확인하세요.",
                    "Size is becoming the issue. Check total exposure before the next entry.")
    else:
        title, kind = t("관리 가능", "Manageable"), "g"
        summary = t("현재 데이터 기준으로는 과도한 위험 신호가 크지 않습니다.",
                    "Based on current data, no major risk signal stands out.")

    lines_ = [
        ("g" if pnl >= 0 else "b", t(f"현재 손익: {signed_money(pnl)} ({signed_pct(roi)}) · 평가금 {money(val)}",
                                      f"Current P&L: {signed_money(pnl)} ({signed_pct(roi)}) · value {money(val)}")),
        (size_kind, t(f"포지션 크기: 총자산의 {pct:.1f}% · {size_label}",
                      f"Position size: {pct:.1f}% of assets · {size_label}")),
        (zone_kind, t(f"가격 구간: {cur:.1f}¢ · {zone_label}. {zone_note}",
                      f"Price zone: {cur:.1f}¢ · {zone_label}. {zone_note}")),
        ("i", t(f"평균 매수가 {buy:.1f}¢ · 보유 수량 {sh:.2f} · 선택 {outcome}",
                 f"Avg buy {buy:.1f}¢ · shares {sh:.2f} · side {outcome}")),
    ]
    return {"name": name, "outcome": outcome, "title": title, "kind": kind, "summary": summary,
            "value": val, "pnl": pnl, "roi": roi, "pct": pct,
            "cur": cur, "buy": buy, "shares": sh, "investment": inv, "lines": lines_}

def portfolio_position_key(p):
    if not isinstance(p, dict):
        return ""
    asset = str(p.get("asset") or p.get("token_id") or p.get("conditionId") or "").strip()
    if asset:
        return f"asset:{asset}"
    return "pos:" + _norm_key(f'{p.get("name", "")}|{p.get("outcome", "")}|{p.get("buy", "")}|{p.get("shares", "")}')

def visible_portfolio_positions(portfolio=None):
    hidden = set(str(x) for x in st.session_state.get("portfolio_hidden_keys", []) or [])
    return [p for p in (portfolio if portfolio is not None else st.session_state.get("portfolio", [])) or []
            if portfolio_position_key(p) not in hidden]

def portfolio_hidden_summary():
    hidden = set(str(x) for x in st.session_state.get("portfolio_hidden_keys", []) or [])
    total = len(st.session_state.get("portfolio", []) or [])
    hidden_count = sum(1 for p in st.session_state.get("portfolio", []) or [] if portfolio_position_key(p) in hidden)
    return total, hidden_count

def portfolio_asset_summary(portfolio=None, include_hidden=True):
    """Return cash and position totals; optionally ignore hidden holdings for display panels."""
    raw_portfolio = portfolio if portfolio is not None else st.session_state.get("portfolio", []) or []
    if include_hidden:
        portfolio_rows = [p for p in raw_portfolio if isinstance(p, dict)]
    else:
        portfolio_rows = [p for p in visible_portfolio_positions(raw_portfolio) if isinstance(p, dict)]
    cash = _safe_float(st.session_state.get("cash"), 0.0)
    pos_value = sum(
        _safe_float(p.get("shares"), 0.0) * (_safe_float(p.get("cur"), 0.0) / 100.0)
        for p in portfolio_rows
    )
    pos_cost = sum(_safe_float(p.get("inv"), 0.0) for p in portfolio_rows)
    total = cash + pos_value
    return {
        "cash": cash,
        "position_value": pos_value,
        "position_cost": pos_cost,
        "total": total,
        "has_basis": bool(portfolio_rows) or cash > 0,
    }

def current_portfolio_assets():
    """Return the full wallet-backed total used by today's operating limits."""
    return portfolio_asset_summary(include_hidden=True)

def recent_completed_trade_rows(limit=None):
    """Completed trade groups shared by the side panel and start-anchor picker."""
    completed = []
    trade_sources = [
        (st.session_state.get("auto_trades", []), st.session_state.get("activity_events", []) or [], t("지갑", "Wallet")),
        (st.session_state.get("paste_trades", []), st.session_state.get("paste_events", []) or [], t("붙여넣기", "Paste")),
    ]
    for trades, events, source_label in trade_sources:
        trade_rows = group_auto_trades_for_pnl(trades)
        if events:
            trade_rows = link_settlement_events_to_trade_groups(trade_rows, events)
        for r in trade_rows:
            pnl = _display_realized(r)
            if pnl is None:
                continue
            bought = _safe_float(r.get("bought_shares"), 0.0)
            remaining = _display_remaining_shares(r)
            close_tolerance = max(0.05, bought * 0.01)
            if remaining > close_tolerance:
                continue
            latest_dt = r.get("linked_event_time") or r.get("latest_dt") or ""
            latest_obj = parse_trade_datetime({"d": latest_dt}) if latest_dt else None
            recovered = _safe_float(r.get("adjusted_effective_proceeds", r.get("sell_proceeds")), 0.0)
            key_src = f'{source_label}|{r.get("market", "")}|{r.get("outcome", "")}|{latest_dt}|{pnl}|{recovered}|{len(completed)}'
            market = r.get("market", "") or t("이름 없는 거래", "Unnamed trade")
            outcome = r.get("outcome", "") or "-"
            completed.append({
                "key": "trade:" + _norm_key(key_src),
                "market": market,
                "outcome": outcome,
                "status": r.get("adjusted_status") or r.get("status", ""),
                "source": source_label,
                "pnl": _safe_float(pnl, 0.0),
                "recovered": recovered,
                "latest_dt": latest_dt,
                "_latest_ts": latest_obj.timestamp() if latest_obj else _safe_float(r.get("_latest_ts"), -1.0),
            })
    completed = sorted(completed, key=lambda r: r.get("_latest_ts", -1.0), reverse=True)
    if limit is None:
        return completed
    return completed[:max(int(limit or 0), 0)]


def resolve_trade_row(r):
    """Apply the user's manual win/lost mark to a grouped trade row and return the final
    realized P&L + status. Unmarked -> the existing auto/settlement values (behavior unchanged).
    won  : remaining shares redeem at $1  -> realized = current + (remaining_shares - remaining_cost)
    lost : remaining shares expire at $0  -> realized = current - remaining_cost"""
    rem = _display_remaining_shares(r)
    rem_cost = _display_remaining_cost(r)
    cur = _display_realized(r)
    cur = cur if cur is not None else 0.0
    try:
        mark = str((st.session_state.get("trade_resolutions") or {}).get(r.get("key"), "") or "")
    except Exception:
        mark = ""
    if mark == "won":
        return {"resolved": "won", "realized_final": round(cur + (rem - rem_cost), 2),
                "status_final": t("승(상환)", "Won (redeemed)"), "remaining_final": 0.0}
    if mark == "lost":
        return {"resolved": "lost", "realized_final": round(cur - rem_cost, 2),
                "status_final": t("패(소멸)", "Lost (expired)"), "remaining_final": 0.0}
    return {"resolved": "", "realized_final": _display_realized(r),
            "status_final": r.get("adjusted_status") or r.get("status", ""), "remaining_final": rem}


def update_trade_ledger():
    """Durable per-trade realized-P&L ledger that survives Polymarket dropping old data.
    Upserts each settled trade (closed by sells OR manually marked won/lost) by its stable
    group key; never deletes, so dropped trades stay. The bottom-of-script save_local_state()
    persists it. Fails soft. Returns the ledger size."""
    try:
        ledger = st.session_state.get("trade_ledger")
        if not isinstance(ledger, dict):
            ledger = {}
        sources = [
            (t("지갑", "Wallet"), st.session_state.get("auto_trades", []), st.session_state.get("activity_events", []) or []),
            (t("붙여넣기", "Paste"), st.session_state.get("paste_trades", []), st.session_state.get("paste_events", []) or []),
        ]
        for label, trades, events in sources:
            rows = group_auto_trades_for_pnl(trades)
            if events:
                rows = link_settlement_events_to_trade_groups(rows, events)
            for r in rows:
                res = resolve_trade_row(r)
                closed_by_sell = res["remaining_final"] <= 1e-6 and _display_sold_shares(r) > 0
                if not (res["resolved"] or closed_by_sell):
                    continue
                pnl = res["realized_final"]
                if pnl is None:
                    continue
                key = str(r.get("key") or f'{r.get("market", "")}|{r.get("outcome", "")}')
                prev = ledger.get(key) if isinstance(ledger.get(key), dict) else {}
                cat = infer_market_category("", r.get("market", ""))
                # 시트 가져오기 등으로 수동 지정된 카테고리는 재생성 때 자동 분류로 덮지 않는다.
                if str(prev.get("category_src", "")) == "manual" and prev.get("category"):
                    cat = prev["category"]
                ledger[key] = {
                    "date": str(r.get("latest_dt") or ""),
                    "market": r.get("market", "") or t("이름 없는 거래", "Unnamed trade"),
                    "outcome": r.get("outcome", "") or "-",
                    "status": res["status_final"],
                    "resolved": res["resolved"],
                    "pnl": round(_safe_float(pnl, 0.0), 2),
                    "category": cat,
                    "source": label,
                    # 행동 인사이트 재료: 진입가·매수금(규칙위반 판정)과 첫/마지막 체결시각(추격 감지)
                    "avg_buy_price": _safe_float(r.get("avg_buy_price"), 0.0),
                    "buy_cost": round(_safe_float(r.get("buy_cost"), 0.0), 2),
                    "first_ts": _safe_float(r.get("_first_ts"), -1.0),
                    "latest_ts": _safe_float(r.get("_latest_ts"), -1.0),
                    "updated_at": datetime.now(KST).isoformat(timespec="minutes"),
                }
                if str(prev.get("category_src", "")) == "manual" and prev.get("category"):
                    ledger[key]["category_src"] = "manual"
        st.session_state.trade_ledger = ledger
        return len(ledger)
    except Exception:
        return 0


def performance_summary(ledger=None):
    """Win/loss + category performance from the durable ledger. Dedupes by market+outcome so
    older ledger key formats cannot double-count. Fails soft."""
    try:
        led = ledger if isinstance(ledger, dict) else (st.session_state.get("trade_ledger") or {})
        uniq = {}
        for v in led.values():
            if not isinstance(v, dict):
                continue
            k = (str(v.get("market", "")).strip().lower(), str(v.get("outcome", "")).strip().lower())
            if k not in uniq or str(v.get("updated_at", "")) >= str(uniq[k].get("updated_at", "")):
                uniq[k] = v
        recs = [v for v in uniq.values() if v.get("pnl") is not None]
        wins = [r for r in recs if _safe_float(r.get("pnl"), 0) > 0]
        losses = [r for r in recs if _safe_float(r.get("pnl"), 0) < 0]
        gross_win = sum(_safe_float(r.get("pnl"), 0) for r in wins)
        gross_loss = -sum(_safe_float(r.get("pnl"), 0) for r in losses)
        n = len(recs)
        cats = {}
        for r in recs:
            cat = str(r.get("category") or "").strip() or t("기타", "Other")
            c = cats.setdefault(cat, {"pnl": 0.0, "wins": 0, "losses": 0, "n": 0})
            p = _safe_float(r.get("pnl"), 0)
            c["pnl"] += p
            c["n"] += 1
            if p > 0:
                c["wins"] += 1
            elif p < 0:
                c["losses"] += 1
        return {
            "n": n, "wins": len(wins), "losses": len(losses),
            "win_rate": (len(wins) / n * 100.0) if n else 0.0,
            "total_pnl": round(gross_win - gross_loss, 2),
            "gross_win": round(gross_win, 2), "gross_loss": round(gross_loss, 2),
            "avg_win": round(gross_win / len(wins), 2) if wins else 0.0,
            "avg_loss": round(gross_loss / len(losses), 2) if losses else 0.0,
            "profit_factor": (gross_win / gross_loss) if gross_loss > 1e-9 else None,
            "by_category": cats,
        }
    except Exception:
        return {"n": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "total_pnl": 0.0,
                "gross_win": 0.0, "gross_loss": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
                "profit_factor": None, "by_category": {}}

def _insight_params():
    """행동 분석 파라미터 — 설정·도구에서 조절: 추격 감지 창(분) · 고가 진입 기준(¢) · 연패 중단 기준."""
    try:
        w = int(_safe_float(st.session_state.get("insight_chase_window"), 60) or 60)
        hp = _safe_float(st.session_state.get("insight_high_price_cents"), 80.0) or 80.0
        stk = int(_safe_float(st.session_state.get("insight_stop_streak"), 2) or 2)
        return {"window": max(w, 1), "high_price": min(max(hp, 50.0), 99.0), "streak": max(stk, 1)}
    except Exception:
        return {"window": 60, "high_price": 80.0, "streak": 2}


def _ledger_recs_for_analysis(ledger=None, emotions=None, chase_window_min=None):
    """장부(dedupe)+감정 태그를 분석용 rec 리스트로 만든다 — behavior_insights와
    rule_simulation이 공유. 추격 자동감지까지 계산해 _chase/_chase_detected를 채운다."""
    led = ledger if isinstance(ledger, dict) else (st.session_state.get("trade_ledger") or {})
    emo = emotions if isinstance(emotions, dict) else (st.session_state.get("trade_emotions") or {})
    uniq = {}
    for k, v in led.items():
        if not isinstance(v, dict):
            continue
        mk = (str(v.get("market", "")).strip().lower(), str(v.get("outcome", "")).strip().lower())
        cur = uniq.get(mk)
        if cur is None or str(v.get("updated_at", "")) >= str(cur[1].get("updated_at", "")):
            uniq[mk] = (str(k), v)
    recs = []
    for k, v in uniq.values():
        if v.get("pnl") is None:
            continue
        tag = emo.get(k)
        tag = tag if isinstance(tag, dict) else {}
        e = int(_safe_float(tag.get("emotion"), 0))
        recs.append({
            "key": k, "pnl": _safe_float(v.get("pnl"), 0.0),
            "date": str(v.get("date", "") or "")[:10],
            "category": str(v.get("category", "") or ""),
            "emotion": e if 1 <= e <= 5 else 0,
            "chase_flag": bool(tag.get("chase")),
            "first_ts": _safe_float(v.get("first_ts"), -1.0),
            "latest_ts": _safe_float(v.get("latest_ts"), -1.0),
            "avg_buy_price": _safe_float(v.get("avg_buy_price"), -1.0),
            "buy_cost": _safe_float(v.get("buy_cost"), -1.0),
        })
    # 추격 자동감지: (다른) 손실 거래의 정산 후 window분 내 첫 매수. 자기 자신은 제외.
    if chase_window_min is None:
        chase_window_min = _insight_params()["window"]
    window = max(_safe_float(chase_window_min, 0.0), 0.0) * 60.0
    loss_times = [(r["key"], r["latest_ts"]) for r in recs if r["pnl"] < 0 and r["latest_ts"] > 0]
    for r in recs:
        detected = r["first_ts"] > 0 and any(
            k != r["key"] and 0 <= r["first_ts"] - lt <= window for k, lt in loss_times)
        r["_chase_detected"] = detected
        r["_chase"] = detected or r["chase_flag"]
    return recs


def behavior_insights(ledger=None, emotions=None, chase_window_min=None):
    """감정·행동 복기 인사이트 — '감정적일 때 얼마 잃는지'를 숫자로 만든다.
    trade_ledger(확정 손익)와 trade_emotions(감정 1 침착~5 틸트 · 추격 플래그)를 그룹 key로 조인해
    ① 감정점수×손익, ② 손실 정산 직후 재진입(추격, window 분 이내 첫 매수 자동감지 + 수동 플래그),
    ③ 규칙위반 비용(80¢ 이상 진입 · 감정 한도 초과 과대베팅)을 집계한다. Fails soft."""
    empty = {"n": 0, "tagged": 0, "by_emotion": {}, "corr": None,
             "calm": {"n": 0, "pnl": 0.0}, "tilt": {"n": 0, "pnl": 0.0},
             "chase": {"n": 0, "pnl": 0.0, "wins": 0, "flagged": 0, "detected": 0},
             "high_price": {"n": 0, "pnl": 0.0, "threshold": _insight_params()["high_price"]},
             "oversized": {"n": 0, "pnl": 0.0, "limit": 0.0},
             "violation": {"n": 0, "pnl": 0.0}, "emotional": {"n": 0, "pnl": 0.0},
             "window_min": chase_window_min if chase_window_min is not None else _insight_params()["window"]}
    try:
        if chase_window_min is None:
            chase_window_min = _insight_params()["window"]
        empty["window_min"] = chase_window_min
        recs = _ledger_recs_for_analysis(ledger, emotions, chase_window_min)
        if not recs:
            return empty
        out = json.loads(json.dumps(empty))  # deep copy
        out["n"] = len(recs)
        # ① 감정 × 손익
        by, pts = {}, []
        for r in recs:
            e = r["emotion"]
            if not e:
                continue
            b = by.setdefault(e, {"n": 0, "pnl": 0.0, "wins": 0, "losses": 0})
            b["n"] += 1
            b["pnl"] += r["pnl"]
            if r["pnl"] > 0:
                b["wins"] += 1
            elif r["pnl"] < 0:
                b["losses"] += 1
            pts.append((float(e), r["pnl"]))
            if e <= 2:
                out["calm"]["n"] += 1
                out["calm"]["pnl"] += r["pnl"]
            elif e >= 4:
                out["tilt"]["n"] += 1
                out["tilt"]["pnl"] += r["pnl"]
        out["by_emotion"] = {lvl: {"n": b["n"], "pnl": round(b["pnl"], 2), "wins": b["wins"], "losses": b["losses"],
                                   "win_rate": (b["wins"] / b["n"] * 100.0) if b["n"] else 0.0}
                             for lvl, b in sorted(by.items())}
        out["tagged"] = len(pts)
        if len(pts) >= 3:
            mx = sum(p[0] for p in pts) / len(pts)
            my = sum(p[1] for p in pts) / len(pts)
            sx = sum((p[0] - mx) ** 2 for p in pts) ** 0.5
            sy = sum((p[1] - my) ** 2 for p in pts) ** 0.5
            if sx > 1e-9 and sy > 1e-9:
                out["corr"] = round(sum((p[0] - mx) * (p[1] - my) for p in pts) / (sx * sy), 2)
        # ② 추격 재진입 (자동감지는 _ledger_recs_for_analysis에서 계산됨 — 자기 자신 제외 규칙 포함)
        for r in recs:
            if r["_chase"]:
                c = out["chase"]
                c["n"] += 1
                c["pnl"] += r["pnl"]
                if r["pnl"] > 0:
                    c["wins"] += 1
                if r["chase_flag"]:
                    c["flagged"] += 1
                if r["_chase_detected"]:
                    c["detected"] += 1
        # ③ 규칙 위반: 80¢ 이상 진입 · 감정 한도($) 초과 과대베팅 (합집합 = violation)
        el = max(_safe_float(profile().get("emotional_limit"), 0.0), 0.0)
        out["oversized"]["limit"] = el
        viol = set()
        for r in recs:
            if r["avg_buy_price"] >= out["high_price"]["threshold"]:
                out["high_price"]["n"] += 1
                out["high_price"]["pnl"] += r["pnl"]
                viol.add(r["key"])
            if el > 0 and r["buy_cost"] > el + 1e-9:
                out["oversized"]["n"] += 1
                out["oversized"]["pnl"] += r["pnl"]
                viol.add(r["key"])
        # 감정적 거래(틸트 4~5 ∪ 추격) / 규칙위반 합집합 합계
        for r in recs:
            if r["key"] in viol:
                out["violation"]["n"] += 1
                out["violation"]["pnl"] += r["pnl"]
            if r["emotion"] >= 4 or r["_chase"]:
                out["emotional"]["n"] += 1
                out["emotional"]["pnl"] += r["pnl"]
        for grp in ("calm", "tilt", "chase", "high_price", "oversized", "violation", "emotional"):
            out[grp]["pnl"] = round(out[grp]["pnl"], 2)
        return out
    except Exception:
        return empty


RULE_SIM_RULES = ("skip_high_price", "cap_size", "no_chase", "stop_after_losses")

def _mark_stopped_after_losses(recs, streak_to_stop=2):
    """'N연패 후 당일 중단' 규칙의 대상 표시: 같은 날 정산 순서로 걸으며 연속 손실이
    streak_to_stop에 도달한 시점 이후에 '진입한'(first_ts 기준) 거래에 _stopped=True.
    시각 정보가 없는 거래(first/latest_ts<=0)는 판단 불가라 건드리지 않는다."""
    by_day = {}
    for r in recs:
        r["_stopped"] = False
        if r.get("date") and r["latest_ts"] > 0:
            by_day.setdefault(r["date"], []).append(r)
    for day_recs in by_day.values():
        day_recs.sort(key=lambda x: x["latest_ts"])
        streak = 0
        cutoff = None
        for r in day_recs:
            if cutoff is not None and r["first_ts"] > cutoff:
                r["_stopped"] = True  # 중단 시점 이후 신규 진입 — 없었을 거래
                continue
            if r["pnl"] < 0:
                streak += 1
            elif r["pnl"] > 0:
                streak = 0
            if streak >= max(int(streak_to_stop), 1) and cutoff is None:
                cutoff = r["latest_ts"]


def rule_simulation(ledger=None, emotions=None, rules=None, chase_window_min=None):
    """Counterfactual 복기 — '이 규칙을 지켰다면 손익이 어땠나'를 장부에 소급 적용한다.
    규칙: skip_high_price(80¢+ 진입 스킵) · cap_size(감정 한도 초과분 비례 축소) ·
    no_chase(추격 재진입 스킵) · stop_after_losses(2연패 후 당일 신규 진입 중단).
    근사 가정 — 스킵된 거래가 이후 행동에 미치는 연쇄 효과는 반영하지 않는다. Fails soft."""
    empty = {"n": 0, "actual_total": 0.0, "limit": 0.0, "rules": {},
             "combined": {"total": 0.0, "delta": 0.0, "skipped": 0, "capped": 0},
             "daily": []}
    try:
        params = _insight_params()
        if chase_window_min is None:
            chase_window_min = params["window"]
        enabled = tuple(rules) if rules is not None else RULE_SIM_RULES
        recs = _ledger_recs_for_analysis(ledger, emotions, chase_window_min)
        if not recs:
            return empty
        el = max(_safe_float(profile().get("emotional_limit"), 0.0), 0.0)
        _mark_stopped_after_losses(recs, streak_to_stop=params["streak"])

        def sim_pnl(r, ruleset):
            if "skip_high_price" in ruleset and r["avg_buy_price"] >= params["high_price"]:
                return 0.0, "skip"
            if "no_chase" in ruleset and r["_chase"]:
                return 0.0, "skip"
            if "stop_after_losses" in ruleset and r.get("_stopped"):
                return 0.0, "skip"
            if "cap_size" in ruleset and el > 0 and r["buy_cost"] > el:
                return r["pnl"] * (el / r["buy_cost"]), "cap"
            return r["pnl"], ""

        actual = sum(r["pnl"] for r in recs)
        out = {"n": len(recs), "actual_total": round(actual, 2), "limit": el, "rules": {}}
        for rule in RULE_SIM_RULES:  # 규칙 하나만 지켰다면
            tot, aff = 0.0, 0
            for r in recs:
                p, kind = sim_pnl(r, (rule,))
                tot += p
                if kind:
                    aff += 1
            out["rules"][rule] = {"total": round(tot, 2), "delta": round(tot - actual, 2),
                                  "affected": aff, "enabled": rule in enabled}
        ctot, skipped, capped, sims = 0.0, 0, 0, {}
        for r in recs:  # 켜진 규칙 전부 지켰다면
            p, kind = sim_pnl(r, enabled)
            sims[r["key"]] = p
            ctot += p
            if kind == "skip":
                skipped += 1
            elif kind == "cap":
                capped += 1
        out["combined"] = {"total": round(ctot, 2), "delta": round(ctot - actual, 2),
                           "skipped": skipped, "capped": capped}
        by_day = {}
        for r in recs:  # 일별 누적 비교 (자산 곡선용)
            if not r.get("date"):
                continue
            a, s = by_day.get(r["date"], (0.0, 0.0))
            by_day[r["date"]] = (a + r["pnl"], s + sims[r["key"]])
        ca, cs, daily = 0.0, 0.0, []
        for d0 in sorted(by_day):
            ca += by_day[d0][0]
            cs += by_day[d0][1]
            daily.append({"date": d0, "actual": round(ca, 2), "ruled": round(cs, 2)})
        out["daily"] = daily
        return out
    except Exception:
        return empty


def equity_curve_data(ledger=None, emotions=None):
    """장부 기준 일별 실현손익 → 누적 자산 곡선 + 최대 낙폭(MDD). Fails soft."""
    empty = {"n": 0, "daily": [], "total": 0.0, "peak": 0.0, "mdd": 0.0, "mdd_date": "", "days": 0}
    try:
        recs = _ledger_recs_for_analysis(ledger, emotions)
        by_day = {}
        for r in recs:
            if r.get("date"):
                by_day[r["date"]] = by_day.get(r["date"], 0.0) + r["pnl"]
        if not by_day:
            return empty
        cum, peak, mdd, mdd_date, daily = 0.0, 0.0, 0.0, "", []
        for d0 in sorted(by_day):
            cum += by_day[d0]
            peak = max(peak, cum)
            dd = peak - cum
            if dd > mdd:
                mdd, mdd_date = dd, d0
            daily.append({"date": d0, "pnl": round(by_day[d0], 2), "cum": round(cum, 2)})
        return {"n": len(recs), "daily": daily, "total": round(cum, 2), "peak": round(peak, 2),
                "mdd": round(mdd, 2), "mdd_date": mdd_date, "days": len(daily)}
    except Exception:
        return empty


def calendar_heatmap_data(weeks=12, end=None, ledger=None, emotions=None):
    """일별 손익 캘린더(월~일 × 최근 N주) 데이터. end는 테스트용 고정 날짜(date).
    셀: {date, pnl(거래 없으면 None), count, future}. Fails soft."""
    try:
        recs = _ledger_recs_for_analysis(ledger, emotions)
        by_day = {}
        for r in recs:
            if r.get("date"):
                a = by_day.setdefault(r["date"], {"pnl": 0.0, "count": 0})
                a["pnl"] += r["pnl"]
                a["count"] += 1
        end_d = end or datetime.now(KST).date()
        start_monday = end_d - timedelta(days=end_d.weekday() + 7 * (max(int(weeks), 1) - 1))
        grid = []
        for w in range(max(int(weeks), 1)):
            row = []
            for wd in range(7):
                d0 = start_monday + timedelta(days=w * 7 + wd)
                iso = d0.isoformat()
                cell = by_day.get(iso)
                row.append({"date": iso, "pnl": round(cell["pnl"], 2) if cell else None,
                            "count": cell["count"] if cell else 0, "future": d0 > end_d})
            grid.append(row)
        traded = [abs(c["pnl"]) for wrow in grid for c in wrow if c["pnl"] is not None and abs(c["pnl"]) > 1e-9]
        if traded:
            idx = min(len(traded) - 1, max(int(round(len(traded) * 0.95)) - 1, 0))
            scale = sorted(traded)[idx]
        else:
            scale = 1.0
        return {"grid": grid, "scale": max(scale, 1e-9), "start": start_monday.isoformat(), "end": end_d.isoformat()}
    except Exception:
        return {"grid": [], "scale": 1.0, "start": "", "end": ""}


def weekly_report(now=None, ledger=None, emotions=None):
    """이번 주(월~일, KST) vs 지난주 요약 — 손익·건수·승률·감정적(틸트∪추격)·규칙위반 손익·최악 카테고리.
    now는 테스트용 고정 date. Fails soft."""
    def _bucket():
        return {"pnl": 0.0, "n": 0, "wins": 0, "win_rate": 0.0,
                "emotional_pnl": 0.0, "emotional_n": 0, "violation_pnl": 0.0, "violation_n": 0,
                "worst_category": "", "worst_category_pnl": 0.0}
    empty = {"this": _bucket(), "last": _bucket(), "delta_pnl": 0.0,
             "this_start": "", "last_start": "", "has_data": False}
    try:
        recs = _ledger_recs_for_analysis(ledger, emotions)
        el = max(_safe_float(profile().get("emotional_limit"), 0.0), 0.0)
        _hp = _insight_params()["high_price"]
        today = now or datetime.now(KST).date()
        this_mon = today - timedelta(days=today.weekday())
        last_mon = this_mon - timedelta(days=7)
        out = {"this": _bucket(), "last": _bucket(), "delta_pnl": 0.0,
               "this_start": this_mon.isoformat(), "last_start": last_mon.isoformat(), "has_data": False}
        cats = {"this": {}, "last": {}}
        for r in recs:
            d0 = r.get("date")
            if not d0:
                continue
            try:
                rd = date.fromisoformat(d0)
            except Exception:
                continue
            if this_mon <= rd <= today:
                w = "this"
            elif last_mon <= rd < this_mon:
                w = "last"
            else:
                continue
            b = out[w]
            b["pnl"] += r["pnl"]
            b["n"] += 1
            if r["pnl"] > 0:
                b["wins"] += 1
            if r["emotion"] >= 4 or r["_chase"]:
                b["emotional_pnl"] += r["pnl"]
                b["emotional_n"] += 1
            if r["avg_buy_price"] >= _hp or (el > 0 and r["buy_cost"] > el):
                b["violation_pnl"] += r["pnl"]
                b["violation_n"] += 1
            cat = r.get("category") or t("기타", "Other")
            cats[w][cat] = cats[w].get(cat, 0.0) + r["pnl"]
        for w in ("this", "last"):
            b = out[w]
            b["win_rate"] = (b["wins"] / b["n"] * 100.0) if b["n"] else 0.0
            for k in ("pnl", "emotional_pnl", "violation_pnl"):
                b[k] = round(b[k], 2)
            if cats[w]:
                worst = min(cats[w].items(), key=lambda kv: kv[1])
                if worst[1] < 0:
                    b["worst_category"], b["worst_category_pnl"] = worst[0], round(worst[1], 2)
        out["delta_pnl"] = round(out["this"]["pnl"] - out["last"]["pnl"], 2)
        out["has_data"] = bool(out["this"]["n"] or out["last"]["n"])
        return out
    except Exception:
        return empty


def today_anchor_timestamp():
    """Timestamp for the selected operating anchor, if one has been stored."""
    raw = str(st.session_state.get("today_anchor_time") or "").strip()
    if not raw:
        return None
    dt = parse_trade_datetime({"d": raw})
    return dt.timestamp() if dt else None

def today_realized_loss_since_anchor():
    """Gross realized losses since the anchor; used for conservative stop-loss mode."""
    rows = recent_completed_trade_rows(limit=None)
    anchor_ts = today_anchor_timestamp()
    today_kst = datetime.now(KST).date()
    gross_loss = 0.0
    for row in rows:
        pnl = _safe_float(row.get("pnl"), 0.0)
        if pnl >= 0:
            continue
        row_ts = _safe_float(row.get("_latest_ts"), -1.0)
        if anchor_ts is not None:
            include = row_ts >= anchor_ts - 1e-6
        else:
            dt = parse_trade_datetime({"d": row.get("latest_dt")})
            include = bool(dt and dt.date() == today_kst)
        if include:
            gross_loss += abs(pnl)
    return gross_loss

def today_operating_metrics(current_assets=None):
    """Compute the top dashboard values from the current portfolio and today controls."""
    assets = current_portfolio_assets()
    current_total = assets["total"] if assets["has_basis"] else float(effective_bankroll() or 0.0)
    if current_assets is not None:
        current_total = float(current_assets or 0.0)
    current_total += _safe_float(st.session_state.get("today_cash_adjustment"), 0.0)

    start = _safe_float(st.session_state.get("today_start_cash"), 0.0)
    stop = _safe_float(st.session_state.get("today_stop_loss_amount"), 0.0)
    goal_mode = st.session_state.get("today_goal_mode", "percent")
    if goal_mode == "percent":
        goal_pct = _safe_float(st.session_state.get("today_goal_pct"), 0.0)
        goal_amount = start * goal_pct / 100.0
    else:
        goal_amount = _safe_float(st.session_state.get("today_goal_amount"), 0.0)
        goal_pct = (goal_amount / start * 100.0) if start > 0 else 0.0

    pnl = current_total - start if start > 0 else 0.0
    gain = max(pnl, 0.0)
    loss = max(-pnl, 0.0)
    gross_realized_loss = today_realized_loss_since_anchor()
    stop_loss_gross_only = bool(st.session_state.get("today_stop_loss_gross_only", False))
    stop_loss_used = gross_realized_loss if stop_loss_gross_only else loss
    goal_progress = (gain / goal_amount * 100.0) if goal_amount > 0 else 0.0
    stop_progress = (stop_loss_used / stop * 100.0) if stop > 0 else 0.0
    loss_pct = (stop_loss_used / start * 100.0) if start > 0 else 0.0
    anchor_mode = st.session_state.get("today_anchor_mode", "next")
    anchor_label = str(st.session_state.get("today_anchor_label") or "").strip()
    if not anchor_label:
        anchor_label = t("다음 거래부터", "From next trade") if anchor_mode == "next" else t("기준 미설정", "No anchor")

    return {
        "current_total": current_total,
        "start": start,
        "stop": stop,
        "goal_amount": goal_amount,
        "goal_pct": goal_pct,
        "pnl": pnl,
        "gain": gain,
        "loss": loss,
        "gross_realized_loss": gross_realized_loss,
        "stop_loss_used": stop_loss_used,
        "stop_loss_gross_only": stop_loss_gross_only,
        "goal_left": max(goal_amount - gain, 0.0),
        "stop_left": max(stop - stop_loss_used, 0.0) if stop > 0 else 0.0,
        "goal_progress": goal_progress,
        "goal_progress_bar": clamp(goal_progress, 0, 100),
        "stop_progress": stop_progress,
        "stop_progress_bar": clamp(stop_progress, 0, 100),
        "loss_pct": loss_pct,
        "anchor_label": anchor_label,
        "anchor_time": st.session_state.get("today_anchor_time", ""),
        "anchor_mode": anchor_mode,
    }


def today_loss_limit_status():
    """Survival circuit breaker: has today's loss reached the user's stop-loss limit?
    Returns a dict; hit=True means new entries should be blocked. Fails soft."""
    try:
        m = today_operating_metrics()
        stop = float(m.get("stop") or 0.0)
        used = float(m.get("stop_loss_used") or 0.0)
        return {"hit": stop > 0 and used >= stop, "stop": stop, "used": used,
                "left": max(stop - used, 0.0),
                "pct": (used / stop * 100.0) if stop > 0 else 0.0, "set": stop > 0}
    except Exception:
        return {"hit": False, "stop": 0.0, "used": 0.0, "left": 0.0, "pct": 0.0, "set": False}


def tilt_status():
    """Behavioral guardrail: count trailing consecutive losing trades (tilt / loss-chasing).
    level: 'stop' (>=3 in a row), 'warn' (2), else 'ok'. Fails soft."""
    try:
        rows = recent_completed_trade_rows(limit=12)  # already newest-first
        streak = 0
        for r in rows:
            if _safe_float(r.get("pnl"), 0.0) < 0:
                streak += 1
            else:
                break
        level = "stop" if streak >= 3 else "warn" if streak >= 2 else "ok"
        return {"streak": streak, "level": level}
    except Exception:
        return {"streak": 0, "level": "ok"}


def day_is_locked():
    """Commitment device: True if the user locked betting for today (survives reload,
    auto-clears next day). Set via the entry tab 'lock today' button."""
    try:
        return str(st.session_state.get("day_locked_date") or "") == datetime.now(KST).date().isoformat()
    except Exception:
        return False


def _safe_price(v, default=50.0):
    try:
        if v is None or v == "":
            return float(default)
        out = float(v)
        return max(1.0, min(99.0, out))
    except Exception:
        return float(default)

def analyze_entry_row(row, stake, fair_price, confidence, purpose, category=None, subcategory=None, ai_context="", adv=None):
    """Build deterministic entry judgment only. Claude is called only from the AI research tab."""
    mk = t("시장", "Market")
    oc = t("선택지", "Outcome")
    pc = t("현재가 (¢)", "Price (¢)")
    q = row.get(mk, "") or row.get("Market", "") or "Unknown"
    o = row.get(oc, "") or row.get("Outcome", "") or "Yes"
    tok = str(row.get("token_id", "") or "")
    price = _safe_price(row.get(pc, row.get("Price (¢)", None)), 50.0)
    bankroll = effective_bankroll() or profile().get("assets", 1000.0) or 1000.0
    adv = adv or {}
    if category is None:
        category = infer_market_category(st.session_state.get("entry_url", "") or st.session_state.get("explore_url", ""), q)
    if subcategory is None:
        subcategory = infer_market_subcategory(st.session_state.get("entry_url", "") or st.session_state.get("explore_url", ""), q)
    market_type = adv.get("market_type") or "Match Moneyline"
    _ll = today_loss_limit_status()
    loss_limit_hit = bool(_ll.get("hit"))
    _tilt = tilt_status()
    # loss-adaptive shrink: cap shrinks as today's loss budget is used and on a losing streak
    loss_adapt_factor = 1.0
    if _ll.get("set"):
        loss_adapt_factor = max(0.0, 1.0 - _ll.get("pct", 0.0) / 100.0)
    if _tilt.get("streak", 0) >= 2:
        loss_adapt_factor *= 0.5
    day_locked = day_is_locked()

    data = dict(
        market_name=f"{q} — {o}",
        team_a=o,
        team_b="",
        league=str(subcategory or ""),
        category=category,
        subcategory=subcategory,
        current_price=price,
        fair_price=float(fair_price),
        stake=float(stake),
        purpose=purpose,
        market_type=market_type,
        bankroll=bankroll,
        confidence=confidence,
        target_price=float(adv.get("target_price", min(price + 10, 99.0))),
        stop_price=float(adv.get("stop_price", max(price - 10, 1.0))),
        bookmaker_prob=float(adv.get("bookmaker_prob", 0.0)),
        previous_good_price=float(adv.get("previous_good_price", 0.0)),
        duplicate_ml=float(adv.get("duplicate_ml", 0.0)),
        duplicate_game=float(adv.get("duplicate_game", 0.0)),
        duplicate_side=float(adv.get("duplicate_side", 0.0)),
        fomo_count=int(adv.get("fomo_count", 0)),
        loss_limit_hit=loss_limit_hit,
        tilt_streak=int(_tilt.get("streak", 0)),
        tilt_level=_tilt.get("level", "ok"),
        loss_adapt_factor=loss_adapt_factor,
        day_locked=day_locked,
    )
    result = calculate_entry(data)
    st.session_state.last_entry = result
    st.session_state.prefill_entry = {
        "market_name": f"{q} — {o}",
        "current_price": price,
        "fair_price": float(fair_price),
        "category": category,
        "subcategory": subcategory,
        "market_type": market_type,
        "token_id": tok,
        "outcome": o,
        "note": str(subcategory or ""),
        "stake": float(stake),
    }
    st.session_state.watching_market = {
        "market": f"{q} — {o}",
        "outcome": o,
        "token_id": tok,
        "entry_price": price,
        "fair_price": float(fair_price),
        "stake": float(stake),
        "category": category,
        "subcategory": subcategory,
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
    }
    return result

__all__ = [
    '_display_exit_price',
    '_display_realized',
    '_display_remaining_cost',
    '_display_remaining_shares',
    '_display_sold_shares',
    '_event_kind',
    '_match_event_to_group',
    '_norm_key',
    '_norm_price_cent',
    '_norm_trade_text',
    '_parse_event_amount',
    '_review_widget_key',
    '_safe_float',
    '_safe_price',
    '_safe_review_id_part',
    '_trade_preset',
    '_trade_ts',
    'add_review_items_from_trade_groups',
    'analyze_entry_row',
    'analyze_portfolio_position',
    'build_review_item_from_trade_group',
    'calculate_entry',
    'confidence_caps',
    'confidence_options',
    'current_portfolio_assets',
    'effective_bankroll',
    'exposure_rule',
    'filter_trades_by_date',
    'group_auto_trades_for_pnl',
    'infer_market_category',
    'infer_market_subcategory',
    'is_open_position',
    'link_position_to_trades',
    'link_settlement_events_to_trade_groups',
    'make_review_id_from_trade_group',
    'market_type_options',
    'market_type_rule',
    'parse_trade_datetime',
    'partial_rows',
    'period_pnl',
    'portfolio_asset_summary',
    'portfolio_caps',
    'portfolio_health',
    'portfolio_hidden_summary',
    'portfolio_position_key',
    'price_zone',
    'purpose_options',
    'purpose_rule',
    'recent_completed_trade_rows',
    'safe_trade_float',
    'size_rule',
    'size_thresholds',
    'sort_trades_newest_first',
    'summarize_selected_trade_groups',
    'today_anchor_timestamp',
    'today_loss_limit_status',
    'today_operating_metrics',
    'today_realized_loss_since_anchor',
    'tilt_status',
    'day_is_locked',
    'update_trade_ledger',
    'resolve_trade_row',
    'behavior_insights',
    '_insight_params',
    '_ledger_recs_for_analysis',
    '_mark_stopped_after_losses',
    'RULE_SIM_RULES',
    'rule_simulation',
    'equity_curve_data',
    'calendar_heatmap_data',
    'weekly_report',
    'performance_summary',
    'visible_portfolio_positions',
]
