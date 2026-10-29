"""Precompute short-term (intraday) data for the second set of mockups.

Input: data/klines_5m.json (Binance spot USDT, 5m, last 300 bars), data/universe.json, data/view_heatmap.json (layout).
Outputs: data/short_live.json, data/short_accel.json, data/short_mood.json, data/short_heat.json
All "vs BTC" values: (1 + coin change) / (1 + BTC change) - 1, in %.
"""
import datetime, json

K = json.load(open("data/klines_5m.json"))
U = {c["tick"]: c for c in json.load(open("data/universe.json"))["coins"]}
HM = json.load(open("data/view_heatmap.json"))
KST = datetime.timezone(datetime.timedelta(hours=9))

# Drop the bar still in progress; every series ends on the same last complete bar.
BT = K["BTC"]["t"][:-1]
END = len(BT) - 1
S = {}
for t, v in K.items():
    m = dict(zip(v["t"], v["c"]))
    S[t] = [m.get(ts) for ts in BT]
TICKS = [t for t in S if t in U]
ASOF = datetime.datetime.fromtimestamp((BT[END] + 300000) / 1000, KST)  # close time of the last complete bar


def hm(i):
    return datetime.datetime.fromtimestamp(BT[i] / 1000 + 300, KST).strftime("%H:%M")


def chg(t, i0, i1):
    a, b = S[t][i0], S[t][i1]
    return None if a is None or b is None or a <= 0 else (b / a - 1) * 100


def vs(c, b):
    return None if c is None or b is None else ((1 + c / 100) / (1 + b / 100) - 1) * 100


def r2(x):
    return None if x is None else round(x, 2)


TIERS = ["1-10", "11-50", "51-100", "101-125"]
meta = dict(asof_kst=ASOF.strftime("%Y-%m-%d %H:%M"), timezone="Asia/Seoul (KST)", bar="5m",
            source="Binance spot USDT 5m klines", coverage=f"{len(TICKS) - 1} of 101 non-BTC coins (Binance-listed)",
            missing=[t for t in U if t not in S])

