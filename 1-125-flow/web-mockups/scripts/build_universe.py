import json
rows = json.load(open("data/tv_top.json"))
EXCL = {"PI", "JST", "FLR", "NEXO", "GNO", "FF", "SUN", "GT", "XAUT", "PAXG"}
uni = []
for r in rows:
    rk = r["crypto_total_rank"]
    if rk is None or rk > 125 or "stablecoins" in (r["crypto_common_categories"] or []) or r["base_currency"] in EXCL:
        continue
    tier = "1-10" if rk <= 10 else "11-50" if rk <= 50 else "51-100" if rk <= 100 else "101-125"
    uni.append(dict(rank=rk, tick=r["base_currency"], name=r["description"], sym=r["sym"], tier=tier, close=r["close"],
                    mcap=r["market_cap_calc"], chg1d=r["change"], chg7d=r["Perf.W"], chg30d=r["Perf.1M"], chg90d=r["Perf.3M"],
                    cats=r["crypto_common_categories"] or []))
uni.sort(key=lambda u: u["rank"])
json.dump({"asof": "2026-10-29", "source": "TradingView coin screener (CRYPTO: index)", "coins": uni}, open("data/universe.json", "w"), ensure_ascii=False, indent=0)
from collections import Counter
print(len(uni), Counter(u["tier"] for u in uni))
