import os
import time
import psycopg2
from psycopg2.extras import DictCursor

DB_USER = os.getenv("POSTGRES_USER")
DB_PASS = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        cursor_factory=DictCursor,
    )

print("worker booted")

conn = None

while True:
    try:
        if conn is None or conn.closed:
            print("worker: opening new DB connection...")
            conn = get_conn()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  count(*) as total,
                  count(*) FILTER (WHERE status = 'active') as active,
                  count(*) FILTER (WHERE status = 'provisioning') as provisioning,
                  count(*) FILTER (WHERE status = 'deleted') as deleted
                FROM workspaces;
                """
            )
            row = cur.fetchone()
            print(
                f"worker: {row['total']} total workspaces "
                f"(active={row['active']}, provisioning={row['provisioning']}, deleted={row['deleted']})"
            )

        conn.commit()
    except Exception as e:
        print(f"worker error: {e}")
        # close bad connection and retry next loop
        try:
            if conn and not conn.closed:
                conn.close()
        except Exception:
            pass
        conn = None

    time.sleep(30)
