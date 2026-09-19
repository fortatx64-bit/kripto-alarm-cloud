import os, json, urllib.request, urllib.parse
TOPIC=os.environ["NTFY_TOPIC"]; STATE_FILE="state.json"
LEVELS={"BTC":{"buy":[73000,70000],"sell":[79000,82000,86000]},"ETH":{"buy":[2300,2150],"sell":[2550,2700,2900]},"SOL":{"buy":[92,85],"sell":[105,115,125]}}
COMPLETED={"BTC":{"sell":[79000]},"ETH":{"sell":[2550]},"SOL":{"sell":[105]}}
CG={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana"}; CB={"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD"}

def req(url):
    r=urllib.request.Request(url,headers={"User-Agent":"KriptoAlarmCloudV2.2/1.0","Accept":"application/json"})
    with urllib.request.urlopen(r,timeout=20) as x:return json.loads(x.read().decode())

def prices():
    try:
        ids=",".join(CG.values()); d=req("https://api.coingecko.com/api/v3/simple/price?ids="+ids+"&vs_currencies=usd")
        print("PRICE SOURCE: CoinGecko"); return {c:float(d[i]["usd"]) for c,i in CG.items()}
    except Exception as e: print("CoinGecko failed:",repr(e))
    out={c:float(req("https://api.coinbase.com/v2/prices/"+p+"/spot")["data"]["amount"]) for c,p in CB.items()}
    print("PRICE SOURCE: Coinbase fallback"); return out

def load():
    try:
        with open(STATE_FILE,encoding="utf-8") as f:return json.load(f)
    except:return {}
def save(s):
    with open(STATE_FILE,"w",encoding="utf-8") as f:json.dump(s,f,indent=2)
def zone(side,p,t):
    if side=="buy":
        if p<=t:return "trigger"
        d=(p-t)/t
    else:
        if p>=t:return "trigger"
        d=(t-p)/t
    return "critical" if d<=.005 else ("near" if d<=.02 else "none")
def send(title,msg,priority,tags):
    data=json.dumps({"topic":TOPIC,"title":title,"message":msg,"priority":priority,"tags":tags},ensure_ascii=False).encode()
    with urllib.request.urlopen(urllib.request.Request("https://ntfy.sh/",data=data,headers={"Content-Type":"application/json; charset=utf-8"},method="POST"),timeout=20) as r:r.read()

p=prices(); old=load(); new={}; events=[]; rank={"none":0,"near":1,"critical":2,"trigger":3}
for coin,cfg in LEVELS.items():
    print(f"{coin}: {p[coin]:.2f} USD")
    for side in ("buy","sell"):
        for i,t in enumerate(cfg[side]):
            k=f"{coin}:{side}:{i}"
            if t in COMPLETED.get(coin,{}).get(side,[]):
                new[k]="completed"; print("SKIP COMPLETED:",coin,side,t); continue
            z=zone(side,p[coin],float(t)); new[k]=z
            prev=old.get(k,"none"); prev_rank=99 if prev=="completed" else rank.get(prev,0)
            if rank[z]>prev_rank:
                label="ALIM" if side=="buy" else "KÂR ALMA"
                if z=="near": events.append((3,["bell"],f"{coin} {label} YAKLAŞIYOR",f"Fiyat {p[coin]:.2f} USD • Hedef {t} USD • hedefe %2 içinde."))
                elif z=="critical": events.append((5,["warning","rotating_light"],f"{coin} {label} KRİTİK",f"Fiyat {p[coin]:.2f} USD • Hedef {t} USD • hedefe %0,5 içinde."))
                elif z=="trigger": events.append((5,["rotating_light"],f"{coin} {label} TETİKLENDİ",f"Fiyat {p[coin]:.2f} USD • Hedef {t} USD. Eşik gerçekleşti."))
for e in events: send(e[2],e[3],e[0],e[1]); print("NTFY SENT:",e[2])
save(new); print("DONE. New alerts:",len(events))
