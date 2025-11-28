Got you — and this is easy because your whole system is now clean and predictable.

You essentially have two ways to create a **10-minute 30-second workspace**:

---

# ✅ **Method 1 — Create a normal workspace (1-day plan) and then manually shorten its expiry**

This is the safest and the way you should test.

### Step 1: Create it normally

Go to your app → pay/ready.html → generate a fresh workspace like usual.

Let’s say it creates:

```
subdomain = u-abc123
```

### Step 2: Update its expiry to 10 minutes 30 seconds from now

SSH to server:

```bash
docker exec -it xcommand-n8n-rental-postgres-1 \
  psql -U xcmd -d xcmd_rental
```

Inside psql, run:

```sql
UPDATE workspaces
SET expires_at = NOW() AT TIME ZONE 'utc' + interval '10 minutes 30 seconds'
WHERE subdomain = 'u-abc123';
```

Check:

```sql
SELECT subdomain, expires_at FROM workspaces WHERE subdomain = 'u-abc123';
```

### Step 3: Done

Janitor will kill it exactly **10:30** minutes later.

---

# ✅ **Method 2 — Create the workspace directly with custom expiration (fastest)**

If you want to skip payment flow entirely, create a row manually + create container manually.

### Step A: Insert row

```sql
INSERT INTO workspaces (email, plan, subdomain, fqdn, container_name, volume_name, status, expires_at)
VALUES (
  'test@n8n.com',
  'test',
  'u-test10min',
  'https://u-test10min.xcommand.cloud',
  'n8n_u-test10min',
  'n8n_u-test10min_data',
  'active',
  NOW() AT TIME ZONE 'utc' + interval '10 minutes 30 seconds'
);
```

### Step B: Create the docker container

```bash
docker run -d \
  --name n8n_u-test10min \
  -p 0:5678 \
  -v n8n_u-test10min_data:/home/node/.n8n \
  --label xcommand.workspace=true \
  --label xcommand.subdomain=u-test10min \
  --label xcommand.expires_at="$(date -u -d '+10 minutes 30 seconds' +%Y-%m-%dT%H:%M:%S%z)" \
  n8nio/n8n:latest
```

### Step C: Visit

```
https://u-test10min.xcommand.cloud
```

It will die automatically after 10:30 minutes.

---

# ⭐ RECOMMENDED FOR YOU

Use **Method 1** — it’s clean, uses your actual workflow, and guarantees the subdomain + labels are correct.

Just tell me the new subdomain **after you create the workspace**, and I’ll generate the exact SQL for you to paste.

If you want, I can even build a `/workspaces/create-test` API endpoint for development that accepts:

```
?minutes=10&seconds=30
```

and auto-creates a short-lived workspace.


Perfect — now we can safely update the expiry for:

```
subdomain = 'u-e57641'
```

You’re already inside the Postgres prompt, so just run this:

---

# ✅ Update expiry to 10 minutes 30 seconds from now

```sql
UPDATE workspaces
SET expires_at = NOW() AT TIME ZONE 'utc' + interval '10 minutes 30 seconds'
WHERE subdomain = 'u-e57641';
```

You should see:

```
UPDATE 1
```

---

# ✅ Verify

```sql
SELECT subdomain, expires_at
FROM workspaces
WHERE subdomain = 'u-e57641';
```

It should show a timestamp ~10m 30s in the future.

---

# 🔥 That’s it

Janitor will now:

* detect that expiry
* stop the container
* wipe the volume
* delete the DB row
* make it disappear from ready.html

Exactly 10 minutes and 30 seconds from now.

If you want, I can also teach you how to:

* force janitor to scan every 5 seconds instead of 30
* or manually trigger janitor for testing
* or create a quick `/force-expire` API endpoint for development

Just tell me.
