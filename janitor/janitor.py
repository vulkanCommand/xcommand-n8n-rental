import os, time, docker
from datetime import datetime, timezone
import psycopg2

client = docker.from_env()


def parse_iso(s: str):
    """Parse ISO8601 expiry into a UTC-aware datetime, or None."""
    if not s:
        return None
    s = s.rstrip("Z")  # tolerate trailing Z
    try:
        # make it explicitly UTC
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def sub_from_container(name: str) -> str:
    # name like "n8n_u-322e55"
    if name.startswith("n8n_"):
        return name.split("n8n_", 1)[1]
    return name


def volume_name_for(sub: str) -> str:
    return f"n8n_{sub}_data"


# ---------- DB helpers ----------

def get_db_conn():
    """
    Create a Postgres connection using the same env vars as your API.
    Adjust defaults if your DB name/user differ.
    """
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "xcmd"),
        user=os.getenv("POSTGRES_USER", "xcmd"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )


def delete_workspace_row(sub: str):
    """
    Hard-delete the workspace row for this subdomain.
    'sub' here is your subdomain like 'u-322e55'.
    """
    try:
        with get_db_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM workspaces WHERE subdomain = %s", (sub,))
        print(f"[janitor] deleted DB row for subdomain {sub}")
    except Exception as e:
        print(f"[janitor] failed to delete DB row for {sub}: {e}")


# ------------------------------------


def stop_and_wipe(container):
    name = container.name
    labels = container.labels or {}

    # Prefer new labels, fall back to old + container name
    sub = (
        labels.get("xcommand.subdomain")
        or labels.get("com.xcommand.sub")
        or sub_from_container(name)
    )
    volume = volume_name_for(sub)

    try:
        container.remove(force=True)
        print(f"[janitor] stopped {name}")
    except Exception as e:
        print(f"[janitor] stop failed {name}: {e}")

    try:
        v = client.volumes.get(volume)
        v.remove(force=True)
        print(f"[janitor] wiped volume {volume}")
    except Exception as e:
        print(f"[janitor] wipe failed {volume}: {e}")

    # delete workspace row in Postgres
    delete_workspace_row(sub)


def sweep_once(now_utc: datetime):
    total = 0
    with_sub = 0
    expired = 0

    # scan all containers, filter by our label in code
    for c in client.containers.list(all=True):
        total += 1
        labels = c.labels or {}

        # Only touch xCommand workspaces
        workspace_flag = (
            labels.get("xcommand.workspace")
            or labels.get("com.xcommand.workspace")
        )
        if workspace_flag != "true":
            continue

        # New subdomain label first, then old
        sub = labels.get("xcommand.subdomain") or labels.get("com.xcommand.sub")
        if not sub:
            continue

        with_sub += 1

        # New expiry label first, then old
        exp_label = (
            labels.get("xcommand.expires_at")
            or labels.get("com.xcommand.expires_at")
            or ""
        )
        exp = parse_iso(exp_label)
        if exp and exp <= now_utc:
            expired += 1
            stop_and_wipe(c)

    print(
        f"[janitor] {now_utc.isoformat()} scan: "
        f"total={total}, with_sub={with_sub}, expired_cleaned={expired}"
    )


if __name__ == "__main__":
    interval = int(os.getenv("JANITOR_INTERVAL_SECONDS", "30"))
    print(f"[janitor] started; scanning every {interval}s")
    while True:
        try:
            sweep_once(datetime.now(timezone.utc))
        except Exception as e:
            print(f"[janitor] sweep error: {e}")
        time.sleep(interval)
