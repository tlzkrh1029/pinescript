<!-- Written as the brief for the agents that built the mockups (2026-10-29). Paths are relative to this folder. -->
# 1-125 Flow: shared spec for four dashboard mockups

Product: "1-125 Flow", a bird's-eye view of the crypto market cap ranks 1-125 (stablecoins, tokenized gold and
PI/JST/FLR/NEXO/GNO/FF/SUN/GT left out), always measured against BTC. Four screens of one product, one artboard each:

| file | tab label | screen |
|---|---|---|
| `Main.dc.html` | 회전 그래프 | Relative rotation of every coin vs BTC (RS-Ratio x RS-Momentum, tails) |
| `Heatmap.dc.html` | 히트맵 | Treemap by rank tier, colour = return vs BTC, period switch |
| `RankFlow.dc.html` | 순위 흐름 | 14 weekly rank snapshots: bump chart + tier migration |
| `Breadth.dc.html` | 시장 폭 | Share of coins beating BTC over 30 days, per tier, over time |

Copy language: Korean (`<html lang="ko">`). Tickers and numbers stay as they are. Write descriptions as complete,
plain Korean sentences (subject and predicate, particles kept, no telegraphic noun-phrase endings); short UI labels
(tabs, chips, axis titles, column heads) may be noun phrases. No em dashes in copy. No emoji anywhere.
Do not invent numbers: every figure on screen comes from the data file you are given or is computed from it in
`renderVals()`. Do not give investment advice; phrase reading guides as "how to read", not "buy/sell".

