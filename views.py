# views.py - auto-extracted from streamlit_app.py (behavior-preserving)
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
from engine import *
from data import *

def _ai_plain_fallback(text):
    """If JSON parsing fails, still show a clean report-like card. Never expose the parse failure."""
    import re as _re
    s = str(text or "")
    s = _re.sub(r"```.*?```", " ", s, flags=_re.S)
    s = s.replace("#", "").replace("---", "").replace("{", " ").replace("}", " ").replace('"', "")
    s = _re.sub(r"\s+", " ", s).strip()
    bullets = [seg.strip() for seg in _re.split(r"(?<=[.!?。])\s+", s) if len(seg.strip()) > 8][:6]
    st.markdown(
        f'<div class="verdict"><div class="eyebrow">{t("AI 리서치", "AI research")}</div>'
        f'<div class="v-title" style="font-size:22px;"><span class="dot i"></span>{t("리서치 요약", "Research summary")}</div></div>',
        unsafe_allow_html=True)
    if bullets:
        st.markdown("".join(line(esc(b), "i") for b in bullets), unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="rc-missing"><div class="rc-h">{t("데이터 부족", "Not enough to report")}</div>'
            f'<div>· {t("리서치 메모를 붙여넣고 다시 생성하면 더 정확한 리포트를 만듭니다.", "Paste research notes and regenerate for a fuller report.")}</div></div>',
            unsafe_allow_html=True)

def render_ai_report_json(text):
    """Render the AI research report as a clean, decision-oriented layout.

    Tolerant of both the current schema and older cached reports. Never shows raw
    JSON or a parser failure to the user.
    """
    d = safe_json_parse(text)
    if not isinstance(d, dict) or not d:
        _ai_plain_fallback(text)
        return

    stance = str(_ai_get(d, "stance", "ai_stance")).lower()
    sk = {"favorable": "g", "neutral": "w", "risky": "b"}.get(stance, "i")
    stance_word = {"g": t("우호적", "Favorable"), "w": t("중립", "Neutral"),
                   "b": t("위험", "Risky"), "i": t("판단 보류", "Undecided")}[sk]
    title = esc(_ai_get(d, "report_title", default=t("AI 리서치", "AI research")))
    verdict = esc(_ai_get(d, "verdict", "ai_opinion"))
    prob = esc(_ai_get(d, "estimated_probability", "ai_estimated_probability"))
    conf = str(_ai_get(d, "confidence")).strip().lower()
    ck = {"high": "g", "medium": "w", "low": "b"}.get(conf, "i")
    conf_word = {"g": t("높음", "High"), "w": t("보통", "Medium"),
                 "b": t("낮음", "Low"), "i": "—"}[ck]

    pills = f'<span class="state {sk}">{stance_word}</span>'
    if prob and prob != "확인 필요":
        pills += f' <span class="state i">{t("AI 예상", "AI est.")} {prob}</span>'
    pills += f' <span class="state {ck}">{t("신뢰도", "Confidence")} {conf_word}</span>'

    st.markdown(
        f'<div class="verdict"><div class="eyebrow">{t("AI 리서치", "AI research")}</div>'
        f'<div class="v-title" style="font-size:24px;"><span class="dot {sk}"></span>{title}</div>'
        + (f'<div class="v-sub">{verdict}</div>' if verdict else "")
        + f'<div style="margin-top:12px;">{pills}</div></div>',
        unsafe_allow_html=True)

    basis = esc(_ai_get(d, "data_basis"))
    if basis:
        st.markdown(
            f'<div class="footnote" style="margin:-6px 0 6px 0;">{t("분석 근거", "Based on")}: {basis}</div>',
            unsafe_allow_html=True)

    summary = [x for x in (_ai_get(d, "summary", "summary_bullets", "research_summary", default=[]) or []) if str(x).strip()][:4]
    if summary:
        st.markdown(f'<div class="eyebrow">{t("핵심 요약", "Summary")}</div>'
                    + "".join(line(esc(x), "i") for x in summary), unsafe_allow_html=True)

    # Odds / edge — the numbers Memento already knows, framed.
    od = _ai_get(d, "odds", "odds_table", default={})
    LBL_OD = {
        "polymarket": "Polymarket", "polymarket_price": "Polymarket",
        "implied": t("시장 implied", "Implied"), "polymarket_implied": t("시장 implied", "Implied"),
        "fair": t("내 적정가", "My fair"), "user_fair_price": t("내 적정가", "My fair"),
        "edge": "Edge", "user_edge": "Edge",
        "bookmaker": t("외부배당", "Bookmaker"), "bookmaker_view": t("외부배당", "Bookmaker"),
        "read": t("코멘트", "Read"), "gap_comment": t("코멘트", "Read"),
    }
    if isinstance(od, dict):
        od_rows = [(LBL_OD.get(k, k), str(v)) for k, v in od.items() if str(v).strip()]
        if od_rows:
            st.markdown(f'<div class="eyebrow">{t("배당 · 엣지", "Odds · edge")}</div>'
                        + '<div class="rc-card">'
                        + "".join(f'<div class="rc-row"><span class="rc-k">{esc(k)}</span><span class="rc-v">{esc(v)}</span></div>' for k, v in od_rows)
                        + '</div>', unsafe_allow_html=True)

    # Resolution read — Claude's main value-add, highlighted.
    res = esc(_ai_get(d, "resolution_read", "resolution_check"))
    if res:
        st.markdown(f'<div class="eyebrow">{t("정산 조건 해석", "Resolution read")}</div>'
                    f'<div class="rc-card"><div class="rc-note">{res}</div></div>', unsafe_allow_html=True)

    # Scouting — only shown when there is real content beyond placeholders.
    sc = _ai_get(d, "scouting", "pre_match_table", "context_table", default={})
    LBL_SC = {
        "head_to_head": t("상대전적", "Head-to-head"), "recent_form": t("최근 폼", "Recent form"),
        "standing": t("순위", "Standing"), "league_standing": t("순위", "Standing"),
        "league_record": t("리그 전적", "League record"),
        "roster_news": t("로스터/뉴스", "Roster / news"), "style_matchup": t("스타일 매치업", "Style matchup"),
    }
    if isinstance(sc, dict):
        sc_rows = [(LBL_SC.get(k, k), str(v)) for k, v in sc.items() if str(v).strip()]
        real = [r for r in sc_rows if str(r[1]).strip() not in ("확인 필요", "Verify", "N/A", "-")]
        if real:
            st.markdown(f'<div class="eyebrow">{t("스카우팅", "Scouting")}</div>'
                        + '<div class="rc-card">'
                        + "".join(f'<div class="rc-row"><span class="rc-k">{esc(k)}</span><span class="rc-v">{esc(v)}</span></div>' for k, v in sc_rows)
                        + '</div>', unsafe_allow_html=True)

    swing = [x for x in (_ai_get(d, "swing_factors", "key_variables", default=[]) or []) if str(x).strip()][:5]
    if swing:
        st.markdown(f'<div class="eyebrow">{t("승부처", "Swing factors")}</div>'
                    + "".join(line(esc(x), "w") for x in swing), unsafe_allow_html=True)

    checklist = [x for x in (_ai_get(d, "checklist", default=[]) or []) if str(x).strip()][:6]
    if checklist:
        st.markdown(
            f'<div class="rc-action"><div class="rc-h">{t("진입 전 체크리스트", "Before you enter")}</div>'
            + "".join(f'<div class="rc-row"><span class="rc-k">☐</span><span class="rc-v" style="text-align:left;">{esc(x)}</span></div>' for x in checklist)
            + '</div>', unsafe_allow_html=True)

    md = [x for x in (_ai_get(d, "missing_data", default=[]) or []) if str(x).strip()]
    if md:
        st.markdown(f'<div class="rc-missing"><div class="rc-h">{t("확인 필요 데이터", "Verify yourself")}</div>'
                    + "".join(f"<div>· {esc(x)}</div>" for x in md) + '</div>', unsafe_allow_html=True)

def render_ai(text):
    render_ai_report_json(text)

def render_live_price_panel(wm):
    """Live mid + edge update + real Polymarket price-history chart. Auto-refreshes; read-only."""
    wm = wm if isinstance(wm, dict) else {}
    tok = str(wm.get("token_id", "") or "")
    if not tok:
        st.markdown(line(t("실시간 추적 token_id가 없습니다.", "No token_id for live tracking."), "w"), unsafe_allow_html=True)
        return

    ranges = ["1H", "6H", "1D", "1W", "1M", "MAX"]
    cc1, cc2 = st.columns([3, 1])
    with cc1:
        rng = st.radio(
            t("기간", "Range"),
            ranges,
            index=2,
            horizontal=True,
            key=f"live_rng_{tok}",
            label_visibility="collapsed",
        )
    with cc2:
        if st.button(t("새로고침", "Refresh"), key=f"live_refresh_{tok}", width="stretch"):
            try:
                fetch_live_token_price.clear()
                fetch_price_history.clear()
            except Exception:
                pass
            st.rerun()
    auto = st.checkbox(t("자동 갱신 (15초)", "Auto-refresh (15s)"), value=True, key=f"live_auto_{tok}")

    def _body():
        lp = fetch_live_token_price(tok)
        if not lp or lp.get("mid") is None:
            st.markdown(line(t("실시간 호가 없음 — Polymarket에서 직접 확인 필요.", "No live book — verify on Polymarket."), "w"), unsafe_allow_html=True)
            return
        live = float(lp["mid"])
        r = st.session_state.get("last_entry", {})
        r = r if isinstance(r, dict) else {}
        ev = evaluate_live_price(r, live)
        st.markdown(
            '<div class="stats">'
            + stat(t("실시간 중간가", "Live mid"), cents(live), t(f"분석시 {cents(wm.get('entry_price', 0))}", f"at analysis {cents(wm.get('entry_price', 0))}"))
            + stat("Bid / Ask", f"{cents(float(lp['bid'])) if lp.get('bid') is not None else '—'} / {cents(float(lp['ask'])) if lp.get('ask') is not None else '—'}", f"{t('스프레드','spread')} {cents(float(lp['spread'])) if lp.get('spread') is not None else '—'}")
            + stat(t("실시간 Edge", "Live edge"), f"{ev['edge']:+.1f}¢", t("적정가 대비", "vs fair"), "pos" if ev['edge'] >= 3 else "neg" if ev['edge'] < 0 else "")
            + stat(t("분석 후 변동", "Move since"), f"{ev['move']:+.1f}¢", t("시장 가격 변화", "market move"), "pos" if ev['move'] >= 0 else "neg")
            + "</div>", unsafe_allow_html=True)
        st.markdown(meter(t("시장 판단 vs 내 판단", "Market view vs my view"), live, ev["kind"], ev["status"], unit="¢"), unsafe_allow_html=True)

        hist = fetch_price_history(tok, rng)
        if not hist:
            st.markdown(f'<div class="footnote">{t("이 기간의 가격 히스토리가 아직 없습니다.", "No price history for this range yet.")}</div>', unsafe_allow_html=True)
            return
        dfh = pd.DataFrame(hist)
        try:
            # Polymarket usually returns unix seconds. Guard ms timestamps too.
            t_numeric = pd.to_numeric(dfh["t"], errors="coerce")
            unit = "ms" if t_numeric.dropna().max() and t_numeric.dropna().max() > 10**11 else "s"
            dfh["ts"] = pd.to_datetime(t_numeric, unit=unit, errors="coerce")
            dfh = dfh.dropna(subset=["ts", "p"])
        except Exception:
            dfh["ts"] = pd.to_datetime(dfh.index, unit="s", errors="coerce")
        if dfh.empty:
            st.markdown(f'<div class="footnote">{t("차트로 표시할 수 있는 가격 데이터가 없습니다.", "No chartable price data.")}</div>', unsafe_allow_html=True)
            return
        try:
            import altair as alt
            lo, hi = float(dfh["p"].min()), float(dfh["p"].max())
            pad = max(1.5, (hi - lo) * 0.2)
            dom = [max(0.0, lo - pad), min(100.0, hi + pad)]
            base = alt.Chart(dfh).encode(
                x=alt.X(
                    "ts:T",
                    title=None,
                    axis=alt.Axis(grid=False, labelColor="#a2a5af", tickColor="#e9eaee", domainColor="#e9eaee"),
                )
            )
            area = base.mark_area(
                line={"color": "#3b4ef0", "strokeWidth": 2},
                color=alt.Gradient(
                    gradient="linear",
                    x1=1,
                    x2=1,
                    y1=1,
                    y2=0,
                    stops=[
                        alt.GradientStop(color="#ffffff", offset=0),
                        alt.GradientStop(color="#e9ecfe", offset=1),
                    ],
                ),
            ).encode(
                y=alt.Y(
                    "p:Q",
                    title=None,
                    scale=alt.Scale(domain=dom),
                    axis=alt.Axis(grid=True, gridColor="#f0f1f4", labelColor="#a2a5af", tickColor="#e9eaee", domainColor="#e9eaee"),
                ),
                tooltip=[alt.Tooltip("ts:T", title="time"), alt.Tooltip("p:Q", title="¢", format=".1f")],
            )
            layers = [area]
            try:
                fairf = float(wm.get("fair_price") or 0)
            except Exception:
                fairf = 0.0
            if fairf:
                layers.append(
                    alt.Chart(pd.DataFrame({"y": [fairf]}))
                    .mark_rule(strokeDash=[4, 4], color="#a2a5af")
                    .encode(y="y:Q")
                )
            st.altair_chart(alt.layer(*layers).properties(height=210).configure_view(strokeWidth=0), width="stretch")
        except Exception:
            st.line_chart(dfh.set_index("ts")["p"], height=210)

    frag = getattr(st, "fragment", None) or getattr(st, "experimental_fragment", None)
    if auto and frag:
        try:
            frag(run_every=15)(_body)()
            return
        except Exception:
            pass
    _body()
    if auto and not frag:
        st.markdown(f'<div class="footnote">{t("자동 갱신은 Streamlit 1.37+에서 지원됩니다. 새로고침 버튼을 눌러 갱신하세요.", "Auto-refresh needs Streamlit 1.37+. Use the Refresh button.")}</div>', unsafe_allow_html=True)

