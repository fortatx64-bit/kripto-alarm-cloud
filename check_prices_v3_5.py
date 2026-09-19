import json, os, time, urllib.request
from pathlib import Path

STATE = Path("state_v3.json")
CFG = json.loads(os.environ["ALARM_CONFIG_JSON"])
PORTFOLIO = json.loads(os.environ["PORTFOLIO_JSON"])
TOPIC = os.environ["NTFY_TOPIC"]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":"KriptoAlarmCloud-v3.3"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read())

def validate(p):
    limits={"BTC":(1000,1000000),"ETH":(100,100000),"SOL":(1,10000)}
    for c,(lo,hi) in limits.items():
        if c not in p or not (lo <= float(p[c]) <= hi):
            raise ValueError(f"Invalid {c} price: {p.get(c)}")
    return {c:float(p[c]) for c in limits}

def prices():
    errors=[]
    try:
        d=get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd")
        p={"BTC":d["bitcoin"]["usd"],"ETH":d["ethereum"]["usd"],"SOL":d["solana"]["usd"]}
        print("PRICE SOURCE: CoinGecko")
        return validate(p)
    except Exception as e:
        errors.append("CoinGecko="+repr(e))
    try:
        p={c:float(get(f"https://api.coinbase.com/v2/prices/{c}-USD/spot")["data"]["amount"]) for c in ("BTC","ETH","SOL")}
        print("PRICE SOURCE: Coinbase fallback")
        return validate(p)
    except Exception as e:
        errors.append("Coinbase="+repr(e))
        raise RuntimeError(" | ".join(errors))

def send(title, body, urgent=False):
    req=urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}", data=body.encode(), method="POST",
        headers={"Title":title,"Priority":"5" if urgent else "3",
                 "Tags":"rotating_light,warning" if urgent else "white_check_mark"})
    with urllib.request.urlopen(req,timeout=12) as r:r.read()

def load_state():
    if not STATE.exists(): return {"levels":{},"health":{"failures":0,"alerted":False}}
    d=json.loads(STATE.read_text())
    # migrate old flat v3 state automatically
    if "levels" not in d:
        old={k:v for k,v in d.items() if ":" in k}
        d={"levels":old,"health":{"failures":0,"alerted":False}}
    d.setdefault("health",{"failures":0,"alerted":False})
    return d

def zone(side,p,t):
    if (side=="buy" and p<=t) or (side=="sell" and p>=t): return "trigger",3
    dist=((p-t)/t*100) if side=="buy" else ((t-p)/t*100)
    if dist<=CFG["critical_pct"]: return "critical",2
    if dist<=CFG["approach_pct"]: return "near",1
    return "none",0

def main():
    s=load_state(); levels=s["levels"]; health=s["health"]
    try:
        p=prices()
        had_problem=health.get("alerted",False)
        health["failures"]=0
        health["last_ok_epoch"]=int(time.time())
        health["last_error"]=""
        if had_problem:
            send("KRIPTO ALARM SISTEM DUZELDI",
                 "Fiyat kaynaklari yeniden calisiyor. Alarm sistemi normale dondu.",False)
        health["alerted"]=False
    except Exception as e:
        health["failures"]=int(health.get("failures",0))+1
        health["last_error"]=str(e)[:500]
        health["last_error_epoch"]=int(time.time())
        print("PRICE ERROR:",repr(e))
        if health["failures"]>=3 and not health.get("alerted",False):
            send("KRIPTO ALARM SISTEM UYARISI",
                 f"Arka arkaya {health['failures']} fiyat kontrolu basarisiz. Fiyat alarmi gecici olarak guvenilir degil.",True)
            health["alerted"]=True
        STATE.write_text(json.dumps(s,indent=2,sort_keys=True)+"\n")
        print("HEALTH FAILURES:",health["failures"])
        return

    ranks={"none":0,"near":1,"critical":2,"trigger":3,"completed":99}
    n=0
    for coin,cfg in CFG["coins"].items():
        px=p[coin]; print(f"{coin}: {px:.2f} USD")
        for t in cfg["buy"]:
            k=f"{coin}:buy:{t}"; st,r=zone("buy",px,float(t))
            if r>ranks.get(levels.get(k,"none"),0):
                lab={"near":"ALIM YAKLASIYOR","critical":"ALIM KRITIK","trigger":"ALIM TETIKLENDI"}[st]
                send(f"{coin} {lab}",f"Fiyat: {px:.2f} USD | Hedef: {t} USD",st!="near"); n+=1
            levels[k]=st
        for x in cfg["sell"]:
            t=float(x["target"]); k=f"{coin}:sell:{t:g}"
            if x.get("completed"):
                levels[k]="completed"; print("SKIP COMPLETED:",coin,"sell",f"{t:g}"); continue
            st,r=zone("sell",px,t)
            if r>ranks.get(levels.get(k,"none"),0):
                lab={"near":"KAR ALMA YAKLASIYOR","critical":"KAR ALMA KRITIK","trigger":"KAR ALMA TETIKLENDI"}[st]
                plan=PORTFOLIO.get("sell_plan",{}).get(coin,[])
                idx=next((i for i,y in enumerate(plan) if float(y["target"])==t),None)
                amount=(plan[idx].get("amount_try") if idx is not None else x.get("amount_try"))
                completed=sum(1 for y in plan if y.get("completed"))
                nxt=next((y for y in plan if not y.get("completed") and float(y["target"])>t),None)
                body=f"Fiyat: {px:.2f} USD | Hedef: {t:g} USD | Planlanan satis: {amount} TL"
                if idx is not None:
                    body+=f" | Kademe: {idx+1}/{len(plan)} | Tamamlanan: {completed}/{len(plan)}"
                if nxt:
                    body+=f" | Sonraki hedef: {nxt['target']} USD"
                send(f"{coin} {lab}",body,st!="near"); n+=1
            levels[k]=st
    STATE.write_text(json.dumps(s,indent=2,sort_keys=True)+"\n")
    print("HEALTH: OK")
    print("DONE. New alerts:",n)

if __name__=="__main__": main()
