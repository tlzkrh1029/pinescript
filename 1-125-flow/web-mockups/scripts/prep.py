"""Precompute the data each mockup needs, so artboards only lay it out.

Inputs (data/): universe.json (TradingView screener, 2026-10-29), klines_1d.json (Binance 1d closes),
data/cmc/cmc_YYYYMMDD.json (CoinMarketCap weekly historical snapshots).
Outputs (data/): view_rrg.json, view_heatmap.json, view_rankflow.json, view_breadth.json
"""
import datetime, glob, json, math

U = json.load(open("data/universe.json"))
COINS = U["coins"]
K = json.load(open("data/klines_1d.json"))
TIER_ORDER = ["1-10", "11-50", "51-100", "101-125"]
EXCL = {"PI", "JST", "FLR", "NEXO", "GNO", "FF", "SUN", "GT", "XAUT", "PAXG", "XAUt"}


def day(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime("%Y-%m-%d")


# Drop today's unfinished bar: every series ends at the last complete UTC day.
LAST_DAY = "2026-10-28"
series = {}
for t, v in K.items():
    pts = [(day(ts), c) for ts, c in zip(v["t"], v["c"]) if day(ts) <= LAST_DAY]
    series[t] = dict(pts)
DATES = sorted(series["BTC"])
BTC = series["BTC"]


def sma(xs, n):
    return [None if i < n - 1 or any(x is None for x in xs[i - n + 1:i + 1]) else sum(xs[i - n + 1:i + 1]) / n for i in range(len(xs))]


def ema(xs, n):
    out, prev, a = [], None, 2 / (n + 1)
    for x in xs:
        if x is None:
            out.append(None); prev = None; continue
        prev = x if prev is None else prev + a * (x - prev)
        out.append(prev)
    return out


# ---------- 1. Relative rotation (vs BTC) ----------
RS_EMA, RATIO_SMA, MOM_LAG, TAIL_N, TAIL_STEP = 5, 30, 5, 6, 3
rrg = []
for c in COINS:
    t = c["tick"]
    if t == "BTC" or t not in series:
        continue
    s = series[t]
    rs = [s[d] / BTC[d] if d in s and s[d] > 0 else None for d in DATES]
    rse = ema(rs, RS_EMA)
    base = sma(rse, RATIO_SMA)
    x = [None if a is None or b is None else 100 * a / b for a, b in zip(rse, base)]
    y = [None if i < MOM_LAG or x[i] is None or x[i - MOM_LAG] is None else 100 * x[i] / x[i - MOM_LAG] for i in range(len(x))]
    idx = [len(DATES) - 1 - k * TAIL_STEP for k in range(TAIL_N)][::-1]
    tail = [(DATES[i], round(x[i], 2), round(y[i], 2)) for i in idx if x[i] is not None and y[i] is not None]
    if len(tail) < TAIL_N:
        continue
    xe, ye = tail[-1][1], tail[-1][2]
    quad = "leading" if xe >= 100 and ye >= 100 else "weakening" if xe >= 100 else "lagging" if ye < 100 else "improving"
    rrg.append(dict(tick=t, name=c["name"], rank=c["rank"], tier=c["tier"], quad=quad,
                    tail=[{"d": d, "x": a, "y": b} for d, a, b in tail],
                    ret30_vs_btc=round(((s[DATES[-1]] / s[DATES[-31]]) / (BTC[DATES[-1]] / BTC[DATES[-31]]) - 1) * 100, 2) if DATES[-31] in s else None))
no_rrg = [c["tick"] for c in COINS if c["tick"] != "BTC" and c["tick"] not in {r["tick"] for r in rrg}]
json.dump(dict(asof=LAST_DAY, benchmark="BTC",
               method=dict(rs="coin close / BTC close (Binance USDT 1d)", smoothing=f"EMA({RS_EMA}) of RS",
                           x=f"RS-Ratio = 100 x EMA-RS / SMA(EMA-RS, {RATIO_SMA})",
                           y=f"RS-Momentum = 100 x RS-Ratio / RS-Ratio {MOM_LAG} days ago",
                           tail=f"{TAIL_N} points every {TAIL_STEP} days"),
               coins=rrg, not_plotted=no_rrg), open("data/view_rrg.json", "w"), ensure_ascii=False, indent=0)


# ---------- 2. Heatmap (squarified treemap, area ~ sqrt(market cap), grouped by tier) ----------
def worst(row, w):
    s = sum(row)
    return max(max(w * w * r / (s * s), (s * s) / (w * w * r)) for r in row)


def squarify(vals, x, y, w, h):
    """vals: list of (key, area) already scaled to w*h. Returns {key: (x, y, w, h)}."""
    out, items = {}, sorted(vals, key=lambda kv: -kv[1])
    while items:
        short = min(w, h)
        row = [items[0]]
        i = 1
        while i < len(items) and worst([a for _, a in row + [items[i]]], short) <= worst([a for _, a in row], short):
            row.append(items[i]); i += 1
        items = items[i:]
        s = sum(a for _, a in row)
        if w >= h:  # lay the row as a column on the left
            cw = s / h; cy = y
            for k, a in row:
                ch = a / cw; out[k] = (x, cy, cw, ch); cy += ch
            x += cw; w -= cw
        else:  # lay the row along the top
            rh = s / w; cx = x
            for k, a in row:
                cw2 = a / rh; out[k] = (cx, y, cw2, rh); cx += cw2
            y += rh; h -= rh
    return out


HM_W, HM_H, GAP = 1184, 600, 6
weights = {c["tick"]: math.sqrt(c["mcap"]) for c in COINS}
tier_w = {t: sum(weights[c["tick"]] for c in COINS if c["tier"] == t) for t in TIER_ORDER}
total = sum(tier_w.values())
tier_rects = squarify([(t, tier_w[t] / total * HM_W * HM_H) for t in TIER_ORDER], 0, 0, HM_W, HM_H)
cells = []
btc = next(c for c in COINS if c["tick"] == "BTC")
for t in TIER_ORDER:
    tx, ty, tw, th = tier_rects[t]
    ix, iy, iw, ih = tx + GAP / 2, ty + GAP / 2 + 18, tw - GAP, th - GAP - 18  # 18px tier caption band
    members = [c for c in COINS if c["tier"] == t]
    s = sum(weights[c["tick"]] for c in members)
    rects = squarify([(c["tick"], weights[c["tick"]] / s * iw * ih) for c in members], ix, iy, iw, ih)
    for c in members:
        rx, ry, rw, rh = rects[c["tick"]]
        rel = {}
        for p, key in (("1d", "chg1d"), ("7d", "chg7d"), ("30d", "chg30d"), ("90d", "chg90d")):
            v, b = c[key], btc[key]
            rel[p] = None if v is None or b is None else round(((1 + v / 100) / (1 + b / 100) - 1) * 100, 2)
        cells.append(dict(tick=c["tick"], name=c["name"], rank=c["rank"], tier=t, mcap_b=round(c["mcap"] / 1e9, 2),
                          x=round(rx, 1), y=round(ry, 1), w=round(rw, 1), h=round(rh, 1),
                          chg={p: (None if c[k] is None else round(c[k], 2)) for p, k in (("1d", "chg1d"), ("7d", "chg7d"), ("30d", "chg30d"), ("90d", "chg90d"))},
                          vs_btc=rel))
json.dump(dict(asof=U["asof"], source=U["source"], area="sqrt(market cap)", box=dict(w=HM_W, h=HM_H),
               btc_chg={p: round(btc[k], 2) for p, k in (("1d", "chg1d"), ("7d", "chg7d"), ("30d", "chg30d"), ("90d", "chg90d"))},
               tiers={t: dict(x=round(r[0], 1), y=round(r[1], 1), w=round(r[2], 1), h=round(r[3], 1), n=sum(1 for c in COINS if c["tier"] == t)) for t, r in tier_rects.items()},
               cells=cells), open("data/view_heatmap.json", "w"), ensure_ascii=False, indent=0)


# ---------- 3. Rank flow (CoinMarketCap weekly snapshots) ----------
snaps = []
for p in sorted(glob.glob("data/cmc/cmc_*.json")):
    d = p.split("_")[1][:8]
    raw = json.load(open(p))
    snaps.append((f"{d[:4]}-{d[4:6]}-{d[6:]}", raw))
weeks = [d for d, _ in snaps]


def eligible(c):
    tags = set(c.get("tags") or [])
    return not ({"stablecoin", "tokenized-gold"} & tags) and c["sym"] not in EXCL


paths = {}
for d, raw in snaps:
    for c in raw:
        if not eligible(c):
            continue
        paths.setdefault(c["slug"], {"sym": c["sym"], "name": c["name"], "r": {}})["r"][d] = c["rank"]


def tier_of(r):
    return None if r is None or r > 125 else "1-10" if r <= 10 else "11-50" if r <= 50 else "51-100" if r <= 100 else "101-125"


flow = []
for slug, v in paths.items():
    rs = [v["r"].get(w) for w in weeks]
    if not any(r is not None and r <= 125 for r in rs):
        continue
    first, last = rs[0], rs[-1]
    flow.append(dict(slug=slug, sym=v["sym"], name=v["name"], ranks=rs, first=first, last=last,
                     change=None if first is None or last is None else first - last,
                     tier_first=tier_of(first), tier_last=tier_of(last)))
moves = {}
for f in flow:
    key = f"{f['tier_first'] or 'out'}>{f['tier_last'] or 'out'}"
    moves[key] = moves.get(key, 0) + 1
ranked = [f for f in flow if f["change"] is not None]
json.dump(dict(source="CoinMarketCap historical snapshots (weekly, Sunday)", weeks=weeks,
               note="raw CMC rank numbers; stablecoins, tokenized gold and PI/JST/FLR/NEXO/GNO/FF/SUN/GT left out but not re-ranked",
               coins=flow, tier_moves=moves,
               climbers=[f["sym"] for f in sorted(ranked, key=lambda f: -f["change"])[:8]],
               fallers=[f["sym"] for f in sorted(ranked, key=lambda f: f["change"])[:8]],
               entered=[f["sym"] for f in flow if f["tier_first"] is None and f["tier_last"] is not None],
               exited=[f["sym"] for f in flow if f["tier_first"] is not None and f["tier_last"] is None]),
          open("data/view_rankflow.json", "w"), ensure_ascii=False, indent=0)


# ---------- 4. Breadth: share of coins beating BTC over a rolling 30 days ----------
WIN = 30
tier_of_tick = {c["tick"]: c["tier"] for c in COINS}
out_days = DATES[-120:]
rows = []
for d in out_days:
    i = DATES.index(d)
    if i < WIN:
        continue
    d0 = DATES[i - WIN]
    b = BTC[d] / BTC[d0]
    cnt = {t: [0, 0] for t in TIER_ORDER + ["all"]}
    for t, s in series.items():
        if t == "BTC" or t not in tier_of_tick or d not in s or d0 not in s:
            continue
        beat = (s[d] / s[d0]) > b
        for key in (tier_of_tick[t], "all"):
            cnt[key][0] += beat; cnt[key][1] += 1
    rows.append(dict(d=d, btc=round(BTC[d], 2), **{k: (round(100 * a / n, 1) if n else None) for k, (a, n) in cnt.items()},
                     n={k: n for k, (a, n) in cnt.items()}))
json.dump(dict(asof=LAST_DAY, window_days=WIN, metric="% of coins whose 30-day return beats BTC's 30-day return (Binance USDT 1d)",
               coverage={t: f"{sum(1 for c in COINS if c['tier'] == t and c['tick'] in series and c['tick'] != 'BTC')}/{sum(1 for c in COINS if c['tier'] == t and c['tick'] != 'BTC')}" for t in TIER_ORDER},
               rows=rows), open("data/view_breadth.json", "w"), ensure_ascii=False, indent=0)

print("rrg", len(rrg), "not plotted", len(no_rrg))
print("heatmap cells", len(cells), "tiers", {t: (round(r[2]), round(r[3])) for t, r in tier_rects.items()})
print("rankflow coins", len(flow), "weeks", len(weeks), "moves", moves)
print("breadth days", len(rows), "last", rows[-1])
