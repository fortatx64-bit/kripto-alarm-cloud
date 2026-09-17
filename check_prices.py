import os, json, urllib.request, time

TOPIC=os.environ["NTFY_TOPIC"]
STATE_FILE="state.json"

LEVELS={
 "BTCUSDT":{"name":"BTC","buy":[73000,70000],"sell":[79000,82000,86000]},
 "ETHUSDT":{"name":"ETH","buy":[2300,2150],"sell":[2550,2700,2900]},
 "SOLUSDT":{"name":"SOL","buy":[92,85],"sell":[105,115,125]}
}

def get_price(symbol):
    url=f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    req=urllib.request.Request(url,headers={"User-Agent":"KriptoAlarmCloudV2/1.0"})
    with urllib.request.urlopen(req,timeout=15) as r:
        return float(json.loads(r.read().decode())["price"])

def publish(title,message,priority,tags):
    payload=json.dumps({
        "topic":TOPIC,"title":title,"message":message,
        "priority":priority,"tags":tags
    },ensure_ascii=False).encode("utf-8")
    req=urllib.request.Request("https://ntfy.sh/",data=payload,
        headers={"Content-Type":"application/json; charset=utf-8"},method="POST")
    with urllib.request.urlopen(req,timeout=15) as r:
        r.read()

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

state=load_state()
newstate={}
events=[]

for symbol,c in LEVELS.items():
    p=get_price(symbol)
    print(c["name"],p)
    for side in ("buy","sell"):
        label="ALIM" if side=="buy" else "KÂR ALMA"
        for idx,target in enumerate(c[side]):
            key=f"{symbol}:{side}:{idx}"
            z=zone(side,p,float(target))
            newstate[key]=z
            previous=state.get(key,"none")
            # Only notify when entering a new/higher zone; no spam every 5 minutes.
            rank={"none":0,"near":1,"critical":2,"trigger":3}
            if rank[z] > rank.get(previous,0):
                if z=="near":
                    events.append((3,["bell"],f"{c['name']} {label} YAKLAŞIYOR",
                      f"Fiyat {fmt(p)} USD • Hedef {fmt(target)} USD • hedefe %2 içinde."))
                elif z=="critical":
                    events.append((5,["warning","rotating_light"],f"{c['name']} {label} KRİTİK",
                      f"Fiyat {fmt(p)} USD • Hedef {fmt(target)} USD • hedefe %0,5 içinde."))
                elif z=="trigger":
                    events.append((5,["rotating_light"],f"{c['name']} {label} TETİKLENDİ",
                      f"Fiyat {fmt(p)} USD • Hedef {fmt(target)} USD. Eşik gerçekleşti."))

# Send all newly entered zones.
for priority,tags,title,msg in events:
    publish(title,msg,priority,tags)
    print("SENT:",title,msg)

save_state(newstate)
