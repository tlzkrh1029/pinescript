import re,json,sys
for day in sys.argv[1:]:
    h=open(f'data/cmc/cmc_{day}.html',encoding='utf-8').read()
    m=re.search(r'"initialState":"((?:[^"\\]|\\.)*)"',h)
    st=json.loads(json.loads('"'+m.group(1)+'"'))
    data=st["cryptocurrency"]["listingHistorical"]["data"]
    out=[]
    for c in data:
        q=c.get("quote"); usd=None
        if isinstance(q,list):
            for x in q:
                if x.get("name")=="USD": usd=x
        elif isinstance(q,dict): usd=q.get("USD")
        out.append(dict(rank=c["cmcRank"],sym=c["symbol"],name=c["name"],slug=c["slug"],price=(usd or {}).get("price"),mcap=(usd or {}).get("marketCap"),tags=c.get("tags",[])))
    json.dump(out,open(f'data/cmc/cmc_{day}.json','w'))
    print(day,len(out),data[0]["lastUpdated"])
