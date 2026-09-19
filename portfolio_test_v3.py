import json,os
p=json.loads(os.environ["PORTFOLIO_JSON"])
print("PORTFOLIO CONFIG OK")
for x in ("USDT","BTC","ETH","SOL"): print(f"{x}: {p['balances'][x]}")
for c in ("BTC","ETH","SOL"):
 plan=p["sell_plan"][c]; done=sum(1 for x in plan if x["completed"]); active=next((x for x in plan if not x["completed"]),None)
 print(f"{c}: completed={done}/{len(plan)}")
 if active: print(f"{c}: next_target={active['target']} USD amount={active['amount_try']} TL")
