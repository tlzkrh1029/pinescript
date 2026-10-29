import json, time, urllib.request, urllib.parse
K = json.load(open("data/klines_1d.json"))
out = {}
for tick, v in K.items():
    url = "https://data-api.binance.vision/api/v3/klines?" + urllib.parse.urlencode({"symbol": v["pair"], "interval": "5m", "limit": 300})
    for a in range(4):
        try:
            k = json.load(urllib.request.urlopen(url, timeout=30)); break
        except Exception:
            time.sleep(2 ** a)
    else:
        print("fail", tick); continue
    out[tick] = {"pair": v["pair"], "t": [r[0] for r in k], "c": [float(r[4]) for r in k], "ct": [r[6] for r in k]}
    time.sleep(0.12)
json.dump(out, open("data/klines_5m.json", "w"))
import datetime
b = out["BTC"]
f = lambda ms: datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
print(len(out), "coins; BTC", f(b["t"][0]), "->", f(b["t"][-1]), "bars", len(b["t"]), "last close_time", f(b["ct"][-1]))
print("short:", {k: len(v["t"]) for k, v in out.items() if len(v["t"]) < 300})