# ---------- 1. live board + line comparison ----------
ANCH = {"1h": 12, "4h": 48, "12h": 144, "24h": 288}
live = {}
for name, n in ANCH.items():
    i0 = END - n
    step = max(1, n // 48)
    idx = list(range(i0, END + 1, step))
    if idx[-1] != END:
        idx.append(END)
    b_now = chg("BTC", i0, END)
    rows = []
    for t in TICKS:
        c = chg(t, i0, END)
        if c is None:
            continue
        line = [r2(chg(t, i0, i)) for i in idx]
        rel = [r2(vs(chg(t, i0, i), chg("BTC", i0, i))) for i in idx]
        last1h = vs(chg(t, END - 12, END), chg("BTC", END - 12, END))
        rows.append(dict(tick=t, name=U[t]["name"], rank=U[t]["rank"], tier=U[t]["tier"], chg=r2(c), vs_btc=r2(vs(c, b_now)),
                         last1h_vs_btc=r2(last1h), line=line, rel=rel))
    rows.sort(key=lambda r: -(r["vs_btc"] if r["tick"] != "BTC" else -1e9))
    beat = sum(1 for r in rows if r["tick"] != "BTC" and r["vs_btc"] > 0)
    live[name] = dict(start_kst=hm(i0), times=[hm(i) for i in idx], btc_chg=r2(b_now),
                      beat=beat, n=sum(1 for r in rows if r["tick"] != "BTC"), rows=rows)
json.dump(dict(meta, anchors=live, note="line = % change since anchor; rel = that change vs BTC; last1h_vs_btc = last 60 minutes vs BTC"),
          open("data/short_live.json", "w"), ensure_ascii=False, indent=0)

# ---------- 2. acceleration scanner ----------
accel = {}
for name in ("4h", "12h", "24h"):
    n = ANCH[name]
    i0 = END - n
    pts = list(range(END - 24, END + 1, 3))  # last 2 hours, every 15 minutes
    rows = []
    for t in TICKS:
        if t == "BTC":
            continue
        tail = []
        for i in pts:
            x = vs(chg(t, i0, i), chg("BTC", i0, i))
            y = vs(chg(t, i - 12, i), chg("BTC", i - 12, i))
            if x is not None and y is not None:
                tail.append({"t": hm(i), "x": r2(x), "y": r2(y)})
        if len(tail) < len(pts):
            continue
        x, y = tail[-1]["x"], tail[-1]["y"]
        quad = "strong" if x >= 0 and y >= 0 else "fading" if x >= 0 else "new" if y >= 0 else "weak"
        rows.append(dict(tick=t, name=U[t]["name"], rank=U[t]["rank"], tier=U[t]["tier"], quad=quad, tail=tail))
    accel[name] = dict(start_kst=hm(i0), rows=rows,
                       counts={q: sum(1 for r in rows if r["quad"] == q) for q in ("strong", "new", "fading", "weak")})
json.dump(dict(meta, anchors=accel,
               axes=dict(x="change since anchor vs BTC (%)", y="last 60 minutes vs BTC (%)"),
               quads=dict(strong="x>=0,y>=0 계속 강함", new="x<0,y>=0 새로 강해짐", fading="x>=0,y<0 꺾임", weak="x<0,y<0 계속 약함"),
               tail="9 points, every 15 minutes over the last 2 hours"),
          open("data/short_accel.json", "w"), ensure_ascii=False, indent=0)

# ---------- 3. intraday mood (breadth) ----------
mood = {}
for name in ("12h", "24h"):
    n = ANCH[name]
    i0 = END - n
    idx = list(range(i0 + 3, END + 1, 3))  # every 15 minutes
    rows = []
    for i in idx:
        b = chg("BTC", i0, i)
        b1 = chg("BTC", max(i - 12, 0), i)
        cnt = {k: [0, 0] for k in TIERS + ["all"]}
        cnt1 = {k: [0, 0] for k in TIERS + ["all"]}
        for t in TICKS:
            if t == "BTC":
                continue
            c = chg(t, i0, i)
            c1 = chg(t, max(i - 12, 0), i)
            for key in (U[t]["tier"], "all"):
                if c is not None:
                    cnt[key][0] += c > b; cnt[key][1] += 1
                if c1 is not None:
                    cnt1[key][0] += c1 > b1; cnt1[key][1] += 1
        rows.append(dict(t=hm(i), btc=round(S["BTC"][i], 2),
                         since={k: (round(100 * a / m, 1) if m else None) for k, (a, m) in cnt.items()},
                         last1h={k: (round(100 * a / m, 1) if m else None) for k, (a, m) in cnt1.items()},
                         n={k: m for k, (a, m) in cnt.items()}))
    mood[name] = dict(start_kst=hm(i0), rows=rows)
json.dump(dict(meta, anchors=mood, metric=dict(since="% of coins whose change since the anchor beats BTC's",
                                               last1h="% of coins whose last-60-minute change beats BTC's")),
          open("data/short_mood.json", "w"), ensure_ascii=False, indent=0)

# ---------- 4. short-window heatmap (same layout as the first heatmap) ----------
WIN = {"15m": 3, "1h": 12, "4h": 48, "12h": 144, "24h": 288}
btc = {w: r2(chg("BTC", END - n, END)) for w, n in WIN.items()}
cells = []
for c in HM["cells"]:
    t = c["tick"]
    have = t in S
    ch = {w: (r2(chg(t, END - n, END)) if have else None) for w, n in WIN.items()}
    cells.append(dict(tick=t, name=c["name"], rank=c["rank"], tier=c["tier"], mcap_b=c["mcap_b"],
                      x=c["x"], y=c["y"], w=c["w"], h=c["h"], binance=have,
                      chg=ch, vs_btc={w: (r2(vs(ch[w], btc[w])) if have else None) for w in WIN}))
json.dump(dict(meta, area=HM["area"], box=HM["box"], tiers=HM["tiers"], btc_chg=btc, cells=cells),
          open("data/short_heat.json", "w"), ensure_ascii=False, indent=0)

print("asof", meta["asof_kst"], "KST; coins", len(TICKS), "missing", len(meta["missing"]))
for a in ANCH:
    L = live[a]
    print(a, "from", L["start_kst"], "BTC", L["btc_chg"], "beat", L["beat"], "/", L["n"], "top", [r["tick"] for r in L["rows"][:5]], "bottom", [r["tick"] for r in L["rows"][-5:]])
for a in accel:
    print("accel", a, accel[a]["counts"])
print("mood 24h last", mood["24h"]["rows"][-1]["since"], "last1h", mood["24h"]["rows"][-1]["last1h"])
print("btc by window", btc)
