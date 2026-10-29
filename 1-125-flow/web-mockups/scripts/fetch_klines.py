import json, time, urllib.parse, urllib.request
uni = json.load(open("data/universe.json"))["coins"]
ex = json.load(open("data/bn_exinfo.json"))
pairs = {x["baseAsset"]: x["symbol"] for x in ex["symbols"] if x["quoteAsset"] == "USDT" and x["status"] == "TRADING"}
ALIAS = {"GRAM": ["TON"], "POL": ["POL", "MATIC"], "BIANRENSHENG": ["币安人生"], "WLD": ["WLD"], "CC": [], "M": []}
out, missing = {}, []
for u in uni:
    cands = [u["tick"]] + ALIAS.get(u["tick"], [])
    pair = next((pairs[c] for c in cands if c in pairs), None)
    if not pair:
        missing.append(u["tick"]); continue
    url = f"https://data-api.binance.vision/api/v3/klines?symbol={urllib.parse.quote(pair)}&interval=1d&limit=200"
    for a in range(4):
        try:
            k = json.load(urllib.request.urlopen(url, timeout=30)); break
        except Exception as e:
            time.sleep(2 ** a)
    else:
        missing.append(u["tick"] + "(err)"); continue
    out[u["tick"]] = {"pair": pair, "t": [r[0] for r in k], "c": [float(r[4]) for r in k]}
    time.sleep(0.15)
json.dump(out, open("data/klines_1d.json", "w"))
print("got", len(out), "missing", len(missing), missing)
import datetime
bt = out["BTC"]["t"]
print("BTC range", datetime.datetime.utcfromtimestamp(bt[0]/1000).date(), "->", datetime.datetime.utcfromtimestamp(bt[-1]/1000).date(), len(bt))
short = {k: len(v["t"]) for k, v in out.items() if len(v["t"]) < 200}
print("shorter histories:", short)