def market_card_html(row, clob=None, book=None, hist=None, cand=None):
    name = row_get(row, "시장", "Market", "Unknown")
    outcome = row_get(row, "선택지", "Outcome", "")
    price = row_get(row, "현재가 (¢)", "Price (¢)", None)
    token = row.get("token_id", "") if isinstance(row, dict) else ""
    clob = clob or {}
    book = book or {}
    hist = hist or {}
    cand = cand or {}
    bid = clob.get("bid")
    ask = clob.get("ask")
    spread = clob.get("spread")
    hs = history_summary(hist)
    bs = book_summary(book)
    price_text = cents(float(price)) if isinstance(price, (int, float)) else "—"
    bid_text = cents(float(bid)) if isinstance(bid, (int, float)) else "—"
    ask_text = cents(float(ask)) if isinstance(ask, (int, float)) else "—"
    spread_text = cents(float(spread)) if isinstance(spread, (int, float)) else "—"
    ch = hs.get("change")
    hist_text = signed_pct(ch) if isinstance(ch, (int, float)) else "—"
    token_short = str(token)[:8] + "…" if token else "—"
    vol = row.get("volume", "") if isinstance(row, dict) else ""
    liq = row.get("liquidity", "") if isinstance(row, dict) else ""
    end_date = row.get("endDate", "") if isinstance(row, dict) else ""
    resolution = str(row.get("resolution", "") or "")[:180]
    cand_note = cand.get("note", "")
    cand_kind = cand.get("kind", "i")
    return html_block(f"""<div class=\"market-card\">
  <div class=\"market-head\">
    <div>
      <div class=\"market-title\">{_escape(name)}</div>
      <div class=\"market-sub\">{t('선택지', 'Outcome')} · <b>{_escape(outcome)}</b></div>
    </div>
    <div class=\"market-price\">{price_text}</div>
  </div>
  <div class=\"market-metrics\">
    <div class=\"market-metric\"><div class=\"k\">Best bid</div><div class=\"v\">{bid_text}</div></div>
    <div class=\"market-metric\"><div class=\"k\">Best ask</div><div class=\"v\">{ask_text}</div></div>
    <div class=\"market-metric\"><div class=\"k\">Spread</div><div class=\"v\">{spread_text}</div></div>
    <div class=\"market-metric\"><div class=\"k\">History</div><div class=\"v\">{hist_text}</div></div>
    <div class=\"market-metric\"><div class=\"k\">Volume</div><div class=\"v\">{_escape(vol or '—')}</div></div>
    <div class=\"market-metric\"><div class=\"k\">Liquidity</div><div class=\"v\">{_escape(liq or '—')}</div></div>
    <div class=\"market-metric\"><div class=\"k\">Book</div><div class=\"v\">B{bs.get('bids',0)} / A{bs.get('asks',0)}</div></div>
    <div class=\"market-metric\"><div class=\"k\">Token</div><div class=\"v\">{_escape(token_short)}</div></div>
  </div>
  <div class=\"market-note\"><b>{t('주문 후보', 'Order candidate')}</b> · <span class=\"state {cand_kind}\">{_escape(cand_note)}</span> · {t('실제 주문은 원본 Polymarket에서 확인하세요.', 'Confirm actual orders on Polymarket.')}</div>
  <div class=\"market-note\"><b>{t('만기/해결 기준', 'End / resolution')}</b> · {_escape(end_date or '—')} · {_escape(resolution or t('데이터 없음/직접 확인 필요', 'No data / verify manually'))}</div>
</div>""")

def render_profile_pnl_dashboard(pnl):
    kind = pnl.get("status_kind", "i")
    prof_line = st.session_state.wallet_addr[:6] + "…" + st.session_state.wallet_addr[-4:] if st.session_state.wallet_addr else t("지갑 미연결", "No wallet")
    adj_tone = "pos" if pnl.get("adjusted_profit", 0) >= 0 else "neg"
    un_tone = "pos" if pnl.get("unrealized", 0) >= 0 else "neg"
    yr_tone = "pos" if pnl.get("year_pnl", 0) >= 0 else "neg"
    roi_val = pnl.get("adjusted_roi")
    roi_text = signed_pct(roi_val) if roi_val is not None else "—"
    html = f"""<div class='profile-hero'>
  <div class='profile-hero-head'>
    <div><div class='title'><span class='dot {kind}'></span>{esc(pnl.get('status_text', ''))}</div>
    <div class='sub'>{t('Polymarket 프로필 손익 요약', 'Polymarket profile P&L summary')} · {esc(prof_line)} · {esc(pnl.get('source_note', ''))}</div></div>
    <span class='state {kind}'>{esc(pnl.get('status_text', ''))}</span>
  </div>
  <div class='profile-grid'>
    <div class='profile-cell'><div class='k'>{t('현재 포지션 가치', 'Position value')}</div><div class='v'>{money(pnl.get('position_value', 0))}</div></div>
    <div class='profile-cell'><div class='k'>{t('지갑 총자산', 'Wallet assets')}</div><div class='v'>{money(pnl.get('wallet_assets', 0))}</div></div>
    <div class='profile-cell'><div class='k'>{t('출금보정 누적손익', 'Cashflow-adjusted P&L')}</div><div class='v {adj_tone}'>{signed_money(pnl.get('adjusted_profit', 0))}</div></div>
    <div class='profile-cell'><div class='k'>{t('보정 수익률', 'Adjusted ROI')}</div><div class='v {adj_tone}'>{roi_text}</div></div>
    <div class='profile-cell'><div class='k'>{t('올해 손익', 'Year P&L')}</div><div class='v {yr_tone}'>{signed_money(pnl.get('year_pnl', 0))}</div></div>
    <div class='profile-cell'><div class='k'>realizedPnl</div><div class='v'>{signed_money(pnl.get('realized_pnl', 0))}</div></div>
  </div>
  <div class='sub' style='margin-top:14px;'>{t('Polymarket 프로필 화면과 소액 차이가 날 수 있습니다. 출금·입금·정산·dust 포지션은 보정값과 API 필드에 따라 달라집니다.', 'This can differ slightly from the Polymarket profile due to withdrawals, deposits, settlements and dust positions.')}</div>
</div>"""
    st.markdown(html_block(html), unsafe_allow_html=True)

def _on_trade_qf_change():
    # Radio uses internal code values, not translated labels.
    code = st.session_state.get("trade_qf_select", "all")
    st.session_state.trade_qf = code
    start_date, end_date = _trade_preset(code, datetime.now(KST).date())
    if start_date is not None:
        # Callback runs before the next script rerun, so updating widget-backed
        # date state here is safe and prevents stale date_input values.
        st.session_state.trade_start_date = start_date
        st.session_state.trade_end_date = end_date

def _on_trade_date_change():
    # Manual date edits must override any quick-filter preset. Keep the radio
    # widget state in sync so it visibly moves to Custom on the next rerun.
    st.session_state.trade_qf = "custom"
    st.session_state.trade_qf_select = "custom"

def render_trade_date_controls():
    today = datetime.now(KST).date()

    # Defaults and safety checks happen before widget rendering.
    if not isinstance(st.session_state.get("trade_start_date"), date):
        st.session_state.trade_start_date = today - timedelta(days=30)
    if not isinstance(st.session_state.get("trade_end_date"), date):
        st.session_state.trade_end_date = today

    codes = [code for code, _, _ in QF_DEF]
    if st.session_state.get("trade_qf") not in codes:
        st.session_state.trade_qf = "all"
    if st.session_state.get("trade_qf_select") not in codes:
        st.session_state.trade_qf_select = st.session_state.get("trade_qf", "all")

    # If a quick preset is already selected when the page reruns, make sure the
    # displayed date widgets and the actual filter stay aligned.
    if st.session_state.trade_qf_select != st.session_state.trade_qf:
        st.session_state.trade_qf_select = st.session_state.trade_qf
    preset_start, preset_end = _trade_preset(st.session_state.trade_qf, today)
    if preset_start is not None:
        st.session_state.trade_start_date = preset_start
        st.session_state.trade_end_date = preset_end

    st.markdown(f'<div class="eyebrow">{t("기간 선택", "Date range")}</div>', unsafe_allow_html=True)
    st.radio(
        "qf",
        codes,
        format_func=lambda code: t(QF_LABEL[code][0], QF_LABEL[code][1]),
        horizontal=True,
        label_visibility="collapsed",
        key="trade_qf_select",
        on_change=_on_trade_qf_change,
    )

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input(t("시작일", "Start"), key="trade_start_date", on_change=_on_trade_date_change)
    with c2:
        end_date = st.date_input(t("종료일", "End"), key="trade_end_date", on_change=_on_trade_date_change)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    if st.session_state.get("trade_qf", "all") == "all":
        return None, None, t("전체 기간", "All time")
    return start_date, end_date, f"{start_date.isoformat()} ~ {end_date.isoformat()}"

