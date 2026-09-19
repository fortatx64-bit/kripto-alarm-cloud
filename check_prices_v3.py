import json,os,time,urllib.request
from pathlib import Path
STATE=Path("state_v3.json")
CFG=json.loads(os.environ["ALARM_CONFIG_JSON"])
TOPIC=os.environ["NTFY_TOPIC"]
def get(url):
 r=urllib.request.Request(url,headers={"User-Agent":"KriptoAlarmCloud-v3"})
 with urllib.request.urlopen(r,timeout=12) as x:return json.loads(x.read())
def prices():
 try:
  d=get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd")
  print("PRICE SOURCE: CoinGecko")
  return {"BTC":float(d["bitcoin"]["usd"]),"ETH":float(d["ethereum"]["usd"]),"SOL":float(d["solana"]["usd"])}
 except Exception as e:
  print("CoinGecko failed:",repr(e)); print("PRICE SOURCE: Coinbase fallback")
  return {c:float(get(f"https://api.coinbase.com/v2/prices/{c}-USD/spot")["data"]["amount"]) for c in ("BTC","ETH","SOL")}
def send(title,body,urgent=False):
 req=urllib.request.Request(f"https://ntfy.sh/{TOPIC}",data=body.encode(),method="POST",
  headers={"Title":title,"Priority":"5" if urgent else "3","Tags":"rotating_light,warning" if urgent else "bell"})
 with urllib.request.urlopen(req,timeout=12) as r:r.read()
def zone(side,p,t):
 if (side=="buy" and p<=t) or (side=="sell" and p>=t):return "trigger",3
 d=((p-t)/t*100) if side=="buy" else ((t-p)/t*100)
 if d<=CFG["critical_pct"]:return "critical",2
 if d<=CFG["approach_pct"]:return "near",1
 return "none",0
def main():
 old=json.loads(STATE.read_text()) if STATE.exists() else {}
 p=prices(); new=dict(old); n=0; ranks={"none":0,"near":1,"critical":2,"trigger":3,"completed":99}
 for coin,cfg in CFG["coins"].items():
  px=p[coin]; print(f"{coin}: {px:.2f} USD")
  for t in cfg["buy"]:
   k=f"{coin}:buy:{t}"; s,r=zone("buy",px,float(t))
   if r>ranks.get(old.get(k,"none"),0):
    lab={"near":"ALIM YAKLASIYOR","critical":"ALIM KRITIK","trigger":"ALIM TETIKLENDI"}[s]
    send(f"{coin} {lab}",f"Fiyat: {px:.2f} USD | Hedef: {t} USD",s!="near"); n+=1
   new[k]=s
  for x in cfg["sell"]:
   t=float(x["target"]); k=f"{coin}:sell:{t:g}"
   if x.get("completed"):
    new[k]="completed"; print("SKIP COMPLETED:",coin,"sell",f"{t:g}"); continue
   s,r=zone("sell",px,t)
   if r>ranks.get(old.get(k,"none"),0):
    lab={"near":"KAR ALMA YAKLASIYOR","critical":"KAR ALMA KRITIK","trigger":"KAR ALMA TETIKLENDI"}[s]
    send(f"{coin} {lab}",f"Fiyat: {px:.2f} USD | Hedef: {t:g} USD | Planlanan satis: {x['amount_try']} TL",s!="near"); n+=1
   new[k]=s
 STATE.write_text(json.dumps(new,indent=2,sort_keys=True)+"\n")
 print("DONE. New alerts:",n)
if __name__=="__main__":main()
