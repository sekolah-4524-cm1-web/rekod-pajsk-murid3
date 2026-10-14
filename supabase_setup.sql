-- Jalankan sekali dalam Supabase Dashboard > SQL Editor.
-- App menggunakan SERVICE ROLE KEY hanya di server Streamlit Secrets.
-- Jangan letakkan service-role key dalam GitHub atau HTML/JavaScript.

create extension if not exists pgcrypto;

create table if not exists public.pajsk_records (
  id uuid primary key default gen_random_uuid(),
  verification_code text unique not null,
  student_name text not null,
  category text not null,
  program text not null,
  level text not null,
  event_date date,
  organizer text not null,
  issuer text not null,
  reference_no text not null,
  letter_date date not null,
  official_url text,
  notes text,
  file_name text not null,
  file_path text not null unique,
  file_type text not null check (file_type in ('application/pdf', 'image/jpeg', 'image/png')),
  file_size bigint not null check (file_size > 0 and file_size <= 10485760),
  status text not null default 'pending' check (status in ('pending', 'verified', 'fix')),
  uploaded_by text,
  created_at timestamptz not null default now(),
  verified_at timestamptz,
  verified_by text,
  verification_notes text
);

create index if not exists pajsk_records_student_name_idx
  on public.pajsk_records using btree (student_name);
create index if not exists pajsk_records_reference_no_idx
  on public.pajsk_records using btree (reference_no);
create index if not exists pajsk_records_status_idx
  on public.pajsk_records using btree (status);

-- Data tidak boleh diakses terus melalui anon/authenticated API.
-- Streamlit server baca/tulis menggunakan secret service-role key.
alter table public.pajsk_records enable row level security;
revoke all on table public.pajsk_records from anon, authenticated;
grant all on table public.pajsk_records to service_role;

-- Bucket private untuk lampiran surat (had saiz 10 MB).
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'pajsk-documents',
  'pajsk-documents',
  false,
  10485760,
  array['application/pdf', 'image/jpeg', 'image/png']
)
on conflict (id) do update set
  public = false,
  file_size_limit = 10485760,
  allowed_mime_types = array['application/pdf', 'image/jpeg', 'image/png'];

-- Bucket kekal private. Jangan tambah polisi awam kepada storage.objects.
