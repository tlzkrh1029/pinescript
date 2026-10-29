<!-- Written as the brief for the agents that built the mockups (2026-10-29). Paths are relative to this folder. -->
# 1-125 Flow, second set: short-term (intraday) screens

Read SPEC.md first (SPEC.md). Everything in it holds
(format rules, look, colours, type, chips, card styles, accessibility, no invented numbers, Korean copy rules) EXCEPT what this file overrides.

## Why a second set
The user watches 12-24 hours of price action, live, with the anchor moved as needed ("그때그때 다름"), the way their TradingView
indicator measures every coin from the leftmost visible bar. The first set (daily/weekly data) missed that. This set answers four
questions on an intraday clock:
1. 강한 코인 순위: which coins are stronger than BTC since the anchor, and by how much.
2. 막 강해지는 코인: which coins are accelerating in the last hour.
3. 시장 분위기: are alts as a whole beating BTC right now.
4. 선 모양 비교: do the lines move with BTC; compare shapes, not just end numbers.

## Screens (one artboard each, page "2차 · 단기 흐름")
| file | tab label | answers |
|---|---|---|
| `Live.dc.html` | 순위·선 비교 | 1 and 4 |
| `Accel.dc.html` | 가속 | 2 |
| `Mood.dc.html` | 시장 분위기 | 3 |
| `ShortHeat.dc.html` | 히트맵 | 1 at a glance |
The tab nav links these four files only (not the first set).

## Shared frame overrides
- Top bar right: chip "기준 BTC", then the as-of line "2026-10-29 21:45 KST 스냅숏" and a small static live-status pill
  "실제 화면은 1분마다 갱신" (a 6px accent dot + text). Do not animate it and do not imply this mockup is live.
- Anchor control, in the control row of every screen, first: label "기준 시각" then chips for the anchors this screen's data has
  (e.g. 1시간 전 / 4시간 전 / 12시간 전 / 24시간 전), each chip showing the KST start time under or beside it (e.g. "12시간 전 · 09:45").
  Default anchor: 12시간 전. Add a "직접 지정" chip that opens a small inline panel with a real `<label>` + `<input type="datetime-local">`
  and the sentence "시안에서는 미리 계산한 기준 시각만 동작합니다. 실제 화면에서는 원하는 시각을 고를 수 있습니다." (no fake results).
- Times on axes and in tooltips are KST HH:MM. Percentages: 2 decimals in tables/tooltips, 1 decimal in tiles; always signed (+/-).
- Footer must state: data = Binance 현물 USDT 5분봉, as-of 2026-10-29 21:45 KST, 81 of 101 non-BTC coins covered, the 20 missing tickers
  (from the data file's `missing`), and that the real screen would refresh every minute via the user's Binance connector.

## Data (folder data/)
- short_live.json: anchors 1h/4h/12h/24h; per anchor: start_kst, times[], btc_chg, beat/n, rows[] (tick, name, rank, tier, chg, vs_btc,
  last1h_vs_btc, line[] = % change since anchor at each time, rel[] = that vs BTC). Rows are sorted by vs_btc; the BTC row sorts last
  and is the reference, not a ranked coin.
- short_accel.json: anchors 4h/12h/24h; per anchor rows[] (tick, name, rank, tier, quad in strong/new/fading/weak, tail[] of 9 points
  {t, x = since-anchor vs BTC %, y = last-60-min vs BTC %}, every 15 min over the last 2 hours), counts.
- short_mood.json: anchors 12h/24h; per anchor rows[] every 15 min: since{tier/all %}, last1h{tier/all %}, n{}, btc close.
- short_heat.json: same treemap layout as the first heatmap (cells x/y/w/h in a 1184 x 600 box, tier blocks with an 18 px caption
  band), windows 15m/1h/4h/12h/24h, chg and vs_btc per window, `binance: false` for the 20 cells without data, btc_chg per window.
Keep each artboard file under about 160 KB: embed only the anchors/fields you draw, round to 2 decimals, and downsample lines you
draw small (sparklines: 24-30 points are plenty).
