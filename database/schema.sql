create extension if not exists pgcrypto;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique not null,
  role text not null default 'user' check (role in ('user','admin','super_admin')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists user_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  display_name text,
  preferred_language text not null default 'en' check (preferred_language in ('en','gu')),
  created_at timestamptz not null default now()
);

create table if not exists job_scans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  source_type text not null check (source_type in ('text','image','url')),
  original_text text,
  risk_label text not null,
  result jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists scan_evidence (
  id uuid primary key default gen_random_uuid(),
  scan_id uuid not null references job_scans(id) on delete cascade,
  rule_id text not null,
  category text not null,
  matched_evidence text not null,
  severity text not null
);

create table if not exists scam_reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete set null,
  company_name text,
  recruiter_name text,
  job_title text,
  suspicious_message text not null,
  job_url text,
  description text,
  status text not null default 'pending' check (status in ('pending','under_investigation','reviewed')),
  created_at timestamptz not null default now()
);

create table if not exists companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  official_website text,
  careers_page text,
  verification_status text not null default 'Not Verified',
  evidence jsonb not null default '[]'::jsonb,
  last_checked timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists audit_logs (
  id uuid primary key default gen_random_uuid(),
  admin_id uuid not null references users(id),
  action text not null,
  record_type text,
  record_id uuid,
  created_at timestamptz not null default now()
);

create index if not exists idx_job_scans_user_created on job_scans(user_id, created_at desc);
create index if not exists idx_scam_reports_status on scam_reports(status);
alter table job_scans enable row level security;
alter table scam_reports enable row level security;