def render_trade_pnl_summary(auto_trades, date_label="", title=None, key_prefix="", events=None):
    rows = group_auto_trades_for_pnl(auto_trades)
    if events:
        rows = link_settlement_events_to_trade_groups(rows, events)
    if not rows:
        st.markdown(f'<div class="footnote">{t("해당 기간 거래내역이 없습니다.", "No trades in this range.")}</div>', unsafe_allow_html=True)
        return

    s0 = summarize_selected_trade_groups(rows, [])
    range_label = f" · {date_label}" if date_label else ""
    header_text = title or t("거래내역 기준 추정손익", "Estimated P&L from trade history")
    linked_count = sum(1 for r in rows if r.get("_adjusted"))
    st.markdown(f'<div class="eyebrow" style="margin-top:16px;">{header_text}{range_label}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="stats">'
        + stat(t("총 매수금", "Buy cost"), money(s0["buy_cost"]), "")
        + stat(t("총 회수금", "Recovered"), money(s0["sell_proceeds"]), t("매도금+정산금", "proceeds+settlement"))
        + stat(t("실현손익(추정)", "Realized (est)"), signed_money(s0["realized_pnl"]), t("정산 이벤트 반영", "settlement events applied") if linked_count else t("매도금−대응매수원가", "proceeds−matched cost"), "pos" if s0["realized_pnl"] >= 0 else "neg")
        + stat(t("잔여 수량", "Remaining"), f'{s0["remaining_shares"]:.2f}', t(f"원가 {money(s0['remaining_cost'])}", f"cost {money(s0['remaining_cost'])}"))
        + "</div>", unsafe_allow_html=True)
    if linked_count:
        st.markdown(line(t(f"정산/손실 이벤트 {linked_count}건을 거래 요약에 자동 연결했습니다.", f"Auto-linked {linked_count} settlement/loss event(s) to trade summaries."), "g"), unsafe_allow_html=True)
    if s0["unverified"]:
        st.markdown(line(t("일부 정산 항목은 금액 정보가 없어 손익 확인이 필요합니다.", "Some settlement rows have no amount; P&L needs review."), "w"), unsafe_allow_html=True)
    st.markdown(f'<div class="footnote">{t("추정치입니다. 공식 포트폴리오 손익과 별개이며 아직 합산하지 않습니다.", "Estimate only. Separate from official portfolio P&L; not merged yet.")}</div>', unsafe_allow_html=True)

    source = "wallet" if str(key_prefix or "").startswith("wallet") else "paste"
    for idx, r in enumerate(rows):
        res = resolve_trade_row(r)
        pnl = res["realized_final"]
        pnl_text = t("확인 필요", "Verify") if pnl is None else signed_money(pnl)
        pnl_cls = "i" if pnl is None else ("g" if pnl >= 0 else "b")
        latest = r.get("latest_dt") or t("시간 확인 필요", "time unknown")
        status_text = res["status_final"]
        rem_shares = _display_remaining_shares(r)
        rem_cost = _display_remaining_cost(r)
        closed_shares = _display_sold_shares(r)
        exit_price = _display_exit_price(r)
        pnl_label = t("실현손익(확정)", "Realized (resolved)") if res["resolved"] else (t("실현손익(추정 · 정산반영)", "Realized est. · settlement applied") if r.get("_adjusted") else t("실현손익(추정)", "Realized est."))
        note_parts = [f'{t("체결 수", "Fills")}: {int(r.get("fills", 0))}']
        if r.get("linked_event_note"):
            note_parts.append(str(r.get("linked_event_note")))
            if r.get("linked_event_shares") is not None:
                note_parts.append(f'{float(r.get("linked_event_shares")):.2f} {t("주", "shares")}')
            if r.get("linked_event_amount") is not None:
                note_parts.append(money(float(r.get("linked_event_amount"))))
        # 미확정 보유 포지션 힌트: 매도·정산이 없어 결과가 안 정해진 거래는 수동 승/패 확정이 필요하다.
        # (콤보/팔레이는 자동 확정이 불가능하므로 특히 안내) — 왼쪽 체크박스를 켜면 확정 라디오가 나온다.
        needs_resolve = (not res["resolved"]) and (not r.get("_adjusted")) and rem_shares > 1e-6 and closed_shares <= 1e-6
        resolve_hint_html = ""
        if needs_resolve:
            _hint = t("결과 미확정 · 아래 버튼으로 승/패 확정",
                      "Unresolved · use the buttons below to mark Won/Lost")
            if r.get("combo"):
                _hint = t("콤보는 자동 확정 불가 · 아래 버튼으로 승/패 확정",
                          "Combos can't auto-resolve · use the buttons below")
            resolve_hint_html = f'<div style="margin-top:6px;"><span class="state w">{_hint}</span></div>'
        rid = make_review_id_from_trade_group(r, source)
        csel, cbody = st.columns([0.28, 3.72])
        with csel:
            open_flag = st.checkbox(
                t("손익 계산 열기", "Open P&L"),
                key=f"review_send_{key_prefix}_{idx}_{rid}",
                label_visibility="collapsed",
            )
        with cbody:
            _pnl_color = "#9aa0aa" if pnl is None else ("#16a34a" if pnl >= 0 else "#dc2626")
            # html_block 필수: {resolve_hint_html}가 빈 값이면 공백 줄이 생기고, 마크다운이 거기서
            # HTML 블록을 끝낸 뒤 4칸 들여쓴 아래 줄들을 코드블록으로 노출한다 (카드에 태그가 글자로 보이던 버그).
            st.markdown(
                html_block(f'''<div class="pf-card" style="margin:10px 0;">
  <div class="pf-card-head">
    <div>
      <div class="pf-title">{esc(r.get("market"))}</div>
      <div class="pf-pills">{outcome_pill(r.get("outcome"))}{"" if r.get("combo") else cents_pill(r.get("avg_buy_price", 0))}</div>
      <div class="pf-sub">{esc(latest)} · {esc(status_text)}</div>
      {resolve_hint_html}
    </div>
    <div style="text-align:right;min-width:96px;">
      <div style="font-size:22px;font-weight:800;line-height:1.15;color:{_pnl_color};">{pnl_text}</div>
      <div class="pf-sub">{pnl_label}</div>
    </div>
  </div>
  <div class="pf-metrics">
    <div class="pf-metric"><div class="k">{t("평균 매수", "Avg buy")}</div><div class="v">{t("콤보", "Combo") if r.get("combo") else cents(r.get("avg_buy_price", 0))}</div></div>
    <div class="pf-metric"><div class="k">{t("평균 청산", "Avg exit")}</div><div class="v">{cents(exit_price) if closed_shares > 0 else "—"}</div></div>
    <div class="pf-metric"><div class="k">{t("매수/청산 수량", "Bought/Closed")}</div><div class="v">{r.get("bought_shares", 0):.2f} / {closed_shares:.2f}</div></div>
    <div class="pf-metric"><div class="k">{t("매수금/회수금", "Cost/Recovered")}</div><div class="v">{money(r.get("buy_cost", 0))} / {money(r.get("adjusted_effective_proceeds", r.get("sell_proceeds", 0)))}</div></div>
    <div class="pf-metric"><div class="k">{t("잔여 노출", "Remaining exposure")}</div><div class="v">{rem_shares:.2f} · {money(rem_cost)}</div></div>
  </div>
  <div class="pf-note">{esc(" · ".join(note_parts))}</div>
</div>'''),
                unsafe_allow_html=True,
            )
            # 미확정 보유분: 카드에서 바로 원클릭 승/패 확정 (체크박스 열 필요 없음).
            # 폴리마켓 API가 진 콤보의 손실을 안 주므로, 손실인데 '보유 중 $0'으로 뜨는 걸 여기서 즉시 확정.
            if needs_resolve and not open_flag:
                _q1, _q2, _q3 = st.columns([1.1, 1.1, 2.6])
                _qkey = r.get("key")
                with _q1:
                    if st.button(t("패로 확정", "Mark Lost"), key=f"quick_lost_{key_prefix}_{idx}", width="stretch"):
                        _rm = dict(st.session_state.get("trade_resolutions") or {})
                        _rm[_qkey] = "lost"
                        st.session_state.trade_resolutions = _rm
                        save_local_state()
                        st.rerun()
                with _q2:
                    if st.button(t("승으로 확정", "Mark Won"), key=f"quick_won_{key_prefix}_{idx}", width="stretch"):
                        _rm = dict(st.session_state.get("trade_resolutions") or {})
                        _rm[_qkey] = "won"
                        st.session_state.trade_resolutions = _rm
                        save_local_state()
                        st.rerun()
                with _q3:
                    st.markdown(f'<div class="footnote" style="padding-top:8px;">{t(f"패 = −{money(rem_cost)} 반영", f"Lost = −{money(rem_cost)}")}</div>', unsafe_allow_html=True)
            if open_flag:
                # 체크하면 그 거래 카드 바로 밑에 손익 계산 박스가 인라인으로 뜬다 (스크롤/하단버튼 불필요).
                buy_cost = float(r.get("buy_cost", 0) or 0)
                recovered = float(r.get("adjusted_effective_proceeds", r.get("sell_proceeds", 0)) or 0)
                _final = res["realized_final"]
                _final_txt = t("확인 필요", "Verify") if _final is None else signed_money(_final)
                calc_lines = [
                    (t("총 매수금", "Buy cost"), f"−{money(buy_cost)}"),
                    (t("회수금 (매도+정산)", "Recovered"), f"+{money(recovered)}"),
                ]
                if res["resolved"] == "won":
                    calc_lines.append((t("승(상환) — 잔여 $1 상환", "Won — redeemed at $1"),
                                       f"+{money(rem_shares)} − {money(rem_cost)}"))
                elif res["resolved"] == "lost":
                    calc_lines.append((t("패(소멸) — 잔여 원가 소멸", "Lost — cost written off"),
                                       f"−{money(rem_cost)}"))
                elif rem_shares > 1e-6:
                    calc_lines.append((t("잔여 노출 (미확정)", "Remaining (unresolved)"),
                                       f"{rem_shares:.2f}{t('주','sh')} · {money(rem_cost)}"))
                _rows_html = "".join(
                    f'<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:13px;">'
                    f'<span style="color:#6b7280;">{esc(_k)}</span>'
                    f'<span style="font-variant-numeric:tabular-nums;color:#374151;">{esc(_v)}</span></div>'
                    for _k, _v in calc_lines
                )
                st.markdown(
                    html_block(f'''<div style="margin:2px 0 8px 0;padding:12px 14px;border:1px solid rgba(2,6,23,.08);border-radius:14px;background:rgba(255,255,255,.66);">
  <div style="font-size:11px;font-weight:700;letter-spacing:.03em;color:#9aa0aa;margin-bottom:6px;">{t("손익 계산", "P&L BREAKDOWN")}</div>
  {_rows_html}
  <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;padding-top:8px;border-top:1px solid rgba(2,6,23,.07);">
    <span style="font-size:13px;font-weight:700;color:#374151;">{t("실현손익", "Realized P&L")}</span>
    <span style="font-size:20px;font-weight:800;color:{_pnl_color};font-variant-numeric:tabular-nums;">{_final_txt}</span>
  </div>
</div>'''),
                    unsafe_allow_html=True,
                )
                if rem_shares > 1e-6:
                    _opts = ["", "won", "lost"]
                    _lbl = {"": t("자동", "Auto"), "won": t("승(상환)", "Won"), "lost": t("패(소멸)", "Lost")}
                    _cur = str((st.session_state.get("trade_resolutions") or {}).get(r.get("key"), "") or "")
                    _pick = st.radio(
                        t("결과 확정 — 보유분이 이기면 승, 지면 패", "Resolve held shares — Won / Lost"),
                        _opts, index=_opts.index(_cur) if _cur in _opts else 0,
                        format_func=lambda x: _lbl[x], horizontal=True,
                        key=f"resolve_{key_prefix}_{idx}",
                    )
                    if _pick != _cur:
                        _rmap = dict(st.session_state.get("trade_resolutions") or {})
                        if _pick:
                            _rmap[r.get("key")] = _pick
                        else:
                            _rmap.pop(r.get("key"), None)
                        st.session_state.trade_resolutions = _rmap
                        save_local_state()
                        st.rerun()
                # --- 감정·행동 태그: '감정적일 때 얼마 잃는지'의 재료 (거래복기 탭 행동 인사이트에 집계) ---
                _ekey = str(r.get("key") or "")
                if _ekey:
                    _emap = st.session_state.get("trade_emotions") or {}
                    _etag = _emap.get(_ekey) if isinstance(_emap.get(_ekey), dict) else {}
                    _cur_emo = int(_safe_float((_etag or {}).get("emotion"), 0))
                    _cur_emo = _cur_emo if 0 <= _cur_emo <= 5 else 0
                    _cur_chase = bool((_etag or {}).get("chase"))
                    _emo_lbl = {0: t("기록 없음", "none"), 1: "1 · " + t("침착", "calm"),
                                2: "2", 3: "3", 4: "4", 5: "5 · " + t("틸트", "tilt")}
                    ec1, ec2 = st.columns([2.6, 1.4])
                    with ec1:
                        _emo = st.radio(
                            t("진입 당시 감정 (1 침착 ~ 5 틸트/충동)", "Emotion at entry (1 calm – 5 tilt)"),
                            [0, 1, 2, 3, 4, 5], index=[0, 1, 2, 3, 4, 5].index(_cur_emo),
                            format_func=lambda x: _emo_lbl[x], horizontal=True,
                            key=f"emo_{key_prefix}_{idx}",
                        )
                    with ec2:
                        _chase = st.checkbox(
                            t("추격 진입(손실 만회)", "Chase entry"),
                            value=_cur_chase, key=f"chase_{key_prefix}_{idx}",
                            help=t("직전 손실을 만회하려고 들어간 거래면 체크", "Check if this entry was chasing/revenge after a loss"),
                        )
                    if int(_emo) != _cur_emo or bool(_chase) != _cur_chase:
                        _em2 = dict(st.session_state.get("trade_emotions") or {})
                        if int(_emo) or bool(_chase):
                            _em2[_ekey] = {"emotion": int(_emo), "chase": bool(_chase),
                                           "updated_at": datetime.now(KST).isoformat(timespec="minutes")}
                        else:
                            _em2.pop(_ekey, None)
                        st.session_state.trade_emotions = _em2
                        save_local_state()
                    st.markdown(f'<div class="footnote" style="margin:2px 0 6px 0;">{t("감정 기록은 거래복기 탭 ‘행동 인사이트’에 집계됩니다.", "Emotion tags feed Behavior insights in the Trade Review tab.")}</div>', unsafe_allow_html=True)
                if st.button(t("이 거래를 거래복기로 보내기", "Send this trade to Review"),
                             key=f"send_one_{key_prefix}_{idx}", width="stretch"):
                    added = add_review_items_from_trade_groups([r], source)
                    if added:
                        st.success(t("거래복기에 추가했습니다.", "Added to Trade Review."))
                    else:
                        st.info(t("이미 거래복기에 있는 항목입니다.", "Already in Trade Review."))

def render_performance_summary(key_prefix="perf"):
    """All-time win/loss + category performance from the durable trade ledger."""
    s = performance_summary()
    if not s["n"]:
        st.markdown(line(t("아직 확정된 거래가 없습니다 — 거래를 동기화하고 보유 거래의 승/패를 확정하면 성과가 집계됩니다.",
                           "No settled trades yet — sync trades and mark held trades Won/Lost to see performance."), "i"), unsafe_allow_html=True)
        return
    pf = s["profit_factor"]
    pf_text = "∞" if pf is None else f"{pf:.2f}"
    st.markdown(f'<div class="eyebrow" style="margin-top:6px;">{t("승패 · 카테고리 성과 (전체 · 장부 기준)", "Win/loss & category performance (all-time)")}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="stats">'
        + stat(t("승률", "Win rate"), f'{s["win_rate"]:.0f}%', t(f'{s["wins"]}승 {s["losses"]}패 · {s["n"]}건', f'{s["wins"]}W {s["losses"]}L · {s["n"]}'))
        + stat(t("총 실현손익", "Total realized"), signed_money(s["total_pnl"]), "", "pos" if s["total_pnl"] >= 0 else "neg")
        + stat(t("손익비(PF)", "Profit factor"), pf_text, t("총이익÷총손실", "gross win ÷ loss"))
        + stat(t("평균 이익 / 손실", "Avg win / loss"), f'{money(s["avg_win"])} / {money(-s["avg_loss"])}', t("비대칭 점검", "asymmetry"))
        + "</div>", unsafe_allow_html=True)
    cats = s["by_category"]
    if cats:
        cells = ""
        for cat, c in sorted(cats.items(), key=lambda kv: kv[1]["pnl"]):
            wr = (c["wins"] / c["n"] * 100) if c["n"] else 0
            tone = "pos" if c["pnl"] >= 0 else "neg"
            cells += (f'<div class="pf-metric"><div class="k">{esc(cat)} · {c["n"]}건 · {wr:.0f}%</div>'
                      f'<div class="v {tone}">{signed_money(c["pnl"])}</div></div>')
        st.markdown(f'<div class="eyebrow" style="margin-top:10px;">{t("카테고리별", "By category")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="pf-metrics">{cells}</div>', unsafe_allow_html=True)


def render_behavior_insights(key_prefix="bi"):
    """감정·행동 복기 인사이트 — 감정적/규칙위반 거래가 실제로 얼마를 잃게 했는지 숫자로 보여준다."""
    ins = behavior_insights()
    st.markdown(f'<div class="eyebrow" style="margin-top:6px;">{t("행동 인사이트 — 감정적일 때 얼마 잃는가", "Behavior insights — what emotion costs you")}</div>', unsafe_allow_html=True)
    if not ins["n"]:
        st.markdown(line(t("확정된 거래가 쌓이면 여기서 감정·추격·규칙위반 비용이 집계됩니다. 거래일지의 손익 계산 박스에서 승/패 확정과 감정(1~5)을 기록하세요.",
                           "Once settled trades accumulate, emotion/chase/rule-violation costs appear here. Mark Won/Lost and tag emotion (1–5) in the Journal P&L box."), "i"), unsafe_allow_html=True)
        return
    emo_n, tilt, calm, chase, viol = ins["tagged"], ins["tilt"], ins["calm"], ins["chase"], ins["violation"]
    corr_note = (t(f"감정↔손익 상관 {ins['corr']:+.2f}", f"emotion↔P&L corr {ins['corr']:+.2f}")
                 if ins["corr"] is not None else t("3건 이상 기록하면 상관 표시", "corr shows after 3+ tags"))
    st.markdown(
        '<div class="stats">'
        + stat(t("감정적 거래 손익", "Emotional trades P&L"), signed_money(ins["emotional"]["pnl"]),
               t(f'{ins["emotional"]["n"]}건 · 틸트(4~5)+추격 합집합', f'{ins["emotional"]["n"]} trades · tilt(4–5)+chase'),
               "pos" if ins["emotional"]["pnl"] >= 0 else "neg")
        + stat(t("추격 재진입 손익", "Chase re-entry P&L"), signed_money(chase["pnl"]),
               t(f'{chase["n"]}건 · 자동감지 {chase["detected"]} · 직접표시 {chase["flagged"]}',
                 f'{chase["n"]} · auto {chase["detected"]} · flagged {chase["flagged"]}'),
               "pos" if chase["pnl"] >= 0 else "neg")
        + stat(t("규칙위반 손익", "Rule-violation P&L"), signed_money(viol["pnl"]),
               t(f'{viol["n"]}건 · {ins["high_price"]["threshold"]:.0f}¢+ 진입/과대베팅',
                 f'{viol["n"]} · {ins["high_price"]["threshold"]:.0f}¢+ entry/oversized'),
               "pos" if viol["pnl"] >= 0 else "neg")
        + stat(t("감정 기록", "Emotion tags"), f'{emo_n}/{ins["n"]}', corr_note)
        + "</div>", unsafe_allow_html=True)
    if ins["by_emotion"]:
        _lvl_lbl = {1: t("침착", "calm"), 2: t("안정", "steady"), 3: t("보통", "neutral"), 4: t("불안", "shaky"), 5: t("틸트", "tilt")}
        cells = ""
        for lvl, b in ins["by_emotion"].items():
            tone = "pos" if b["pnl"] >= 0 else "neg"
            cells += (f'<div class="pf-metric"><div class="k">{lvl} {_lvl_lbl.get(lvl, "")} · {b["n"]}건 · {b["win_rate"]:.0f}%</div>'
                      f'<div class="v {tone}">{signed_money(b["pnl"])}</div></div>')
        st.markdown(f'<div class="eyebrow" style="margin-top:10px;">{t("감정점수별 손익", "P&L by emotion score")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="pf-metrics">{cells}</div>', unsafe_allow_html=True)
        if calm["n"] and tilt["n"]:
            gap = calm["pnl"] - tilt["pnl"]
            st.markdown(line(t(
                f'침착(1~2) {calm["n"]}건 합계 {signed_money(calm["pnl"])} vs 틸트(4~5) {tilt["n"]}건 합계 {signed_money(tilt["pnl"])} — 차이 {money(abs(gap))}',
                f'Calm (1–2) {calm["n"]} trades {signed_money(calm["pnl"])} vs tilt (4–5) {tilt["n"]} trades {signed_money(tilt["pnl"])} — gap {money(abs(gap))}'),
                "b" if tilt["pnl"] < 0 else "i"), unsafe_allow_html=True)
    hp, ov = ins["high_price"], ins["oversized"]
    if hp["n"] or ov["n"]:
        _lim_txt = money(ov["limit"]) if ov["limit"] > 0 else t("미설정", "not set")
        _hp_thr = hp["threshold"]
        st.markdown(line(t(
            f'{_hp_thr:.0f}¢ 이상 진입 {hp["n"]}건 {signed_money(hp["pnl"])} · 과대베팅(감정 한도 {_lim_txt} 초과) {ov["n"]}건 {signed_money(ov["pnl"])}',
            f'Entries at {_hp_thr:.0f}¢+ {hp["n"]} {signed_money(hp["pnl"])} · oversized (> emotional limit {_lim_txt}) {ov["n"]} {signed_money(ov["pnl"])}'),
            "w" if (hp["pnl"] + ov["pnl"]) < 0 else "i"), unsafe_allow_html=True)
    _win = int(ins["window_min"])
    st.markdown(f'<div class="footnote">{t(f"감정·추격 태그는 거래일지 → 손익 계산 박스에서 기록합니다. 추격 자동감지 = 손실 정산 후 {_win}분 내 첫 매수.", f"Tag emotion/chase in Journal → P&L box. Chase auto-detect = first buy within {_win} min after a loss settles.")}</div>', unsafe_allow_html=True)


