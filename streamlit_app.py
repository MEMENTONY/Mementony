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
from views import *


# =====================================================
# Memento v5 — onboarding · personal risk profile
# =====================================================
st.set_page_config(
    page_title="Memento",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');

/* =====================================================================
   Memento — single design system
   Brief: a calm analyst's terminal for prediction markets.
   Identity: hairlines, tabular numerics, one indigo accent, a verdict
   system (dot + word + pill) repeated identically everywhere.
   Every class name below is also used by the Python render helpers, so
   this stylesheet is purely visual — it changes no app logic.
   ===================================================================== */
:root {
  --bg:        #fbfbfc;
  --surface:   #ffffff;
  --surface-2: #f4f5f7;
  --surface-3: #fafafb;
  --ink:       #15161a;
  --ink2:      #3c3e46;
  --gray:      #71747e;
  --gray2:     #a2a5af;
  --hairline:  #e9eaee;
  --hairline-2:#f0f1f4;

  --accent:      #2e7cf6;   /* Polymarket blue — the one accent */
  --accent-press:#1b5fd9;
  --accent-soft: #eaf2fe;

  --green:      #0f7a43;  --green-soft: #e7f5ec;  --green-soft2:#eaf6f0;
  --amber:      #a45e07;  --amber-soft: #fdf3e3;
  --red:        #c5362f;  --red-soft:   #fdeeed;

  --radius-s: 10px;
  --radius-m: 16px;
  --radius-l: 22px;

  --shadow-1: 0 1px 1px rgba(20,22,30,.03);
  --shadow-2: 0 1px 2px rgba(20,22,30,.04), 0 10px 30px rgba(20,22,30,.05);

  --mono: ui-monospace, "SF Mono", "JetBrains Mono", "Cascadia Mono", Menlo, monospace;
}

html, body, .stApp { background: var(--bg) !important; color: var(--ink) !important; }

*:not([data-testid="stIconMaterial"]):not(.material-icons):not([class*="material-symbols"]) {
  font-family: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
  -webkit-font-smoothing: antialiased;
}
span[data-testid="stIconMaterial"] {
  font-family: 'Material Symbols Rounded' !important;
  font-size: 19px !important; color: var(--gray) !important;
}

.block-container {
  max-width: 1080px;
  padding-top: 3.2rem !important;
  padding-bottom: 5rem !important;
  overflow: visible !important;
}
section[data-testid="stSidebar"] {
  display: flex !important;
  width: 22.5rem !important;
  min-width: 22.5rem !important;
  background: transparent !important;
}
section[data-testid="stSidebar"] > div {
  background: transparent !important;
  padding: 1.25rem .95rem !important;
}
[data-testid="collapsedControl"] { display: flex !important; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
  background: transparent !important;
  border: none !important;
}
section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] > div {
  background:
    linear-gradient(180deg, rgba(255,255,255,.96) 0%, rgba(248,249,252,.92) 100%) !important;
  border: 1px solid rgba(226,228,235,.9) !important;
  border-radius: 28px !important;
  box-shadow: 0 1px 1px rgba(20,22,30,.04), 0 22px 54px rgba(20,22,30,.10) !important;
  backdrop-filter: saturate(180%) blur(22px);
  -webkit-backdrop-filter: saturate(180%) blur(22px);
  padding: 18px 16px 17px 16px !important;
}
.today-panel { padding: 1px 1px 8px 1px; }
.today-panel-head { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom: 14px; }
.today-panel-title { font-size: 15px; font-weight: 780; letter-spacing: -.02em; line-height: 1.2; }
.today-panel-sub { margin-top: 4px; font-size: 12px; color: var(--gray); line-height: 1.45; }
.today-panel-dot {
  width: 30px; height: 30px; border-radius: 12px;
  background: linear-gradient(180deg, #f6f8ff, #e9edff);
  border: 1px solid #dfe4ff;
  position: relative; flex: 0 0 auto;
}
.today-panel-dot::after {
  content: ""; position:absolute; inset: 9px; border-radius: 50%;
  background: var(--accent); box-shadow: 0 0 0 5px rgba(46,124,246,.12);
}
.today-goal-kpi {
  margin: 0 0 12px 0;
  padding: 18px 17px 16px 17px;
  background: #111318;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 24px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 16px 34px rgba(20,22,30,.16);
}
.today-goal-kpi .k {
  font-size: 11px; font-weight: 760; letter-spacing: .075em; text-transform: uppercase;
  color: rgba(255,255,255,.64);
}
.today-goal-kpi .v {
  margin-top: 8px; font-size: 39px; font-weight: 790; letter-spacing: -.04em;
  line-height: .98; color: #fff; font-variant-numeric: tabular-nums;
}
.today-goal-kpi .s { margin-top: 9px; font-size: 12.5px; color: rgba(255,255,255,.66); line-height: 1.45; }
.today-limit-grid { display:grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }
.today-limit-cell {
  background: rgba(255,255,255,.72); border: 1px solid rgba(233,234,238,.9);
  border-radius: 17px; padding: 11px 12px;
}
.today-limit-cell .k { font-size: 10.5px; color: var(--gray); font-weight: 700; letter-spacing: .02em; }
.today-limit-cell .v {
  margin-top: 5px; font-size: 15px; font-weight: 760; letter-spacing: -.025em;
  color: var(--ink); font-variant-numeric: tabular-nums;
}
.today-status-card {
  margin: 0 0 14px 0; padding: 13px 13px 12px 13px;
  border-radius: 18px; border: 1px solid rgba(233,234,238,.9);
  background: rgba(255,255,255,.72);
}
.today-status-card .k {
  font-size: 10.5px; font-weight: 760; letter-spacing: .075em;
  text-transform: uppercase; color: var(--gray);
}
.today-status-card .v {
  margin-top: 5px; font-size: 15px; font-weight: 780;
  letter-spacing: -.025em; color: var(--ink);
}
.today-status-card .s {
  margin-top: 6px; font-size: 12px; line-height: 1.45; color: var(--gray);
}
.today-status-card.g { background: rgba(231,245,236,.72); border-color: rgba(15,122,67,.14); }
.today-status-card.w { background: rgba(253,243,227,.76); border-color: rgba(164,94,7,.15); }
.today-status-card.b { background: rgba(253,238,237,.78); border-color: rgba(197,54,47,.16); }
.today-control-label {
  margin: 3px 0 9px 0; font-size: 11px; font-weight: 760;
  letter-spacing: .08em; text-transform: uppercase; color: var(--gray);
}
.portfolio-side-panel {
  position: fixed;
  right: 18px;
  top: 76px;
  width: 21rem;
  z-index: 42;
  pointer-events: none;
}
.portfolio-panel-card {
  pointer-events: auto;
  background: linear-gradient(180deg, rgba(255,255,255,.96) 0%, rgba(248,249,252,.92) 100%);
  border: 1px solid rgba(226,228,235,.9);
  border-radius: 28px;
  box-shadow: 0 1px 1px rgba(20,22,30,.04), 0 22px 54px rgba(20,22,30,.10);
  backdrop-filter: saturate(180%) blur(22px);
  -webkit-backdrop-filter: saturate(180%) blur(22px);
  padding: 18px 16px 16px 16px;
  max-height: calc(100vh - 98px);
  overflow-y: auto;
}
.portfolio-panel-head { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom: 14px; }
.portfolio-panel-title { font-size: 15px; font-weight: 780; letter-spacing: -.02em; line-height: 1.2; }
.portfolio-panel-sub { margin-top: 4px; font-size: 12px; color: var(--gray); line-height: 1.45; }
.portfolio-panel-badge {
  min-width: 52px; padding: 6px 8px; border-radius: 999px; text-align:center;
  font-size: 11px; font-weight: 760; color: var(--green);
  background: var(--green-soft2); border: 1px solid rgba(15,122,67,.10);
}
.portfolio-total-kpi {
  margin: 0 0 12px 0; padding: 18px 17px 16px 17px;
  background: #111318; border: 1px solid rgba(255,255,255,.08);
  border-radius: 24px; box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 16px 34px rgba(20,22,30,.16);
}
.portfolio-total-kpi .k {
  font-size: 11px; font-weight: 760; letter-spacing: .075em; text-transform: uppercase;
  color: rgba(255,255,255,.64);
}
.portfolio-total-kpi .v {
  margin-top: 8px; font-size: 36px; font-weight: 790; letter-spacing: -.04em;
  line-height: .98; color: #fff; font-variant-numeric: tabular-nums;
}
.portfolio-total-kpi .s { margin-top: 9px; font-size: 12.5px; color: rgba(255,255,255,.66); line-height: 1.45; }
.portfolio-mini-grid { display:grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 13px; }
.portfolio-mini-cell {
  background: rgba(255,255,255,.72); border: 1px solid rgba(233,234,238,.9);
  border-radius: 17px; padding: 11px 12px;
}
.portfolio-mini-cell .k { font-size: 10.5px; color: var(--gray); font-weight: 700; letter-spacing: .02em; }
.portfolio-mini-cell .v {
  margin-top: 5px; font-size: 15px; font-weight: 760; letter-spacing: -.025em;
  color: var(--ink); font-variant-numeric: tabular-nums;
}
.portfolio-today-card {
  margin: 0 0 13px 0; padding: 12px 12px 11px 12px;
  border-radius: 18px; border: 1px solid rgba(233,234,238,.9);
  background: rgba(255,255,255,.72);
}
.portfolio-today-card .k {
  font-size: 10.5px; font-weight: 760; letter-spacing: .075em;
  text-transform: uppercase; color: var(--gray);
}
.portfolio-today-card .v {
  margin-top: 5px; font-size: 15px; font-weight: 790;
  letter-spacing: -.025em; color: var(--ink); font-variant-numeric: tabular-nums;
}
.portfolio-today-card .s {
  margin-top: 5px; font-size: 11.5px; line-height: 1.45; color: var(--gray);
}
.portfolio-today-card.g { background: rgba(231,245,236,.72); border-color: rgba(15,122,67,.14); }
.portfolio-today-card.w { background: rgba(253,243,227,.76); border-color: rgba(164,94,7,.15); }
.portfolio-today-card.b { background: rgba(253,238,237,.78); border-color: rgba(197,54,47,.16); }
.portfolio-position-list { display:flex; flex-direction:column; gap: 7px; margin-top: 8px; }
.portfolio-position-row {
  display:grid; grid-template-columns: 1fr auto; gap: 10px; align-items:center;
  padding: 9px 10px; border: 1px solid rgba(233,234,238,.9);
  border-radius: 15px; background: rgba(255,255,255,.62);
}
.portfolio-position-row .n {
  font-size: 12px; font-weight: 710; color: var(--ink2);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.portfolio-position-row .o { margin-top: 3px; font-size: 11px; color: var(--gray); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.portfolio-position-row .v { font-size: 12.5px; font-weight: 760; color: var(--ink); font-variant-numeric: tabular-nums; }
.portfolio-empty {
  padding: 18px 14px; border-radius: 20px; background: rgba(255,255,255,.72);
  border: 1px dashed rgba(162,165,175,.45); font-size: 12.5px; color: var(--gray);
  line-height: 1.55; text-align:center;
}
.portfolio-section-head {
  display:flex; justify-content:space-between; align-items:center; gap: 10px;
  margin: 13px 0 8px 0;
}
.portfolio-section-head .k {
  font-size: 11px; font-weight: 760; letter-spacing: .08em; text-transform: uppercase; color: var(--gray);
}
.portfolio-section-head .v { font-size: 11.5px; font-weight: 720; color: var(--gray2); }
.portfolio-more {
  padding: 2px 4px 0 4px; font-size: 11.5px; color: var(--gray2); text-align:center;
}
.portfolio-completed-list { display:flex; flex-direction:column; gap: 7px; margin-top: 8px; }
.portfolio-completed-row {
  display:grid; grid-template-columns: 1fr auto; gap: 10px; align-items:center;
  padding: 10px 10px; border-radius: 16px; background: rgba(255,255,255,.68);
  border: 1px solid rgba(233,234,238,.9);
}
.portfolio-completed-row.g { border-color: rgba(15,122,67,.16); background: rgba(231,245,236,.72); }
.portfolio-completed-row.b { border-color: rgba(197,54,47,.16); background: rgba(253,238,237,.72); }
.portfolio-completed-row .n {
  font-size: 12px; font-weight: 720; color: var(--ink2);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.portfolio-completed-row .o { margin-top: 3px; font-size: 11px; color: var(--gray); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.portfolio-completed-row .v { font-size: 13px; font-weight: 790; font-variant-numeric: tabular-nums; }
.portfolio-completed-row.g .v { color: var(--green); }
.portfolio-completed-row.b .v { color: var(--red); }
.sync-details {
  margin-top: 13px; border-radius: 17px; border: 1px solid rgba(233,234,238,.9);
  background: rgba(255,255,255,.62); overflow: hidden;
}
.sync-details summary {
  cursor: pointer; list-style: none; padding: 11px 12px;
  font-size: 12px; font-weight: 760; color: var(--ink2);
}
.sync-details summary::-webkit-details-marker { display: none; }
.sync-details summary::after { content: "+"; float: right; color: var(--gray2); font-weight: 780; }
.sync-details[open] summary::after { content: "−"; }
.sync-details .sync-body {
  padding: 0 12px 12px 12px; display: grid; gap: 7px;
  font-size: 11.5px; color: var(--gray); line-height: 1.45;
}
.sync-details .sync-row { display:flex; justify-content:space-between; gap: 12px; }
.sync-details .sync-row b { color: var(--ink2); font-weight: 720; }
@media (min-width: 1380px) {
  .block-container { margin-right: 22.5rem !important; }
}
@media (max-width: 1379px) {
  .portfolio-side-panel { display: none; }
}
.stApp, .main, div[data-testid="stAppViewContainer"] { overflow: visible !important; }
header[data-testid="stHeader"] {
  background: rgba(251,251,252,.82) !important;
  backdrop-filter: saturate(180%) blur(16px); -webkit-backdrop-filter: saturate(180%) blur(16px);
  height: auto !important; min-height: 2.6rem !important; z-index: 50 !important; border: none !important;
}
h1,h2,h3,h4,p,span,div,label { color: var(--ink); }
:focus-visible { outline: 2px solid var(--accent) !important; outline-offset: 2px; }

/* ---------- masthead + page intros ---------- */
.masthead { padding: 4px 0 2px 0 !important; margin: 0 !important; overflow: visible !important; }
.masthead .name {
  font-size: 23px; font-weight: 760; letter-spacing: -.04em;
  display: inline-flex; align-items: center; gap: 9px;
}
.masthead .name::before {
  content: ""; width: 13px; height: 13px; border-radius: 4px; transform: rotate(45deg);
  background: linear-gradient(135deg, var(--accent), #6fb0ff);
}
.masthead .tag { font-size: 12px; color: var(--gray2); margin-top: 4px; }
.mh-chip {
  display: inline-block; margin: 8px 0 16px 0 !important;
  font-size: 11.5px; color: var(--gray); background: var(--surface-2);
  border: 1px solid var(--hairline); border-radius: 999px; padding: 5px 13px;
  letter-spacing: .005em;
}

.headline { font-size: 29px; font-weight: 760; letter-spacing: -.04em; line-height: 1.1; margin: 10px 0 4px 0; }
.subline  { font-size: 14px; color: var(--gray); line-height: 1.55; margin-bottom: 20px; max-width: 740px; }
.eyebrow  {
  margin: 22px 0 9px 0; font-size: 11px; font-weight: 750; color: var(--gray);
  letter-spacing: .09em; text-transform: uppercase;
}

/* ---------- verdict band (the signature element) ---------- */
.verdict {
  background: var(--surface);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-l);
  box-shadow: var(--shadow-2);
  padding: 22px 24px;
  margin: 14px 0 18px 0;
}
.verdict .eyebrow { margin-top: 0; }
.verdict .v-title { font-size: 33px; font-weight: 770; letter-spacing: -.045em; line-height: 1.1; }
.verdict .v-sub   { margin-top: 9px; font-size: 14px; color: var(--gray); line-height: 1.6; }

.dot { display:inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 11px; vertical-align: 3px; }
.dot.g { background: var(--green); }
.dot.w { background: var(--amber); }
.dot.b { background: var(--red); }
.dot.i { background: var(--gray2); }

/* ---------- pills / state chips ---------- */
.state, .pill {
  display:inline-block; border-radius: 999px; padding: 5px 11px;
  font-size: 12px; font-weight: 680; letter-spacing: -.005em; white-space: nowrap;
}
.state.g, .pill.g { background: var(--green-soft2); color: var(--green); }
.state.w, .pill.w { background: var(--amber-soft);  color: var(--amber); }
.state.b, .pill.b { background: var(--red-soft);    color: var(--red); }
.state.i, .pill.i { background: var(--surface-2);   color: var(--gray); }

/* ---------- stat grid (KPI strip) ---------- */
.stats {
  display: grid; grid-template-columns: repeat(4, 1fr);
  background: var(--surface); border: 1px solid var(--hairline);
  border-radius: var(--radius-l); box-shadow: var(--shadow-1);
  margin: 10px 0 22px 0; overflow: hidden;
}
.stats.three { grid-template-columns: repeat(3, 1fr); }
.stat { padding: 17px 18px; border-right: 1px solid var(--hairline-2); }
.stat:last-child { border-right: none; }
.stat .s-label { font-size: 11.5px; font-weight: 650; color: var(--gray); }
.stat .s-value {
  margin-top: 7px; font-size: 25px; font-weight: 750; letter-spacing: -.04em;
  font-variant-numeric: tabular-nums; line-height: 1.05;
}
.stat .s-value.pos { color: var(--green); }
.stat .s-value.neg { color: var(--red); }
.stat .s-note { margin-top: 5px; font-size: 11.5px; color: var(--gray2); line-height: 1.4; }

/* ---------- spec rows (labelled key/value cards) ---------- */
.spec { display: block; }
.spec-row {
  display: grid; grid-template-columns: 180px 1fr auto; gap: 18px; align-items: start;
  background: var(--surface); border: 1px solid var(--hairline);
  border-radius: var(--radius-m); padding: 14px 16px; margin: 9px 0; box-shadow: var(--shadow-1);
}
.spec-key { font-size: 12.5px; font-weight: 650; color: var(--gray); padding-top: 1px; }
.spec-val { font-size: 14px; color: var(--ink2); line-height: 1.6; font-variant-numeric: tabular-nums; }
.spec-val b { color: var(--ink); font-weight: 700; }

/* ---------- list lines ---------- */
.line {
  display: flex; gap: 11px; padding: 11px 2px; border-bottom: 1px solid var(--hairline-2);
  font-size: 14px; color: var(--ink2); line-height: 1.6; align-items: baseline;
}
.line:last-child { border-bottom: none; }
.line b { color: var(--ink); font-weight: 700; }

/* ---------- meter (gauge motif) ---------- */
.meter {
  background: var(--surface); border: 1px solid var(--hairline);
  border-radius: var(--radius-m); padding: 14px 16px; margin: 9px 0; box-shadow: var(--shadow-1);
}
.meter .m-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 9px; }
.meter .m-label { font-size: 13px; color: var(--ink2); font-weight: 650; }
.meter .m-right { display: flex; gap: 10px; align-items: center; }
.meter .m-num { font-size: 15px; font-weight: 720; font-variant-numeric: tabular-nums; letter-spacing: -.02em; }
.meter .m-num.g { color: var(--green); } .meter .m-num.w { color: var(--amber); }
.meter .m-num.b { color: var(--red); }   .meter .m-num.i { color: var(--ink); }
.meter .m-track { height: 6px; border-radius: 999px; background: var(--surface-2); overflow: hidden; }
.meter .m-fill  { height: 100%; border-radius: 999px; transition: width .4s cubic-bezier(.2,.7,.2,1); }

/* ---------- empty / quiet states ---------- */
.quiet {
  border: 1px dashed var(--hairline); border-radius: var(--radius-l);
  padding: 50px 24px; text-align: center; background: var(--surface-3);
}
.quiet .q-title { font-size: 16px; font-weight: 700; }
.quiet .q-body  { margin-top: 9px; font-size: 13.5px; color: var(--gray); line-height: 1.65; }

/* ---------- portfolio + activity cards ---------- */
.pf-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 14px; margin: 10px 0 20px 0; }
.pf-card {
  border: 1px solid var(--hairline); border-radius: var(--radius-l);
  padding: 19px 20px; background: var(--surface); box-shadow: var(--shadow-1);
}
.pf-card-head { display:flex; justify-content:space-between; gap:14px; align-items:flex-start; margin-bottom: 14px; }
.pf-title { font-size: 15px; font-weight: 700; letter-spacing: -.018em; line-height: 1.35; }
.pf-sub   { margin-top: 5px; font-size: 12.5px; color: var(--gray); line-height: 1.45; }
.pf-big   { font-size: 29px; font-weight: 760; letter-spacing: -.04em; font-variant-numeric: tabular-nums; margin: 2px 0; }
.pf-big.pos { color: var(--green); } .pf-big.neg { color: var(--red); }
.pf-metrics { display:grid; grid-template-columns: repeat(3,1fr); gap: 10px; margin: 14px 0; }
.pf-metric { border-top: 1px solid var(--hairline); padding-top: 10px; min-width: 0; }
.pf-metric .k { font-size: 11px; color: var(--gray); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pf-metric .v { margin-top: 4px; font-size: 14px; font-weight: 700; color: var(--ink2); font-variant-numeric: tabular-nums; }
.pf-note { font-size: 12.5px; line-height: 1.6; color: var(--ink2); padding-top: 12px; border-top: 1px solid var(--hairline); }

/* Polymarket-style outcome / price pills (color-coded chips) */
.pf-pills { display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-top:6px; }
.pill { display:inline-flex; align-items:center; padding:2px 10px; border-radius:999px;
  font-size:12px; font-weight:700; line-height:1.7; letter-spacing:.01em; white-space:nowrap; }
.pill.blue   { background:#e8edfe; color:#2c47d6; }
.pill.green  { background:#e6f5ec; color:#0f7a43; }
.pill.red    { background:#fdeaea; color:#c5362f; }
.pill.amber  { background:#fbf0dc; color:#a45e07; }
.pill.purple { background:#f0e9fd; color:#6d3bd1; }
.pill.teal   { background:#e0f3f1; color:#0d7a70; }
.price-pill { display:inline-flex; align-items:center; padding:2px 9px; border-radius:999px;
  background:var(--surface-2); color:var(--ink2); font-weight:700; font-size:12px;
  font-variant-numeric:tabular-nums; }

.trade-grid { display:grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin: 10px 0 16px 0; }
.trade-card { border: 1px solid var(--hairline); border-radius: var(--radius-m); padding: 16px; background: var(--surface); box-shadow: var(--shadow-1); }
.trade-card .k { font-size: 11.5px; color: var(--gray); }
.trade-card .v { margin-top: 6px; font-size: 23px; font-weight: 750; letter-spacing: -.035em; font-variant-numeric: tabular-nums; }
.trade-insight { border-top: 1px solid var(--hairline-2); padding: 12px 2px; font-size: 14px; line-height: 1.6; color: var(--ink2); }
.trade-insight:first-child { border-top: none; }

/* ---------- profile hero (P&L summary) ---------- */
.profile-hero {
  border: 1px solid var(--hairline); border-radius: var(--radius-l);
  padding: 22px 24px; background: var(--surface); box-shadow: var(--shadow-2); margin: 12px 0 22px 0;
}
.profile-hero-head { display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom: 18px; }
.profile-hero .title { font-size: 17px; font-weight: 760; letter-spacing: -.02em; }
.profile-hero .sub   { margin-top: 6px; font-size: 12.5px; color: var(--gray); line-height: 1.5; }
.profile-grid { display:grid; grid-template-columns: repeat(4,1fr); gap: 14px 12px; }
.profile-cell { border-top: 1px solid var(--hairline); padding-top: 12px; min-width: 0; }
.profile-cell .k { font-size: 11px; color: var(--gray); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.profile-cell .v { margin-top: 6px; font-size: 20px; font-weight: 760; letter-spacing: -.035em; font-variant-numeric: tabular-nums; }
.profile-cell .v.pos { color: var(--green); } .profile-cell .v.neg { color: var(--red); }

/* ---------- market cards ---------- */
.market-grid { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 14px; margin: 10px 0 20px 0; }
.market-card { border: 1px solid var(--hairline); border-radius: var(--radius-l); padding: 18px 20px; background: var(--surface); box-shadow: var(--shadow-1); margin-bottom: 12px; }
.market-head { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom: 12px; }
.market-title { font-size: 15px; font-weight: 720; line-height: 1.35; letter-spacing: -.018em; }
.market-sub { margin-top: 5px; font-size: 12.5px; color: var(--gray); line-height: 1.45; }
.market-price { font-size: 28px; font-weight: 760; letter-spacing: -.04em; font-variant-numeric: tabular-nums; }
.market-metrics { display:grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-top: 12px; }
.market-metric { border-top: 1px solid var(--hairline); padding-top: 10px; min-width:0; }
.market-metric .k { font-size: 11px; color: var(--gray); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.market-metric .v { margin-top: 4px; font-size: 13.5px; font-weight: 700; color: var(--ink2); font-variant-numeric: tabular-nums; }
.market-note { font-size: 12.5px; color: var(--gray); line-height: 1.55; margin-top: 10px; }

/* ---------- AI report cards ---------- */
.ai-report-grid { display:grid; grid-template-columns: repeat(2,1fr); gap: 14px; margin-top: 12px; }
.ai-report-card { border: 1px solid var(--hairline); border-radius: var(--radius-m); padding: 16px; background: var(--surface); box-shadow: var(--shadow-1); }
.ai-report-card .a-key { font-size: 11px; font-weight: 750; color: var(--gray); letter-spacing: .07em; text-transform: uppercase; }
.ai-report-card .a-body { margin-top: 8px; font-size: 14px; line-height: 1.65; color: var(--ink2); }

.rc-grid { display:grid; grid-template-columns: repeat(2,1fr); gap: 14px; margin-top: 12px; }
.rc-card, .rc-action {
  border: 1px solid var(--hairline); border-radius: var(--radius-m);
  padding: 16px 17px; background: var(--surface); box-shadow: var(--shadow-1); margin-top: 12px;
}
.rc-action { background: var(--accent-soft); border-color: #dfe3fd; }
.rc-h { font-size: 11px; font-weight: 750; color: var(--gray); letter-spacing:.07em; text-transform: uppercase; margin-bottom: 8px; }
.rc-row { display:flex; justify-content:space-between; gap: 14px; border-top: 1px solid var(--hairline-2); padding: 9px 0; font-size: 13.5px; }
.rc-row:first-of-type { border-top: none; }
.rc-k { color: var(--gray); flex: 0 0 36%; }
.rc-v { color: var(--ink2); text-align:right; flex:1; font-variant-numeric: tabular-nums; }
.rc-v b { color: var(--ink); }
.rc-note { font-size: 14px; line-height: 1.7; color: var(--ink2); }
.rc-missing {
  margin-top: 12px; border: 1px dashed var(--hairline); border-radius: var(--radius-m);
  padding: 15px 16px; color: var(--gray); font-size: 13px; line-height: 1.7; background: var(--surface-3);
}
.rc-missing .rc-h { color: var(--gray); }

.ai-block { border-top: 1px solid var(--hairline-2); padding: 15px 0; }
.ai-block .a-key { font-size: 11px; font-weight: 700; color: var(--gray); letter-spacing: .07em; text-transform: uppercase; }
.ai-block .a-body { margin-top: 7px; font-size: 14.5px; color: var(--ink2); line-height: 1.7; }

.footnote { font-size: 11.5px; color: var(--gray2); line-height: 1.6; margin-top: 10px; }
.ob-step { font-size: 12px; font-weight: 650; color: var(--accent); letter-spacing: .06em; text-transform: uppercase; margin-bottom: 6px; }

/* legacy card/metric helpers kept for compatibility */
.card, .card-lead, .pos-card {
  background: var(--surface); border: 1px solid var(--hairline);
  border-radius: var(--radius-l); box-shadow: var(--shadow-1); padding: 18px 20px; margin: 12px 0;
}
.card-lead { padding: 22px 24px; }
.card-title { font-size: 13px; font-weight: 650; color: var(--gray); margin-bottom: 8px; }
.card-value { font-size: 33px; font-weight: 760; letter-spacing: -.045em; font-variant-numeric: tabular-nums; }
.card-sub { font-size: 13px; color: var(--gray); line-height: 1.55; margin-top: 5px; }
.muted { color: var(--gray2) !important; font-size: 12px !important; }
.metric { display:flex; flex-direction:column; gap: 5px; }
.metric .metric-label, .metric-label { font-size: 12px; color: var(--gray); font-weight: 600; }
.metric .metric-value, .metric-value { font-size: 24px; color: var(--ink); font-weight: 750; letter-spacing: -.03em; font-variant-numeric: tabular-nums; }
.metric-lg .metric-value, .metric-value-lg { font-size: 33px; font-weight: 760; letter-spacing: -.045em; }
.metric-sub { font-size: 12px; color: var(--gray2); }

/* ---------- Streamlit inputs ---------- */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
textarea {
  background: var(--surface) !important; border: 1px solid var(--hairline) !important;
  border-radius: 13px !important; color: var(--ink) !important;
  font-size: 15px !important; font-weight: 480 !important; min-height: 44px;
  box-shadow: var(--shadow-1) !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus,
textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 4px rgba(46,124,246,.14) !important;
}
div[data-baseweb="select"] > div {
  background: var(--surface) !important; border: 1px solid var(--hairline) !important;
  border-radius: 13px !important; color: var(--ink) !important; min-height: 44px; box-shadow: var(--shadow-1) !important;
}
div[data-testid="stNumberInput"] button { background: transparent !important; border: none !important; color: var(--gray) !important; }
div[data-testid="stWidgetLabel"] p { font-size: 12.5px !important; font-weight: 600 !important; color: var(--ink2) !important; }

.stButton > button, .stFormSubmitButton > button {
  background: var(--accent) !important; color: #fff !important;
  border: none !important; border-radius: 12px !important;
  font-size: 14.5px !important; font-weight: 680 !important;
  min-height: 45px; box-shadow: none !important; transition: background .16s ease, transform .12s ease !important;
}
.stButton > button:hover, .stFormSubmitButton > button:hover { background: var(--accent-press) !important; color:#fff !important; transform: translateY(-1px); }
div[data-testid="stDownloadButton"] > button {
  background: var(--surface-2) !important; color: var(--ink) !important;
  border: 1px solid var(--hairline) !important; border-radius: 12px !important; font-weight: 650 !important;
}
div[data-testid="stDownloadButton"] > button:hover { background: #eceef1 !important; }

/* ---------- tabs ---------- */
div[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: var(--surface-2); border-radius: 13px; padding: 4px; gap: 2px;
  border: 1px solid var(--hairline); display: inline-flex; width: auto; flex-wrap: wrap;
}
div[data-testid="stTabs"] [data-baseweb="tab"] { border-radius: 10px !important; padding: 7px 15px !important; background: transparent !important; border: none !important; }
div[data-testid="stTabs"] [data-baseweb="tab"] p { font-size: 13.5px !important; font-weight: 620 !important; color: var(--gray) !important; }
div[data-testid="stTabs"] [aria-selected="true"] { background: var(--surface) !important; box-shadow: var(--shadow-1) !important; }
div[data-testid="stTabs"] [aria-selected="true"] p { color: var(--ink) !important; }
div[data-testid="stTabs"] [data-baseweb="tab-highlight"], div[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }

div[data-testid="stRadio"] > div { gap: 4px; }
div[data-testid="stRadio"] label p { font-size: 13.5px !important; color: var(--ink2) !important; }

div[data-testid="stExpander"] {
  border: 1px solid var(--hairline) !important; border-radius: var(--radius-m) !important;
  background: var(--surface) !important; box-shadow: var(--shadow-1) !important; overflow: hidden;
}
div[data-testid="stExpander"] summary { padding: 13px 16px !important; align-items: center !important; }
div[data-testid="stExpander"] summary p { font-size: 13.5px !important; font-weight: 650 !important; }

div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
  border: 1px solid var(--hairline) !important; border-radius: var(--radius-m); overflow: hidden;
}

code, pre {
  background: var(--surface-2) !important; border: 1px solid var(--hairline) !important;
  border-radius: 11px !important; color: var(--ink2) !important; font-size: 12.5px !important;
  font-family: var(--mono) !important; white-space: pre-wrap !important;
}
hr { border: none; border-top: 1px solid var(--hairline); margin: 24px 0; }

/* ---------- responsive ---------- */
@media (max-width: 900px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 3rem !important; }
  .stats, .stats.three { grid-template-columns: repeat(2,1fr); }
  .pf-grid, .market-grid, .ai-report-grid, .rc-grid { grid-template-columns: 1fr; }
  .pf-metrics { grid-template-columns: repeat(2,1fr); }
  .trade-grid { grid-template-columns: repeat(2,1fr); }
  .profile-grid { grid-template-columns: repeat(2,1fr); }
  .spec-row { grid-template-columns: 1fr; gap: 7px; }
  .verdict .v-title { font-size: 27px; }
  .headline { font-size: 25px; }
}
@media (max-width: 560px) {
  .stats, .stats.three, .trade-grid, .profile-grid { grid-template-columns: 1fr; }
  .stat { border-right: none; border-bottom: 1px solid var(--hairline-2); }
  .stat:last-child { border-bottom: none; }
}

/* =====================================================================
   Memento — Apple cognitive-minimal design override
   Philosophy: fewer recognition steps, basic geometry, symmetry, grouping.
   This section intentionally overrides the legacy visual layer only.
   ===================================================================== */
:root {
  --bg: #f5f5f7;
  --surface: rgba(255,255,255,.92);
  --surface-2: #f2f2f4;
  --surface-3: #fbfbfd;
  --ink: #1d1d1f;
  --ink2: #34363d;
  --gray: #6e6e73;
  --gray2: #a1a1a6;
  --hairline: rgba(0,0,0,.08);
  --hairline-2: rgba(0,0,0,.055);
  --accent: #0071e3;
  --accent-press: #0066cc;
  --accent-soft: #eaf3ff;
  --green: #12805c; --green-soft:#e8f6ef; --green-soft2:#edf8f2;
  --amber: #b46a00; --amber-soft:#fff3df;
  --red: #d43d32; --red-soft:#fff0ee;
  --radius-s: 12px;
  --radius-m: 18px;
  --radius-l: 26px;
  --shadow-1: 0 1px 2px rgba(0,0,0,.03), 0 8px 24px rgba(0,0,0,.035);
  --shadow-2: 0 2px 4px rgba(0,0,0,.04), 0 18px 56px rgba(0,0,0,.07);
}

html, body, .stApp {
  background:
    radial-gradient(circle at top left, rgba(0,113,227,.07), transparent 34rem),
    linear-gradient(180deg, #fbfbfd 0%, var(--bg) 100%) !important;
}

.block-container {
  max-width: 1120px;
  padding-top: 3.6rem !important;
}

.masthead {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}
.masthead .name {
  font-size: 26px;
  font-weight: 780;
  letter-spacing: -.055em;
}
.masthead .name::before {
  width: 11px; height: 11px;
  border-radius: 50%;
  transform: none;
  background: var(--accent);
}
.masthead .tag, .subline, .footnote { color: var(--gray) !important; }
.mh-chip {
  background: rgba(255,255,255,.75);
  border-color: var(--hairline);
  color: var(--gray);
  backdrop-filter: blur(18px);
}

.headline {
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 780;
  letter-spacing: -.06em;
  line-height: 1.04;
  margin-top: 18px;
}
.subline {
  font-size: 15px;
  max-width: 680px;
  line-height: 1.65;
}
.eyebrow {
  color: var(--gray) !important;
  letter-spacing: .11em;
}

.verdict, .profile-hero, .pf-card, .market-card, .trade-card, .card, .card-lead, .pos-card,
.ai-report-card, .rc-card, .rc-action, .meter, .spec-row, .quiet, div[data-testid="stExpander"] {
  background: var(--surface) !important;
  border: 1px solid var(--hairline) !important;
  border-radius: var(--radius-l) !important;
  box-shadow: var(--shadow-1) !important;
  backdrop-filter: saturate(180%) blur(18px);
  -webkit-backdrop-filter: saturate(180%) blur(18px);
}

.verdict { padding: 26px 28px; }
.verdict .v-title {
  font-size: clamp(30px, 4vw, 44px);
  font-weight: 790;
  letter-spacing: -.06em;
}
.verdict .v-sub { max-width: 760px; }

.stats {
  border-radius: var(--radius-l);
  background: var(--surface);
  box-shadow: var(--shadow-1);
}
.stat {
  padding: 18px 20px;
}
.stat .s-value, .pf-big, .profile-cell .v, .trade-card .v, .market-price {
  letter-spacing: -.05em;
}

.pf-grid, .market-grid, .ai-report-grid, .rc-grid {
  gap: 16px;
}
.pf-card, .market-card {
  padding: 20px 22px;
}
.pf-metrics, .market-metrics, .profile-grid {
  gap: 12px;
}

.spec-row {
  grid-template-columns: 170px minmax(0,1fr) auto;
  gap: 16px;
  margin: 8px 0;
}
.spec-val, .line, .rc-note, .ai-block .a-body {
  word-break: keep-all;
  overflow-wrap: anywhere;
}

.state, .pill {
  border-radius: 999px;
  font-weight: 720;
}
.dot {
  width: 8px; height: 8px;
}

.meter .m-track { height: 7px; background: #ebebef; }
.meter .m-fill { box-shadow: inset 0 0 0 1px rgba(255,255,255,.18); }

div[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: rgba(255,255,255,.72) !important;
  border: 1px solid var(--hairline) !important;
  border-radius: 999px !important;
  padding: 5px !important;
  box-shadow: var(--shadow-1);
  backdrop-filter: saturate(180%) blur(18px);
}
div[data-testid="stTabs"] [data-baseweb="tab"] {
  border-radius: 999px !important;
  padding: 8px 16px !important;
}
div[data-testid="stTabs"] [aria-selected="true"] {
  background: var(--ink) !important;
  box-shadow: none !important;
}
div[data-testid="stTabs"] [aria-selected="true"] p {
  color: #fff !important;
}

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
textarea,
div[data-baseweb="select"] > div {
  background: rgba(255,255,255,.88) !important;
  border: 1px solid var(--hairline) !important;
  border-radius: 16px !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.6), var(--shadow-1) !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus,
textarea:focus {
  border-color: rgba(0,113,227,.65) !important;
  box-shadow: 0 0 0 4px rgba(0,113,227,.14) !important;
}

.stButton > button, .stFormSubmitButton > button {
  border-radius: 999px !important;
  min-height: 44px;
  font-weight: 740 !important;
  background: var(--accent) !important;
}
div[data-testid="stDownloadButton"] > button {
  border-radius: 999px !important;
}

/* User-facing tables must compress rather than create horizontal cognition cost. */
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
  max-width: 100% !important;
  border-radius: var(--radius-l) !important;
}
div[data-testid="stDataFrame"] * , div[data-testid="stDataEditor"] * {
  font-size: 12px !important;
}

/* Grouped cards: one visual family, one recognition pattern. */
.pf-card-head, .market-head, .profile-hero-head {
  align-items: flex-start;
}
.pf-title, .market-title, .profile-hero .title {
  font-weight: 760;
  letter-spacing: -.025em;
}

@media (max-width: 900px) {
  .block-container { padding-top: 2.8rem !important; }
  .spec-row { grid-template-columns: 1fr; }
  div[data-testid="stTabs"] [data-baseweb="tab-list"] { width: 100%; }
}

</style>
""",
    unsafe_allow_html=True,
)

# =====================================================
# State
# =====================================================












for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

load_local_state()

# 재배포/재부팅으로 로컬 상태 파일이 사라졌을 때 구글 시트 스냅샷에서 자동 복원.
# Apps Script URL을 Streamlit Secrets(gsheet_webapp_url)에 넣어두면 URL도 재배포를 살아남는다.
try:
    if (st.session_state.get("_local_state_status") == "empty"
            and not st.session_state.get("_state_restore_attempted")
            and gsheet_webapp_endpoint()):
        st.session_state._state_restore_attempted = True
        _rs = restore_state_from_webapp()
        if _rs.get("ok") and _rs.get("restored"):
            try:
                st.toast(t(f"구글 시트에서 상태 복원됨 · {_rs.get('saved_at', '')}",
                           f"State restored from Google Sheets · {_rs.get('saved_at', '')}"))
            except Exception:
                pass
except Exception:
    pass

if not isinstance(st.session_state.get("portfolio"), list):
    st.session_state.portfolio = []
else:
    st.session_state.portfolio = [p for p in st.session_state.portfolio if isinstance(p, dict)]
if not isinstance(st.session_state.get("portfolio_hidden_keys"), (list, tuple, set)):
    st.session_state.portfolio_hidden_keys = []
else:
    st.session_state.portfolio_hidden_keys = [str(x) for x in st.session_state.get("portfolio_hidden_keys", [])]
for _num_state_key in (
    "cash", "deposits", "withdrawals", "adj_month", "adj_year",
    "today_start_cash", "today_stop_loss_amount", "today_goal_pct",
    "today_goal_amount", "today_cash_adjustment",
):
    try:
        st.session_state[_num_state_key] = float(st.session_state.get(_num_state_key, 0.0) or 0.0)
    except (TypeError, ValueError):
        st.session_state[_num_state_key] = 0.0

if st.session_state.get("side_panel_mode") not in ("panels", "focus"):
    st.session_state.side_panel_mode = "panels"
if st.session_state.get("side_panel_section") not in ("today", "portfolio"):
    st.session_state.side_panel_section = "today"
if st.session_state.get("display_currency") not in ("USD", "KRW"):
    st.session_state.display_currency = "USD"
try:
    st.session_state.usd_krw_rate = max(float(st.session_state.get("usd_krw_rate", 1400.0) or 1400.0), 1.0)
except (TypeError, ValueError):
    st.session_state.usd_krw_rate = 1400.0
try:
    st.session_state.today_cash_adjustment = max(float(st.session_state.get("today_cash_adjustment", 0.0) or 0.0), 0.0)
except (TypeError, ValueError):
    st.session_state.today_cash_adjustment = 0.0
try:
    st.session_state.side_panel_trade_limit = max(int(st.session_state.get("side_panel_trade_limit", 5) or 5), 5)
except (TypeError, ValueError):
    st.session_state.side_panel_trade_limit = 5

# Auto-sync the saved wallet once per session: just opening/refreshing the app keeps the
# trade ledger current. Dedup is by tx_id (no duplicate saving). The Journal tab button
# forces a fresh re-sync within a session.
# Wrapped so this startup network step can NEVER break the app boot (e.g. a slow/failed
# fetch, or a stale module after a redeploy) -- worst case it silently skips.
try:
    if not st.session_state.get("_wallet_autosynced"):
        st.session_state._wallet_autosynced = True
        _wa = str(st.session_state.get("wallet_addr", "") or "").strip()
        if _wa.startswith("0x") and len(_wa) == 42:
            _auto = sync_wallet(_wa, limit=100, force=False)
            if _auto.get("ok") and _auto.get("added"):
                try:
                    st.toast(t(f"지갑 자동 동기화 · 새 거래 {_auto['added']}건 장부에 저장",
                               f"Wallet auto-synced · {_auto['added']} new trades saved"))
                except Exception:
                    pass
except Exception:
    pass

_panel_mode = st.session_state.get("side_panel_mode", "panels")
_panel_section = st.session_state.get("side_panel_section", "today")
_sidebar_width = "clamp(23.5rem, 28vw, 28rem)" if _panel_mode == "panels" else "10.5rem"
_main_max = "1120px" if _panel_mode == "panels" else "1280px"
_sidebar_pad = "1.1rem .85rem" if _panel_mode == "panels" else ".9rem .6rem"
if _panel_mode == "focus":
    _panel_hide_css = (
        'section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"], '
        '.sidebar-portfolio-panel { display: none !important; }'
    )
elif _panel_section == "today":
    _panel_hide_css = '.sidebar-portfolio-panel { display: none !important; }'
else:
    _panel_hide_css = 'section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] { display: none !important; }'
st.markdown(
    f"""
<style>
.portfolio-side-panel {{ display: none !important; }}
{_panel_hide_css}
section[data-testid="stSidebar"] {{
  width: {_sidebar_width} !important;
  min-width: {_sidebar_width} !important;
  max-width: {_sidebar_width} !important;
  border-right: 1px solid rgba(226,228,235,.78) !important;
}}
section[data-testid="stSidebar"] > div {{
  padding: {_sidebar_pad} !important;
  background: rgba(246,247,250,.84) !important;
  backdrop-filter: saturate(180%) blur(22px);
  -webkit-backdrop-filter: saturate(180%) blur(22px);
}}
.block-container {{
  max-width: {_main_max} !important;
  padding-left: 1.9rem !important;
  padding-right: 1.9rem !important;
  margin-right: auto !important;
}}
.sidebar-panel-stack {{
  display: flex;
  flex-direction: column;
  gap: 14px;
}}
.sidebar-portfolio-panel {{
  margin-top: 12px;
}}
.sidebar-portfolio-panel .portfolio-panel-card {{
  max-height: none;
  overflow: visible;
}}
section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] > div,
.portfolio-panel-card {{
  background: rgba(255,255,255,.88) !important;
  border: 1px solid rgba(226,228,235,.86) !important;
  border-radius: 24px !important;
  box-shadow: 0 1px 1px rgba(20,22,30,.03), 0 14px 34px rgba(20,22,30,.075) !important;
  backdrop-filter: saturate(180%) blur(24px);
  -webkit-backdrop-filter: saturate(180%) blur(24px);
}}
.today-goal-kpi,
.portfolio-total-kpi {{
  background: linear-gradient(180deg, #ffffff 0%, #f7f8fb 100%) !important;
  border: 1px solid rgba(226,228,235,.88) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.85), 0 10px 24px rgba(20,22,30,.055) !important;
}}
.today-goal-kpi .k,
.portfolio-total-kpi .k {{
  color: var(--gray) !important;
}}
.today-goal-kpi .v,
.portfolio-total-kpi .v {{
  color: var(--ink) !important;
}}
.today-goal-kpi .s,
.portfolio-total-kpi .s {{
  color: var(--gray) !important;
}}
.today-panel-dot {{
  background: linear-gradient(180deg, #f5f7fb, #eef1f6) !important;
  border-color: rgba(210,214,224,.95) !important;
}}
.today-panel-dot::after {{
  background: #007aff !important;
  box-shadow: 0 0 0 5px rgba(0,122,255,.10) !important;
}}
.portfolio-panel-badge {{
  color: #0a7f45 !important;
  background: rgba(232,246,238,.82) !important;
}}
.today-compact-summary {{
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  margin: 12px 0 4px;
}}
.today-compact-summary div {{
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 11px;
  border: 1px solid rgba(232,234,240,.88);
  border-radius: 16px;
  background: rgba(247,248,251,.78);
}}
.today-compact-summary span {{
  color: var(--gray);
  font-size: 12px;
  font-weight: 650;
}}
.today-compact-summary b {{
  color: var(--ink);
  font-size: 12.5px;
  font-weight: 760;
  font-variant-numeric: tabular-nums;
}}
.today-anchor-note {{
  margin: 10px 0 0;
  color: var(--gray);
  font-size: 12px;
  line-height: 1.45;
}}
.today-dashboard-bar {{
  display: grid;
  grid-template-columns: 1.1fr 1.1fr 1.1fr 1.25fr;
  gap: 9px;
  margin: 10px 0 16px;
}}
.today-dash-cell {{
  min-width: 0;
  padding: 11px 13px 12px;
  border: 1px solid rgba(226,228,235,.86);
  border-radius: 18px;
  background: rgba(255,255,255,.88);
  box-shadow: 0 1px 1px rgba(20,22,30,.025), 0 10px 24px rgba(20,22,30,.045);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
}}
.today-dash-cell .k {{
  color: var(--gray);
  font-size: 10.5px;
  font-weight: 760;
  letter-spacing: 0;
}}
.today-dash-cell .v {{
  margin-top: 4px;
  color: var(--ink);
  font-size: 16px;
  font-weight: 820;
  line-height: 1.16;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.today-dash-cell .s {{
  margin-top: 4px;
  color: var(--gray);
  font-size: 11.5px;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.today-progress-track {{
  height: 4px;
  margin-top: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(232,234,240,.92);
}}
.today-progress-fill {{
  height: 100%;
  border-radius: 999px;
  background: #007aff;
}}
.today-progress-fill.loss {{
  background: #ff3b30;
}}
.today-dash-cell.good .v {{
  color: #0a7f45;
}}
.today-dash-cell.warn .v {{
  color: #9a6700;
}}
.today-dash-cell.bad .v {{
  color: #b42318;
}}
@media (max-width: 1100px) {{
  section[data-testid="stSidebar"] {{
    width: min(92vw, 31rem) !important;
    min-width: min(92vw, 31rem) !important;
    max-width: min(92vw, 31rem) !important;
  }}
  .block-container {{
    max-width: 100% !important;
  }}
  .today-dashboard-bar {{
    grid-template-columns: 1fr 1fr;
  }}
}}
@media (max-width: 720px) {{
  .today-dashboard-bar {{
    grid-template-columns: 1fr;
  }}
}}
</style>
""",
    unsafe_allow_html=True,
)






# =====================================================
# Utility
# =====================================================
















# =====================================================
# Rules — thresholds come from the user's profile
# =====================================================














# =====================================================
# Entry engine
# =====================================================


# =====================================================
# Partial sell engine
# =====================================================


# =====================================================
# Claude AI
# =====================================================













# =====================================================
# Polymarket APIs
# =====================================================

























































































# =====================================================
# Imported trade P&L review — date filter + grouped estimates
# =====================================================












































































# =====================================================
# Period P&L
# =====================================================


































# =====================================================
# Masthead + language
# =====================================================
mh_l, mh_r = st.columns([3.25, 1.75])
with mh_l:
    st.markdown(
        f"""<div class="masthead">
<div class="name">Memento</div>
<div class="tag">{t("폴리마켓 진입 판단 터미널", "Polymarket entry-decision terminal")}</div>
</div>""", unsafe_allow_html=True)
with mh_r:
    lang_col, currency_col = st.columns([1.15, .85])
    with lang_col:
        lang_choice = st.radio("lang", ["한국어", "English"],
                               index=0 if st.session_state.lang == "ko" else 1,
                               horizontal=True, label_visibility="collapsed")
        new_lang = "ko" if lang_choice == "한국어" else "en"
        if new_lang != st.session_state.lang:
            st.session_state.lang = new_lang
            st.rerun()
    with currency_col:
        st.radio("currency", ["USD", "KRW"], horizontal=True,
                 key="display_currency", label_visibility="collapsed")
    if st.session_state.get("display_currency") == "KRW":
        st.number_input(t("환율 ₩/$", "FX ₩/$"), min_value=1.0, step=10.0,
                        format="%.0f", key="usd_krw_rate")

# The app opens directly with a safe default risk profile; no onboarding gate.
# Users can adjust bankroll/risk settings later in Settings · tools.
if st.session_state.profile is None:
    st.session_state.profile = dict(DEFAULT_PROFILE)

# 리스크 임계값은 다른 탭(설정·포트폴리오)에서 쓰이므로 변수는 유지하되, 칩 표시는 제거함.
prof = profile()
g_, c1_, c2_, blk_ = size_thresholds()
eb_ = effective_bankroll()
exp_limit_ = min(blk_ * 2, 50)
_today_assets = current_portfolio_assets()
_today_portfolio_assets = _today_assets["total"]
_today_has_portfolio_basis = _today_assets["has_basis"]
_today_current_basis = _today_portfolio_assets if _today_has_portfolio_basis else float(eb_ or 0.0)

# ---- 좌측 사이드바: 오늘 운용 기준 ----
with st.sidebar:
    st.radio(
        t("화면 구성", "Layout"),
        ["panels", "focus"],
        format_func=lambda mode: t("패널 보기", "Panels") if mode == "panels" else t("메인 크게", "Focus"),
        horizontal=True,
        key="side_panel_mode",
        label_visibility="collapsed",
    )
    if st.session_state.get("side_panel_mode") == "panels":
        st.radio(
            t("패널", "Panel"),
            ["today", "portfolio"],
            format_func=lambda section: t("운용기준", "Limits") if section == "today" else t("포트폴리오", "Portfolio"),
            horizontal=True,
            key="side_panel_section",
            label_visibility="collapsed",
        )
    if st.session_state.get("side_panel_mode") == "focus":
        st.caption(t("패널을 숨기고 메인 화면을 넓게 씁니다.", "Panels are hidden so the main view gets more room."))

    st.session_state.setdefault("today_start_cash", float(_today_portfolio_assets if _today_has_portfolio_basis else 0.0))
    st.session_state.setdefault("today_stop_loss_amount", 0.0)
    st.session_state.setdefault("today_goal_mode", "percent")
    st.session_state.setdefault("today_goal_pct", 3.0)
    st.session_state.setdefault("today_goal_amount", 0.0)
    st.session_state.setdefault("today_cash_adjustment", 0.0)
    pending_today_start = st.session_state.pop("_pending_today_start_cash", None)
    if pending_today_start is not None:
        st.session_state.today_start_cash = float(pending_today_start)
        st.session_state.today_cash_adjustment = max(float(pending_today_start) - _today_current_basis, 0.0)
    if _today_has_portfolio_basis and _safe_float(st.session_state.get("today_start_cash"), 0.0) <= 0:
        st.session_state.today_start_cash = float(_today_portfolio_assets)

    panel_start_cash = float(st.session_state.get("today_start_cash") or 0.0)
    panel_stop_loss = float(st.session_state.get("today_stop_loss_amount") or 0.0)
    panel_goal_mode = st.session_state.get("today_goal_mode", "percent")
    if panel_goal_mode == "percent":
        panel_goal_pct = float(st.session_state.get("today_goal_pct") or 0.0)
        panel_goal_amount = panel_start_cash * panel_goal_pct / 100.0
    else:
        panel_goal_amount = float(st.session_state.get("today_goal_amount") or 0.0)
        panel_goal_pct = (panel_goal_amount / panel_start_cash * 100.0) if panel_start_cash > 0 else 0.0
    panel_current_assets = float(_today_current_basis or 0.0) + _safe_float(st.session_state.get("today_cash_adjustment"), 0.0)
    panel_today_pnl = panel_current_assets - panel_start_cash
    panel_gain = max(panel_today_pnl, 0.0)
    panel_loss = max(-panel_today_pnl, 0.0)
    panel_goal_left = max(panel_goal_amount - panel_gain, 0.0)
    panel_stop_left = max(panel_stop_loss - panel_loss, 0.0) if panel_stop_loss > 0 else 0.0
    if panel_start_cash <= 0:
        panel_status_kind = "i"
        panel_status_title = t("시작 현금 입력 필요", "Set starting cash")
        panel_status_body = t("오늘 손익 판단을 위해 시작 현금을 먼저 입력하세요.", "Enter starting cash to judge today’s P&L.")
    elif panel_stop_loss > 0 and panel_loss >= panel_stop_loss:
        panel_status_kind = "b"
        panel_status_title = t("중단선 도달", "Stop line reached")
        panel_status_body = t("오늘 신규 진입을 멈추고 거래를 마감하는 기준입니다.", "This is the point to stop new entries for today.")
    elif panel_stop_loss > 0 and panel_loss >= panel_stop_loss * 0.8:
        panel_status_kind = "w"
        panel_status_title = t("중단선 근접", "Near stop line")
        panel_status_body = t(f"손실 중단까지 {money(panel_stop_left)} 남았습니다.", f"{money(panel_stop_left)} left before stop.")
    elif panel_goal_amount > 0 and panel_gain >= panel_goal_amount:
        panel_status_kind = "g"
        panel_status_title = t("오늘 목표 달성", "Goal reached")
        panel_status_body = t("수익 보존이 신규 진입보다 우선입니다.", "Protecting gains comes before new entries.")
    elif panel_today_pnl >= 0:
        panel_status_kind = "g"
        panel_status_title = t("운용 정상", "On track")
        panel_status_body = t(f"목표까지 {money(panel_goal_left)} 남았습니다.", f"{money(panel_goal_left)} left to goal.")
    else:
        panel_status_kind = "w"
        panel_status_title = t("손실 관리 중", "Managing loss")
        panel_status_body = t(f"현재 손실 {money(panel_loss)} · 중단선까지 {money(panel_stop_left)}", f"Loss {money(panel_loss)} · {money(panel_stop_left)} to stop.")

    today_panel_slot = st.empty()
    with today_panel_slot.container(border=True):
        st.markdown(
            f'<div class="today-panel">'
            f'<div class="today-panel-head">'
            f'<div><div class="today-panel-title">{t("오늘 운용 기준", "Today’s operating limits")}</div>'
            f'<div class="today-panel-sub">{t("목표와 중단 기준만 간단히 조정합니다.", "Keep the target and stop line simple.")}</div></div>'
            f'<div class="today-panel-dot"></div>'
            f'</div>'
            f'<div class="today-compact-summary">'
            f'<div><span>{t("현재", "Current")}</span><b>{money(panel_current_assets)}</b></div>'
            f'<div><span>{t("목표", "Goal")}</span><b>{money(panel_goal_amount)} · {panel_goal_pct:.1f}%</b></div>'
            f'<div><span>{t("중단", "Stop")}</span><b>{money(panel_stop_loss)}</b></div>'
            f'</div>'
            f'<div class="today-control-label">{t("입력", "Inputs")}</div>'
            f'</div>',
            unsafe_allow_html=True)

        _limits_set = panel_start_cash > 0 and panel_stop_loss > 0
        with st.expander(t("기준 입력 · 수정", "Edit limits"), expanded=not _limits_set):
            if st.button(t("현재 포트폴리오를 시작 기준으로 설정", "Use current portfolio as start"), width="stretch", key="sync_today_start_from_portfolio"):
                now_label = datetime.now(KST).isoformat(timespec="minutes")
                st.session_state.today_anchor_mode = "next"
                st.session_state.today_anchor_key = ""
                st.session_state.today_anchor_label = t("현재 포트폴리오 기준", "Current portfolio basis")
                st.session_state.today_anchor_time = now_label
                st.session_state.today_anchor_set_at = now_label
                st.session_state.today_start_cash = float(panel_current_assets)
                st.session_state.today_cash_adjustment = max(float(panel_current_assets) - _today_current_basis, 0.0)
                st.rerun()

            start_cash = st.number_input(t("오늘 시작 현금 ($)", "Starting cash today ($)"),
                                         min_value=0.0, key="today_start_cash",
                                         on_change=sync_today_cash_adjustment)
            st.number_input(t("손실 시 중단 금액 ($)", "Stop-trading loss ($)"),
                            min_value=0.0, key="today_stop_loss_amount")
            st.checkbox(
                t("손실만 기준으로 보기 (이익 합치기 X)", "Use loss-only stop (ignore gains)"),
                key="today_stop_loss_gross_only",
            )

            goal_mode = st.radio(
                t("목표 금액 입력 방식", "Goal input"),
                ["percent", "amount"],
                format_func=lambda mo: t("시작 현금의 %", "% of start cash") if mo == "percent" else t("직접 입력 ($)", "Direct ($)"),
                key="today_goal_mode", horizontal=True,
            )
            if goal_mode == "percent":
                goal_pct = st.number_input(t("목표 (시작 현금의 %)", "Goal (% of start cash)"),
                                           min_value=0.0, key="today_goal_pct")
                goal_amount = start_cash * goal_pct / 100.0
            else:
                goal_amount = st.number_input(t("목표 금액 ($)", "Goal amount ($)"),
                                              min_value=0.0, key="today_goal_amount")
                goal_pct = (goal_amount / start_cash * 100.0) if start_cash > 0 else 0.0

            stop_now = _safe_float(st.session_state.get("today_stop_loss_amount"), 0.0)
            anchor_note = t(f"상단 바에는 목표 {money(goal_amount)} · 중단 {money(stop_now)} 기준으로 표시됩니다.",
                            f"Top bar uses goal {money(goal_amount)} · stop {money(stop_now)}.")
            st.markdown(f'<div class="today-anchor-note">{esc(anchor_note)}</div>', unsafe_allow_html=True)

        with st.expander(t("오늘 시작 기준 · 상세 설정", "Start anchor · details"), expanded=False):
            st.markdown(f'<div class="today-control-label">{t("오늘 시작 기준", "Today start anchor")}</div>', unsafe_allow_html=True)
            anchor_rows = recent_completed_trade_rows(limit=10)
            anchor_by_key = {r["key"]: r for r in anchor_rows}
            anchor_options = ["__next__"] + [r["key"] for r in anchor_rows]
            stored_anchor_key = str(st.session_state.get("today_anchor_key") or "")
            if stored_anchor_key and stored_anchor_key not in anchor_options:
                anchor_options.append(stored_anchor_key)

            def _anchor_option_label(key):
                if key == "__next__":
                    return t("다음 거래부터 운용 기준 적용", "Apply from the next trade")
                row = anchor_by_key.get(key)
                if row:
                    when = str(row.get("latest_dt") or "-")[:16]
                    market = str(row.get("market") or t("이름 없는 거래", "Unnamed trade"))
                    if len(market) > 40:
                        market = market[:39] + "…"
                    return f'{market} · {row.get("outcome", "-")} · {signed_money(_safe_float(row.get("pnl"), 0.0))} · {when}'
                return st.session_state.get("today_anchor_label") or t("저장된 기준 거래", "Saved anchor trade")

            current_anchor_select = st.session_state.get("today_anchor_select")
            if current_anchor_select not in anchor_options:
                st.session_state.today_anchor_select = stored_anchor_key if stored_anchor_key in anchor_options else "__next__"

            selected_anchor = st.selectbox(
                t("기준 선택", "Anchor"),
                anchor_options,
                format_func=_anchor_option_label,
                key="today_anchor_select",
                label_visibility="collapsed",
            )

            ac1, ac2 = st.columns(2)
            with ac1:
                if st.button(t("다음 거래부터", "From next trade"), width="stretch", key="set_anchor_next_trade"):
                    now_label = datetime.now(KST).isoformat(timespec="minutes")
                    st.session_state.today_anchor_mode = "next"
                    st.session_state.today_anchor_key = ""
                    st.session_state.today_anchor_label = t("다음 거래부터", "From next trade")
                    st.session_state.today_anchor_time = now_label
                    st.session_state.today_anchor_set_at = now_label
                    st.session_state._pending_today_start_cash = float(panel_current_assets)
                    st.toast(t("현재 포트폴리오를 시작점으로 저장했습니다.", "Saved current portfolio as the start."))
                    st.rerun()
            with ac2:
                selected_row = anchor_by_key.get(selected_anchor)
                if st.button(t("선택 거래부터", "From selected"), width="stretch",
                             disabled=selected_row is None, key="set_anchor_selected_trade"):
                    all_completed = recent_completed_trade_rows(limit=None)
                    anchor_ts = _safe_float(selected_row.get("_latest_ts"), -1.0)
                    pnl_since_anchor = sum(
                        _safe_float(r.get("pnl"), 0.0)
                        for r in all_completed
                        if _safe_float(r.get("_latest_ts"), -1.0) >= anchor_ts - 1e-6
                    )
                    inferred_start = max(float(panel_current_assets) - pnl_since_anchor, 0.0)
                    market_label = str(selected_row.get("market") or t("이름 없는 거래", "Unnamed trade"))
                    if len(market_label) > 42:
                        market_label = market_label[:41] + "…"
                    anchor_label = f'{market_label} · {selected_row.get("outcome", "-")}'
                    st.session_state.today_anchor_mode = "trade"
                    st.session_state.today_anchor_key = selected_row["key"]
                    st.session_state.today_anchor_label = anchor_label
                    st.session_state.today_anchor_time = str(selected_row.get("latest_dt") or "")
                    st.session_state.today_anchor_set_at = datetime.now(KST).isoformat(timespec="minutes")
                    st.session_state._pending_today_start_cash = float(inferred_start)
                    st.toast(t("선택한 거래를 오늘 운용 기준으로 저장했습니다.", "Saved the selected trade as today's anchor."))
                    st.rerun()

    show_today_panel = st.session_state.get("side_panel_mode") == "panels" and st.session_state.get("side_panel_section") == "today"
    show_portfolio_panel = st.session_state.get("side_panel_mode") == "panels" and st.session_state.get("side_panel_section") == "portfolio"
    if not show_today_panel:
        today_panel_slot.empty()

    if show_portfolio_panel:
        st.markdown(portfolio_side_panel_html(), unsafe_allow_html=True)
        side_completed_total = len(recent_completed_trade_rows(limit=None))
        side_limit = max(int(st.session_state.get("side_panel_trade_limit", 5) or 5), 5)
        if side_completed_total > side_limit:
            if st.button(t("최근 거래 5개 더 보기", "Show 5 more trades"),
                         width="stretch", key="load_more_side_completed_trades"):
                st.session_state.side_panel_trade_limit = side_limit + 5
                st.rerun()
        elif side_limit > 5:
            if st.button(t("최근 거래 5개만 보기", "Show only 5 trades"),
                         width="stretch", key="reset_side_completed_trades"):
                st.session_state.side_panel_trade_limit = 5
                st.rerun()

st.markdown(today_dashboard_html(today_operating_metrics()), unsafe_allow_html=True)

tab1, _tab_pf_top, tab_rec, tab_ai, tab_set = st.tabs([
    t("진입 판독", "Entry check"),
    t("포트폴리오", "Portfolio"),
    t("기록", "Records"),
    t("AI 리서치", "AI research"),
    t("설정 · 도구", "Settings · tools"),
])
# 7 -> 5 tabs: 부분매도 folds under 포트폴리오, 거래일지+거래복기 fold under 기록.
# Sub-tabs are created here; the existing `with tab3/tab_pf/tab4/tab_review:` blocks below
# render into them unchanged.
with _tab_pf_top:
    tab_pf, tab3 = st.tabs([t("보유 · 손익", "Holdings & P&L"), t("부분매도", "Partial sell")])
with tab_rec:
    tab4, tab_review = st.tabs([t("거래일지", "Journal"), t("거래복기", "Trade Review")])


# =====================================================
# Render: entry result
# =====================================================


# =====================================================
# Tab 1 — Entry
# =====================================================








with tab1:
    st.markdown(f'<div class="headline">{t("진입 판독", "Entry check")}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="subline">{t("Polymarket URL을 불러와 선택지를 고르고, 필요한 정보를 입력한 뒤 분석하세요.", "Load a Polymarket URL, select an outcome, enter context, then analyze.")}</div>',
        unsafe_allow_html=True,
    )

    # --- compact status: lock button + only the banner that needs action (less noise) ---
    if day_is_locked():
        st.markdown(line(t(
            "🔒 오늘 베팅 잠금 — 신규 진입 차단. 잘하고 있어요, 내일 다시.",
            "Locked for today — new entries blocked. Well done; back tomorrow."), "b"),
            unsafe_allow_html=True)
        with st.expander(t("잠금 해제 (권장하지 않음)", "Unlock (not recommended)")):
            if st.checkbox(t("오늘은 쉬기로 했지만 정말 해제합니다", "I really do want to unlock"), key="entry_unlock_confirm"):
                if st.button(t("잠금 해제", "Unlock"), key="entry_unlock_btn"):
                    st.session_state.day_locked_date = ""
                    save_local_state()
                    st.rerun()
    else:
        _ll = today_loss_limit_status()
        _tilt = tilt_status()
        if _ll["hit"]:
            _msg, _kind = t(f"손실 한도 도달 ({money(_ll['used'])}/{money(_ll['stop'])}) — 오늘은 멈추세요.",
                            f"Daily loss limit hit ({money(_ll['used'])}/{money(_ll['stop'])}) — stop for today."), "b"
        elif _tilt["level"] == "stop":
            _msg, _kind = t(f"최근 {_tilt['streak']}연속 손실 — 쿨다운 권장.",
                            f"{_tilt['streak']} losses in a row — cool down."), "b"
        elif _tilt["level"] == "warn":
            _msg, _kind = t(f"최근 {_tilt['streak']}연속 손실 — 추격 베팅 주의.",
                            f"{_tilt['streak']} losses in a row — watch tilt."), "w"
        else:
            _msg, _kind = "", ""
        _lk1, _lk2 = st.columns([1, 4])
        with _lk1:
            if st.button(t("🔒 오늘 그만", "🔒 Lock today"), key="entry_lock_btn", width="stretch"):
                st.session_state.day_locked_date = datetime.now(KST).date().isoformat()
                save_local_state()
                st.rerun()
        with _lk2:
            if _msg:
                st.markdown(line(_msg, _kind), unsafe_allow_html=True)

    u1, u2 = st.columns([4, 1])
    with u1:
        entry_url_value = st.text_input(
            "Polymarket URL",
            value=st.session_state.get("entry_url", ""),
            key="entry_url_input",
            label_visibility="collapsed",
            placeholder="https://polymarket.com/...",
        )
    with u2:
        load_market = st.button(t("시장 불러오기", "Load market"), width="stretch", key="entry_load_market")

    if load_market:
        st.session_state.entry_url = entry_url_value
        st.session_state.explore_url = entry_url_value
        slug = extract_slug(entry_url_value)
        if not slug:
            st.markdown(line(t("URL에서 slug를 찾지 못했습니다.", "No slug found in URL."), "b"), unsafe_allow_html=True)
        else:
            try:
                with st.spinner(t("시장 정보를 불러오는 중", "Fetching market data")):
                    payload = fetch_gamma(slug)
                    rows = extract_markets(payload, infer_market_category(entry_url_value, ""))
                st.session_state.entry_raw = payload
                st.session_state.entry_markets = rows
                st.session_state.explore_raw = payload
                st.session_state.explore_markets = rows
                st.session_state._entry_active = None
                st.session_state._entry_sel = None
                if rows:
                    st.markdown(line(t(f"{len(rows)}개 선택지를 불러왔습니다.", f"Loaded {len(rows)} outcomes."), "g"), unsafe_allow_html=True)
                else:
                    st.markdown(line(t("분석 가능한 선택지를 찾지 못했습니다.", "No analyzable outcomes found."), "w"), unsafe_allow_html=True)
            except Exception as e:
                st.session_state.entry_raw = {"error": str(e)}
                st.session_state.entry_markets = []
                st.markdown(line(t(f"불러오기 실패 — {e}", f"Fetch failed — {e}"), "b"), unsafe_allow_html=True)

    rows = st.session_state.get("entry_markets", []) or []
    if not rows:
        st.markdown(
            f"""<div class="quiet">
<div class="q-title">{t('URL을 먼저 불러오세요', 'Load a URL first')}</div>
<div class="q-body">{t('시장 URL을 붙여넣으면 전체 경기/머니라인과 단일경기 선택지를 표로 보여줍니다.', 'Paste a market URL to show full-match moneyline and game outcomes as tables.')}</div>
</div>""",
            unsafe_allow_html=True,
        )
    else:
        default_cat = infer_market_category(st.session_state.get("entry_url", ""), row_get(rows[0], "시장", "Market", ""))
        default_sub = infer_market_subcategory(st.session_state.get("entry_url", ""), row_get(rows[0], "시장", "Market", ""))
        ccat, csub = st.columns([1, 1])
        with ccat:
            cat_options = [t("e스포츠", "Esports"), t("일반 스포츠", "Sports"), t("정치", "Politics"), t("뉴스·이벤트", "News / events"), t("크립토", "Crypto"), t("기타", "Other")]
            if default_cat not in cat_options:
                default_cat = cat_options[-1]
            entry_category = st.selectbox(t("시장 카테고리", "Market category"), cat_options, index=cat_options.index(default_cat), key="entry_url_category")
        with csub:
            entry_subcategory = st.text_input(t("세부종목/분류", "Subcategory"), value=default_sub, key="entry_url_subcategory")

        main_rows = [x for x in rows if x.get("market_class") == "p1_main"]
        game_rows = [x for x in rows if x.get("market_class") == "p2_game"]
        fallback_rows = [x for x in rows if x.get("market_class") == "fallback_binary"]

        if main_rows or fallback_rows:
            st.markdown(f'<div class="eyebrow" style="margin-top:14px;">{t("전체 경기 / 머니라인", "Full match / moneyline")}</div>', unsafe_allow_html=True)
            _market_table(main_rows or fallback_rows, "main")
        else:
            st.markdown(line(t("메인 머니라인을 못 찾았습니다. 단일경기만 표시됩니다.", "No moneyline found; game markets only."), "w"), unsafe_allow_html=True)
        if game_rows:
            with st.expander(t("단일경기 / 맵 승리 (고변동)", "Single game / map (volatile)")):
                _market_table(game_rows, "game")
        _selected_entry_form(entry_category, entry_subcategory)

# =====================================================
# Tab 3 — Partial sell
# =====================================================
with tab3:
    st.markdown(f'<div class="headline">{t("부분매도 계산기", "Partial-sell calculator")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subline">{t("원금 회수 최소 비율과 비율별 회수금·확정손익을 계산합니다.", "Min sell ratio to recover cost, plus per-ratio recovery and locked P&L.")}</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1: buy_price = st.number_input(t("매수가 (¢)", "Buy (¢)"), 1.0, 99.0, 16.0, key="pb")
    with c2: cur_price = st.number_input(t("현재가 (¢)", "Price (¢)"), 1.0, 100.0, 73.0, key="pc")
    with c3: inv = st.number_input(t("투자금 ($)", "Cost ($)"), 0.0, value=16.08, key="pi")

    manual = st.checkbox(t("보유 수량 직접 입력", "Enter shares manually"))
    shares_ps = st.number_input(t("보유 수량", "Shares"), 0.0, value=100.0, key="psh") if manual else (inv / (buy_price / 100) if buy_price > 0 else 0)

    if st.button(t("계산하기", "Calculate"), width="stretch"):
        rows, need = partial_rows(shares_ps, cur_price, inv)
        cur_val = shares_ps * (cur_price / 100)
        add = shares_ps - cur_val
        st.markdown(
            '<div class="stats" style="margin-top:22px;">'
            + stat(t("보유 수량", "Shares"), f"{shares_ps:.2f}", "")
            + stat(t("현재 평가금", "Current value"), money(cur_val), "")
            + stat(t("100¢까지 추가수익", "Left to 100¢"), money(add), "", "pos")
            + stat(t("실패 시 손실", "Loss if fails"), money(-cur_val), "", "neg")
            + "</div>", unsafe_allow_html=True)
        if need is not None:
            if need <= 100:
                st.markdown(line(t(f"원금 회수 최소 매도 비율: <b>{need:.1f}%</b>", f"Min sell ratio: <b>{need:.1f}%</b>"), "g"), unsafe_allow_html=True)
            else:
                st.markdown(line(t(f"100% 팔아도 원금 회수 불가 (필요 {need:.1f}%).", f"Even 100% can't recover cost ({need:.1f}% needed)."), "w"), unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


# =====================================================
# Tab 4 — Journal
# =====================================================
with tab4:
    st.markdown(f'<div class="headline">{t("거래일지", "Journal")}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="subline">{t("거래일지는 지갑 조회와 붙여넣기 정리로 분리됩니다. 지갑 거래는 auto_trades, 붙여넣기 거래는 paste_trades에 따로 저장되어 서로 합산되지 않습니다.", "Journal separates wallet import and paste-based organization. Wallet trades use auto_trades; pasted activity uses paste_trades. They are never merged.")}</div>',
        unsafe_allow_html=True,
    )

    # --- durable local trade ledger: auto-saved every run, survives Polymarket purges ---
    update_trade_ledger()
    _led = st.session_state.get("trade_ledger", {}) or {}
    _led_n = len(_led)
    _led_pnl = sum(_safe_float(v.get("pnl"), 0.0) for v in _led.values()) if _led else 0.0
    st.markdown(line(t(
        f"📒 완료 거래 {_led_n}건이 로컬 장부에 자동 저장돼 있습니다 (누적 손익 {money(_led_pnl)}) — 폴리마켓에서 사라져도 이 장부엔 남습니다.",
        f"{_led_n} completed trades auto-saved to your local ledger (net {money(_led_pnl)}) — kept even if Polymarket drops them."),
        "g" if _led_n else "i"), unsafe_allow_html=True)
    if _led:
        # 구글시트 백업과 같은 포맷(키·감정·추격 포함) — 내부 계산용 필드는 제외됨
        _lbody, _ln = _ledger_rows_for_export()
        _ldf = pd.DataFrame(_lbody[1:], columns=_lbody[0])
        st.download_button(
            t("📒 거래장부 전체 다운로드 (CSV)", "📒 Download full trade ledger (CSV)"),
            data=_ldf.to_csv(index=False).encode("utf-8-sig"),
            file_name="memento_trade_ledger.csv", mime="text/csv",
            width="stretch", key="ledger_download_btn")
    render_performance_summary()
    # 자산 곡선 + 일별 손익 캘린더 — 추세와 '폭발한 날'을 한눈에.
    render_equity_section()
    st.markdown("<hr>", unsafe_allow_html=True)

    if st.session_state.get("journal_mode") not in ("wallet", "paste"):
        st.session_state.journal_mode = "wallet"

    journal_mode = st.radio(
        t("거래일지 입력 방식", "Journal input mode"),
        ["wallet", "paste"],
        format_func=lambda c: t("폴리마켓 지갑으로 조회", "Load from Polymarket wallet") if c == "wallet" else t("활동내역 붙여넣기 정리", "Paste Activity text"),
        horizontal=True,
        key="journal_mode",
        label_visibility="collapsed",
    )

    if journal_mode == "wallet":
        st.markdown(f'<div class="eyebrow">{t("폴리마켓 지갑 조회", "Polymarket wallet lookup")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="footnote" style="margin:0 0 10px 0;">'
            f'{t("지갑 주소 기준으로 최근 체결내역을 불러오고 최신 거래가 위에 오도록 정리합니다.", "Import recent wallet activity and display newest trades first.")}'
            f'</div>',
            unsafe_allow_html=True,
        )
        ac1, ac2 = st.columns([3, 1])
        with ac1:
            st.session_state.wallet_addr = st.text_input(
                t("지갑 주소", "Wallet address"),
                value=st.session_state.wallet_addr,
                placeholder="0x...",
                key="activity_wallet_addr",
            )
        with ac2:
            act_limit = st.number_input(t("불러올 개수", "Limit"), 10, 300, 100, step=10, key="activity_import_limit")

        if st.button(t("거래내역 불러오기 (강제 새로고침)", "Import trades (force refresh)"), width="stretch", key="activity_import_btn"):
            with st.spinner(t("거래내역 불러오는 중", "Fetching activity")):
                _res = sync_wallet(st.session_state.wallet_addr, limit=act_limit, force=True)
            if _res["error"] == "bad_address":
                st.markdown(line(t("주소 형식 오류 — 0x로 시작하는 42자 주소인지 확인하세요.", "Bad address — must be 42 chars starting with 0x."), "b"), unsafe_allow_html=True)
            elif not _res["ok"]:
                st.markdown(line(t(f"거래내역 불러오기 실패 — {_res['error']}", f"Activity import failed — {_res['error']}"), "b"), unsafe_allow_html=True)
            else:
                st.markdown(line(t(f"거래내역 {_res['found']}건 확인 · 새로 추가 {_res['added']}건 (장부에 저장됨)", f"Found {_res['found']} trades · added {_res['added']} (saved to ledger)"), "g"), unsafe_allow_html=True)

        # --- 승/패 자동 확정: 폴리마켓 결과를 조회해 잔여 보유 미확정 거래를 자동 판정 ---
        _arm = str(st.session_state.pop("_auto_resolve_msg", "") or "")
        if _arm:
            st.markdown(line(_arm, "g"), unsafe_allow_html=True)
        if st.button(t("승/패 자동 확정 (폴리마켓 결과 조회)", "Auto-resolve Won/Lost (fetch market results)"),
                     width="stretch", key="auto_resolve_btn",
                     help=t("잔여 보유가 있는 미확정 거래의 마켓이 종료됐으면 자동으로 승/패를 확정합니다. 수동 확정은 덮어쓰지 않습니다.",
                            "If a market with unresolved held shares has closed, marks it Won/Lost automatically. Never overrides manual marks.")):
            with st.spinner(t("폴리마켓 결과 확인 중", "Checking Polymarket results")):
                _ar = auto_resolve_trades()
            if not _ar["ok"]:
                st.markdown(line(t(f"자동 확정 실패 — {_ar['error']}", f"Auto-resolve failed — {_ar['error']}"), "b"), unsafe_allow_html=True)
            elif _ar["won"] or _ar["lost"]:
                st.session_state._auto_resolve_msg = t(
                    f"자동 확정 완료 · 승 {_ar['won']} · 패 {_ar['lost']} · 미종료 {_ar['open']}건 · 판정불가 {_ar['unknown']}건",
                    f"Auto-resolved · won {_ar['won']} · lost {_ar['lost']} · open {_ar['open']} · unknown {_ar['unknown']}")
                st.rerun()
            elif _ar["checked"] == 0:
                st.markdown(line(t("자동 확정 대상이 없습니다 — 잔여 보유가 있는 미확정 거래가 없어요.",
                                   "Nothing to auto-resolve — no unresolved trades with held shares."), "i"), unsafe_allow_html=True)
            else:
                st.markdown(line(t(f"아직 종료된 마켓이 없습니다 · 검사 {_ar['checked']}건 (미종료 {_ar['open']} · 판정불가 {_ar['unknown']})",
                                   f"No closed markets yet · checked {_ar['checked']} (open {_ar['open']} · unknown {_ar['unknown']})"), "i"), unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        if st.session_state.auto_trades:
            sd, ed, date_label = render_trade_date_controls()
            filtered_trades, unknown_dates = filter_trades_by_date(st.session_state.get("auto_trades", []), sd, ed)
            if unknown_dates:
                st.markdown(line(t(f"날짜 확인 필요 {unknown_dates}건은 선택 기간에서 제외되었습니다.", f"{unknown_dates} unknown-date rows excluded from the selected range."), "w"), unsafe_allow_html=True)

            render_trade_pnl_summary(filtered_trades, date_label, title=t("지갑 거래내역 기준 추정손익", "Wallet activity estimated P&L"), key_prefix="wallet_")

            sm = habit_report(filtered_trades)
            if filtered_trades:
                st.markdown(f'<div class="eyebrow" style="margin-top:18px;">{t("거래습관 리포트", "Trading habit report")}</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="verdict" style="padding:12px 0 10px 0;border-top:none;">'
                    f'<div class="v-title" style="font-size:26px;"><span class="dot {sm.get("habit_level", "i")}"></span>{esc(sm.get("habit_title", ""))}</div>'
                    f'<div class="v-sub">{t("선택한 기간의 자동 거래내역 기준 행동 패턴입니다. 실현손익에는 합산하지 않습니다.", "Behavior pattern for the selected imported-trade period. Not merged into official P&L.")}</div></div>',
                    unsafe_allow_html=True,
                )
                st.markdown(''.join(f'<div class="trade-insight"><span class="dot {kk}"></span>{esc(txt)}</div>' for kk, txt in sm.get("habit_insights", [])), unsafe_allow_html=True)

            cdl, crs = st.columns(2)
            with cdl:
                csv_auto = pd.DataFrame(filtered_trades).to_csv(index=False).encode("utf-8-sig") if filtered_trades else b""
                st.download_button(t("선택 기간 CSV", "Download selected range CSV"), data=csv_auto, file_name="memento_auto_trades_filtered.csv", mime="text/csv", width="stretch")
            with crs:
                if st.button(t("자동 거래내역 전체 비우기", "Clear all auto trades"), width="stretch", key="clear_auto_trades_btn"):
                    st.session_state.auto_trades = []
                    st.session_state.imported_tx_ids = []
                    st.rerun()
        else:
            st.markdown(f'<div class="quiet"><div class="q-title">{t("불러온 지갑 거래내역이 없습니다", "No wallet activity loaded")}</div><div class="q-body">{t("지갑 주소를 불러오면 기간별 추정손익과 거래습관 분석이 표시됩니다.", "Import a wallet to see date-based estimated P&L and habit analysis.")}</div></div>', unsafe_allow_html=True)

        if st.session_state.get("dev_mode", False):
            with st.expander(t("디버그 — activity raw 응답", "Debug — raw activity response")):
                st.json(st.session_state.activity_raw)

    else:
        st.markdown(f'<div class="eyebrow">{t("활동내역 붙여넣기 정리", "Paste Activity text")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="footnote" style="margin:0 0 10px 0;">'
            f'{t("Polymarket Activity 화면에서 보이는 텍스트를 그대로 붙여넣으면 매수·매도·손실·상환 행을 인식해 시장별로 정리합니다. 붙여넣기 결과는 지갑 조회 거래내역과 합산하지 않습니다.", "Paste the visible Polymarket Activity text. Buys, sells, losses, and redemptions are recognized and grouped by market. Pasted rows are not merged with wallet-imported rows.")}'
            f'</div>',
            unsafe_allow_html=True,
        )

        paste_text = st.text_area(
            t("거래내역 텍스트", "Activity text"),
            value="",
            height=220,
            key="paste_activity_text",
            placeholder="매수\nicon for Jordan vs. Algeria: O/U 6.5 Total Corners\nJordan vs. Algeria: O/U 6.5 Total Corners\nUnder 27.6¢\n30.0 주\n-$8.28\n2시 전",
            label_visibility="collapsed",
        )

        pc1, pc2 = st.columns(2)
        with pc1:
            parse_now = st.button(t("붙여넣기 정리", "Organize pasted activity"), width="stretch", key="parse_paste_activity_btn")
        with pc2:
            clear_paste = st.button(t("붙여넣기 결과 비우기", "Clear pasted result"), width="stretch", key="clear_paste_activity_btn")

        if clear_paste:
            st.session_state.paste_trades = []
            st.session_state.paste_events = []
            st.session_state.paste_unparsed = []
            st.session_state.paste_meta = {"ok": 0, "buy": 0, "sell": 0, "events": [], "unparsed": []}
            st.rerun()

        if parse_now:
            parsed_rows, meta = parse_pasted_activity(paste_text)
            st.session_state.paste_trades = sort_trades_newest_first(parsed_rows)
            st.session_state.paste_events = meta.get("events", [])
            st.session_state.paste_unparsed = meta.get("unparsed", [])
            st.session_state.paste_meta = meta
            st.markdown(line(t(f"정리 완료 — 매수 {meta.get('buy', 0)}건 · 매도 {meta.get('sell', 0)}건 · 정산/상환 {len(meta.get('events', []))}건", f"Organized — buys {meta.get('buy', 0)} · sells {meta.get('sell', 0)} · settlements {len(meta.get('events', []))}"), "g"), unsafe_allow_html=True)

        meta = st.session_state.get("paste_meta", {}) or {}
        if st.session_state.get("paste_trades") or st.session_state.get("paste_events") or st.session_state.get("paste_unparsed"):
            paste_events_for_stats = st.session_state.get("paste_events", []) or []
            linked_event_count = 0
            if st.session_state.get("paste_trades") and paste_events_for_stats:
                stat_rows = group_auto_trades_for_pnl(st.session_state.get("paste_trades", []))
                stat_rows = link_settlement_events_to_trade_groups(stat_rows, paste_events_for_stats)
                linked_event_count = sum(1 for ev in paste_events_for_stats if isinstance(ev, dict) and ev.get("_linked_to"))
            unlinked_event_count = max(len(paste_events_for_stats) - linked_event_count, 0)
            exit_count = int(meta.get("sell", 0)) + linked_event_count
            st.markdown(
                '<div class="stats">'
                + stat(t("매수 인식", "Buys parsed"), f"{int(meta.get('buy', 0))}", "")
                + stat(t("청산/회수 인식", "Exits parsed"), f"{exit_count}", t("매도+상환+손실정산", "sell+redeem+loss"))
                + stat(t("미연결 이벤트", "Unlinked events"), f"{unlinked_event_count}", t("거래 매칭 필요", "needs matching"), "neg" if unlinked_event_count else "")
                + stat(t("확인 필요", "Needs review"), f"{len(st.session_state.get('paste_unparsed', []))}", t("불완전 행만", "incomplete only"), "neg" if st.session_state.get("paste_unparsed") else "")
                + "</div>", unsafe_allow_html=True
            )

        if st.session_state.get("paste_trades"):
            render_trade_pnl_summary(
                st.session_state.get("paste_trades", []),
                title=t("붙여넣기 거래내역 기준 추정손익", "Pasted activity estimated P&L"),
                key_prefix="paste_",
                events=st.session_state.get("paste_events", []),
            )
        else:
            st.markdown(f'<div class="quiet"><div class="q-title">{t("아직 정리된 붙여넣기 거래가 없습니다", "No pasted trades organized yet")}</div><div class="q-body">{t("Activity 텍스트를 붙여넣고 ‘붙여넣기 정리’를 누르세요.", "Paste Activity text and press Organize.")}</div></div>', unsafe_allow_html=True)

        render_trade_event_cards(st.session_state.get("paste_events", []), title=t("인식된 손실·상환·정산 이벤트", "Recognized loss/redemption/settlement events"))

        if st.session_state.get("paste_unparsed"):
            with st.expander(t("확인 필요 행", "Rows needing review"), expanded=False):
                for title_, reason_ in st.session_state.get("paste_unparsed", []):
                    st.markdown(line(f"<b>{esc(title_)}</b> · {esc(reason_)}", "w"), unsafe_allow_html=True)


# =====================================================
# Tab — Trade Review
# =====================================================
with tab_review:
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
                f'''<div class="pf-card" style="margin:14px 0;">
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
</div>''',
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


# =====================================================
# Tab — AI research (optional, manual-trigger only)
# =====================================================
with tab_ai:
    st.markdown(f'<div class="headline">{t("AI 리서치", "AI research")}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="subline">{t("Claude는 실시간 인터넷이 없어 최근 전적·부상·배당을 직접 가져오지 못합니다. 대신 정산 규칙 해석, 붙여넣은 리서치 정리, 엣지 판단, 진입 전 체크리스트에 집중합니다. 버튼을 눌렀을 때만 호출되어 토큰을 아낍니다.", "Claude has no live internet, so it can’t pull recent form, injuries, or odds itself. It focuses on reading the resolution rules, organizing the notes you paste, framing the edge, and a pre-bet checklist. It runs only when you press the button.")}</div>',
        unsafe_allow_html=True)

    has_key = bool(get_api_key())
    if not has_key:
        st.markdown(line(t("Claude API 키가 없습니다 — 설정 · 도구 탭에서 ANTHROPIC_API_KEY를 등록하세요.", "No Claude API key — add ANTHROPIC_API_KEY in Settings · tools."), "w"), unsafe_allow_html=True)

    pend = st.session_state.get("ai_pending", {}) or {}
    has_pend = bool(pend.get("market"))

    # ---- choose the subject: pending market from Entry, or a manual quick entry ----
    if has_pend:
        src_choice = st.radio(
            t("리서치 대상", "Research subject"),
            ["pending", "manual"],
            format_func=lambda c: t("진입 판독에서 보낸 시장", "Market sent from Entry") if c == "pending" else t("직접 입력", "Enter manually"),
            horizontal=True, key="ai_src_choice", label_visibility="collapsed",
        )
    else:
        src_choice = "manual"
        st.markdown(f'<div class="footnote" style="margin:0 0 8px 0;">{t("진입 판독에서 ‘AI 분석 탭으로 보내기’를 누르면 시장이 자동으로 채워집니다. 또는 아래에 직접 입력하세요.", "Press ‘Send to AI tab’ in Entry to auto-fill a market, or enter one below.")}</div>', unsafe_allow_html=True)

    if src_choice == "pending" and has_pend:
        subj = {
            "market": pend.get("market", ""), "outcome": pend.get("outcome", ""),
            "current_price": float(pend.get("current_price", 0.0) or 0.0),
            "fair_price": float(pend.get("fair_price", 0.0) or 0.0),
            "edge": float(pend.get("edge", 0.0) or 0.0),
            "category": pend.get("category", "기타"), "subcategory": pend.get("subcategory", ""),
            "market_class": pend.get("market_class", ""), "token_id": pend.get("token_id", ""),
            "bookmaker_prob": float(pend.get("bookmaker_prob", 0.0) or 0.0),
            "resolution": str(pend.get("resolution", "") or ""),
            "default_memo": st.session_state.get("_ai_memo_cache", pend.get("ai_memo", "")),
            "default_bk": st.session_state.get("_ai_bk_cache", pend.get("bookmaker_memo", "")),
        }
    else:
        mc1, mc2 = st.columns([3, 1])
        with mc1:
            m_name = st.text_input(t("시장 / 매치", "Market / match"), value=st.session_state.get("ai_manual_name", ""), key="ai_manual_name", placeholder=t("예: T1 vs Gen.G — Match Winner", "e.g. T1 vs Gen.G — Match Winner"))
        with mc2:
            m_out = st.text_input(t("선택 결과", "Outcome"), value=st.session_state.get("ai_manual_out", ""), key="ai_manual_out", placeholder="T1")
        mc3, mc4, mc5 = st.columns(3)
        with mc3:
            m_price = st.number_input(t("현재가 (¢)", "Price (¢)"), 0.0, 100.0, float(st.session_state.get("ai_manual_price", 50.0)), key="ai_manual_price")
        with mc4:
            m_fair = st.number_input(t("내 적정가 (¢)", "My fair (¢)"), 0.0, 100.0, float(st.session_state.get("ai_manual_fair", 50.0)), key="ai_manual_fair")
        with mc5:
            cat_opts = [t("e스포츠", "Esports"), t("일반 스포츠", "Sports"), t("정치", "Politics"), t("뉴스·이벤트", "News / events"), t("크립토", "Crypto"), t("기타", "Other")]
            m_cat = st.selectbox(t("카테고리", "Category"), cat_opts, key="ai_manual_cat")
        m_res = st.text_area(t("정산 규칙 (Polymarket resolution 텍스트 붙여넣기)", "Resolution rules (paste Polymarket resolution text)"), value=st.session_state.get("ai_manual_res", ""), height=70, key="ai_manual_res", placeholder=t("이 시장이 어떻게 정산되는지에 대한 공식 설명", "the official description of how this market resolves"))
        subj = {
            "market": m_name, "outcome": m_out, "current_price": float(m_price),
            "fair_price": float(m_fair), "edge": float(m_fair) - float(m_price),
            "category": m_cat, "subcategory": "", "market_class": "", "token_id": "",
            "bookmaker_prob": 0.0, "resolution": str(m_res or ""),
            "default_memo": st.session_state.get("_ai_memo_cache", ""), "default_bk": st.session_state.get("_ai_bk_cache", ""),
        }

    # ---- subject summary line ----
    if subj["market"]:
        edge_txt = f"Edge {subj['edge']:+.1f}¢" if subj["fair_price"] else t("적정가 미입력", "no fair yet")
        st.markdown(
            f'<div class="spec-row"><div class="spec-key">{esc(subj["market"])}</div>'
            f'<div class="spec-val"><b>{esc(subj["outcome"]) or "—"}</b> · {cents(subj["current_price"])} · {edge_txt} · {esc(str(subj["category"]))}'
            + (f' · {t("정산 규칙 있음", "has resolution text")}' if subj["resolution"] else f' · {t("정산 규칙 없음", "no resolution text")}')
            + '</div><div></div></div>',
            unsafe_allow_html=True)

    # ---- depth + research notes ----
    mode_label = st.selectbox(
        t("리포트 상세도", "Report depth"),
        [t("요약", "Brief"), t("표준", "Standard"), t("상세", "Detailed")],
        index={"brief": 0, "standard": 1, "detailed": 2}.get(st.session_state.get("ai_report_mode", "standard"), 1),
        key="ai_report_mode_label",
    )
    mode = {"요약": "brief", "Brief": "brief", "표준": "standard", "Standard": "standard", "상세": "detailed", "Detailed": "detailed"}.get(mode_label, "standard")
    st.session_state.ai_report_mode = mode

    ai_memo = st.text_area(
        t("리서치 메모 (전적·순위·라인업·부상·뉴스)", "Research notes (form, standings, lineup, injuries, news)"),
        value=subj["default_memo"],
        placeholder=t("여기에 붙여넣은 내용만 근거로 사용합니다. 비우면 정산 규칙 해석과 분석 틀만 제공합니다.", "Only what you paste here is used as evidence. Leave empty for a resolution read and framework only."),
        height=110, key="ai_tab_memo",
    )
    bk_memo = st.text_input(
        t("외부배당 메모", "Bookmaker memo"),
        value=subj["default_bk"],
        placeholder=t("예: Pinnacle T1 -180, Bet365 Gen.G 1.55", "e.g. Pinnacle T1 -180, Bet365 Gen.G 1.55"),
        key="ai_tab_bk_memo",
    )

    subj_id = subj["token_id"] or f'{subj["market"]}|{subj["outcome"]}'
    mkey = f"{subj_id}|{mode}|{ai_memo.strip()}|{bk_memo.strip()}|{subj['fair_price']}|{subj['edge']}|{subj['resolution'][:60]}"
    c1, c2 = st.columns([1, 1])
    gen = c1.button(t("AI 리포트 생성", "Generate report"), width="stretch", key="ai_generate_report", disabled=not subj["market"])
    force = c2.button(t("새로 생성", "Force refresh"), width="stretch", key="ai_force_report", disabled=not subj["market"])

    if (gen or force) and subj["market"]:
        st.session_state._ai_memo_cache = ai_memo
        st.session_state._ai_bk_cache = bk_memo
        cache = st.session_state.ai_report_cache
        if (not force) and mkey in cache:
            st.session_state.ai_text = cache[mkey]
            st.session_state.ai_error = ""
        else:
            prompt = build_prompt(
                market_name=subj["market"], outcome=subj["outcome"], current_price=subj["current_price"],
                category=subj["category"], sub=subj["subcategory"], ai_context=ai_memo,
                bookmaker_memo=bk_memo, bookmaker_prob=subj["bookmaker_prob"],
                fair_price=subj["fair_price"], edge=subj["edge"], market_class=subj["market_class"],
                resolution=subj["resolution"], report_mode=mode,
            )
            try:
                with st.spinner(t("AI 분석 중", "Analyzing")):
                    txt, err = call_claude(prompt, mode=mode)
            except Exception as e:
                txt, err = None, str(e)
            st.session_state.ai_text = txt or ""
            st.session_state.ai_error = err or ""
            if txt:
                cache[mkey] = txt
        st.session_state.ai_last_market_key = mkey

    if st.session_state.get("ai_text"):
        render_ai_report_json(st.session_state.ai_text)
    elif st.session_state.get("ai_error"):
        err = str(st.session_state.get("ai_error"))
        if err == "no_key":
            st.markdown(line(t("Claude API 키가 없어 생성하지 못했습니다 — 설정 · 도구에서 등록하세요.", "Couldn’t generate — add your Claude API key in Settings · tools."), "w"), unsafe_allow_html=True)
        else:
            st.markdown(line(t("AI 호출에 실패했습니다 — 새로 생성을 눌러 다시 시도하세요.", "The AI call failed — press Force refresh to retry."), "w"), unsafe_allow_html=True)


with tab_pf:
    st.markdown(f'<div class="headline">{t("포트폴리오", "Portfolio")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subline">{t("현재 보유 포지션을 먼저 보고, 그다음 전체 자산 요약과 손익을 확인합니다.", "Open holdings first, then the wallet summary, then P&L.")}</div>', unsafe_allow_html=True)

    # ---- import wallet (read-only) ----
    with st.expander(t("폴리마켓 지갑으로 포지션 불러오기", "Import positions from a Polymarket wallet")):
        st.markdown(f'<div class="footnote" style="margin:0 0 10px 0;">{t("폴리마켓 프로필 주소(0x로 시작)를 붙여넣으면 공개 데이터 API로 현재 보유 포지션을 읽어옵니다. 로그인·서명 없이 조회만 합니다.", "Paste your Polymarket wallet address. We read open positions via the public data API — read-only, no login or signing.")}</div>', unsafe_allow_html=True)
        st.session_state.wallet_addr = st.text_input(t("지갑 주소", "Wallet address"), value=st.session_state.wallet_addr, placeholder="0x...", key="portfolio_wallet_addr")
        if st.button(t("보유 포지션 불러오기", "Import open positions"), width="stretch"):
            a = st.session_state.wallet_addr.strip()
            if not (a.startswith("0x") and len(a) == 42):
                st.markdown(line(t("주소 형식 오류 — 0x로 시작하는 42자 주소인지 확인하세요.", "Bad address — must be 42 chars starting with 0x."), "b"), unsafe_allow_html=True)
            else:
                try:
                    with st.spinner(t("폴리마켓에서 불러오는 중", "Fetching")):
                        fetch_wallet_positions.clear()
                        items = fetch_wallet_positions(a)
                    st.session_state.wallet_raw = items
                    try:
                        fetch_wallet_value.clear()
                        st.session_state.pnl_raw = fetch_wallet_value(a)
                    except Exception as _pnl_err:
                        st.session_state.pnl_raw = {"error": str(_pnl_err)}
                    activity_raw = []
                    activity_items = []
                    activity_events = []
                    activity_added = 0
                    activity_error = ""
                    try:
                        fetch_wallet_activity.clear()
                        activity_raw = fetch_wallet_activity(a, limit=200)
                        st.session_state.activity_raw = activity_raw
                        activity_events = normalize_activity_events(activity_raw)
                        st.session_state.activity_events = activity_events
                        activity_items = sort_trades_newest_first(normalize_activity(activity_raw))
                        activity_added = merge_activity_into_log(activity_items)
                        st.session_state.auto_trades = sort_trades_newest_first(st.session_state.get("auto_trades", []))
                    except Exception as _activity_err:
                        activity_error = str(_activity_err)
                        st.session_state.activity_events = st.session_state.get("activity_events", [])
                        st.session_state.activity_raw = st.session_state.get("activity_raw", [])
                        st.session_state.pnl_raw = {
                            **(st.session_state.pnl_raw if isinstance(st.session_state.pnl_raw, dict) else {}),
                            "activity_error": str(_activity_err),
                        }
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
                    st.session_state.api_sync_meta = {
                        "status": "partial" if activity_error else "ok",
                        "source": t("포트폴리오", "Portfolio"),
                        "wallet": a,
                        "last_sync_at": datetime.now(KST).isoformat(timespec="minutes"),
                        "positions": len(open_items),
                        "raw_activity": len(activity_raw) if isinstance(activity_raw, list) else 0,
                        "trades": len(activity_items),
                        "events": len(activity_events),
                        "added": activity_added,
                        "error": activity_error,
                    }
                    st.toast(t(f"현재 보유 포지션 {len(open_items)}개", f"{len(open_items)} open positions"))
                    st.rerun()
                except urllib.error.HTTPError as e:
                    st.markdown(line(t(f"연결 실패 (HTTP {e.code}) — 주소 확인 필요", f"Failed (HTTP {e.code}) — check address"), "b"), unsafe_allow_html=True)
                except urllib.error.URLError:
                    st.markdown(line(t("응답 없음 — 잠시 후 다시 시도하세요.", "No response — try again later."), "b"), unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(line(t(f"불러오기 실패 — {e}", f"Import failed — {e}"), "b"), unsafe_allow_html=True)

    if st.session_state.portfolio:
        hidden_labels = {}
        hidden_options = []
        for p in st.session_state.portfolio:
            if not isinstance(p, dict):
                continue
            k = portfolio_position_key(p)
            if not k:
                continue
            val = _safe_float(p.get("shares"), 0.0) * (_safe_float(p.get("cur"), 0.0) / 100.0)
            label = f'{p.get("name", "Polymarket position")} · {p.get("outcome", "—")} · {money(val)}'
            hidden_options.append(k)
            hidden_labels[k] = label
        hidden_keys_raw = st.session_state.get("portfolio_hidden_keys", []) or []
        if not isinstance(hidden_keys_raw, (list, tuple, set)):
            hidden_keys_raw = []
        valid_hidden = [str(k) for k in hidden_keys_raw if str(k) in hidden_labels]
        if valid_hidden != st.session_state.get("portfolio_hidden_keys", []):
            st.session_state.portfolio_hidden_keys = valid_hidden

    if st.session_state.get("dev_mode", False):
        with st.expander(t("디버그 — positions raw 응답", "Debug — raw positions response")):
            st.json(st.session_state.wallet_raw)
        with st.expander(t("디버그 — profile/value raw 응답", "Debug — profile/value raw response")):
            st.json(st.session_state.pnl_raw)

    # ---- capital inputs (drive every calculation; manual cash is source of truth) ----
    with st.expander(t("내 자금 입력 (현금 · 입금 · 출금)", "My capital (cash · deposits · withdrawals)"), expanded=not bool(st.session_state.portfolio)):
        pf_i1, pf_i2, pf_i3 = st.columns(3)
        with pf_i1:
            st.session_state.cash = st.number_input(t("현금 보유량 (USDC, $)", "Cash balance (USDC, $)"), 0.0, value=float(st.session_state.cash), key="cash_input")
        with pf_i2:
            st.session_state.deposits = st.number_input(t("총 입금액 ($)", "Total deposits ($)"), 0.0, value=float(st.session_state.deposits), key="deposit_input")
        with pf_i3:
            st.session_state.withdrawals = st.number_input(t("총 출금액 ($)", "Total withdrawals ($)"), 0.0, value=float(st.session_state.withdrawals), key="withdrawal_input")
        st.markdown(f'<div class="footnote" style="margin-top:4px;">{t("현금은 수동 입력값이 기준입니다. 입금·출금 모두 양수로 입력하세요.", "Manual cash is the source of truth. Enter both deposits and withdrawals as positive values.")}</div>', unsafe_allow_html=True)

    # ---- shared figures ----
    cash = float(st.session_state.cash)
    pos_value = sum((p.get("shares", 0) or 0) * ((p.get("cur", 0) or 0) / 100) for p in st.session_state.portfolio)
    pos_cost = sum((p.get("inv", 0) or 0) for p in st.session_state.portfolio)
    total_assets = cash + pos_value
    bankroll_for_positions = total_assets if total_assets > 0 else prof["assets"]

    if st.session_state.portfolio:
        hidden_set = set(str(x) for x in st.session_state.get("portfolio_hidden_keys", []) or [])
        ordered_keys = []
        st.markdown(f'<div class="eyebrow">{t("내 보유 종목 표시", "Holding visibility")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="footnote" style="margin:0 0 8px 0;">'
            f'{t("숨김을 체크하면 보유종목 카드와 좌측 포트폴리오 패널에서 빠집니다. 총자산·오늘 손익 계산에는 계속 포함됩니다.",
                 "Check Hide to remove a holding from cards and the left portfolio panel. It still counts toward total assets and today P&L.")}'
            f'</div>',
            unsafe_allow_html=True,
        )
        for idx, p in enumerate(st.session_state.portfolio):
            if not isinstance(p, dict):
                continue
            pkey = portfolio_position_key(p) or f"row:{idx}"
            ordered_keys.append(pkey)
            cb_key = f"portfolio_hide_{_norm_key(pkey)[:32]}_{idx}"
            if cb_key not in st.session_state:
                st.session_state[cb_key] = pkey in hidden_set
            value = _safe_float(p.get("shares"), 0.0) * (_safe_float(p.get("cur"), 0.0) / 100.0)
            label = f'{t("숨김", "Hide")} · {p.get("name", "Polymarket position")} · {p.get("outcome", "—")} · {money(value)}'
            is_hidden = st.checkbox(label, key=cb_key, on_change=sync_portfolio_hidden_checkbox, args=(pkey, cb_key))
            if is_hidden:
                hidden_set.add(pkey)
            else:
                hidden_set.discard(pkey)
        st.session_state.portfolio_hidden_keys = [k for k in ordered_keys if k in hidden_set]

    visible_pf = visible_portfolio_positions(st.session_state.portfolio)
    pf_total_count, pf_hidden_count = portfolio_hidden_summary()

    # ================= 1) OPEN POSITIONS FIRST =================
    hidden_note = f" · {t(f'{pf_hidden_count}개 숨김', f'{pf_hidden_count} hidden')}" if pf_hidden_count else ""
    st.markdown(f'<div class="eyebrow">{t("현재 보유 포지션", "Open positions")}{hidden_note}</div>', unsafe_allow_html=True)
    if st.session_state.portfolio:
        if visible_pf:
            cards = []
            for p in visible_pf:
                ar = analyze_portfolio_position(p, bankroll_for_positions)
                ar.update(link_position_to_trades(p, st.session_state.auto_trades))
                cards.append(portfolio_card_html(ar))
            st.markdown('<div class="pf-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="quiet" style="padding:28px 18px;"><div class="q-title">{t("표시할 보유 포지션이 없습니다", "No visible holdings")}</div><div class="q-body">{t("보유항목 숨김 관리에서 선택을 해제하면 다시 표시됩니다.", "Unselect items in Hide holdings to show them again.")}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="footnote">{t("카드는 현재가·평균가·수량·투자금만으로 자동 판단합니다. 아래 편집표에서 값을 고치면 즉시 다시 계산됩니다.", "Cards use price, average, shares and cost only. Edit the table below to recalculate instantly.")}</div>', unsafe_allow_html=True)

        with st.expander(t("보유 포지션 편집표", "Edit open positions table"), expanded=False):
            df = pd.DataFrame(st.session_state.portfolio)
            col_cfg = {
                "name": st.column_config.TextColumn(t("시장", "Market")),
                "outcome": st.column_config.TextColumn(t("선택", "Side")),
                "buy": st.column_config.NumberColumn(t("평균 매수가 (¢)", "Avg buy (¢)"), format="%.1f"),
                "shares": st.column_config.NumberColumn(t("수량", "Shares"), format="%.2f"),
                "inv": st.column_config.NumberColumn(t("투자금 ($)", "Cost ($)"), format="%.2f"),
                "cur": st.column_config.NumberColumn(t("현재가 (¢)", "Now (¢)"), format="%.1f"),
                "asset": st.column_config.TextColumn(t("토큰/자산 ID", "Token/asset ID")),
            }
            edited = st.data_editor(df, column_config=col_cfg, width="stretch",
                                    hide_index=True, num_rows="dynamic", key="pf_editor")
            st.session_state.portfolio = edited.to_dict("records")

        with st.expander(t("포지션별 핵심 판단", "Per-position verdicts"), expanded=False):
            for p in visible_pf:
                ar = analyze_portfolio_position(p, bankroll_for_positions)
                ar.update(link_position_to_trades(p, st.session_state.auto_trades))
                st.markdown(line(f'<b>{esc(ar["name"])}</b> — {esc(ar["title"])} · {esc(ar["summary"])} · {esc(ar.get("match_note", ""))}', ar["kind"]), unsafe_allow_html=True)
    else:
        st.markdown(
            f"""<div class="quiet" style="padding:36px 20px;">
<div class="q-title">{t("등록된 포지션이 없습니다", "No positions yet")}</div>
<div class="q-body">{t("위에서 지갑으로 불러오거나, 아래에서 직접 추가하세요.", "Import via wallet above, or add one manually below.")}</div>
</div>""", unsafe_allow_html=True)

    with st.expander(t("수동으로 포지션 추가", "Add a position manually"), expanded=False):
        with st.form("add_pos"):
            a1, a2, a3 = st.columns(3)
            with a1:
                np_name = st.text_input(t("시장 이름", "Market name"), "")
                np_out = st.text_input(t("선택한 결과", "Outcome"), "")
            with a2:
                np_buy = st.number_input(t("평균 매수가 (¢)", "Avg buy (¢)"), 0.1, 99.9, 50.0)
                np_cur = st.number_input(t("현재가 (¢)", "Now (¢)"), 0.1, 100.0, 50.0)
            with a3:
                np_shares = st.number_input(t("보유 수량", "Shares"), 0.0, value=0.0)
                np_inv = st.number_input(t("투자금 ($)", "Cost ($)"), 0.0, value=0.0)
            add_pos = st.form_submit_button(t("포지션 추가", "Add position"), width="stretch")

        if add_pos:
            if not np_name.strip():
                st.markdown(line(t("시장 이름을 입력해주세요.", "Please enter a market name."), "w"), unsafe_allow_html=True)
            else:
                shares_v = np_shares if np_shares > 0 else (np_inv / (np_buy / 100) if np_buy > 0 else 0)
                inv_v = np_inv if np_inv > 0 else shares_v * (np_buy / 100)
                st.session_state.portfolio.append(dict(name=np_name, outcome=np_out, buy=np_buy,
                                                       shares=round(shares_v, 2), inv=round(inv_v, 2), cur=np_cur, asset=""))
                st.rerun()

    # ================= 2) PORTFOLIO SUMMARY =================
    pos_value = sum((p.get("shares", 0) or 0) * ((p.get("cur", 0) or 0) / 100) for p in st.session_state.portfolio)
    pos_cost = sum((p.get("inv", 0) or 0) for p in st.session_state.portfolio)
    wallet_value = cash + pos_value
    deposits = st.session_state.deposits
    withdrawals = st.session_state.withdrawals
    net_profit = cash + pos_value + withdrawals - deposits
    roi = net_profit / deposits * 100 if deposits else None
    wallet_gap = withdrawals - deposits

    ph = portfolio_health(st.session_state.portfolio, cash)
    st.markdown(f'<div class="eyebrow" style="margin-top:8px;">{t("전체 포트폴리오 판단", "Overall portfolio verdict")}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="verdict" style="padding-top:18px;">'
        f'<div class="v-title" style="font-size:28px;"><span class="dot {ph["kind"]}"></span>{ph["title"]}</div>'
        f'<div class="v-sub">{ph["summary"]}</div></div>', unsafe_allow_html=True)

    st.markdown(f'<div class="eyebrow">{t("자산 요약", "Wallet summary")}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="stats">'
        + stat(t("현금", "Cash"), money(cash), "USDC")
        + stat(t("포지션 평가금", "Position value"), money(pos_value), t(f"원금 {money(pos_cost)}", f"cost {money(pos_cost)}"))
        + stat(t("총 지갑가치", "Wallet value"), money(wallet_value), t("현금+포지션", "cash+pos"))
        + stat(t("실제 누적손익", "Net profit"), signed_money(net_profit), (signed_pct(roi) if roi is not None else "—"), "pos" if net_profit >= 0 else "neg")
        + "</div>"
        + '<div class="stats three">'
        + stat(t("전체 포지션 노출", "Total exposure"), f"{ph['exposure_pct']:.1f}%", t("평가금 / 총자산", "Value / assets"), "neg" if ph['exposure_pct'] >= blk_ else "")
        + stat(t("현금 비중", "Cash ratio"), f"{ph['cash_pct']:.1f}%", t("현금 / 총자산", "Cash / assets"))
        + stat(t("지갑-성과 차이", "Wallet-performance gap"), signed_money(wallet_gap), t("출금/추가입금 영향", "Deposits/withdrawals effect"), "pos" if wallet_gap >= 0 else "neg")
        + "</div>", unsafe_allow_html=True)
    if ph["lines"]:
        st.markdown("".join(line(txt, kk) for kk, txt in ph["lines"]), unsafe_allow_html=True)

    # ================= 3) P&L =================
    st.markdown(f'<div class="eyebrow" style="margin-top:22px;">{t("손익 요약", "P&L summary")}</div>', unsafe_allow_html=True)
    st.session_state.profile_pnl = calc_profile_pnl(st.session_state.portfolio, st.session_state.cash, st.session_state.wallet_raw, st.session_state.pnl_raw)
    render_profile_pnl_dashboard(st.session_state.profile_pnl)

    st.markdown(f'<div class="eyebrow">{t("기간별 실현손익", "Realized P&L by period")}</div>', unsafe_allow_html=True)
    with st.expander(t("앱 사용 전 손익 보정 (이미 번 돈 반영)", "Pre-app P&L adjustment (count earlier gains)")):
        st.markdown(f'<div class="footnote" style="margin:0 0 10px 0;">{t("앱을 쓰기 전에 이미 번(잃은) 금액을 더해 이번 달·올해 손익에 반영합니다.", "Add gains/losses made before using this app, so monthly/yearly totals are accurate.")}</div>', unsafe_allow_html=True)
        j1, j2 = st.columns(2)
        with j1:
            st.session_state.adj_month = st.number_input(t("이번 달 보정 ($)", "This-month adjustment ($)"), value=float(st.session_state.adj_month))
        with j2:
            st.session_state.adj_year = st.number_input(t("올해 보정 ($)", "This-year adjustment ($)"), value=float(st.session_state.adj_year))

    w, m, y = period_pnl()
    def pct_of_start(v):
        sc = (profile().get("start_capital", 0) or profile().get("assets", 0) or 0)
        return signed_pct(v / sc * 100) if sc else "—"
    st.markdown(
        '<div class="stats three">'
        + stat(t("이번 주", "This week"), signed_money(w), pct_of_start(w), "pos" if w >= 0 else "neg")
        + stat(t("이번 달", "This month"), signed_money(m), pct_of_start(m), "pos" if m >= 0 else "neg")
        + stat(t("올해", "This year"), signed_money(y), pct_of_start(y), "pos" if y >= 0 else "neg")
        + "</div>", unsafe_allow_html=True)
    st.markdown(f'<div class="footnote">{t("퍼센트는 시작 자금 기준입니다. 자동 거래내역은 아직 손익 집계에 합산하지 않고, 직접 거래일지와 보정값만 합산합니다.", "Percentages are vs starting capital. Auto-imported activity is not yet paired into realized P&L; only manual journal entries and adjustments are counted.")}</div>', unsafe_allow_html=True)


# =====================================================
# Tab — Settings · tools
# =====================================================
with tab_set:
    st.markdown(f'<div class="headline">{t("설정 · 도구", "Settings · tools")}</div>', unsafe_allow_html=True)

    # ---- Claude API test ----
    st.markdown(f'<div class="eyebrow">{t("Claude API 상태", "Claude API status")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="footnote" style="margin:0 0 10px 0;">{t("API 키는 코드에 직접 넣지 말고 Streamlit Secrets의 ANTHROPIC_API_KEY에 저장하세요.", "Do not hard-code keys. Save it as ANTHROPIC_API_KEY in Streamlit Secrets.")}</div>', unsafe_allow_html=True)
    if st.button(t("Claude API 연결 테스트", "Test Claude API"), width="stretch"):
        test_text, test_err = call_claude(t("한 문장으로 '연결 성공'이라고 답해.", "Reply with one sentence: connection successful."))
        if test_err:
            st.markdown(line(t(f"Claude API 실패 — {test_err}", f"Claude API failed — {test_err}"), "b"), unsafe_allow_html=True)
        else:
            st.markdown(line(t("Claude API 연결 성공", "Claude API connection successful"), "g"), unsafe_allow_html=True)
            st.caption(test_text)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---- Google Sheets backup ----
    st.markdown(f'<div class="eyebrow">{t("구글 시트 백업 · 양방향", "Google Sheets backup · two-way")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="footnote" style="margin:0 0 10px 0;">{t("거래장부를 내 구글 시트로 백업하고(앱→시트, 장부가 바뀔 때마다 자동), 시트에서 고친 카테고리·감정(1-5)·추격(Y)은 다시 앱으로 가져올 수 있습니다(시트→앱). 폴리마켓이 오래된 거래를 지워도 시트에 영구 보존됩니다.", "Backs up your trade ledger to your own Google Sheet (app→sheet, automatically whenever the ledger changes), and category/emotion(1-5)/chase(Y) edited in the sheet can be imported back (sheet→app). Records survive Polymarket dropping old data.")}</div>', unsafe_allow_html=True)

    _method = gsheet_active_method()
    if _method == "webapp":
        st.markdown(line(t("연결됨 · Apps Script 웹앱 (내 구글 계정)", "Connected · Apps Script web app (your Google account)"), "g"), unsafe_allow_html=True)
    elif _method == "service_account":
        st.markdown(line(t("연결됨 · 서비스 계정", "Connected · service account"), "g"), unsafe_allow_html=True)
    else:
        st.markdown(line(t("아직 연결 안 됨 — 아래 ‘간단 연결’에 Apps Script URL을 넣으세요.", "Not connected — paste your Apps Script URL under ‘Simple connect’ below."), "w"), unsafe_allow_html=True)

    st.markdown(f'<div class="footnote" style="margin:10px 0 2px 0;font-weight:700;color:var(--ink2);">{t("간단 연결 (추천) — Apps Script 웹앱", "Simple connect (recommended) — Apps Script web app")}</div>', unsafe_allow_html=True)
    with st.expander(t("① 처음 한 번 설정하는 법 (구글 클라우드 · 서비스계정 불필요)", "① One-time setup (no Google Cloud / service account)")):
        st.markdown(t(
            r"""내 구글 계정·내 시트에 직접 저장하는 가장 쉬운 방법입니다.
1. 브라우저에 `sheets.new` → 새 스프레드시트 생성(이름 아무거나).
2. 상단 메뉴 **확장 프로그램 → Apps Script**.
3. 기본 코드 지우고 아래 v3 코드를 붙여넣고 저장(💾) — 장부 백업/가져오기 + **전체 상태 스냅샷**까지 처리합니다:
```javascript
var SECRET = "";  // (선택) 아래 '공유 토큰'과 같은 값. 비우면 검사 안 함.

function doPost(e) {  // 앱 → 시트 (장부 백업 + 전체 상태 스냅샷)
  try {
    var body = JSON.parse(e.postData.contents);
    if (SECRET && String(body.token || "") !== SECRET) return _json({ok:false,error:"bad token"});
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (body.state !== undefined) {  // 전체 상태: JSON을 40,000자 청크로 'state' 탭에 저장
      var st = ss.getSheetByName("state") || ss.insertSheet("state");
      st.clearContents();
      var s = String(body.state || "");
      var out = [[String(body.saved_at || "")]];
      for (var i = 0; i < s.length; i += 40000) out.push(["#" + s.substring(i, i + 40000)]);
      st.getRange(1, 1, out.length, 1).setValues(out);
      return _json({ok:true, chunks: out.length - 1});
    }
    var rows = body.rows || [];
    var sh = ss.getSheetByName("ledger") || ss.insertSheet("ledger");
    sh.clearContents();
    if (rows.length) sh.getRange(1,1,rows.length,rows[0].length).setValues(rows);
    return _json({ok:true,written:Math.max(rows.length-1,0)});
  } catch (err) { return _json({ok:false,error:String(err)}); }
}

function doGet(e) {  // 시트 → 앱 (장부 가져오기 + 상태 복원)
  try {
    var p = (e && e.parameter) || {};
    if (SECRET && String(p.token || "") !== SECRET) return _json({ok:false,error:"bad token"});
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (String(p.action || "") === "read_state") {  // 전체 상태 스냅샷 읽기
      var st = ss.getSheetByName("state");
      if (!st) return _json({ok:true, state:"", saved_at:""});
      var vals = st.getDataRange().getValues();
      var parts = [];
      for (var i = 1; i < vals.length; i++) parts.push(String(vals[i][0]).replace(/^#/, ""));
      return _json({ok:true, state: parts.join(""), saved_at: vals.length ? String(vals[0][0]) : ""});
    }
    var sh = ss.getSheetByName("ledger");
    return _json({ok:true, rows: sh ? sh.getDataRange().getDisplayValues() : []});
  } catch (err) { return _json({ok:false,error:String(err)}); }
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
```
4. **배포 → 새 배포 → 유형: 웹 앱**, 실행: **나**, 액세스: **모든 사용자** → 배포 → 구글 로그인 승인.
5. 나오는 **웹 앱 URL**(.../exec)을 복사해 아래에 붙여넣기.
6. **(강력 추천)** Streamlit Cloud → 앱 설정 → **Secrets**에 아래를 추가 — 재배포되어도 URL이 살아남아 부팅 자동 복원이 동작합니다:
```toml
gsheet_webapp_url = "https://script.google.com/macros/s/..../exec"
# 토큰을 쓰면: gsheet_webapp_token = "SECRET과 같은 값"
```
* 보호하려면 코드의 SECRET과 아래 '공유 토큰'을 같은 값으로 두세요.
* 이미 예전 코드로 배포했다면: 코드를 위 v3로 교체 → **배포 관리 → 수정 → 새 버전** (URL은 그대로 유지됩니다).""",
            r"""The easiest way — writes to your own sheet with your own Google account.
1. Go to `sheets.new` → create a spreadsheet.
2. Menu **Extensions → Apps Script**.
3. Replace the default code with the v3 block below and save — it handles ledger backup/import plus the **full-state snapshot**:
```javascript
var SECRET = "";  // (optional) same value as 'Shared token' below; empty = no check.

function doPost(e) {  // app → sheet (ledger backup + full-state snapshot)
  try {
    var body = JSON.parse(e.postData.contents);
    if (SECRET && String(body.token || "") !== SECRET) return _json({ok:false,error:"bad token"});
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (body.state !== undefined) {  // full state: JSON stored in 40,000-char chunks on 'state' tab
      var st = ss.getSheetByName("state") || ss.insertSheet("state");
      st.clearContents();
      var s = String(body.state || "");
      var out = [[String(body.saved_at || "")]];
      for (var i = 0; i < s.length; i += 40000) out.push(["#" + s.substring(i, i + 40000)]);
      st.getRange(1, 1, out.length, 1).setValues(out);
      return _json({ok:true, chunks: out.length - 1});
    }
    var rows = body.rows || [];
    var sh = ss.getSheetByName("ledger") || ss.insertSheet("ledger");
    sh.clearContents();
    if (rows.length) sh.getRange(1,1,rows.length,rows[0].length).setValues(rows);
    return _json({ok:true,written:Math.max(rows.length-1,0)});
  } catch (err) { return _json({ok:false,error:String(err)}); }
}

function doGet(e) {  // sheet → app (ledger import + state restore)
  try {
    var p = (e && e.parameter) || {};
    if (SECRET && String(p.token || "") !== SECRET) return _json({ok:false,error:"bad token"});
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (String(p.action || "") === "read_state") {
      var st = ss.getSheetByName("state");
      if (!st) return _json({ok:true, state:"", saved_at:""});
      var vals = st.getDataRange().getValues();
      var parts = [];
      for (var i = 1; i < vals.length; i++) parts.push(String(vals[i][0]).replace(/^#/, ""));
      return _json({ok:true, state: parts.join(""), saved_at: vals.length ? String(vals[0][0]) : ""});
    }
    var sh = ss.getSheetByName("ledger");
    return _json({ok:true, rows: sh ? sh.getDataRange().getDisplayValues() : []});
  } catch (err) { return _json({ok:false,error:String(err)}); }
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
```
4. **Deploy → New deployment → Web app**, Execute as **Me**, Access **Anyone** → Deploy → authorize.
5. Copy the **web app URL** (.../exec) and paste it below.
6. **(Strongly recommended)** Streamlit Cloud → App settings → **Secrets** — add the lines below so the URL survives redeploys and boot auto-restore always works:
```toml
gsheet_webapp_url = "https://script.google.com/macros/s/..../exec"
# if you use a token: gsheet_webapp_token = "same as SECRET"
```
* To protect it, set SECRET in the code and the 'Shared token' below to the same value.
* Already deployed an older version? Replace the code with v3 above → **Manage deployments → Edit → New version** (URL stays the same)."""))

    st.session_state.gsheet_webapp_url = st.text_input(
        t("Apps Script URL", "Apps Script URL"),
        value=str(st.session_state.get("gsheet_webapp_url", "") or ""),
        placeholder="https://script.google.com/macros/s/..../exec",
        key="gsheet_webapp_url_input",
    )
    st.session_state.gsheet_webapp_token = st.text_input(
        t("공유 토큰 (선택)", "Shared token (optional)"),
        value=str(st.session_state.get("gsheet_webapp_token", "") or ""),
        placeholder=t("코드의 SECRET과 같은 값 (비워도 됨)", "same as SECRET in the code (optional)"),
        key="gsheet_webapp_token_input",
    )

    st.session_state.gsheet_autobackup = st.checkbox(
        t("자동 백업 (장부가 바뀔 때마다)", "Auto-backup (whenever the ledger changes)"),
        value=bool(st.session_state.get("gsheet_autobackup", False)),
        help=t("켜두면 승/패 확정·감정 태그·새 거래로 장부 내용이 바뀔 때마다 자동으로 시트에 저장됩니다.",
               "When on, every ledger change (resolutions, emotion tags, new trades) is backed up automatically."),
    )
    _gs_last = str(st.session_state.get("_gsheet_last_backup", "") or "")
    _gs_lastn = int(st.session_state.get("_gsheet_last_count", 0) or 0)
    if _gs_last:
        st.markdown(f'<div class="footnote">{t(f"마지막 백업: {_gs_last} · {_gs_lastn}건", f"Last backup: {_gs_last} · {_gs_lastn} rows")}</div>', unsafe_allow_html=True)

    if st.button(t("지금 구글 시트로 백업", "Back up to Google Sheets now"), width="stretch", key="gsheet_backup_now"):
        _b = backup_ledger(force=True)
        if _b["ok"]:
            st.success(t(f"백업 완료 · {_b['written']}건을 시트에 저장했습니다.", f"Backed up · {_b['written']} rows written."))
        else:
            _emap = {
                "not_configured": t("먼저 Apps Script URL(또는 서비스계정)을 설정하세요.", "Set an Apps Script URL (or service account) first."),
                "no_url": t("Apps Script URL을 먼저 입력하세요.", "Enter the Apps Script URL first."),
                "no_lib": t("gspread 미설치 — requirements 반영 후 재배포하세요.", "gspread not installed — redeploy after requirements update."),
                "no_creds": t("Secrets에 gcp_service_account가 없습니다.", "Missing gcp_service_account in Secrets."),
                "empty_ledger": t("백업할 거래장부가 비어 있습니다.", "Trade ledger is empty."),
            }
            st.markdown(line(_emap.get(_b["error"], t(f"백업 실패 — {_b['error']}", f"Backup failed — {_b['error']}")), "b"), unsafe_allow_html=True)

    # ---- 시트 → 앱 가져오기 (양방향의 반대 방향) ----
    st.markdown(f'<div class="footnote" style="margin:10px 0 2px 0;">{t("시트의 ledger 탭에서 카테고리·감정(1-5)·추격(Y) 칸을 고친 뒤 아래 버튼을 누르면 앱에 반영됩니다 (‘키’ 컬럼 기준 매칭 · Apps Script 방식 전용).", "Edit category / emotion(1-5) / chase(Y) cells in the sheet’s ledger tab, then press below to apply them in the app (matched by the ‘키’ key column · Apps Script method only).")}</div>', unsafe_allow_html=True)
    if st.button(t("시트에서 가져오기 (카테고리·감정 반영)", "Import from sheet (category · emotion)"), width="stretch", key="gsheet_import_btn"):
        with st.spinner(t("시트 읽는 중", "Reading sheet")):
            _ri = restore_ledger_from_webapp()
        if _ri["ok"]:
            st.success(t(f"가져오기 완료 · 시트 {_ri['rows']}행 확인 · 카테고리 {_ri['categories']}건 · 감정/추격 {_ri['tags']}건 반영",
                         f"Imported · {_ri['rows']} sheet rows · {_ri['categories']} categories · {_ri['tags']} emotion/chase tags applied"))
        else:
            _imap = {
                "no_url": t("Apps Script URL을 먼저 입력하세요 (가져오기는 웹앱 방식 전용).", "Enter the Apps Script URL first (import is web-app only)."),
                "empty_sheet": t("시트의 ledger 탭이 비어 있습니다 — 먼저 한 번 백업하세요.", "The ledger tab is empty — back up once first."),
                "no_key_column": t("시트에 ‘키’ 컬럼이 없습니다 — 새 스크립트(doGet 포함)로 재배포하고 한 번 백업하세요.", "No ‘키’ key column — redeploy the new script (with doGet) and back up once."),
            }
            st.markdown(line(_imap.get(_ri["error"], t(f"가져오기 실패 — {_ri['error']}", f"Import failed — {_ri['error']}")), "b"), unsafe_allow_html=True)

    # ---- 전체 상태 백업 · 복원 (재배포 대비) ----
    st.markdown(f'<div class="footnote" style="margin:14px 0 2px 0;font-weight:700;color:var(--ink2);">{t("전체 상태 백업 · 복원 (재배포 대비)", "Full-state backup · restore (survives redeploys)")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="footnote" style="margin:0 0 6px 0;">{t("장부 외의 모든 기록(승/패 확정 · 감정 태그 · 복기 노트 · 현금/입출금 입력 등)을 시트의 state 탭에 저장합니다. Streamlit Cloud가 재배포·재부팅되어 로컬 파일이 초기화되면 부팅 때 자동 복원됩니다. ⚠️ URL 자체도 살아남게 하려면 앱 설정 → Secrets에 gsheet_webapp_url(및 토큰 쓰면 gsheet_webapp_token)을 넣어두세요.", "Saves everything beyond the ledger (resolutions, emotion tags, review notes, cash inputs …) to the sheet’s state tab. If a redeploy wipes the local file, the app auto-restores on boot. ⚠️ Put gsheet_webapp_url (and gsheet_webapp_token if used) in App settings → Secrets so the URL itself survives redeploys.")}</div>', unsafe_allow_html=True)
    _ss_last = str(st.session_state.get("_gsheet_state_last_backup", "") or "")
    if _ss_last:
        st.markdown(f'<div class="footnote">{t(f"마지막 상태 백업: {_ss_last}", f"Last state backup: {_ss_last}")}</div>', unsafe_allow_html=True)
    _c_sb, _c_sr = st.columns(2)
    with _c_sb:
        if st.button(t("지금 전체 상태 백업", "Back up full state now"), width="stretch", key="state_backup_now"):
            _sb = backup_state_via_webapp()
            if _sb["ok"]:
                st.success(t("전체 상태를 시트 state 탭에 저장했습니다.", "Full state saved to the sheet’s state tab."))
            else:
                _sbmap = {"no_url": t("Apps Script URL을 먼저 입력하세요.", "Enter the Apps Script URL first.")}
                st.markdown(line(_sbmap.get(_sb["error"], t(f"상태 백업 실패 — {_sb['error']}", f"State backup failed — {_sb['error']}")), "b"), unsafe_allow_html=True)
    with _c_sr:
        _confirm_restore = st.checkbox(
            t("복원이 현재 앱 상태를 시트 스냅샷으로 덮어쓰는 것을 이해했습니다", "I understand restore overwrites the current app state"),
            key="state_restore_confirm")
        if st.button(t("시트에서 전체 상태 복원", "Restore full state from sheet"), width="stretch",
                     key="state_restore_now", disabled=not _confirm_restore):
            _sr = restore_state_from_webapp()
            if _sr["ok"]:
                st.success(t(f"복원 완료 · {_sr['restored']}개 항목 · 스냅샷 {_sr['saved_at']}",
                             f"Restored · {_sr['restored']} keys · snapshot {_sr['saved_at']}"))
                st.rerun()
            else:
                _srmap = {
                    "no_url": t("Apps Script URL을 먼저 입력하세요.", "Enter the Apps Script URL first."),
                    "no_snapshot": t("시트에 상태 스냅샷이 없습니다 — 먼저 ‘지금 전체 상태 백업’을 누르세요.", "No snapshot in the sheet — press ‘Back up full state now’ first."),
                }
                st.markdown(line(_srmap.get(_sr["error"], t(f"복원 실패 — {_sr['error']}", f"Restore failed — {_sr['error']}")), "b"), unsafe_allow_html=True)

    with st.expander(t("고급: 서비스 계정 (gspread) 방식", "Advanced: service account (gspread)")):
        _gs = gsheet_status()
        if _gs["ready"]:
            st.markdown(line(t(f"서비스계정 준비됨 · {_gs['email']}", f"Service account ready · {_gs['email']}"), "g"), unsafe_allow_html=True)
        st.markdown(t(
            r"""구글 클라우드에서 서비스계정 JSON 키를 발급해 Streamlit Secrets의 `[gcp_service_account]`에 넣고, 시트를 그 client_email에 편집자로 공유한 뒤 아래에 시트 URL을 입력합니다. (위 Apps Script 방식이 더 쉽습니다.)""",
            r"""Create a service-account JSON key in Google Cloud, put it in Streamlit Secrets as `[gcp_service_account]`, share the sheet (Editor) with its client_email, then paste the sheet URL below. (The Apps Script method above is simpler.)"""))
        st.session_state.gsheet_url = st.text_input(
            t("구글 시트 주소 (URL) — 서비스계정용", "Google Sheet URL — for service account"),
            value=str(st.session_state.get("gsheet_url", "") or ""),
            placeholder="https://docs.google.com/spreadsheets/d/....",
            key="gsheet_url_input",
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---- developer mode ----
    st.markdown(f'<div class="eyebrow">{t("개발자 모드", "Developer mode")}</div>', unsafe_allow_html=True)
    st.session_state.dev_mode = st.checkbox(
        t("디버그/Raw API 응답 보기", "Show debug / raw API responses"),
        value=bool(st.session_state.get("dev_mode", False)),
        help=t("일반 사용 시 꺼두면 포트폴리오와 거래내역 화면이 더 깔끔해집니다.", "Keep this off for a cleaner portfolio and journal UI."),
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---- self-check settings ----
    st.markdown(f'<div class="eyebrow">{t("자가평가 설정", "Self-check settings")}</div>', unsafe_allow_html=True)
    _scale_labels = {t("5단계", "5-step"): 5, t("10단계", "10-step"): 10}
    _current_scale = self_check_scale()
    _scale_keys = list(_scale_labels.keys())
    _scale_index = 1 if _current_scale == 10 else 0
    _selected_scale_label = st.selectbox(t("자가평가 점수 단계", "Self-check rating scale"), _scale_keys, index=_scale_index, key="self_check_scale_widget")
    st.session_state.self_check_scale = _scale_labels.get(_selected_scale_label, 5)
    st.markdown(f'<div class="footnote">{t("5단계: 1 매우 낮음 · 3 보통 · 5 매우 높음 / 10단계: 1 매우 낮음 · 10 매우 높음", "5-step: 1 very low · 3 normal · 5 very high / 10-step: 1 very low · 10 very high")}</div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---- risk profile ----
    st.markdown(f'<div class="eyebrow">{t("내 리스크 프로필", "My risk profile")}</div>', unsafe_allow_html=True)
    with st.form("profile_form"):
        s1, s2 = st.columns(2)
        with s1:
            pf_assets = st.number_input(t("총자산 ($) — 포트폴리오 미사용 시 기준값", "Total assets ($) — fallback when portfolio empty"), 1.0, value=float(prof["assets"]))
            pf_start = st.number_input(t("시작 자금 ($)", "Starting capital ($)"), 1.0, value=float(prof["start_capital"]))
            pf_emotional = st.number_input(t("감정 한도 ($)", "Emotional cap ($)"), 1.0, value=float(prof["emotional_limit"]))
        with s2:
            pf_max = st.slider(t("적정 배팅 비율 (%)", "Comfort bet ratio (%)"), 1, 30, int(prof["max_pct"]))
            pf_block = st.slider(t("진입 금지선 (%)", "No-entry line (%)"), 5, 40, int(prof["block_pct"]))
        save_prof = st.form_submit_button(t("저장", "Save"), width="stretch")

    if save_prof:
        p = dict(prof)
        p.update(assets=pf_assets, start_capital=pf_start, emotional_limit=pf_emotional,
                 max_pct=float(pf_max), block_pct=float(max(pf_block, pf_max + 2)))
        st.session_state.profile = p
        st.toast(t("저장했습니다", "Saved"))
        st.rerun()

    if st.button(t("리스크 기준 기본값으로 초기화", "Reset risk defaults"), width="stretch"):
        st.session_state.profile = dict(DEFAULT_PROFILE)
        st.rerun()

    st.markdown(
        f'<div class="footnote">{t(f"현재 적용 — 적정 {g_:.0f}% · 주의 {c1_:.0f}% · 위험 {c2_:.0f}% · 진입 금지 {blk_:.0f}% · 시스템 실패 50% / 감정 한도 {money(prof['emotional_limit'])} · 강한 경고 {money(prof['emotional_limit']*2)} · 시스템 실패 {money(prof['emotional_limit']*4)}", f"Active — comfort {g_:.0f}% · caution {c1_:.0f}% · risk {c2_:.0f}% · block {blk_:.0f}% · failure 50% / cap {money(prof['emotional_limit'])} · strong warning {money(prof['emotional_limit']*2)} · failure {money(prof['emotional_limit']*4)}")}</div>',
        unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---- URL helper ----
    st.markdown(f'<div class="eyebrow">{t("Polymarket URL 도우미", "Polymarket URL helper")}</div>', unsafe_allow_html=True)
    url = st.text_input("Polymarket URL", "https://polymarket.com/event/")
    if st.button(t("시장 정보 불러오기", "Fetch market info"), width="stretch"):
        slug = extract_slug(url)
        if not slug:
            st.markdown(line(t("URL에서 slug를 찾지 못했습니다.", "Couldn't find a slug."), "b"), unsafe_allow_html=True)
        else:
            try:
                with st.spinner(t("불러오는 중", "Fetching")):
                    payload = fetch_gamma(slug)
                rows = extract_markets(payload, infer_market_category(url, ""))
                st.session_state.url_rows = rows
                if not rows:
                    st.markdown(line(t("시장을 찾지 못했습니다. /event/ URL인지 확인해주세요.", "No markets found. Check it's an /event/ URL."), "w"), unsafe_allow_html=True)
            except Exception as e:
                st.markdown(line(t(f"불러오기 실패 — {e}", f"Fetch failed — {e}"), "b"), unsafe_allow_html=True)
    if st.session_state.url_rows:
        st.dataframe(pd.DataFrame(st.session_state.url_rows), width="stretch", hide_index=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---- backup ----
    st.markdown(f'<div class="eyebrow">{t("백업 · 복원", "Backup · restore")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="footnote" style="margin:0 0 10px 0;">{t("새로고침하면 데이터가 사라집니다. 백업을 내려받아 두세요. 프로필도 함께 저장됩니다.", "Data is lost on refresh. Download a backup — your profile is included.")}</div>', unsafe_allow_html=True)
    _local_status = str(st.session_state.get("_local_state_status", ""))
    _local_saved_at = str(st.session_state.get("_local_state_saved_at", ""))
    st.markdown(
        f'<div class="footnote" style="margin:0 0 10px 0;">'
        f'{t("로컬 자동저장", "Local autosave")} · {esc(_local_status or "-")}'
        + (f' · {esc(_local_saved_at)}' if _local_saved_at else '')
        + f'<br>{esc(LOCAL_STATE_PATH)}</div>',
        unsafe_allow_html=True,
    )
    bc1, bc2 = st.columns(2)
    with bc1:
        backup = {"profile": st.session_state.profile, "cash": st.session_state.cash,
                  "display_currency": st.session_state.get("display_currency", "USD"),
                  "usd_krw_rate": st.session_state.get("usd_krw_rate", 1400.0),
                  "deposits": st.session_state.deposits, "withdrawals": st.session_state.withdrawals,
                  "portfolio": st.session_state.portfolio, "trade_log": st.session_state.trade_log,
                  "auto_trades": st.session_state.auto_trades, "wallet_addr": st.session_state.wallet_addr,
                  "imported_tx_ids": st.session_state.imported_tx_ids,
                  "portfolio_hidden_keys": st.session_state.get("portfolio_hidden_keys", []),
                  "side_panel_trade_limit": st.session_state.get("side_panel_trade_limit", 5),
                  "today_start_cash": st.session_state.get("today_start_cash", 0.0),
                  "today_stop_loss_amount": st.session_state.get("today_stop_loss_amount", 0.0),
                  "today_goal_mode": st.session_state.get("today_goal_mode", "percent"),
                  "today_goal_pct": st.session_state.get("today_goal_pct", 3.0),
                  "today_goal_amount": st.session_state.get("today_goal_amount", 0.0),
                  "today_stop_loss_gross_only": st.session_state.get("today_stop_loss_gross_only", False),
                  "today_anchor_mode": st.session_state.get("today_anchor_mode", "next"),
                  "today_anchor_key": st.session_state.get("today_anchor_key", ""),
                  "today_anchor_label": st.session_state.get("today_anchor_label", ""),
                  "today_anchor_time": st.session_state.get("today_anchor_time", ""),
                  "today_anchor_set_at": st.session_state.get("today_anchor_set_at", ""),
                  "today_cash_adjustment": st.session_state.get("today_cash_adjustment", 0.0),
                  "activity_events": st.session_state.get("activity_events", []),
                  "api_sync_meta": st.session_state.get("api_sync_meta", {}),
                  "watchlist": st.session_state.watchlist, "order_candidates": st.session_state.order_candidates,
                  "pnl_raw": st.session_state.pnl_raw, "profile_pnl": st.session_state.profile_pnl,
                  "explore_url": st.session_state.explore_url, "explore_markets": st.session_state.explore_markets,
                  "prefill_entry": st.session_state.prefill_entry,
                  "dev_mode": st.session_state.dev_mode,
                  "adj_month": st.session_state.adj_month, "adj_year": st.session_state.adj_year,
                  "reviews": st.session_state.reviews,
                  "review_notes": st.session_state.get("review_notes", {}),
                  "entry_self_strategy": st.session_state.get("entry_self_strategy", {}),
                  "self_check_scale": st.session_state.get("self_check_scale", 5)}
        st.download_button(t("백업 내려받기 (JSON)", "Download backup (JSON)"),
                           data=json.dumps(backup, ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name="memento_backup.json", mime="application/json", width="stretch")
    with bc2:
        up = st.file_uploader(t("백업 불러오기", "Restore backup"), type=["json"], label_visibility="collapsed")
        if up is not None:
            try:
                data = json.loads(up.read().decode("utf-8"))
                st.session_state.profile = data.get("profile") or st.session_state.profile
                st.session_state.display_currency = data.get("display_currency", st.session_state.get("display_currency", "USD"))
                st.session_state.usd_krw_rate = float(data.get("usd_krw_rate", st.session_state.get("usd_krw_rate", 1400.0)) or 1400.0)
                st.session_state.cash = float(data.get("cash", 0))
                st.session_state.deposits = float(data.get("deposits", 0))
                st.session_state.withdrawals = float(data.get("withdrawals", 0))
                st.session_state.dev_mode = bool(data.get("dev_mode", False))
                st.session_state.portfolio = data.get("portfolio", [])
                st.session_state.trade_log = data.get("trade_log", [])
                st.session_state.auto_trades = data.get("auto_trades", [])
                st.session_state.wallet_addr = data.get("wallet_addr", "")
                st.session_state.imported_tx_ids = data.get("imported_tx_ids", [])
                st.session_state.portfolio_hidden_keys = data.get("portfolio_hidden_keys", st.session_state.get("portfolio_hidden_keys", []))
                st.session_state.side_panel_trade_limit = int(data.get("side_panel_trade_limit", st.session_state.get("side_panel_trade_limit", 5)) or 5)
                st.session_state.today_start_cash = float(data.get("today_start_cash", st.session_state.get("today_start_cash", 0.0)) or 0.0)
                st.session_state.today_stop_loss_amount = float(data.get("today_stop_loss_amount", st.session_state.get("today_stop_loss_amount", 0.0)) or 0.0)
                st.session_state.today_goal_mode = data.get("today_goal_mode", st.session_state.get("today_goal_mode", "percent"))
                st.session_state.today_goal_pct = float(data.get("today_goal_pct", st.session_state.get("today_goal_pct", 3.0)) or 0.0)
                st.session_state.today_goal_amount = float(data.get("today_goal_amount", st.session_state.get("today_goal_amount", 0.0)) or 0.0)
                st.session_state.today_stop_loss_gross_only = bool(data.get("today_stop_loss_gross_only", st.session_state.get("today_stop_loss_gross_only", False)))
                st.session_state.today_anchor_mode = data.get("today_anchor_mode", st.session_state.get("today_anchor_mode", "next"))
                st.session_state.today_anchor_key = data.get("today_anchor_key", st.session_state.get("today_anchor_key", ""))
                st.session_state.today_anchor_label = data.get("today_anchor_label", st.session_state.get("today_anchor_label", ""))
                st.session_state.today_anchor_time = data.get("today_anchor_time", st.session_state.get("today_anchor_time", ""))
                st.session_state.today_anchor_set_at = data.get("today_anchor_set_at", st.session_state.get("today_anchor_set_at", ""))
                st.session_state.today_cash_adjustment = float(data.get("today_cash_adjustment", st.session_state.get("today_cash_adjustment", 0.0)) or 0.0)
                st.session_state.activity_events = data.get("activity_events", st.session_state.get("activity_events", []))
                st.session_state.api_sync_meta = data.get("api_sync_meta", st.session_state.get("api_sync_meta", {}))
                st.session_state.watchlist = data.get("watchlist", [])
                st.session_state.order_candidates = data.get("order_candidates", [])
                st.session_state.pnl_raw = data.get("pnl_raw", {})
                st.session_state.profile_pnl = data.get("profile_pnl", {})
                st.session_state.adj_month = float(data.get("adj_month", 0))
                st.session_state.adj_year = float(data.get("adj_year", 0))
                st.session_state.reviews = data.get("reviews", [])
                st.session_state.review_notes = data.get("review_notes", st.session_state.get("review_notes", {}))
                st.session_state.entry_self_strategy = data.get("entry_self_strategy", st.session_state.get("entry_self_strategy", {}))
                st.session_state.self_check_scale = int(data.get("self_check_scale", st.session_state.get("self_check_scale", 5)) or 5)
                st.toast(t("복원했습니다", "Restored"))
                st.rerun()
            except Exception:
                st.markdown(line(t("백업 파일을 읽지 못했습니다.", "Could not read backup."), "b"), unsafe_allow_html=True)


# =====================================================
# Floating right panel: portfolio summary
# =====================================================
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
_rp_wallet_label = (_rp_wallet[:6] + "…" + _rp_wallet[-4:]) if _rp_wallet else t("수동", "Manual")

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
        f'<div class="o">{esc(p.get("outcome", "") or "—")} · {cents(_safe_float(p.get("cur"), 0.0))}</div></div>'
        f'<div class="v">{money(value)}</div>'
        f'</div>'
        for value, p in _rp_rows
    )
    if _rp_more_holdings:
        _rp_holdings_html += f'<div class="portfolio-more">{t(f"외 {_rp_more_holdings}개 더", f"+{_rp_more_holdings} more")}</div>'
else:
    _rp_holdings_html = (
        f'<div class="portfolio-empty">'
        f'{t("포트폴리오 탭에서 지갑 주소를 불러오면 여기에 요약이 표시됩니다.", "Import a wallet in the Portfolio tab to show a summary here.")}'
        f'</div>'
    )

_rp_completed = []
_rp_trade_sources = [
    (st.session_state.get("auto_trades", []), st.session_state.get("activity_events", []) or [], t("지갑", "Wallet")),
    (st.session_state.get("paste_trades", []), st.session_state.get("paste_events", []) or [], t("붙여넣기", "Paste")),
]
for _rp_trades, _rp_events, _rp_source_label in _rp_trade_sources:
    _rp_trade_rows = group_auto_trades_for_pnl(_rp_trades)
    if _rp_events:
        _rp_trade_rows = link_settlement_events_to_trade_groups(_rp_trade_rows, _rp_events)
    for _rp_r in _rp_trade_rows:
        _rp_pnl = _display_realized(_rp_r)
        if _rp_pnl is None:
            continue
        _rp_bought = _safe_float(_rp_r.get("bought_shares"), 0.0)
        _rp_remaining = _display_remaining_shares(_rp_r)
        _rp_close_tolerance = max(0.05, _rp_bought * 0.01)
        if _rp_remaining > _rp_close_tolerance:
            continue
        _rp_latest_dt = _rp_r.get("linked_event_time") or _rp_r.get("latest_dt") or ""
        _rp_latest_obj = parse_trade_datetime({"d": _rp_latest_dt}) if _rp_latest_dt else None
        _rp_completed.append({
            "market": _rp_r.get("market", ""),
            "outcome": _rp_r.get("outcome", ""),
            "status": _rp_r.get("adjusted_status") or _rp_r.get("status", ""),
            "source": _rp_source_label,
            "pnl": _safe_float(_rp_pnl, 0.0),
            "recovered": _safe_float(_rp_r.get("adjusted_effective_proceeds", _rp_r.get("sell_proceeds")), 0.0),
            "cost": _safe_float(_rp_r.get("buy_cost"), 0.0),
            "latest_dt": _rp_latest_dt,
            "_latest_ts": _rp_latest_obj.timestamp() if _rp_latest_obj else _safe_float(_rp_r.get("_latest_ts"), -1.0),
        })
_rp_completed = sorted(_rp_completed, key=lambda r: r.get("_latest_ts", -1.0), reverse=True)[:5]
_rp_completed_total = sum(_safe_float(r.get("pnl"), 0.0) for r in _rp_completed)

_rp_today_start = _safe_float(st.session_state.get("today_start_cash"), 0.0)
_rp_today_stop = _safe_float(st.session_state.get("today_stop_loss_amount"), 0.0)
_rp_today_goal_mode = st.session_state.get("today_goal_mode", "percent")
if _rp_today_goal_mode == "percent":
    _rp_today_goal_pct = _safe_float(st.session_state.get("today_goal_pct"), 0.0)
    _rp_today_goal = _rp_today_start * _rp_today_goal_pct / 100.0
else:
    _rp_today_goal = _safe_float(st.session_state.get("today_goal_amount"), 0.0)
    _rp_today_goal_pct = (_rp_today_goal / _rp_today_start * 100.0) if _rp_today_start > 0 else 0.0
_rp_today_pnl = _rp_total - _rp_today_start
_rp_today_gain = max(_rp_today_pnl, 0.0)
_rp_today_loss = max(-_rp_today_pnl, 0.0)
_rp_today_goal_left = max(_rp_today_goal - _rp_today_gain, 0.0)
_rp_today_stop_left = max(_rp_today_stop - _rp_today_loss, 0.0) if _rp_today_stop > 0 else 0.0
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
    _rp_completed_html = "".join(
        f'<div class="portfolio-completed-row {"g" if r["pnl"] >= 0 else "b"}">'
        f'<div><div class="n">{esc(r["market"] or t("이름 없는 거래", "Unnamed trade"))}</div>'
        f'<div class="o">{esc(r["outcome"] or "—")} · {esc(r["source"])} · {esc(r["status"])} · {t("회수", "Recovered")} {money(r["recovered"])}</div></div>'
        f'<div class="v">{t("이득", "Gain") if r["pnl"] >= 0 else t("손실", "Loss")} {signed_money(r["pnl"])}</div>'
        f'</div>'
        for r in _rp_completed
    )
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
_sync_wallet_short = (_sync_wallet[:6] + "…" + _sync_wallet[-4:]) if _sync_wallet else "—"
_sync_error = str(_sync_meta.get("error", "") or "")
_rp_sync_html = (
    f'<details class="sync-details">'
    f'<summary>{t("API 동기화 상태", "API sync status")}</summary>'
    f'<div class="sync-body">'
    f'<div class="sync-row"><span>{t("상태", "Status")}</span><b>{esc(_sync_status_text)}</b></div>'
    f'<div class="sync-row"><span>{t("마지막 동기화", "Last sync")}</span><b>{esc(_sync_meta.get("last_sync_at", "—") or "—")}</b></div>'
    f'<div class="sync-row"><span>{t("호출 위치", "Source")}</span><b>{esc(_sync_meta.get("source", "—") or "—")}</b></div>'
    f'<div class="sync-row"><span>{t("지갑", "Wallet")}</span><b>{esc(_sync_wallet_short)}</b></div>'
    f'<div class="sync-row"><span>{t("포지션", "Positions")}</span><b>{int(_sync_meta.get("positions", 0) or 0)}</b></div>'
    f'<div class="sync-row"><span>{t("활동 원본", "Raw activity")}</span><b>{int(_sync_meta.get("raw_activity", 0) or 0)}</b></div>'
    f'<div class="sync-row"><span>{t("거래/정산", "Trades/events")}</span><b>{int(_sync_meta.get("trades", 0) or 0)} / {int(_sync_meta.get("events", 0) or 0)}</b></div>'
    f'<div class="sync-row"><span>{t("새로 추가", "Added")}</span><b>{int(_sync_meta.get("added", 0) or 0)}</b></div>'
    + (f'<div class="sync-row"><span>{t("오류", "Error")}</span><b>{esc(_sync_error)}</b></div>' if _sync_error else '')
    + f'</div></details>'
)

st.markdown(
    f'<div class="portfolio-side-panel">'
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
    f'<div class="portfolio-section-head"><div class="k">{t("최근 완료 거래", "Recent completed")}</div><div class="v">{len(_rp_completed)}/5 · {signed_money(_rp_completed_total)}</div></div>'
    f'<div class="portfolio-completed-list">{_rp_completed_html}</div>'
    f'{_rp_sync_html}'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# 구글 시트 자동 백업 — 맨 아래(장부 갱신 후)에서, 장부 내용이 마지막 성공 백업과
# 달라졌을 때마다 실행 (승/패 확정·감정 태그·새 거래 즉시 반영, 세션 첫 로드 포함).
# 같은 내용으로 실패가 반복되면 내용이 바뀔 때까지 재시도하지 않는다. 전부 fail-soft.
try:
    if st.session_state.get("gsheet_autobackup") and gsheet_active_method():
        _gb_sig, _gb_n = ledger_backup_signature()
        if (_gb_n and _gb_sig
                and _gb_sig != str(st.session_state.get("_gsheet_backup_sig", ""))
                and _gb_sig != str(st.session_state.get("_gsheet_backup_fail_sig", ""))):
            _gb = backup_ledger(force=False)
            if _gb.get("ok"):
                st.session_state._gsheet_backup_sig = _gb_sig
                st.session_state.pop("_gsheet_backup_fail_sig", None)
                try:
                    st.toast(t(f"구글 시트 자동 백업 · {_gb.get('written', _gb_n)}건 저장",
                               f"Google Sheets auto-backup · {_gb.get('written', _gb_n)} rows"))
                except Exception:
                    pass
            else:
                st.session_state._gsheet_backup_fail_sig = _gb_sig
except Exception:
    pass

# 전체 상태 스냅샷 자동 백업 — 내용이 실제로 바뀌었을 때만, 최소 2분 간격 (웹앱 방식 전용).
# 재배포로 로컬 파일이 사라져도 부팅 복원이 가능하도록 시트 'state' 탭을 최신으로 유지한다.
try:
    if st.session_state.get("gsheet_autobackup"):
        maybe_backup_state()
except Exception:
    pass

save_local_state()
