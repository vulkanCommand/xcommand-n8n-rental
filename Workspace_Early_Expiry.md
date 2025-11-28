Step 1: SSH to server:

docker exec -it xcommand-n8n-rental-postgres-1 \
  psql -U xcmd -d xcmd_rental

  Step 2: See your latest workspaces (do this now inside psql)

You’re already at the xcmd_rental=# prompt, so run:

SELECT id, email, subdomain, expires_at
FROM workspaces
ORDER BY created_at DESC
LIMIT 5;

✅ Update expiry to 10 minutes 30 seconds from now
UPDATE workspaces
SET expires_at = NOW() AT TIME ZONE 'utc' + interval '10 minutes 30 seconds'
WHERE subdomain = 'u-e57641';


You should see:

UPDATE 1

✅ Verify
SELECT subdomain, expires_at
FROM workspaces
WHERE subdomain = 'u-e57641';


It should show a timestamp ~10m 30s in the future.

That’s it

Janitor will now:

detect that expiry

stop the container

wipe the volume

delete the DB row

make it disappear from ready.html

Exactly 10 minutes and 30 seconds from now.
