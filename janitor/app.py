import os, time, docker
from datetime import datetime, timezone

client = docker.from_env()

def parse_iso(s: str):
    if not s: return None
    s = s.rstrip("Z")
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except Exception:
        return None

def sub_from_container(name: str):
    # name like "n8n_u-322e55"
    if name.startswith("n8n_"):
        return name.split("n8n_",1)[1]
    return name

def volume_name_for(sub: str):
    return f"n8n_{sub}_data"

def stop_and_wipe(container):
    name = container.name
    lbls = container.labels or {}
    sub = lbls.get("com.xcommand.sub") or sub_from_container(name)
    vol = volume_name_for(sub)

    try:
        container.remove(force=True)
        print(f"[janitor] stopped {name}")
    except Exception as e:
        print(f"[janitor] stop failed {name}: {e}")

    try:
        v = client.volumes.get(vol)
        v.remove(force=True)
        print(f"[janitor] wiped volume {vol}")
    except Exception as e:
        print(f"[janitor] wipe failed {vol}: {e}")

def sweep_once(now_utc: datetime):
    total = 0
    with_sub = 0
    expired = 0
    for c in client.containers.list(all=True):  # scan all; filter in code
        total += 1
        lbls = c.labels or {}
        sub = lbls.get("com.xcommand.sub")
        if not sub:
            continue
        with_sub += 1
        exp = parse_iso(lbls.get("com.xcommand.expires_at",""))
        if exp and exp <= now_utc:
            expired += 1
            stop_and_wipe(c)
    print(f"[janitor] scan: total={total}, with_sub={with_sub}, expired_cleaned={expired}")

if __name__ == "__main__":
    interval = int(os.getenv("JANITOR_INTERVAL_SECONDS","60"))
    print(f"[janitor] started, interval={interval}s")
    while True:
        try:
            sweep_once(datetime.now(timezone.utc))
        except Exception as e:
            print(f"[janitor] sweep error: {e}")
        time.sleep(interval)