def _heat_color(pnl, scale):
    """캘린더 셀 색: 수익=초록·손실=빨강(다이버징, 중립=회색), |손익|이 클수록 짙게."""
    if pnl is None:
        return "var(--surface-2)"
    if abs(pnl) < 1e-9:
        return "#e5e7eb"
    a = 0.25 + 0.75 * min(abs(pnl) / max(scale, 1e-9), 1.0)
    return f"rgba(15,122,67,{a:.2f})" if pnl > 0 else f"rgba(197,54,47,{a:.2f})"


def render_equity_section(key_prefix="eq"):
    """자산 곡선(누적 실현손익 + MDD)과 일별 손익 캘린더 — 장부 기준."""
    eq = equity_curve_data()
    st.markdown(f'<div class="eyebrow" style="margin-top:14px;">{t("자산 곡선 · 일별 캘린더 (장부 기준)", "Equity curve · daily calendar (ledger)")}</div>', unsafe_allow_html=True)
    if not eq["days"]:
        st.markdown(line(t("확정된 거래가 쌓이면 누적 곡선과 일별 캘린더가 표시됩니다.",
                           "Cumulative curve and daily calendar appear once settled trades accumulate."), "i"), unsafe_allow_html=True)
        return
    st.markdown(
        '<div class="stats">'
        + stat(t("누적 실현손익", "Cumulative realized"), signed_money(eq["total"]),
               t(f'{eq["n"]}건 · {eq["days"]}거래일', f'{eq["n"]} trades · {eq["days"]} days'),
               "pos" if eq["total"] >= 0 else "neg")
        + stat(t("최고점", "Peak"), signed_money(eq["peak"]), t("누적 기준 고점", "cumulative high"))
        + stat(t("최대 낙폭 (MDD)", "Max drawdown"), money(-eq["mdd"]) if eq["mdd"] > 0 else "$0.00",
               eq["mdd_date"] or "", "neg" if eq["mdd"] > 0 else "")
        + stat(t("고점 대비", "From peak"), signed_money(eq["total"] - eq["peak"]),
               t("0이면 신고점", "0 = at high"), "pos" if eq["total"] >= eq["peak"] else "neg")
        + "</div>", unsafe_allow_html=True)
    _lbl_cum = t("누적 실현손익", "Cumulative realized")
    _df = pd.DataFrame(eq["daily"]).rename(columns={"cum": _lbl_cum})
    st.line_chart(_df, x="date", y=_lbl_cum, color="#2e7cf6", height=220)
    cal = calendar_heatmap_data()
    if cal["grid"]:
        wd_lbl = [t("월", "Mon"), "", t("수", "Wed"), "", t("금", "Fri"), "", t("일", "Sun")]
        rows_html = ""
        for wd in range(7):
            cells = ""
            for wrow in cal["grid"]:
                c = wrow[wd]
                if c["future"]:
                    cells += '<div style="width:14px;height:14px;"></div>'
                    continue
                if c["pnl"] is None:
                    tip = f'{c["date"]} · {t("거래 없음", "no trades")}'
                else:
                    tip = f'{c["date"]} · {signed_money(c["pnl"])} · {c["count"]}{t("건", "")}'
                cells += (f'<div title="{esc(tip)}" style="width:14px;height:14px;border-radius:3px;'
                          f'background:{_heat_color(c["pnl"], cal["scale"])};"></div>')
            rows_html += (f'<div style="display:flex;gap:3px;align-items:center;">'
                          f'<div style="width:26px;font-size:10px;color:var(--gray);text-align:right;padding-right:4px;">{wd_lbl[wd]}</div>'
                          f'{cells}</div>')
        _c_start, _c_end = cal["start"], cal["end"]
        st.markdown(
            f'<div style="display:flex;flex-direction:column;gap:3px;margin:10px 0 4px 0;">{rows_html}</div>'
            f'<div class="footnote">{t(f"최근 12주 ({_c_start} ~ {_c_end}) · 초록 수익 / 빨강 손실 · 짙을수록 금액 큼", f"Last 12 weeks ({_c_start} – {_c_end}) · green win / red loss · darker = larger")}</div>',
            unsafe_allow_html=True)
    with st.expander(t("일별 손익 데이터 표", "Daily P&L table")):
        st.dataframe(pd.DataFrame(eq["daily"]).rename(columns={"date": t("날짜", "Date"), "pnl": t("일 손익", "Day P&L")}),
                     width="stretch", hide_index=True)


def render_weekly_report(key_prefix="wr"):
    """주간 리포트 — 이번 주 vs 지난주 (손익·건수·승률·감정적/규칙위반 손익·최악 카테고리)."""
    wr = weekly_report()
    st.markdown(f'<div class="eyebrow" style="margin-top:6px;">{t("주간 리포트 — 이번 주 vs 지난주", "Weekly report — this week vs last")}</div>', unsafe_allow_html=True)
    if not wr["has_data"]:
        st.markdown(line(t("이번 주/지난주에 확정된 거래가 없습니다.", "No settled trades this or last week."), "i"), unsafe_allow_html=True)
        return
    tw, lw = wr["this"], wr["last"]
    st.markdown(
        '<div class="stats">'
        + stat(t("이번 주 손익", "This week P&L"), signed_money(tw["pnl"]),
               t(f'지난주 {signed_money(lw["pnl"])} · 대비 {signed_money(wr["delta_pnl"])}',
                 f'last {signed_money(lw["pnl"])} · Δ {signed_money(wr["delta_pnl"])}'),
               "pos" if tw["pnl"] >= 0 else "neg")
        + stat(t("거래 · 승률", "Trades · win rate"), f'{tw["n"]}{t("건", "")} · {tw["win_rate"]:.0f}%',
               t(f'지난주 {lw["n"]}건 · {lw["win_rate"]:.0f}%', f'last {lw["n"]} · {lw["win_rate"]:.0f}%'))
        + stat(t("감정적 거래 손익", "Emotional P&L"), signed_money(tw["emotional_pnl"]),
               t(f'{tw["emotional_n"]}건 · 지난주 {signed_money(lw["emotional_pnl"])}',
                 f'{tw["emotional_n"]} · last {signed_money(lw["emotional_pnl"])}'),
               "pos" if tw["emotional_pnl"] >= 0 else "neg")
        + stat(t("규칙위반 손익", "Violation P&L"), signed_money(tw["violation_pnl"]),
               t(f'{tw["violation_n"]}건 · 지난주 {signed_money(lw["violation_pnl"])}',
                 f'{tw["violation_n"]} · last {signed_money(lw["violation_pnl"])}'),
               "pos" if tw["violation_pnl"] >= 0 else "neg")
        + "</div>", unsafe_allow_html=True)
    if tw["worst_category"]:
        st.markdown(line(t(f'이번 주 최대 손실 카테고리: {tw["worst_category"]} {signed_money(tw["worst_category_pnl"])}',
                           f'Worst category this week: {tw["worst_category"]} {signed_money(tw["worst_category_pnl"])}'), "w"), unsafe_allow_html=True)
    _tw_start = wr["this_start"]
    st.markdown(f'<div class="footnote">{t(f"이번 주 = {_tw_start}(월)부터 오늘까지 · 장부 정산일 기준", f"This week = {_tw_start} (Mon) to today · by ledger settle date")}</div>', unsafe_allow_html=True)


def render_rule_simulator(key_prefix="rs"):
    """규칙 시뮬레이터 — '이 규칙을 지켰다면 얼마였나'를 실제 장부에 소급 적용해 보여준다."""
    st.markdown(f'<div class="eyebrow" style="margin-top:18px;">{t("규칙 시뮬레이터 — 지켰다면 얼마였나", "Rule simulator — what if you had followed the rules")}</div>', unsafe_allow_html=True)
    _bp = _insight_params()
    _rule_lbl = {
        "skip_high_price": t(f'{_bp["high_price"]:.0f}¢+ 진입 스킵', f'Skip {_bp["high_price"]:.0f}¢+ entries'),
        "cap_size": t("사이즈 캡 (감정 한도)", "Cap size (emotional limit)"),
        "no_chase": t("추격 재진입 금지", "No chase re-entries"),
        "stop_after_losses": t(f'{_bp["streak"]}연패 후 당일 중단', f'Stop day after {_bp["streak"]} losses'),
    }
    cols = st.columns(len(RULE_SIM_RULES))
    enabled = []
    for i, rule in enumerate(RULE_SIM_RULES):
        with cols[i]:
            if st.checkbox(_rule_lbl[rule], value=True, key=f"{key_prefix}_rule_{rule}"):
                enabled.append(rule)
    sim = rule_simulation(rules=enabled)
    if not sim["n"]:
        st.markdown(line(t("확정된 거래가 쌓이면 규칙별 가상 손익을 비교할 수 있습니다.",
                           "Once settled trades accumulate, per-rule counterfactual P&L appears here."), "i"), unsafe_allow_html=True)
        return
    comb = sim["combined"]
    delta_tone = "pos" if comb["delta"] >= 0 else "neg"
    st.markdown(
        '<div class="stats">'
        + stat(t("실제 손익", "Actual P&L"), signed_money(sim["actual_total"]),
               t(f'{sim["n"]}건 (장부 기준)', f'{sim["n"]} trades'),
               "pos" if sim["actual_total"] >= 0 else "neg")
        + stat(t("규칙 준수 시", "If rules followed"), signed_money(comb["total"]),
               t(f'켠 규칙 {len(enabled)}개 적용', f'{len(enabled)} rules applied'),
               "pos" if comb["total"] >= 0 else "neg")
        + stat(t("차이 (규칙의 값어치)", "Difference (value of rules)"), signed_money(comb["delta"]),
               t("규칙 준수 − 실제", "ruled − actual"), delta_tone)
        + stat(t("영향 거래", "Affected trades"), f'{comb["skipped"] + comb["capped"]}',
               t(f'스킵 {comb["skipped"]} · 축소 {comb["capped"]}', f'skip {comb["skipped"]} · cap {comb["capped"]}'))
        + "</div>", unsafe_allow_html=True)
    cells = ""
    for rule in RULE_SIM_RULES:  # 규칙 '하나만' 지켰다면 — 어떤 규칙이 가장 값진지
        rr = sim["rules"][rule]
        tone = "pos" if rr["delta"] >= 0 else "neg"
        cells += (f'<div class="pf-metric"><div class="k">{esc(_rule_lbl[rule])} · {rr["affected"]}건</div>'
                  f'<div class="v {tone}">{signed_money(rr["delta"])}</div></div>')
    st.markdown(f'<div class="eyebrow" style="margin-top:10px;">{t("규칙 하나만 지켰다면 (개별 효과)", "One rule alone (individual effect)")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pf-metrics">{cells}</div>', unsafe_allow_html=True)
    daily = sim["daily"]
    if len(daily) >= 2:
        _lbl_actual = t("실제", "Actual")
        _lbl_ruled = t("규칙 준수", "Rules followed")
        _df = pd.DataFrame(daily).rename(columns={"actual": _lbl_actual, "ruled": _lbl_ruled})
        # 팔레트는 validate_palette 통과: 실제=#a45e07(앰버) · 규칙 준수=#2e7cf6(파랑)
        st.line_chart(_df, x="date", y=[_lbl_actual, _lbl_ruled],
                      color=["#a45e07", "#2e7cf6"], height=260)
        with st.expander(t("일별 누적 데이터 표", "Daily cumulative table")):
            st.dataframe(_df.rename(columns={"date": t("날짜", "Date")}), width="stretch", hide_index=True)
    _lim_txt = money(sim["limit"]) if sim["limit"] > 0 else t("미설정", "not set")
    st.markdown(f'<div class="footnote">{t(f"근사치입니다 — 스킵한 거래가 이후 판단에 미치는 연쇄 효과는 반영하지 않으며, 사이즈 캡은 손익을 (한도 {_lim_txt} ÷ 매수금)으로 비례 축소합니다. 시각 정보가 없는 옛 장부 행은 ‘2연패 중단’ 판정에서 제외됩니다.", f"Approximation — knock-on effects of skipped trades are not modeled; size cap scales P&L by (limit {_lim_txt} ÷ cost). Old ledger rows without timestamps are excluded from the stop rule.")}</div>', unsafe_allow_html=True)


def render_trade_event_cards(events, title=None):
    events = [ev for ev in (events or []) if isinstance(ev, dict) and not ev.get("_linked_to")]
    if not events:
        return
    st.markdown(f'<div class="eyebrow" style="margin-top:16px;">{title or t("인식된 비거래 이벤트", "Recognized non-trade events")}</div>', unsafe_allow_html=True)
    for ev in events:
        dt = parse_trade_datetime(ev)
        when = dt.isoformat(timespec="minutes") if dt else t("시간 확인 필요", "time unknown")
        detail = []
        if ev.get("outcome"):
            detail.append(str(ev.get("outcome")))
        if ev.get("price") is not None:
            detail.append(cents(float(ev.get("price"))))
        if ev.get("shares") is not None:
            detail.append(f'{float(ev.get("shares")):.2f} {t("주", "shares")}')
        if ev.get("amount"):
            detail.append(str(ev.get("amount")))
        if ev.get("_linked_note"):
            detail.append(str(ev.get("_linked_note")))
        state_html = f'<span class="state w">{t("미연결", "Unlinked")}</span>'
        st.markdown(
            f'''<div class="spec-row">
  <div class="spec-key">{esc(ev.get("result", t("이벤트", "Event")))}</div>
  <div class="spec-val"><b>{esc(ev.get("name", ""))}</b><br>{esc(" · ".join(detail) if detail else t("정산/이벤트 행으로 인식됨", "Recognized settlement/event row"))}</div>
  <div>{state_html}<div class="footnote">{esc(when)}</div></div>
</div>''',
            unsafe_allow_html=True,
        )

