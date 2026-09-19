import json, os, urllib.request
from pathlib import Path

STATE = Path("health_test_state.json")
MODE = os.environ.get("HEALTH_TEST_MODE", "fail")
TOPIC = os.environ["NTFY_TOPIC"]

def send(title, body, urgent=False):
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}",
        data=body.encode(),
        method="POST",
        headers={
            "Title": title,
            "Priority": "5" if urgent else "3",
            "Tags": "rotating_light,warning" if urgent else "white_check_mark"
        }
    )
    with urllib.request.urlopen(req, timeout=12) as r:
        r.read()

def load():
    if not STATE.exists():
        return {"failures": 0, "alerted": False}
    return json.loads(STATE.read_text())

s = load()

if MODE == "fail":
    s["failures"] = int(s.get("failures", 0)) + 1
    print("SIMULATED FAILURE:", s["failures"])
    if s["failures"] >= 3 and not s.get("alerted", False):
        send(
            "KRIPTO ALARM SISTEM UYARISI - TEST",
            "TEST: Arka arkaya 3 fiyat kontrolu basarisiz senaryosu dogrulandi.",
            True
        )
        s["alerted"] = True
        print("TEST ALERT SENT")
    else:
        print("NO TEST ALERT")
elif MODE == "recover":
    if s.get("alerted", False):
        send(
            "KRIPTO ALARM SISTEM DUZELDI - TEST",
            "TEST: Fiyat kaynaklari yeniden calisiyor senaryosu dogrulandi.",
            False
        )
        print("RECOVERY ALERT SENT")
    else:
        print("NO RECOVERY ALERT NEEDED")
    s = {"failures": 0, "alerted": False}
else:
    raise SystemExit("Unknown mode")

STATE.write_text(json.dumps(s, indent=2, sort_keys=True) + "\n")
print("TEST STATE:", s)
