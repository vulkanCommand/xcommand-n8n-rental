### Step 1: SSH to server:

```bash
docker exec -it xcommand-n8n-rental-postgres-1 \
  psql -U xcmd -d xcmd_rental
```


### Step 2: See your latest workspaces (do this now inside psql)

You’re already at the `xcmd_rental=#` prompt, so run:

```sql
SELECT id, email, subdomain, expires_at
FROM workspaces
ORDER BY created_at DESC
LIMIT 5;
```

Look at that output and pick the **subdomain** of the workspace you want to use for your test, e.g. something like `u-6a1758` or `u-36a481`.


###Step 3: Inside psql, run:

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

# 🔥 That’s it

Janitor will now:

* detect that expiry
* stop the container
* wipe the volume
* delete the DB row
* make it disappear from ready.html

Exactly 10 minutes and 30 seconds from now.