def portfolio_card_html(ar):
    pnl_cls = "pos" if ar.get("pnl", 0) >= 0 else "neg"
    return html_block(f'''<div class="pf-card">
  <div class="pf-card-head">
    <div>
      <div class="pf-title">{esc(ar.get("name"))}</div>
      <div class="pf-pills">{outcome_pill(ar.get("outcome"))}{cents_pill(ar.get("cur", 0))}</div>
    </div>
    <span class="state {ar.get("kind", "i")}">{esc(ar.get("title"))}</span>
  </div>
  <div class="pf-big {pnl_cls}">{signed_money(ar.get("pnl", 0))}</div>
  <div class="pf-sub">{t("포지션 손익", "Position P&L")} · {signed_pct(ar.get("roi", 0))}</div>
  <div class="pf-metrics">
    <div class="pf-metric"><div class="k">{t("평가금", "Value")}</div><div class="v">{money(ar.get("value", 0))}</div></div>
    <div class="pf-metric"><div class="k">{t("비중", "Weight")}</div><div class="v">{ar.get("pct", 0):.1f}%</div></div>
    <div class="pf-metric"><div class="k">{t("현재가", "Now")}</div><div class="v">{ar.get("cur", 0):.1f}¢</div></div>
    <div class="pf-metric"><div class="k">{t("평균가", "Avg")}</div><div class="v">{ar.get("buy", 0):.1f}¢</div></div>
    <div class="pf-metric"><div class="k">{t("연결 거래", "Linked")}</div><div class="v">{int(ar.get("matched_trades", 0))}건</div></div>
    <div class="pf-metric"><div class="k">{t("매수 횟수", "Buys")}</div><div class="v">{int(ar.get("buy_trades", 0))}회</div></div>
  </div>
  <div class="pf-note">{esc(ar.get("summary"))}<br><b>{t("거래 연결", "Trade link")}:</b> {esc(ar.get("match_note", t("자동 거래내역 없음", "No imported activity")))}</div>
</div>''')

def sync_portfolio_hidden_checkbox(pkey, cb_key):
    hidden = set(str(x) for x in st.session_state.get("portfolio_hidden_keys", []) or [])
    if st.session_state.get(cb_key):
        hidden.add(str(pkey))
    else:
        hidden.discard(str(pkey))
    st.session_state.portfolio_hidden_keys = list(hidden)

def sync_today_cash_adjustment():
    """Keep manual starting cash from appearing as an artificial loss."""
    assets = current_portfolio_assets()
    raw_current = assets["total"] if assets["has_basis"] else float(effective_bankroll() or 0.0)
    start = _safe_float(st.session_state.get("today_start_cash"), 0.0)
    st.session_state.today_cash_adjustment = max(start - raw_current, 0.0)

def today_dashboard_html(metrics):
    """Thin portfolio-linked operating dashboard shown above the tabs."""
    pnl_cls = "good" if metrics["pnl"] > 0 else "bad" if metrics["pnl"] < 0 else ""
    goal_cls = "good" if metrics["goal_amount"] > 0 and metrics["goal_progress"] >= 100 else ""
    stop_cls = "bad" if metrics["stop"] > 0 and metrics["stop_progress"] >= 100 else "warn" if metrics["stop"] > 0 and metrics["stop_progress"] >= 80 else ""
    if metrics["start"] <= 0:
        pnl_cls = "warn"
    anchor_time = str(metrics.get("anchor_time") or "-")
    current_text = t(f"현재 포트폴리오 {money(metrics['current_total'])}",
                     f"Current portfolio {money(metrics['current_total'])}")
    goal_left_text = t(f"남은 목표 {money(metrics['goal_left'])}",
                       f"{money(metrics['goal_left'])} left")
    loss_label = t("손실", "lost")
    stop_mode_text = t("손실만", "loss-only") if metrics.get("stop_loss_gross_only") else t("순손익", "net")
    stop_left_text = t(f"중단까지 {money(metrics['stop_left'])}",
                       f"{money(metrics['stop_left'])} to stop")
    anchor_text = t(f"시작 {money(metrics['start'])} · {anchor_time}",
                    f"Start {money(metrics['start'])} · {anchor_time}")
    return (
        f'<div class="today-dashboard-bar">'
        f'<div class="today-dash-cell {pnl_cls}">'
        f'<div class="k">{t("오늘 손익", "Today P&L")}</div>'
        f'<div class="v">{signed_money(metrics["pnl"])}</div>'
        f'<div class="s">{esc(current_text)}</div>'
        f'</div>'
        f'<div class="today-dash-cell {goal_cls}">'
        f'<div class="k">{t("목표 달성률", "Goal progress")}</div>'
        f'<div class="v">{metrics["goal_progress"]:.0f}% · {money(metrics["gain"])}/{money(metrics["goal_amount"])}</div>'
        f'<div class="s">{esc(goal_left_text)}</div>'
        f'<div class="today-progress-track"><div class="today-progress-fill" style="width:{metrics["goal_progress_bar"]:.1f}%"></div></div>'
        f'</div>'
        f'<div class="today-dash-cell {stop_cls}">'
        f'<div class="k">{t("손실 중단선", "Stop-loss line")}</div>'
        f'<div class="v">{money(metrics["stop_loss_used"])} · {metrics["loss_pct"]:.1f}% {loss_label}</div>'
        f'<div class="s">{esc(stop_mode_text)} · {esc(stop_left_text)}</div>'
        f'<div class="today-progress-track"><div class="today-progress-fill loss" style="width:{metrics["stop_progress_bar"]:.1f}%"></div></div>'
        f'</div>'
        f'</div>'
    )

def portfolio_side_panel_html():
    """Render the portfolio summary card for the left panel."""
    _rp_portfolio = st.session_state.get("portfolio", []) or []
    _rp_visible_portfolio = visible_portfolio_positions(_rp_portfolio)
    _rp_total_holdings, _rp_hidden_holdings = portfolio_hidden_summary()
    _rp_assets = portfolio_asset_summary(_rp_portfolio, include_hidden=False)
    _rp_cash = _rp_assets["cash"]
    _rp_wallet = str(st.session_state.get("wallet_addr", "") or "").strip()
    _rp_pos_value = _rp_assets["position_value"]
    _rp_pos_cost = _rp_assets["position_cost"]
    _rp_total = _rp_assets["total"]
    _rp_unrealized = _rp_pos_value - _rp_pos_cost
    _rp_unrealized_pct = (_rp_unrealized / _rp_pos_cost * 100.0) if _rp_pos_cost else 0.0
    _rp_exposure_pct = (_rp_pos_value / _rp_total * 100.0) if _rp_total else 0.0
    _rp_wallet_label = (_rp_wallet[:6] + "..." + _rp_wallet[-4:]) if _rp_wallet else t("수동", "Manual")

    _rp_rows = []
    for _rp_p in _rp_visible_portfolio:
        if not isinstance(_rp_p, dict):
            continue
        _rp_value = _safe_float(_rp_p.get("shares"), 0.0) * (_safe_float(_rp_p.get("cur"), 0.0) / 100.0)
        _rp_rows.append((_rp_value, _rp_p))
    _rp_rows_all = sorted(_rp_rows, key=lambda x: x[0], reverse=True)
    _rp_rows = _rp_rows_all[:5]
    _rp_more_holdings = max(len(_rp_rows_all) - len(_rp_rows), 0)

    if _rp_rows:
        _rp_holdings_html = "".join(
            f'<div class="portfolio-position-row">'
            f'<div><div class="n">{esc(p.get("name", "") or t("이름 없는 포지션", "Unnamed position"))}</div>'
            f'<div class="o">{esc(p.get("outcome", "") or "-")} · {cents(_safe_float(p.get("cur"), 0.0))}</div></div>'
            f'<div class="v">{money(value)}</div>'
            f'</div>'
            for value, p in _rp_rows
        )
        if _rp_more_holdings:
            _rp_holdings_html += f'<div class="portfolio-more">{t(f"+{_rp_more_holdings}개 더", f"+{_rp_more_holdings} more")}</div>'
    else:
        _rp_holdings_html = (
            f'<div class="portfolio-empty">'
            f'{t("포트폴리오 탭에서 지갑 주소를 불러오면 여기에 요약이 표시됩니다.", "Import a wallet in the Portfolio tab to show a summary here.")}'
            f'</div>'
        )

    _rp_completed_all = recent_completed_trade_rows(limit=None)
    _rp_trade_limit = max(int(st.session_state.get("side_panel_trade_limit", 5) or 5), 5)
    _rp_completed = _rp_completed_all[:_rp_trade_limit]
    _rp_completed_total = sum(_safe_float(r.get("pnl"), 0.0) for r in _rp_completed)

    _rp_today_start = _safe_float(st.session_state.get("today_start_cash"), 0.0)
    _rp_today_stop = _safe_float(st.session_state.get("today_stop_loss_amount"), 0.0)
    _rp_today_goal_mode = st.session_state.get("today_goal_mode", "percent")
    if _rp_today_goal_mode == "percent":
        _rp_today_goal_pct = _safe_float(st.session_state.get("today_goal_pct"), 0.0)
        _rp_today_goal = _rp_today_start * _rp_today_goal_pct / 100.0
    else:
        _rp_today_goal = _safe_float(st.session_state.get("today_goal_amount"), 0.0)
    _rp_today_metrics = today_operating_metrics(_rp_total)
    _rp_today_pnl = _rp_today_metrics["pnl"]
    _rp_today_gain = _rp_today_metrics["gain"]
    _rp_today_loss = _rp_today_metrics["stop_loss_used"]
    _rp_today_goal_left = _rp_today_metrics["goal_left"]
    _rp_today_stop_left = _rp_today_metrics["stop_left"]
    if _rp_today_start <= 0:
        _rp_today_kind = "i"
        _rp_today_title = t("시작 기준 필요", "Set start basis")
        _rp_today_detail = t("왼쪽 패널에서 오늘 시작 금액을 먼저 설정하세요.", "Set today's starting cash in the left panel.")
    elif _rp_today_stop > 0 and _rp_today_loss >= _rp_today_stop:
        _rp_today_kind = "b"
        _rp_today_title = t("중단선 도달", "Stop line reached")
        _rp_today_detail = t(f"오늘 손익 {signed_money(_rp_today_pnl)} · 신규 진입 중단 기준입니다.", f"Today P&L {signed_money(_rp_today_pnl)} · stop new entries.")
    elif _rp_today_goal > 0 and _rp_today_gain >= _rp_today_goal:
        _rp_today_kind = "g"
        _rp_today_title = t("목표 달성", "Goal reached")
        _rp_today_detail = t(f"오늘 손익 {signed_money(_rp_today_pnl)} · 수익 보존 우선.", f"Today P&L {signed_money(_rp_today_pnl)} · protect gains.")
    elif _rp_today_pnl < 0:
        _rp_today_kind = "w"
        _rp_today_title = t("손실 관리", "Managing loss")
        _rp_today_detail = t(f"중단선까지 {money(_rp_today_stop_left)} 남음.", f"{money(_rp_today_stop_left)} left before stop.")
    else:
        _rp_today_kind = "g"
        _rp_today_title = t("목표 진행 중", "On track")
        _rp_today_detail = t(f"목표까지 {money(_rp_today_goal_left)} 남음.", f"{money(_rp_today_goal_left)} left to goal.")

    _rp_today_html = (
        f'<div class="portfolio-today-card {_rp_today_kind}">'
        f'<div class="k">{t("오늘 기준 연결", "Today link")}</div>'
        f'<div class="v">{esc(_rp_today_title)} · {signed_money(_rp_today_pnl)}</div>'
        f'<div class="s">{t(f"현재 포트폴리오 {money(_rp_total)} · 목표 {money(_rp_today_goal)} · 중단 {money(_rp_today_stop)}", f"Portfolio {money(_rp_total)} · Goal {money(_rp_today_goal)} · Stop {money(_rp_today_stop)}")}<br>{esc(_rp_today_detail)}</div>'
        f'</div>'
    )

    if _rp_completed:
        parts = []
        for r in _rp_completed:
            cls = "g" if r["pnl"] >= 0 else "b"
            pnl_label = t("이득", "Gain") if r["pnl"] >= 0 else t("손실", "Loss")
            parts.append(
                f'<div class="portfolio-completed-row {cls}">'
                f'<div><div class="n">{esc(r["market"] or t("이름 없는 거래", "Unnamed trade"))}</div>'
                f'<div class="o">{esc(r["outcome"] or "-")} · {esc(r["source"])} · {esc(r["status"])} · {t("회수", "Recovered")} {money(r["recovered"])}</div></div>'
                f'<div class="v">{pnl_label} {signed_money(r["pnl"])}</div>'
                f'</div>'
            )
        _rp_completed_html = "".join(parts)
    else:
        _rp_completed_html = (
            f'<div class="portfolio-empty">'
            f'{t("최근 완료된 매수/매도·상환 짝을 아직 찾지 못했습니다.", "No recent completed buy/sell or redemption matches yet.")}'
            f'</div>'
        )

    _rp_has_data = bool(_rp_portfolio) or bool(_rp_wallet) or _rp_cash > 0
    _rp_sub = (
        t(f"{len(_rp_portfolio)}개 포지션 · {_rp_wallet_label}", f"{len(_rp_portfolio)} positions · {_rp_wallet_label}")
        if _rp_has_data else
        t("지갑 API 요약 대기 중", "Waiting for wallet API summary")
    )
    _rp_holdings_count_text = f'{len(_rp_visible_portfolio)}/{len(_rp_portfolio)}'
    if _rp_hidden_holdings:
        _rp_holdings_count_text += t(f" · {_rp_hidden_holdings}숨김", f" · {_rp_hidden_holdings} hidden")
    _rp_total_label = t("표시 자산", "Visible assets") if _rp_hidden_holdings else t("총 자산", "Total assets")
    _rp_badge = t("연결됨", "Live") if _rp_wallet else t("요약", "Summary")
    _sync_meta = st.session_state.get("api_sync_meta", {}) or {}
    _sync_status = str(_sync_meta.get("status", "") or "")
    _sync_status_text = {
        "ok": t("정상", "OK"),
        "partial": t("부분 실패", "Partial"),
    }.get(_sync_status, t("기록 없음", "No record"))
    _sync_wallet = str(_sync_meta.get("wallet", "") or "")
    _sync_wallet_short = (_sync_wallet[:6] + "..." + _sync_wallet[-4:]) if _sync_wallet else "-"
    _sync_error = str(_sync_meta.get("error", "") or "")
    _rp_sync_html = (
        f'<details class="sync-details">'
        f'<summary>{t("API 동기화 상태", "API sync status")}</summary>'
        f'<div class="sync-body">'
        f'<div class="sync-row"><span>{t("상태", "Status")}</span><b>{esc(_sync_status_text)}</b></div>'
        f'<div class="sync-row"><span>{t("마지막 동기화", "Last sync")}</span><b>{esc(_sync_meta.get("last_sync_at", "-") or "-")}</b></div>'
        f'<div class="sync-row"><span>{t("호출 위치", "Source")}</span><b>{esc(_sync_meta.get("source", "-") or "-")}</b></div>'
        f'<div class="sync-row"><span>{t("지갑", "Wallet")}</span><b>{esc(_sync_wallet_short)}</b></div>'
        f'<div class="sync-row"><span>{t("포지션", "Positions")}</span><b>{int(_sync_meta.get("positions", 0) or 0)}</b></div>'
        f'<div class="sync-row"><span>{t("활동 원본", "Raw activity")}</span><b>{int(_sync_meta.get("raw_activity", 0) or 0)}</b></div>'
        f'<div class="sync-row"><span>{t("거래/정산", "Trades/events")}</span><b>{int(_sync_meta.get("trades", 0) or 0)} / {int(_sync_meta.get("events", 0) or 0)}</b></div>'
        f'<div class="sync-row"><span>{t("새로 추가", "Added")}</span><b>{int(_sync_meta.get("added", 0) or 0)}</b></div>'
        + (f'<div class="sync-row"><span>{t("오류", "Error")}</span><b>{esc(_sync_error)}</b></div>' if _sync_error else '')
        + f'</div></details>'
    )

    return (
        f'<div class="sidebar-portfolio-panel">'
        f'<div class="portfolio-panel-card">'
        f'<div class="portfolio-panel-head">'
        f'<div><div class="portfolio-panel-title">{t("현재 포트폴리오", "Current portfolio")}</div>'
        f'<div class="portfolio-panel-sub">{esc(_rp_sub)}</div></div>'
        f'<div class="portfolio-panel-badge">{_rp_badge}</div>'
        f'</div>'
        f'<div class="portfolio-total-kpi">'
        f'<div class="k">{_rp_total_label}</div>'
        f'<div class="v">{money(_rp_total)}</div>'
        f'<div class="s">{t(f"미실현 {signed_money(_rp_unrealized)} · 수익률 {_rp_unrealized_pct:+.1f}%", f"Unrealized {signed_money(_rp_unrealized)} · ROI {_rp_unrealized_pct:+.1f}%")}</div>'
        f'</div>'
        f'<div class="portfolio-mini-grid">'
        f'<div class="portfolio-mini-cell"><div class="k">{t("포지션 평가금", "Position value")}</div><div class="v">{money(_rp_pos_value)}</div></div>'
        f'<div class="portfolio-mini-cell"><div class="k">{t("노출 비중", "Exposure")}</div><div class="v">{_rp_exposure_pct:.1f}%</div></div>'
        f'</div>'
        f'{_rp_today_html}'
        f'<div class="portfolio-section-head"><div class="k">{t("보유종목", "Holdings")}</div><div class="v">{esc(_rp_holdings_count_text)}</div></div>'
        f'<div class="portfolio-position-list">{_rp_holdings_html}</div>'
        f'<div class="portfolio-section-head"><div class="k">{t("최근 완료 거래", "Recent completed")}</div><div class="v">{len(_rp_completed)}/{len(_rp_completed_all)} · {signed_money(_rp_completed_total)}</div></div>'
        f'<div class="portfolio-completed-list">{_rp_completed_html}</div>'
        f'{_rp_sync_html}'
        f'</div>'
        f'</div>'
    )

