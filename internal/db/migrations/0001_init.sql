-- internal/db/migrations/0001_init.sql
create table if not exists licenses (
    id uuid primary key,
    license_key text unique not null,
    customer text not null,
    machine_id text not null,
    features jsonb not null default '{}',
    expires_at timestamptz not null,
    revoked boolean not null default false,
    last_seen_at timestamptz null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists idx_licenses_license_key on licenses(license_key);