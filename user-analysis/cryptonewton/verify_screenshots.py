"""Recompute the Razor Harmonics / Razor Divergence dashboard values from Binance klines.

The screenshots in images/ show values printed by a closed-source TradingView indicator.
This script downloads Binance USD-M perpetual 4h klines from the public archive
(data.binance.vision), rebuilds each trade plan from the pivot bars identified in README.md,
and prints displayed vs. recomputed values side by side.

Usage: python3 verify_screenshots.py [--data DIR]
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import tempfile
import urllib.request
import zipfile

ARCHIVE = "https://data.binance.vision/data/futures/um"
START = dt.date(2026, 7, 1)
# The archive publishes a day's file after the day closes.
END = dt.date.today() - dt.timedelta(days=1)
START_MS_OCT21 = 1792540800000  # 2026-10-21 00:00 UTC


def fetch_zip(url):
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            blob = r.read()
    except Exception:
        return []
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        text = z.read(z.namelist()[0]).decode()
    rows = []
    for line in text.splitlines():
        if line and not line.startswith("open_time"):
            p = line.split(",")
            rows.append((int(p[0]), float(p[1]), float(p[2]), float(p[3]), float(p[4])))
    return rows


def load(symbol, data_dir):
    path = os.path.join(data_dir, f"{symbol}_4h.csv")
    if not os.path.exists(path):
        rows = {}
        month = START.replace(day=1)
        while month <= END:
            nxt = (month.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
            if nxt - dt.timedelta(days=1) <= END:
                for r in fetch_zip(f"{ARCHIVE}/monthly/klines/{symbol}/4h/{symbol}-4h-{month:%Y-%m}.zip"):
                    rows[r[0]] = r
            else:
                day = month
                while day <= END:
                    for r in fetch_zip(f"{ARCHIVE}/daily/klines/{symbol}/4h/{symbol}-4h-{day:%Y-%m-%d}.zip"):
                        rows[r[0]] = r
                    day += dt.timedelta(days=1)
            month = nxt
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            for k in sorted(rows):
                w.writerow(rows[k])
    bars = []
    with open(path) as f:
        for p in csv.reader(f):
            t = dt.datetime.fromtimestamp(int(p[0]) / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
            bars.append({"t": t, "o": float(p[1]), "h": float(p[2]), "l": float(p[3]), "c": float(p[4])})
    return bars


def atr_rma(bars, length=14):
    out, prev = [], None
    for i, b in enumerate(bars):
        tr = b["h"] - b["l"] if i == 0 else max(b["h"] - b["l"], abs(b["h"] - bars[i - 1]["c"]), abs(b["l"] - bars[i - 1]["c"]))
        prev = tr if prev is None else (prev * (length - 1) + tr) / length
        out.append(prev)
    return out


def idx(bars, t):
    return next(i for i, b in enumerate(bars) if b["t"] == t)


def fib_targets(d, a):
    return d + 0.382 * (a - d), d + 0.618 * (a - d), a


def show(label, shown, value):
    print(f"    {label:<10} shown {shown:<10} recomputed {value:.6f}")


# Full / Elite build: entry at the D extreme, SL = D - ATR14, TPs on the AD leg.
FULL = [
    # symbol, screenshot, pattern, {pivot: (bar time, price)}, shown entry, SL, TP1, TP2, TP3
    ("ETHFIUSDT", "1", "Cypher (long)",
     {"X": ("2026-10-02 16:00", 0.6717), "A": ("2026-10-05 08:00", 0.7770), "B": ("2026-10-06 00:00", 0.7195),
      "C": ("2026-10-06 12:00", 0.8010), "D": ("2026-10-07 12:00", 0.6991)},
     "0.6991", "0.6719", "0.7289", "0.7472", "0.7770"),
    ("POLUSDT", "3", "Butterfly / Deep Crab (long)",
     {"X": ("2026-09-23 12:00", 0.09825), "A": ("2026-09-27 20:00", 0.12548), "B": ("2026-10-02 16:00", 0.10376),
      "C": ("2026-10-05 08:00", 0.11177), "D": ("2026-10-15 00:00", 0.09054)},
     "0.09054", "0.08776", "0.10389", "0.11213", "0.12548"),
    ("LINKUSDT", "4", "Shark / Cypher (long)",
     {"X": ("2026-10-08 16:00", 12.079), "A": ("2026-10-10 12:00", 13.244), "B": ("2026-10-11 04:00", 12.829),
      "C": ("2026-10-12 04:00", 13.496), "D": ("2026-10-13 00:00", 12.249)},
     "12.249", "11.950", "12.629", "12.864", "13.244"),
    ("STXUSDT", "7", "Shark (long)",
     {"X": ("2026-09-25 04:00", 0.3073), "A": ("2026-09-26 08:00", 0.3549), "B": ("2026-09-26 20:00", 0.3314),
      "C": ("2026-09-27 04:00", 0.3596), "D": ("2026-09-29 00:00", 0.3029)},
     "0.3029", "0.2917", "0.3228", "0.3350", "0.3549"),
]

# Compact build: D = first touch of the PRZ near edge, entry = D + 0.1 * (C - D), SL = PRZ far edge.
COMPACT = [
    ("FETUSDT", "6", "Cypher (long)",
     {"X": 0.1671, "A": 0.2597, "B": 0.2128, "C": 0.2723, "D": 0.1925},
     lambda p: p["C"] - 0.786 * 1.08 * (p["C"] - p["X"]),
     "0.2005", "0.1830", "0.2182", "0.2340", "0.2597"),
    ("ICPUSDT", "8", "Shark (long)",
     {"X": 2.898, "A": 3.553, "B": 3.165, "C": 3.607, "D": 2.938},
     lambda p: max(p["A"] - 1.13 * 1.08 * (p["A"] - p["X"]), p["C"] - 2.236 * 1.08 * (p["C"] - p["B"])),
     "3.005", "2.754", "3.173", "3.318", "3.553"),
    ("TWTUSDT", "11", "Shark (long)",
     {"X": 0.4884, "A": 0.6059, "B": 0.5551, "C": 0.6197, "D": 0.4940},
     lambda p: max(p["A"] - 1.13 * 1.08 * (p["A"] - p["X"]), p["C"] - 2.236 * 1.08 * (p["C"] - p["B"])),
     "0.5066", "0.4637", "0.5367", "0.5632", "0.6059"),
    ("FETUSDT", "10", "Crab (short)",
     {"X": 0.1707, "A": 0.1453, "B": 0.1607, "C": 0.1510, "D": 0.1844},
     lambda p: min(p["A"] + 1.618 * 1.08 * (p["X"] - p["A"]), p["C"] + 3.618 * 1.08 * (p["B"] - p["C"])),
     "0.1811", "0.1889", "0.1695", "0.1602", "0.1453"),
]


def check_full(data_dir):
    print("== Full / Elite build ==")
    for sym, shot, name, piv, *shown in FULL:
        bars = load(sym, data_dir)
        atr = atr_rma(bars)
        print(f"\n[{shot}.webp] {sym} {name}")
        for k, (t, price) in piv.items():
            b = bars[idx(bars, t)]
            field = "low" if abs(b["l"] - price) < 1e-12 else "high" if abs(b["h"] - price) < 1e-12 else "NO MATCH"
            print(f"    {k} {t} {price} = bar {field}")
        d_i = idx(bars, piv["D"][0])
        d, a = piv["D"][1], piv["A"][1]
        tp1, tp2, tp3 = fib_targets(d, a)
        show("ENTRY", shown[0], d)
        # The ATR is read 2-4 bars after D; which bar is not explained by the screenshots.
        decimals = len(shown[1].split(".")[1])
        sl = None
        for k in (2, 3, 4):
            value = d - atr[d_i + k]
            show(f"SL(D+{k})", shown[1], value)
            if sl is None and f"{value:.{decimals}f}" == shown[1]:
                sl = value
        sl = sl if sl is not None else d - atr[d_i + 3]
        show("TP1", shown[2], tp1)
        show("TP2", shown[3], tp2)
        show("TP3", shown[4], tp3)
        # Published NORMAL mode: wait for a close beyond the D bar's opposite extreme.
        trigger = bars[d_i]["h"]
        for j in range(d_i + 1, len(bars)):
            if bars[j]["c"] > trigger:
                fill = bars[j]["c"]
                print(f"    NORMAL fill {fill} at {bars[j]['t']} (D+{j - d_i}): risk x{(fill - sl) / (d - sl):.2f} vs. displayed plan, "
                      f"TP1 at {(tp1 - fill) / (fill - sl):+.2f}R from the fill")
                break


def check_compact():
    print("\n== Compact build ==")
    for sym, shot, name, p, far_edge, *shown in COMPACT:
        tp1, tp2, tp3 = fib_targets(p["D"], p["A"])
        print(f"\n[{shot}.webp] {sym} {name}")
        show("ENTRY", shown[0], p["D"] + 0.1 * (p["C"] - p["D"]))
        show("SL", shown[1], far_edge(p))
        show("TP1", shown[2], tp1)
        show("TP2", shown[3], tp2)
        show("TP3", shown[4], tp3)


def check_divergence(data_dir):
    print("\n== Razor Divergence (ADAUSDT, 5.webp) ==")
    bars = load("ADAUSDT", data_dir)
    atr = atr_rma(bars)
    l2 = idx(bars, "2026-10-20 08:00")
    sig = l2 + 5  # pivot low confirmed with right length 5
    if sig >= len(bars):
        # The archive lags by a day; fall back to the live API for the newest bars.
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol=ADAUSDT&interval=4h&startTime={START_MS_OCT21}&limit=6"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                live = json.loads(r.read())
            bars += [{"t": dt.datetime.fromtimestamp(k[0] / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),
                      "o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4])} for k in live]
            atr = atr_rma(bars)
        except Exception as e:
            print(f"    signal bar 2026-10-21 04:00 is not in the archive yet and the live API failed ({e})")
            return
    entry = bars[sig]["c"]
    sl = bars[sig]["l"] - 1.5 * atr[sig]
    r = entry - sl
    show("ENTRY", "0.2254", entry)
    show("SL", "0.2149", sl)
    for n, s in ((1, "0.2359"), (2, "0.2463"), (3, "0.2568")):
        show(f"TP{n}", s, entry + n * r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(tempfile.gettempdir(), "razor-klines"))
    args = ap.parse_args()
    os.makedirs(args.data, exist_ok=True)
    check_full(args.data)
    check_compact()
    check_divergence(args.data)


if __name__ == "__main__":
    main()