def render_entry_result(r):
    if not r:
        st.markdown(
            f"""<div class="quiet">
<div class="q-title">{t("판독 결과가 여기에 표시됩니다", "Your verdict appears here")}</div>
<div class="q-body">{t("오른쪽에서 시장 정보와 투자금을 입력하고<br>판독하기를 누르세요.", "Enter the market details on the right<br>and press Evaluate.")}</div>
</div>""", unsafe_allow_html=True)
        return

    k = verdict_dot(r["level"])
    score_word = t("적절성", "Suitability") if r["level"] != "bad" else t("부적절도", "Unsuitability")
    score_val = r["final_score"] if r["level"] != "bad" else 100 - r["final_score"]

    st.markdown(
        f"""<div class="verdict">
<div class="eyebrow">{t("판정", "Verdict")}</div>
<div class="v-title"><span class="dot {k}"></span>{r["decision"]}</div>
<div class="v-sub">{r["market_name"]} · {score_word} {score_val:.0f}% · {t("규모 제외 순수 가치", "Pure value")} {r["value_score"]:.0f}%</div>
</div>""", unsafe_allow_html=True)

    edge_tone = "pos" if r["edge"] >= 5 else "neg" if r["edge"] < 0 else ""
    pos_tone = "neg" if r["size_kind"] == "b" else ""
    st.markdown(
        '<div class="stats">'
        + stat(t("현재가", "Price"), cents(r["current_price"]), t("시장 implied probability", "Implied probability"))
        + stat("Edge", f"{r['edge']:+.1f}¢", t("내 적정가 대비", "vs fair price"), edge_tone)
        + stat(t("포트폴리오 비중", "Portfolio %"), f"{r['position_pct']:.1f}%", r["size_label"], pos_tone)
        + stat(t("추천 상한선", "Suggested cap"), money(r["rec_cap"]), t(f"투자금 {money(r['stake'])}", f"Stake {money(r['stake'])}"))
        + stat(t("켈리 추천액", "Kelly stake"), money(r["kelly_stake"]), t(f"{r['kelly_fraction']:.0%} 켈리 · edge {r['edge']:+.0f}¢", f"{r['kelly_fraction']:.0%} Kelly · edge {r['edge']:+.0f}¢"))
        + "</div>",
        unsafe_allow_html=True)

    # ---- meters with explicit verdicts ----
    fs = r["final_score"]
    fs_kind = "g" if fs >= 70 else "w" if fs >= 50 else "b"
    vs = r["value_score"]
    vs_kind = "g" if vs >= 70 else "w" if vs >= 50 else "b"
    pp = min(r["position_pct"], 100)
    pp_kind = r["size_kind"]
    pz_kind = r["zone_kind"]

    st.markdown(
        meter(t("리스크 포함 최종 적절성", "Final suitability incl. risk"), fs, fs_kind, grade_word(fs_kind), unit="%")
        + meter(t("배팅 규모 제외 순수 가치", "Pure value ex-size"), vs, vs_kind, grade_word(vs_kind), unit="%")
        + meter(t("포트폴리오 사용 비중", "Portfolio usage"), pp, pp_kind, r["size_label"], unit="%")
        + meter(t("현재가 위치", "Price position"), r["current_price"], pz_kind, r["zone_label"], unit="¢"),
        unsafe_allow_html=True)

    st.markdown(f'<div class="eyebrow" style="margin-top:22px;">{t("핵심 판단 근거", "Key reasoning")}</div>', unsafe_allow_html=True)
    notes = "".join(line(txt, kk) for kk, txt in r["reasons"])
    if r["fomo_count"] > 0: notes += line(r["fomo_note"], r["fomo_kind"])
    if r["duplicate_pct"] >= size_thresholds()[1]: notes += line(r["exp_note"], r["exp_kind"])
    if r["high_warn"]: notes += line(r["high_warn"], "b")
    notes += line(r["kelly_note"], r["kelly_kind"])
    if r.get("tilt_note"): notes += line(r["tilt_note"], r["tilt_kind"])
    if r.get("adapt_note"): notes += line(r["adapt_note"], r["adapt_kind"])
    st.markdown(notes, unsafe_allow_html=True)

    with st.expander(t("상세 리포트", "Detailed report")):
        st.markdown(
            '<div class="spec">'
            + spec_row(t("진입가격 구간", "Price zone"), f"{t('현재가','Price')} <b>{cents(r['current_price'])}</b> — {r['zone_note']}", r["zone_label"], r["zone_kind"])
            + spec_row(t("배팅금액 · 계좌 생존", "Stake · survival"), f"{t('투자금','Stake')} <b>{money(r['stake'])}</b> / {t('총자산','Portfolio')} <b>{money(r['bankroll'])}</b> · <b>{r['position_pct']:.1f}%</b><br>{r['size_note']}", r["size_label"], r["size_kind"])
            + spec_row(t("북메이커 비교", "Bookmaker check"), f"{t('내 적정가−현재가','Fair−mkt')} <b>{r['my_vs_poly']:+.1f}%p</b> · {t('북메이커−현재가','Book−mkt')} <b>{r['book_vs_poly']:+.1f}%p</b><br>{r['book_note']}", r["book_label"], r["book_kind"])
            + spec_row(t("추천 상한선", "Suggested cap"), f"<b>{money(r['rec_cap'])}</b> · {t('투자금','Stake')} <b>{money(r['stake'])}</b> · {r['confidence']}", r["cap_label"], r["cap_kind"])
            + spec_row(t("켈리 베팅 사이징", "Kelly sizing"), f"{t('추천','Suggested')} <b>{money(r['kelly_stake'])}</b> · {t('전체 켈리','full Kelly')} {r['kelly_full']*100:.0f}% × {r['kelly_fraction']:.0%}<br>{r['kelly_note']}", r["kelly_label"], r["kelly_kind"])
            + spec_row(t("손익비", "Risk : reward"), f"{t('목표 도달','At target')} <b>{money(r['target_profit'])}</b> · {t('손절','At stop')} <b>{money(r['stop_loss_amt'])}</b><br>{r['rr_text']}", f"{r['rr']:.2f} : 1", r["rr_kind"])
            + spec_row(t("감정 · FOMO", "Emotion · FOMO"), f"{t('체크','Checks')} <b>{r['fomo_count']}</b> — {r['fomo_note']}", r["fomo_label"], r["fomo_kind"])
            + spec_row(t("중복 노출", "Stacked exposure"), f"<b>{money(r['duplicate_total'])}</b> · <b>{r['duplicate_pct']:.1f}%</b><br>{r['exp_note']}", r["exp_label"], r["exp_kind"])
            + spec_row(t("추격매수 점검", "Chase check"), r["chase_note"], r["chase_label"], r["chase_kind"])
            + spec_row(t("목적 · 시장 유형", "Purpose · type"), f"<b>{r['purpose']}</b> — {r['purpose_note']}<br><b>{r['market_type']}</b> — {r['market_type_note']}", t("구조", "Structure"), "i")
            + "</div>", unsafe_allow_html=True)

        st.markdown(f'<div class="eyebrow" style="margin-top:24px;">{t("수익 · 손실 시나리오", "P&L scenarios")}</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="stats">'
            + stat(t("보유 수량", "Shares"), f"{r['shares']:.2f}", t("투자금 ÷ 현재가", "Stake ÷ price"))
            + stat(t("승리 시 순이익", "Profit if win"), money(r["win_profit"]), t("100¢ 상환 기준", "At 100¢"), "pos")
            + stat(t("패배 시 손실", "Loss if lose"), money(-r["stake"]), t("전액 손실 가정", "Total loss"), "neg")
            + stat(t("100¢까지 추가수익", "Left to 100¢"), money(r["additional_to_100"]), t("남은 업사이드", "Upside left"))
            + "</div>", unsafe_allow_html=True)

        summary = (f"{r['market_name']} | {cents(r['current_price'])} → fair {cents(r['fair_price'])} · edge {r['edge']:+.0f}¢ | "
                   f"{money(r['stake'])} · {r['position_pct']:.1f}% | {r['decision']} | {r['final_score']:.0f}% / {r['value_score']:.0f}%")
        st.markdown(f'<div class="eyebrow" style="margin-top:20px;">{t("기록용 한 줄 요약", "One-line summary")}</div>', unsafe_allow_html=True)
        st.code(summary)

def _market_table(rows, section_key):
    """Compact market table. Select one row, then use a single detailed form below.

    Live quotes are intentionally NOT fetched per row — that made one blocking HTTP
    call per outcome on every render. Gamma's last price is shown instantly here, and
    the live bid/ask/spread is fetched only for the market you select (in the result
    panel below). Much faster, especially for events with many outcomes.
    """
    if not rows:
        return
    mk = t("시장", "Market")
    oc = t("선택지", "Outcome")
    pc = t("현재가 (¢)", "Price (¢)")
    st.markdown(
        '<div class="spec-row" style="box-shadow:none;background:transparent;border-color:transparent;padding-bottom:4px;">'
        f'<div class="spec-key">{t("결과 · 시장","Outcome · market")}</div>'
        f'<div class="spec-val" style="color:var(--gray);">{t("현재가 · 시장 implied","Price · implied")}</div>'
        '<div></div></div>', unsafe_allow_html=True)
    for i, m in enumerate(rows):
        q = m.get(mk, "")
        o = m.get(oc, "")
        tok = str(m.get("token_id", "") or "")
        price = m.get(pc, None)
        disp = 50.0 if price is None else float(price)
        cinfo, cprice, cbtn = st.columns([3, 2.2, 1.1])
        cinfo.markdown(
            f'<div class="spec-val" style="padding-top:8px;"><b>{esc(o)}</b>'
            f'<br><span style="color:var(--gray2);font-size:11px;">{esc(q[:72])}</span></div>',
            unsafe_allow_html=True)
        cprice.markdown(
            f'<div class="spec-val" style="padding-top:8px;font-weight:650;">{cents(disp)}'
            f' <span style="color:var(--gray2);font-size:12px;font-weight:500;">· {disp:.0f}%</span></div>',
            unsafe_allow_html=True)
        with cbtn:
            keytok = tok if tok else f"idx_{section_key}_{i}"
            if st.button(t("선택", "Select"), key=f"sel_{section_key}_{i}_{keytok}", width="stretch"):
                st.session_state._entry_sel = {**m, "_disp_price": disp, "_sel_key": keytok}
                st.session_state._entry_active = None
                st.rerun()

