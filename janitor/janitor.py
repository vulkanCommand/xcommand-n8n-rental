import os, time, docker
from datetime import datetime, timezone
import psycopg2
import requests


client = docker.from_env()


# ---------- helpers ----------

def parse_iso(s: str):
    """Parse ISO8601 expiry into a UTC-aware datetime, or None."""
    if not s:
        return None
    s = s.rstrip("Z")  # tolerate trailing Z
    try:
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
    Create a Postgres connection using the same env vars as the API.
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

def get_workspace_info(sub: str):
    """
    Look up this workspace in Postgres by subdomain.
    Returns {"email": str, "backup_sent_at": datetime|None} or None.
    """
    try:
        with get_db_conn() as conn, conn.cursor() as cur:
            # TODO: if your column is not 'user_email', change it here
            cur.execute(
                "SELECT user_email, backup_sent_at FROM workspaces WHERE subdomain = %s",
                (sub,),
            )
            row = cur.fetchone()
            if not row:
                return None
            email, backup_sent_at = row
            return {"email": email, "backup_sent_at": backup_sent_at}
    except Exception as e:
        print(f"[janitor] failed to fetch workspace info for {sub}: {e}")
        return None


def mark_backup_sent(sub: str):
    """
    Mark backup_sent_at = now() for this workspace.
    """
    now = datetime.now(timezone.utc)
    try:
        with get_db_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE workspaces SET backup_sent_at = %s WHERE subdomain = %s",
                (now, sub),
            )
        print(f"[janitor] marked backup_sent_at for {sub} at {now.isoformat()}")
    except Exception as e:
        print(f"[janitor] failed to update backup_sent_at for {sub}: {e}")


def trigger_backup(sub: str, email: str, exp: datetime) -> bool:
    """
    Call the n8n backup webhook for this workspace.
    Returns True on success, False on failure.
    """
    # For now we use a single URL in env for testing.
    # Later you can switch to per-subdomain URL if needed.
    url = os.getenv("BACKUP_WEBHOOK_URL")
    if not url:
        print("[janitor] BACKUP_WEBHOOK_URL not set; skipping backup")
        return False

    payload = {
        "workspace_subdomain": sub,
        "user_email": email,
        "expires_at": exp.isoformat().replace("+00:00", "Z"),
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        try:
            data = resp.json()
        except Exception:
            data = None

        if resp.status_code == 200 and isinstance(data, dict) and data.get("ok") is True:
            print(f"[janitor] backup webhook OK for {sub}")
            return True

        print(
            f"[janitor] backup webhook failed for {sub}: "
            f"status={resp.status_code}, body={data}"
        )
    except Exception as e:
        print(f"[janitor] backup webhook error for {sub}: {e}")

    return False


# ---------- label logic ----------

def is_workspace(labels: dict, name: str) -> bool:
    """
    Decide if this container belongs to xCommand workspaces.
    1) Prefer explicit workspace flag
    2) Fallback to name pattern n8n_u-*
    """
    flag = labels.get("xcommand.workspace") or labels.get("com.xcommand.workspace")
    if flag == "true":
        return True

    if name.startswith("n8n_u-"):
        return True

    return False


def get_subdomain(labels: dict, name: str) -> str:
    """
    Get subdomain from labels, falling back to container name.
    """
    return (
        labels.get("xcommand.subdomain")
        or labels.get("com.xcommand.sub")
        or sub_from_container(name)
    )


def get_expiry(labels: dict):
    """
    Get expiry datetime from either new or old label keys.
    """
    label = (
        labels.get("xcommand.expires_at")
        or labels.get("com.xcommand.expires_at")
        or ""
    )
    return parse_iso(label)


# ---------- main cleanup ----------

def stop_and_wipe(container):
    name = container.name
    labels = container.labels or {}

    sub = get_subdomain(labels, name)
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

    for c in client.containers.list(all=True):
        total += 1
        labels = c.labels or {}
        name = c.name

        # Only touch our workspace containers
        if not is_workspace(labels, name):
            continue

        sub = get_subdomain(labels, name)
        if not sub:
            continue
        with_sub += 1

        exp = get_expiry(labels)
        if not exp:
            # no expiry set → skip
            continue

        # how many minutes until expiry
        delta_min = (exp - now_utc).total_seconds() / 60.0

        # EXPIRED: delete as before
        if delta_min <= 0:
            expired += 1
            stop_and_wipe(c)
            continue

        # PRE-EXPIRY WINDOW: 0 < delta_min <= 10
        if delta_min <= 10:
            info = get_workspace_info(sub)
            if not info:
                print(f"[janitor] no DB row for subdomain {sub}, skipping backup")
            else:
                email = info["email"]
                backup_sent_at = info["backup_sent_at"]

                if backup_sent_at is None:
                    print(
                        f"[janitor] triggering backup for {sub}, "
                        f"{delta_min:.1f} minutes left"
                    )
                    ok = trigger_backup(sub, email, exp)
                    if ok:
                        mark_backup_sent(sub)

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
