import os, json, urllib.request, urllib.parse

TOPIC=os.environ["NTFY_TOPIC"]
STATE_FILE="state.json"

LEVELS={
 "BTC":{"buy":[73000,70000],"sell":[79000,82000,86000]},
 "ETH":{"buy":[2300,2150],"sell":[2550,2700,2900]},
 "SOL":{"buy":[92,85],"sell":[105,115,125]}
}

CG_IDS={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana"}
CB_PAIRS={"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD"}

def request_json(url):
    req=urllib.request.Request(url,headers={
        "User-Agent":"KriptoAlarmCloudV2.1/1.0",
        "Accept":"application/json"
    })
    with urllib.request.urlopen(req,timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def coingecko_prices():
    ids=",".join(CG_IDS.values())
    url="https://api.coingecko.com/api/v3/simple/price?ids="+urllib.parse.quote(ids,safe=",")+"&vs_currencies=usd"
    d=request_json(url)
    return {coin:float(d[cgid]["usd"]) for coin,cgid in CG_IDS.items()}

def coinbase_price(coin):
    d=request_json("https://api.coinbase.com/v2/prices/"+CB_PAIRS[coin]+"/spot")
    return float(d["data"]["amount"])

def get_prices():
    # Primary: one CoinGecko request for all coins.
    try:
        p=coingecko_prices()
        print("PRICE SOURCE: CoinGecko")
        return p
    except Exception as e:
        print("CoinGecko failed:",repr(e))
    # Fallback: Coinbase, separately per asset.
    out={}
    for coin in LEVELS:
        out[coin]=coinbase_price(coin)
    print("PRICE SOURCE: Coinbase fallback")
    return out

def publish(title,message,priority,tags):
    payload=json.dumps({
        "topic":TOPIC,"title":title,"message":message,
        "priority":priority,"tags":tags
    },ensure_ascii=False).encode("utf-8")
    req=urllib.request.Request("https://ntfy.sh/",data=payload,
        headers={"Content-Type":"application/json; charset=utf-8"},method="POST")
    with urllib.request.urlopen(req,timeout=20) as r:r.read()

def load_state():
    try:
        with open(STATE_FILE,encoding="utf-8") as f:return json.load(f)
    except:return {}

def save_state(s):
    with open(STATE_FILE,"w",encoding="utf-8") as f:json.dump(s,f,indent=2)

def zone(side,p,target):
    if side=="buy":
        if p<=target:return "trigger"
        dist=(p-target)/target
    else:
        if p>=target:return "trigger"
        dist=(target-p)/target
    if 0<=dist<=0.005:return "critical"
    if 0.005<dist<=0.02:return "near"
    return "none"

def fmt(x):
    return f"{x:,.2f}".replace(",","X").replace(".",",").replace("X",".")

prices=get_prices()
state=load_state()
newstate={}
events=[]
rank={"none":0,"near":1,"critical":2,"trigger":3}

for coin,c in LEVELS.items():
    p=prices[coin]
    print(f"{coin}: {p:.2f} USD")
    for side in ("buy","sell"):
        label="ALIM" if side=="buy" else "KÂR ALMA"
        for idx,target in enumerate(c[side]):
            key=f"{coin}:{side}:{idx}"
            z=zone(side,p,float(target))
            newstate[key]=z
            previous=state.get(key,"none")
            if rank[z] > rank.get(previous,0):
                if z=="near":
                    events.append((3,["bell"],f"{coin} {label} YAKLAŞIYOR",
                        f"Fiyat {fmt(p)} USD • Hedef {fmt(target)} USD • hedefe %2 içinde."))
                elif z=="critical":
                    events.append((5,["warning","rotating_light"],f"{coin} {label} KRİTİK",
                        f"Fiyat {fmt(p)} USD • Hedef {fmt(target)} USD • hedefe %0,5 içinde."))
                elif z=="trigger":
                    events.append((5,["rotating_light"],f"{coin} {label} TETİKLENDİ",
                        f"Fiyat {fmt(p)} USD • Hedef {fmt(target)} USD. Eşik gerçekleşti."))

for priority,tags,title,msg in events:
    publish(title,msg,priority,tags)
    print("NTFY SENT:",title,"|",msg)

save_state(newstate)
print("DONE. New alerts:",len(events))