## Format (Design canvas `.dc.html`) — read these first
- Format rules: the Design canvas type's artifact-type/reference/format.md
- Craft rules: same folder, craft.md
- Skeleton and silent-failure rules (from the type's SKILL.md):
  - keep `<script src="./support.js"></script>` in `<head>` EXACTLY; close every non-void element; quote every attribute.
  - `{{hole}}` is a dotted lookup into `renderVals()` only, never an expression. Compute everything in `renderVals()`.
  - all UI is `<x-dc>` markup; never build DOM in script (`innerHTML`, `appendChild`, `document.*`, `window.X`).
  - one `<script type="text/x-dc" data-dc-script data-props='…'>` block, classic JS, `class Component extends DCLogic`, no imports.
    Put the embedded data in that same script (e.g. a `const DATA = {...};` line above the class).
  - `data-props` is single-quoted JSON; escape `&` as `&amp;`, `'` as `&#39;`. Declare `$preview` = {width:1280,height:<your h>}.
    Tweaks are levers only (e.g. a density or label toggle); never copy.
  - Loops: `<sc-for list="{{xs}}" as="x" hint-placeholder-count="N">`, branches `<sc-if value="{{flag}}" hint-placeholder-val="{{ true }}">`.
    Per-item handlers are functions attached to each item in `renderVals()`; bind `onClick="{{ x.pick }}"`.
  - Do NOT put `<sc-for>` or `<sc-if>` inside an `<svg>`. For charts, either (a) loop over absolutely positioned HTML
    wrappers, each holding its own small `<svg>` or being the mark itself (a positioned div dot/cell), or (b) use a fixed
    set of SVG elements whose attributes are holes (`<path d="{{lines.all}}">`). Precompute pixel coordinates and SVG path
    strings in `renderVals()`.
  - no network except the Google Fonts `<link>` below; no `<iframe>`; no global keydown handlers.
  - Links between screens: `<a href="Heatmap.dc.html">히트맵</a>` (relative path of the other artboard).
- This artboard is a PAGE: fluid root (`max-width: 1280px; margin: 0 auto;` %/fr/rem, no px width on the root),
  `$preview.width` 1280. Charts may keep a fixed px drawing size inside a box with `overflow-x: auto`, so a phone scrolls the
  chart rather than squashing it. Toolbars and chip rows wrap. Report the page's total height at 1280 px wide (over-tall beats clipped).

## Look: "night desk" (dark, data-first, quiet chrome)
Fonts: `<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap" rel="stylesheet">` in `<helmet>`.
Text: `"IBM Plex Sans KR", system-ui, sans-serif`. Numbers in tables, ticks and tooltips: `"IBM Plex Mono", ui-monospace, monospace` with `font-variant-numeric: tabular-nums`.
Type scale: page title 28/36 600; section title 16/24 600; body 14/22 400; small 12/18; tick labels 11/14 mono. Nothing below 11px.

Colours (dark only; put them inline as literal values, they are not tweaks):
- page `#0d0d0d`; card surface `#1a1a19`; raised `#222220`; hairline border `rgba(255,255,255,0.10)`; gridline `#2c2c2a`; axis `#383835`
- ink `#f0efec`; ink-2 `#c3c2b7`; muted `#898781` (only for >= 12px secondary labels on `#1a1a19`)
- accent / "stronger than BTC" / selection: blue `#3987e5`; "weaker than BTC": red `#e66767`; neutral midpoint `#383835`
- diverging ramp for the heatmap (5 steps per arm around a neutral midpoint). On a dark surface the largest magnitude is
  the most prominent, i.e. the brightest step:
  - midpoint (|value| below the first threshold): `#383835`
  - blue arm, small -> large: `#1d3550 #1f4a7a #2563a8 #3987e5 #6da7ec`
  - red arm, small -> large: `#4a2526 #6e2c2d #9c3838 #c94d4d #e66767`
  Check lightness is monotonic per arm and pick the cell label colour per step (black or white, whichever reaches >= 4.5:1).
- categorical (lines, max 4 at once, fixed order): tier 1-10 `#3987e5`, 11-50 `#d95926`, 51-100 `#199e70`, 101-125 `#c98500`
  (validated: dark mode, adjacent pairs PASS; yellow/aqua at CVD 8.4 so always direct-label lines). "전체" (all tiers) line: ink `#f0efec`.
  For scatter forms (RRG) do NOT colour 4 tiers at once: highlight the selected tier in accent blue and draw the rest in `#55544f`.
- status colours are not used.
Shape: cards radius 12px, 1px hairline border, padding 20-24px; chips/buttons radius 999px, min-height 44px, padding 0 16px,
1px hairline border, selected = `#3987e5` border + `rgba(57,135,229,0.16)` fill + ink text; focus-visible outline 2px `#3987e5`.
Marks: lines 2px (context lines 1px at 35-50% opacity), dots >= 8px, 2px surface ring (`#1a1a19`) where marks overlap,
gridlines 1px `#2c2c2a`, no chart borders, no gradients, no drop shadows, no left-border accent cards.

## Shared page frame (copy identically into every screen, mark the current tab active)
1. Top bar (height 64px, bottom hairline): left = product mark (a small inline stroke SVG of four concentric arcs, 20px,
   `aria-hidden="true"`) + "1-125 Flow" 16px 600; centre/left = tab nav `<nav aria-label="화면">` with four `<a href>` tabs
   (회전 그래프, 히트맵, 순위 흐름, 시장 폭), current one `aria-current="page"` with a 2px accent underline;
   right = a chip "기준 BTC" and the as-of text (e.g. "2026-10-28 종가 기준").
2. Title block: h1 (the screen's name and claim), one or two sentences explaining what the screen shows and how to read it.
3. Control row (wrapping flex, gap 8px): real `<button aria-pressed>` chips.
4. Main grid: chart card (flex 999 1 760px) + side panel (flex 1 1 300px) in a wrapping flex row, gap 24px.
5. "표로 보기" toggle: a button that swaps the chart for an accessible `<table>` of the same numbers (dataviz rule: a table view exists).
6. Footer notes (12px ink-2): data source, method, as-of date, coverage gaps (list the coins not shown and why).

## Data (already computed; embed what you need, rounding to what you display)
Folder: data/
- universe.json: 102 coins (rank, tick, name, tier, mcap, chg1d/7d/30d/90d in %), TradingView coin screener (CRYPTO: index), 2026-10-29.
- view_rrg.json, view_heatmap.json, view_rankflow.json, view_breadth.json: one per screen; each carries its own method/source notes.
Dataviz method: the dataviz skill  (SKILL.md is summarized here;
read references/marks-and-anatomy.md, interaction.md, anti-patterns.md; run scripts/validate_palette.js with `--mode dark --surface #1a1a19` for any palette you add).
Interaction (by default): per-mark hover tooltip (state-driven positioned div with ticker, name, rank, values), click to pin a selection
that the side panel details; legend always present for >= 2 series; selective direct labels, never a label on every point;
one axis per chart (never dual axis: BTC price goes in its own small chart).
