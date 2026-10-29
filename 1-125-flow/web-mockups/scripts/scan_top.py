import json, sys, urllib.request
cols = ["base_currency", "description", "close", "market_cap_calc", "crypto_total_rank", "change", "Perf.W", "Perf.1M", "Perf.3M", "Perf.6M", "Perf.YTD", "24h_vol_cmc", "crypto_common_categories"]
body = {"columns": cols, "sort": {"sortBy": "crypto_total_rank", "sortOrder": "asc"}, "range": [0, 160],
        "filter": [{"left": "exchange", "operation": "equal", "right": "CRYPTO"}]}
req = urllib.request.Request("https://scanner.tradingview.com/coin/scan", data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json", "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/", "User-Agent": "Mozilla/5.0"})
d = json.load(urllib.request.urlopen(req, timeout=30))
print("total", d.get("totalCount"), "rows", len(d.get("data", [])))
rows = [dict(sym=x["s"], **dict(zip(cols, x["d"]))) for x in d["data"]]
json.dump(rows, open(sys.argv[1], "w"), ensure_ascii=False, indent=0)
for r in rows[:12] + rows[118:130]:
    print(r["crypto_total_rank"], r["sym"], r["base_currency"], r["description"], r["close"], round((r["market_cap_calc"] or 0)/1e9, 2), r["change"], r["Perf.W"], r["Perf.1M"], r["Perf.3M"], r["crypto_common_categories"])