def _selected_entry_form(entry_category, entry_subcategory):
    """Selected market inputs plus optional Korean self-strategy fields.

    Main visible inputs are deterministic only. Optional bookmaker/research/self-check
    fields appear only when the user selects them in the self-strategy section.
    """
    sel = st.session_state.get("_entry_sel")
    if not sel:
        st.markdown(f'<div class="footnote">{t("위에서 시장을 선택하면 입력 폼이 열립니다.", "Select a market above to open inputs.")}</div>', unsafe_allow_html=True)
        return

    mk = t("시장", "Market")
    oc = t("선택지", "Outcome")
    q = sel.get(mk, "")
    o = sel.get(oc, "")
    tok = str(sel.get("token_id", "") or "")
    keytok = tok if tok else str(sel.get("_sel_key", "selected"))
    disp = float(sel.get("_disp_price", 50.0) or 50.0)

    # ---- visibility control: market inputs and self-check are separate blocks ----
    visible_options = ["선택한 시장", "내 진입 전략 / 자가 판단"]
    if not isinstance(st.session_state.get("entry_visible_sections"), list):
        st.session_state.entry_visible_sections = list(visible_options)
    st.multiselect(
        "표시할 영역 선택",
        visible_options,
        key="entry_visible_sections",
        help="선택한 영역만 아래에 표시됩니다. 둘 다 선택하면 두 영역이 모두 표시됩니다.",
    )
    visible_sections = st.session_state.get("entry_visible_sections", visible_options)
    show_market_block = "선택한 시장" in visible_sections
    show_strategy_block = "내 진입 전략 / 자가 판단" in visible_sections

    default_stake = float(min(50.0, (effective_bankroll() or 1000.0) * 0.03) or 50.0)
    default_conf = confidence_options()[2]
    default_target = float(min(disp + 10, 99.0))
    default_fair = float(min(disp + 5, 99.0))
    default_purpose = purpose_options()[0]
    default_stop = float(max(disp - 10, 1.0))

    # ---- core deterministic inputs: visible only when selected ----
    if show_market_block:
        st.markdown(f'<div class="eyebrow" style="margin-top:16px;">{t("선택한 시장", "Selected")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="spec-row"><div class="spec-key">{esc(q)}</div><div class="spec-val"><b>{esc(o)}</b> · {cents(disp)}</div><div></div></div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            stake = st.number_input(t("투자금($)", "Stake($)"), min_value=1.0, value=default_stake, key="sel_stake")
            conf = st.selectbox(t("확신", "Conviction"), confidence_options(), index=2, key="sel_conf")
            target = st.number_input(t("목표가(¢)", "Target(¢)"), min_value=1.0, max_value=100.0, value=default_target, key="sel_target")
        with c2:
            fair = st.number_input(t("적정가(¢)", "Fair(¢)"), min_value=1.0, max_value=99.0, value=default_fair, key="sel_fair")
            purp = st.selectbox(t("목적", "Purpose"), purpose_options(), key="sel_purpose")
            stop = st.number_input(t("손절가(¢)", "Stop(¢)"), min_value=0.0, max_value=99.0, value=default_stop, key="sel_stop")
    else:
        # Keep selected market data internally, but do not render the market/input block.
        # If the user analyzes from self-check only, use previous widget values or safe defaults.
        stake = float(st.session_state.get("sel_stake", default_stake) or default_stake)
        conf = st.session_state.get("sel_conf", default_conf)
        if conf not in confidence_options():
            conf = default_conf
        target = float(st.session_state.get("sel_target", default_target) or default_target)
        fair = float(st.session_state.get("sel_fair", default_fair) or default_fair)
        purp = st.session_state.get("sel_purpose", default_purpose)
        if purp not in purpose_options():
            purp = default_purpose
        stop = float(st.session_state.get("sel_stop", default_stop) or default_stop)

    # ---- optional self-strategy section ----

    strategy_options = [
        "리스크", "엣지", "매도 타이밍", "내가 생각한 확률", "시장이 보는 확률",
        "진입 근거", "청산/매도 근거", "포지션 크기", "감정/FOMO",
        "외부배당", "AI 리서치 메모", "배운 점", "실수/규칙 위반", "다음 행동",
    ]
    scale = self_check_scale()
    selected_strategy_fields = []
    strategy_payload = {"selected_fields": [], "rating_scale": scale}
    bk = 0.0
    bk_memo = ""
    ai_memo = ""

    if show_strategy_block:
        st.markdown(f'<div class="eyebrow" style="margin-top:18px;">{t("내 진입 전략 / 자가 판단", "My entry strategy / self-check")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="footnote">{t("앱이 판단하기 전에 스스로 확인할 항목만 선택하세요. 선택하지 않은 항목은 입력창을 숨깁니다.", "Choose only the self-check items you want before the app verdict.")}</div>', unsafe_allow_html=True)
        strategy_fields_key = f"entry_strategy_fields_{keytok}"
        if strategy_fields_key not in st.session_state or not isinstance(st.session_state.get(strategy_fields_key), list):
            st.session_state[strategy_fields_key] = []
        selected_strategy_fields = st.multiselect(
            "평가할 항목 선택",
            strategy_options,
            key=strategy_fields_key,
            help=t("선택한 항목만 아래에 표시됩니다.", "Only selected fields are shown below."),
        )
        strategy_payload = {"selected_fields": list(selected_strategy_fields), "rating_scale": scale}

    if show_strategy_block and selected_strategy_fields:

        if "리스크" in selected_strategy_fields:
            r1, r2 = st.columns([1, 2])
            with r1:
                strategy_payload["risk_score"] = st.slider("리스크 점수", 1, scale, max(1, min(scale, (scale + 1) // 2)), key=f"entry_risk_score_{keytok}", help=self_check_scale_help())
            with r2:
                strategy_payload["risk_note"] = st.text_area("리스크 판단 메모", key=f"entry_risk_note_{keytok}", height=70, placeholder="고가 진입, 변동성, 정산 리스크, 손실 가능성 등")

        if "엣지" in selected_strategy_fields:
            e1, e2 = st.columns([1, 2])
            with e1:
                strategy_payload["self_edge_cents"] = st.number_input("내가 본 엣지(¢)", min_value=-99.0, max_value=99.0, value=float(round(fair - disp, 1)), step=0.5, key=f"entry_self_edge_{keytok}")
            with e2:
                strategy_payload["edge_note"] = st.text_area("왜 저평가라고 봤는가?", key=f"entry_edge_note_{keytok}", height=70, placeholder="시장 가격보다 높게 보는 핵심 근거")

        if "매도 타이밍" in selected_strategy_fields:
            s1, s2 = st.columns([1, 1])
            with s1:
                strategy_payload["selling_plan"] = st.selectbox("매도 전략", ["만기 보유", "중간 익절", "손절", "상환/정산 대기", "매도 타이밍 놓침"], key=f"entry_selling_plan_{keytok}")
            with s2:
                strategy_payload["desired_sell_price"] = st.number_input("원하는 매도가(¢)", min_value=0.0, max_value=100.0, value=float(min(disp + 10, 99.0)), step=0.5, key=f"entry_desired_sell_{keytok}")
            strategy_payload["selling_note"] = st.text_area("매도 타이밍 판단 메모", key=f"entry_selling_note_{keytok}", height=70, placeholder="예: 92¢ 도달 시 절반 익절, 80¢ 이탈 시 재평가")

        if "내가 생각한 확률" in selected_strategy_fields or "시장이 보는 확률" in selected_strategy_fields:
            pcols = st.columns(2)
            if "내가 생각한 확률" in selected_strategy_fields:
                with pcols[0]:
                    strategy_payload["my_probability"] = st.number_input("내가 생각한 실제 확률(%)", min_value=0.0, max_value=100.0, value=float(min(fair, 99.0)), step=0.5, key=f"entry_my_prob_{keytok}")
            if "시장이 보는 확률" in selected_strategy_fields:
                with pcols[1]:
                    strategy_payload["market_probability"] = st.number_input("시장이 반영한 확률(%)", min_value=0.0, max_value=100.0, value=float(disp), step=0.5, key=f"entry_market_prob_{keytok}")

        if "진입 근거" in selected_strategy_fields:
            strategy_payload["entry_rationale"] = st.text_area("진입 근거", key=f"entry_rationale_{keytok}", height=80, placeholder="내가 이 포지션에 들어가려는 핵심 근거")

        if "청산/매도 근거" in selected_strategy_fields:
            strategy_payload["exit_rationale"] = st.text_area("청산/매도 근거", key=f"entry_exit_rationale_{keytok}", height=70, placeholder="어떤 조건이면 팔거나 보유할지")

        if "포지션 크기" in selected_strategy_fields:
            strategy_payload["position_size_note"] = st.text_area("포지션 크기 판단", key=f"entry_pos_size_note_{keytok}", height=70, placeholder="$30로 제한하는 이유, 추가진입 금지 조건 등")

        if "감정/FOMO" in selected_strategy_fields:
            emo1, emo2 = st.columns([1, 2])
            with emo1:
                strategy_payload["emotion_score"] = st.slider("감정/FOMO 점수", 1, scale, 1, key=f"entry_emotion_score_{keytok}", help=self_check_scale_help())
            with emo2:
                strategy_payload["emotion_note"] = st.text_area("감정 상태 메모", key=f"entry_emotion_note_{keytok}", height=70, placeholder="충동, 복구심리, FOMO, 규칙 위반 가능성")

        if "외부배당" in selected_strategy_fields:
            b1, b2 = st.columns([1, 2])
            with b1:
                bk = st.number_input("외부배당/북메이커 승률(%)", min_value=0.0, max_value=99.0, value=0.0, key="sel_book")
            with b2:
                bk_memo = st.text_input("외부배당 출처 메모", key="sel_bm", placeholder="예: Pinnacle T1 -180, Bet365 Gen.G 1.55")
            strategy_payload["bookmaker_prob"] = bk
            strategy_payload["bookmaker_memo"] = bk_memo

        if "AI 리서치 메모" in selected_strategy_fields:
            ai_memo = st.text_area("AI 리서치 메모 / 외부정보", key="sel_ai_memo", height=84, placeholder="최근 10경기·상대전적·순위·라인업·부상·뉴스 링크 붙여넣기")
            strategy_payload["ai_memo"] = ai_memo

        if "배운 점" in selected_strategy_fields:
            strategy_payload["lesson_note"] = st.text_area("배운 점", key=f"entry_lesson_{keytok}", height=60)

        if "실수/규칙 위반" in selected_strategy_fields:
            strategy_payload["mistake_note"] = st.text_area("실수 또는 규칙 위반", key=f"entry_mistake_{keytok}", height=60)

        if "다음 행동" in selected_strategy_fields:
            strategy_payload["next_action"] = st.selectbox("다음 행동", ["다음엔 같은 조건이면 진입", "다음엔 금액 축소", "다음엔 진입하지 않음", "정보 확인 후 진입", "규칙 재설정 필요"], key=f"entry_next_action_{keytok}")
            strategy_payload["next_action_note"] = st.text_area("다음 행동 메모", key=f"entry_next_note_{keytok}", height=60)


    with st.expander(t("고급 (감정·중복노출)", "Advanced (emotion · duplicate exposure)")):
        a1, a2 = st.columns(2)
        with a1:
            fomo = st.slider(t("감정 체크", "Emotion check"), 0, 7, 0, key="sel_fomo")
            prev_good = st.number_input(t("처음 봤던 좋은 가격(¢)", "Previous good price (¢)"), min_value=0.0, max_value=99.0, value=0.0, key="sel_prev_good")
        with a2:
            dup_ml = st.number_input(t("중복 Moneyline 노출($)", "Duplicate ML exposure ($)"), min_value=0.0, value=0.0, key="sel_dup_ml")
            dup_game = st.number_input(t("중복 Game/Map 노출($)", "Duplicate game/map exposure ($)"), min_value=0.0, value=0.0, key="sel_dup_game")
            dup_side = st.number_input(t("같은 방향 총 노출($)", "Same-side exposure ($)"), min_value=0.0, value=0.0, key="sel_dup_side")

    go = st.button(t("분석", "Analyze"), key=f"sel_entry_analyze_{keytok}", width="stretch")

    def _strategy_context_text(payload):
        if not isinstance(payload, dict) or not payload.get("selected_fields"):
            return ""
        lines = [t("[진입 전 자가 판단]", "[Pre-entry self-check]")]
        mapping = {
            "risk_score": "리스크 점수",
            "risk_note": "리스크 메모",
            "self_edge_cents": "엣지(¢)",
            "edge_note": "엣지 근거",
            "selling_plan": "매도 전략",
            "desired_sell_price": "원하는 매도가",
            "selling_note": "매도 타이밍 메모",
            "my_probability": "내가 생각한 확률",
            "market_probability": "시장이 보는 확률",
            "entry_rationale": "진입 근거",
            "exit_rationale": "청산/매도 근거",
            "position_size_note": "포지션 크기",
            "emotion_score": "감정/FOMO 점수",
            "emotion_note": "감정 메모",
            "bookmaker_prob": "외부배당 승률",
            "bookmaker_memo": "외부배당 메모",
            "ai_memo": "AI 리서치 메모",
            "lesson_note": "배운 점",
            "mistake_note": "실수/규칙 위반",
            "next_action": "다음 행동",
            "next_action_note": "다음 행동 메모",
        }
        for k, label in mapping.items():
            v = payload.get(k)
            if v not in (None, ""):
                if isinstance(v, float):
                    v = round(v, 2)
                lines.append(f"- {label}: {v}")
        return "\n".join(lines)

    if go:
        st.session_state.entry_self_strategy[keytok] = dict(strategy_payload)
        analyze_entry_row(sel, stake, fair, conf, purp, category=entry_category, subcategory=entry_subcategory, ai_context=ai_memo,
                          adv={"target_price": target, "stop_price": stop, "bookmaker_prob": bk,
                               "bookmaker_source_memo": bk_memo, "ai_extra_context": ai_memo,
                               "previous_good_price": prev_good, "duplicate_ml": dup_ml,
                               "duplicate_game": dup_game, "duplicate_side": dup_side,
                               "fomo_count": fomo, "market_type": "Match Moneyline",
                               "self_strategy": dict(strategy_payload)})
        st.session_state._entry_active = keytok
        st.rerun()

    if st.session_state.get("_entry_active") == keytok and st.session_state.get("last_entry"):
        saved_strategy = st.session_state.get("entry_self_strategy", {}).get(keytok, {})
        if show_strategy_block and saved_strategy:
            st.markdown(f'<div class="eyebrow" style="margin-top:16px;">{t("내 진입 전 판단", "My pre-entry view")}</div>', unsafe_allow_html=True)
            strategy_text = _strategy_context_text(saved_strategy)
            if strategy_text:
                st.markdown(f'<div class="rc-card"><div class="rc-h">{t("자가 전략 요약", "Self-strategy summary")}</div><div class="rc-note">{esc(strategy_text).replace(chr(10), "<br>")}</div></div>', unsafe_allow_html=True)

        render_entry_result(st.session_state.last_entry)
        if st.session_state.get("watching_market", {}).get("token_id"):
            st.markdown(f'<div class="eyebrow" style="margin-top:16px;">{t("실시간 가격 추적", "Live price watch")}</div>', unsafe_allow_html=True)
            render_live_price_panel(st.session_state.watching_market)
        if st.button(t("AI 분석 탭으로 보내기", "Send to AI tab"), key=f"toai_{keytok}", width="stretch"):
            r = st.session_state.last_entry
            saved_strategy = st.session_state.get("entry_self_strategy", {}).get(keytok, {})
            memo_for_ai = str(saved_strategy.get("ai_memo", "") or "")
            bk_for_ai = str(saved_strategy.get("bookmaker_memo", "") or "")
            strategy_for_ai = _strategy_context_text(saved_strategy)
            if strategy_for_ai:
                memo_for_ai = (memo_for_ai + "\n\n" + strategy_for_ai).strip()
            st.session_state.ai_pending = {
                "market": sel.get(mk, ""),
                "outcome": sel.get(oc, ""),
                "token_id": tok,
                "market_class": sel.get("market_class", ""),
                "current_price": r.get("current_price", disp),
                "fair_price": r.get("fair_price", disp),
                "edge": r.get("edge", 0.0),
                "category": entry_category,
                "subcategory": entry_subcategory,
                "bookmaker_prob": float(saved_strategy.get("bookmaker_prob", 0.0) or 0.0),
                "bookmaker_memo": bk_for_ai,
                "ai_memo": memo_for_ai,
                "self_strategy": saved_strategy,
                "resolution": str(sel.get("resolution", "") or ""),
                "end_date": str(sel.get("endDate", "") or ""),
                "source_url": st.session_state.get("entry_url", ""),
            }
            st.session_state._ai_memo_cache = memo_for_ai
            st.session_state._ai_bk_cache = bk_for_ai
            st.session_state.ai_text = ""
            st.session_state.ai_error = ""
            st.session_state.ai_last_market_key = ""
            st.success(t("AI 리서치 탭에서 리포트를 생성하세요", "Generate the report in the AI research tab"))


def sync_wallet(addr, limit=1000, force=False):
    """Fetch wallet activity, merge new trades (dedup by tx_id), archive completed trades
    to the durable ledger, and record sync meta. Shared by the manual button and the
    once-per-session auto-sync. Returns a result dict; never raises."""
    a = str(addr or "").strip()
    if not (a.startswith("0x") and len(a) == 42):
        return {"ok": False, "error": "bad_address", "added": 0, "found": 0}
    try:
        if force:
            fetch_wallet_activity.clear()
            fetch_wallet_activity_all.clear()
        # 페이지네이션으로 limit(총 상한)까지 과거 체결을 전부 수집 — 최근 1페이지만 보던
        # 예전 방식에선 오래된 기존 거래가 인식되지 않았다.
        raw = fetch_wallet_activity_all(a, max_rows=int(limit or 500))
        st.session_state.activity_raw = raw
        st.session_state.activity_events = normalize_activity_events(raw)
        items = sort_trades_newest_first(normalize_activity(raw))
        added = merge_activity_into_log(items)
        st.session_state.auto_trades = sort_trades_newest_first(st.session_state.get("auto_trades", []))
        update_trade_ledger()
        st.session_state.api_sync_meta = {
            "status": "ok",
            "source": t("거래일지", "Journal") if force else t("자동 동기화", "Auto sync"),
            "wallet": a,
            "last_sync_at": datetime.now(KST).isoformat(timespec="minutes"),
            "positions": len(st.session_state.get("portfolio", []) or []),
            "raw_activity": len(raw) if isinstance(raw, list) else 0,
            "trades": len(items),
            "events": len(st.session_state.get("activity_events", []) or []),
            "added": added,
            "error": "",
        }
        return {"ok": True, "error": "", "added": added, "found": len(items)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"http_{e.code}", "added": 0, "found": 0}
    except Exception as e:
        return {"ok": False, "error": str(e), "added": 0, "found": 0}


def sync_wallet_full(addr, limit=1000, force=False, resolve=True):
    """지갑 동기화 단일 파이프라인: 보유 포지션 + 지갑 가치 + 활동내역(→장부) + 승/패 자동확정.
    포트폴리오/거래일지 버튼과 부팅 자동 동기화가 전부 이 함수를 쓴다. 포지션 조회가 실패해도
    활동내역 동기화는 계속한다(부분 성공은 partial에 기록). Never raises."""
    a = str(addr or "").strip()
    base = {"ok": False, "error": "", "added": 0, "found": 0, "positions": 0,
            "resolved_won": 0, "resolved_lost": 0, "partial": ""}
    if not (a.startswith("0x") and len(a) == 42):
        return {**base, "error": "bad_address"}
    partial = []
    positions_n = 0
    try:
        # 1) 보유 포지션 + 지갑 가치
        try:
            if force:
                fetch_wallet_positions.clear()
                fetch_wallet_value.clear()
            items = fetch_wallet_positions(a)
            st.session_state.wallet_raw = items
            open_items = [it for it in items if is_open_position(it)] if isinstance(items, list) else []
            st.session_state.portfolio = [dict(
                name=it.get("title") or "Polymarket position",
                outcome=it.get("outcome", ""),
                buy=round(_safe_float(it.get("avgPrice"), 0) * 100, 1),
                shares=round(_safe_float(it.get("size"), 0), 2),
                inv=round(_safe_float(it.get("initialValue"), 0), 2),
                cur=round(_safe_float(it.get("curPrice"), 0) * 100, 1),
                asset=str(it.get("asset") or it.get("tokenId") or it.get("clobTokenId") or it.get("conditionId") or ""),
            ) for it in open_items]
            positions_n = len(open_items)
            try:
                st.session_state.pnl_raw = fetch_wallet_value(a)
            except Exception as e:
                st.session_state.pnl_raw = {"error": str(e)}
                partial.append(f"value: {e}")
        except Exception as e:
            partial.append(f"positions: {e}")
        # 2) 활동내역 → auto_trades 병합 → 장부 갱신 (+ sync meta)
        r = sync_wallet(a, limit=limit, force=force)
        if not r.get("ok"):
            return {**base, **r, "positions": positions_n, "partial": " · ".join(partial)}
        # 3) 종료된 마켓 승/패 자동확정 (fail-soft — 실패해도 동기화는 성공으로 취급)
        won = lost = 0
        if resolve:
            try:
                ar = auto_resolve_trades()
                if ar.get("ok"):
                    won, lost = int(ar.get("won", 0)), int(ar.get("lost", 0))
            except Exception:
                pass
        meta = dict(st.session_state.get("api_sync_meta") or {})
        meta["positions"] = positions_n
        if partial:
            meta["status"] = "partial"
            meta["error"] = " · ".join(partial)
        st.session_state.api_sync_meta = meta
        return {**base, **r, "ok": True, "positions": positions_n,
                "resolved_won": won, "resolved_lost": lost, "partial": " · ".join(partial)}
    except Exception as e:
        return {**base, "error": str(e), "positions": positions_n, "partial": " · ".join(partial)}


def render_tab_review():
    """거래복기 탭 전체 — 주간 리포트 → 행동 인사이트 → 규칙 시뮬레이터 → 복기 목록.
    (streamlit_app 해체 1단계: 탭 본문을 views로 이관)"""
    st.markdown(f'<div class="headline">{t("거래복기", "Trade Review")}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="subline">{t("거래일지에서 보낸 거래를 기준으로 스스로 진입 근거와 매도 타이밍을 복기합니다.", "Review trades sent from Journal and evaluate your own entry logic and exit timing.")}</div>',
        unsafe_allow_html=True,
    )

    # 주간 리포트 — 이번 주가 지난주보다 나은지부터 확인한다.
    render_weekly_report()
    # 감정·행동 복기 인사이트 — 계좌 생존의 핵심 지표라 복기 목록보다 먼저 보여준다.
    render_behavior_insights()
    # 규칙 시뮬레이터 — "지켰다면 얼마였나"로 인사이트를 행동 변화로 연결한다.
    render_rule_simulator()
    st.markdown("<hr>", unsafe_allow_html=True)

    review_items = st.session_state.get("reviews", []) or []
    if not review_items:
        st.markdown(
            f'''<div class="quiet">
<div class="q-title">{t("아직 복기할 거래가 없습니다", "No trades to review yet")}</div>
<div class="q-body">{t("거래일지에서 거래를 선택해 보내세요.", "Send trades from Journal.")}</div>
</div>''',
            unsafe_allow_html=True,
        )
    else:
        if "review_notes" not in st.session_state or not isinstance(st.session_state.review_notes, dict):
            st.session_state.review_notes = {}
        review_options = [
            "리스크", "엣지", "매도 타이밍", "내가 생각한 확률", "시장이 보는 확률",
            "진입 근거", "청산/매도 근거", "포지션 크기", "감정/FOMO",
            "배운 점", "실수/규칙 위반", "다음 행동",
        ]
        for item in list(review_items):
            if not isinstance(item, dict):
                continue
            rid = item.get("review_id") or make_review_id_from_trade_group(item, item.get("source", "review"))
            kbase = _review_widget_key("rv", rid)
            saved = st.session_state.review_notes.get(rid, {}) if isinstance(st.session_state.review_notes, dict) else {}
            saved_values = saved.get("values", {}) if isinstance(saved.get("values", {}), dict) else {}
            pnl = item.get("estimated_realized_pnl")
            pnl_text = t("확인 필요", "Verify") if pnl is None else signed_money(safe_trade_float(pnl, 0.0))
            pnl_cls = "i" if pnl is None else ("pos" if safe_trade_float(pnl, 0.0) >= 0 else "neg")
            st.markdown(
                html_block(f'''<div class="pf-card" style="margin:14px 0;">
  <div class="pf-card-head">
    <div>
      <div class="pf-title">{esc(item.get("market"))}</div>
      <div class="pf-pills">{outcome_pill(item.get("outcome"))}{cents_pill(safe_trade_float(item.get("avg_buy_price"), 0))}</div>
      <div class="pf-sub">{esc(item.get("status"))} · {esc(item.get("source", ""))}</div>
    </div>
    <span class="state i">{esc(item.get("latest_dt") or item.get("created_at", ""))}</span>
  </div>
  <div class="pf-metrics">
    <div class="pf-metric"><div class="k">{t("평균 매수", "Avg buy")}</div><div class="v">{cents(safe_trade_float(item.get("avg_buy_price"), 0))}</div></div>
    <div class="pf-metric"><div class="k">{t("평균 매도", "Avg sell")}</div><div class="v">{cents(safe_trade_float(item.get("avg_sell_price"), 0)) if safe_trade_float(item.get("sold_shares"), 0) > 0 else "—"}</div></div>
    <div class="pf-metric"><div class="k">{t("실현손익(추정)", "Realized est.")}</div><div class="v {pnl_cls}">{pnl_text}</div></div>
    <div class="pf-metric"><div class="k">{t("잔여 노출", "Remaining")}</div><div class="v">{safe_trade_float(item.get("remaining_shares"), 0):.2f} · {money(safe_trade_float(item.get("remaining_cost"), 0))}</div></div>
  </div>
</div>'''),
                unsafe_allow_html=True,
            )
            with st.expander(t("복기 작성", "Write review"), expanded=False):
                fields = st.multiselect(
                    t("복기 항목 선택", "Select review fields"),
                    review_options,
                    default=saved.get("selected_fields", []),
                    key=f"{kbase}_fields",
                )
                values = {}
                if "리스크" in fields:
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        scale = self_check_scale()
                        values["risk_score"] = st.slider("리스크 점수", 1, scale, int(saved_values.get("risk_score", max(1, min(scale, (scale + 1) // 2))) or 1), key=f"{kbase}_risk_score", help=self_check_scale_help())
                    with c2:
                        values["risk_note"] = st.text_area(t("리스크 판단 메모", "Risk notes"), value=saved_values.get("risk_note", ""), key=f"{kbase}_risk_note", height=70)
                if "엣지" in fields:
                    values["edge_cents"] = st.number_input(t("내가 봤던 Edge(¢)", "Edge I saw (¢)"), value=float(saved_values.get("edge_cents", 0.0)), key=f"{kbase}_edge")
                    values["edge_note"] = st.text_area(t("왜 저평가라고 봤는가?", "Why did it look mispriced?"), value=saved_values.get("edge_note", ""), key=f"{kbase}_edge_note", height=70)
                if "매도 타이밍" in fields:
                    sell_opts = [t("만기 보유", "Hold to expiry"), t("중간 익절", "Mid take-profit"), t("손절", "Stop-loss"), t("상환/정산 대기", "Wait redemption/settlement"), t("매도 타이밍 놓침", "Missed sell timing")]
                    values["selling_timing"] = st.selectbox(t("매도 타이밍", "Selling timing"), sell_opts, key=f"{kbase}_sell_timing")
                    values["target_sell_price"] = st.number_input(t("원했던 매도가(¢)", "Target sell price (¢)"), min_value=0.0, max_value=100.0, value=float(saved_values.get("target_sell_price", 0.0)), key=f"{kbase}_target_sell")
                    values["selling_note"] = st.text_area(t("실제 매도 판단 메모", "Exit timing notes"), value=saved_values.get("selling_note", ""), key=f"{kbase}_selling_note", height=70)
                if "내가 생각한 확률" in fields:
                    values["my_probability"] = st.number_input(t("내가 생각한 실제 확률(%)", "My estimated probability (%)"), min_value=0.0, max_value=100.0, value=float(saved_values.get("my_probability", 0.0)), key=f"{kbase}_my_prob")
                if "시장이 보는 확률" in fields:
                    values["market_probability"] = st.number_input(t("시장이 반영한 확률(%)", "Market implied probability (%)"), min_value=0.0, max_value=100.0, value=float(saved_values.get("market_probability", 0.0)), key=f"{kbase}_mkt_prob")
                if "진입 근거" in fields:
                    values["entry_rationale"] = st.text_area(t("진입 근거", "Entry rationale"), value=saved_values.get("entry_rationale", ""), key=f"{kbase}_entry_reason", height=90)
                if "청산/매도 근거" in fields:
                    values["exit_rationale"] = st.text_area(t("청산/매도 근거", "Exit rationale"), value=saved_values.get("exit_rationale", ""), key=f"{kbase}_exit_reason", height=90)
                if "포지션 크기" in fields:
                    values["position_size_note"] = st.text_area(t("포지션 크기 판단", "Position size review"), value=saved_values.get("position_size_note", ""), key=f"{kbase}_size_note", height=70)
                if "감정/FOMO" in fields:
                    scale = self_check_scale()
                    values["emotion_score"] = st.slider("감정/FOMO 점수", 1, scale, int(saved_values.get("emotion_score", 1) or 1), key=f"{kbase}_emotion_score", help=self_check_scale_help())
                    values["emotion_note"] = st.text_area(t("감정 상태 메모", "Emotion notes"), value=saved_values.get("emotion_note", ""), key=f"{kbase}_emotion_note", height=70)
                if "배운 점" in fields:
                    values["lesson"] = st.text_area(t("배운 점", "What I learned"), value=saved_values.get("lesson", ""), key=f"{kbase}_lesson", height=90)
                if "실수/규칙 위반" in fields:
                    values["mistake"] = st.text_area(t("실수 또는 규칙 위반", "Mistake or rule violation"), value=saved_values.get("mistake", ""), key=f"{kbase}_mistake", height=90)
                if "다음 행동" in fields:
                    next_opts = [t("다음엔 같은 조건이면 진입", "Enter again under same conditions"), t("다음엔 금액 축소", "Reduce size next time"), t("다음엔 진입하지 않음", "Do not enter next time"), t("정보 확인 후 진입", "Enter only after checking info"), t("규칙 재설정 필요", "Need rule reset")]
                    values["next_action"] = st.selectbox(t("다음 행동", "Next action"), next_opts, key=f"{kbase}_next_action")
                    values["next_action_note"] = st.text_area(t("다음 행동 메모", "Next action notes"), value=saved_values.get("next_action_note", ""), key=f"{kbase}_next_note", height=70)

                b1, b2 = st.columns(2)
                with b1:
                    if st.button(t("복기 저장", "Save review"), key=f"{kbase}_save", width="stretch"):
                        st.session_state.review_notes[rid] = {
                            "selected_fields": fields,
                            "values": values,
                            "saved_at": datetime.now(KST).isoformat(timespec="seconds"),
                        }
                        st.success(t("복기를 저장했습니다.", "Review saved."))
                with b2:
                    if st.button(t("복기에서 제거", "Remove from review"), key=f"{kbase}_remove", width="stretch"):
                        st.session_state.reviews = [x for x in st.session_state.get("reviews", []) if not isinstance(x, dict) or x.get("review_id") != rid]
                        if isinstance(st.session_state.get("review_notes"), dict):
                            st.session_state.review_notes.pop(rid, None)
                        st.rerun()


__all__ = [
    '_ai_plain_fallback',
    '_market_table',
    '_on_trade_date_change',
    '_on_trade_qf_change',
    '_selected_entry_form',
    'market_card_html',
    'portfolio_card_html',
    'portfolio_side_panel_html',
    'render_ai',
    'render_ai_report_json',
    'render_entry_result',
    'render_live_price_panel',
    'render_behavior_insights',
    'render_rule_simulator',
    'render_tab_review',
    '_heat_color',
    'render_equity_section',
    'render_weekly_report',
    'render_performance_summary',
    'render_profile_pnl_dashboard',
    'render_trade_date_controls',
    'render_trade_event_cards',
    'render_trade_pnl_summary',
    'sync_portfolio_hidden_checkbox',
    'sync_today_cash_adjustment',
    'sync_wallet',
    'sync_wallet_full',
    'today_dashboard_html',
]
