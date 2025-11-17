-- users of your rental app (not n8n users)
create table if not exists app_users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  created_at timestamptz not null default now()
);

-- successful checkouts
create table if not exists payments (
  id bigserial primary key,
  stripe_session_id text unique not null,
  email text not null,
  plan text not null,              -- '1d' or '5d'
  amount_cents int not null,
  created_at timestamptz not null default now()
);

-- per-user n8n containers you provision
create table if not exists workspaces (
  id bigserial primary key,
  email text not null,
  plan text not null,
  subdomain text not null,         -- e.g. u-7f3a
  fqdn text not null,              -- e.g. u-7f3a.n8n.xcommand.cloud (localhost in dev)
  container_name text not null,
  volume_name text not null,
  status text not null default 'provisioning', -- provisioning|active|stopping|deleted
  expires_at timestamptz not null,
  export_notice_sent boolean not null default false,
  created_at timestamptz not null default now()
);

-- helpful indexes
create index if not exists idx_workspaces_email on workspaces(email);
create index if not exists idx_workspaces_expires_at on workspaces(expires_at);
