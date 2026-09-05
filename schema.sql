-- Cross-device sync for 52 Weeks Behind the Bar.
-- Paste this into the Supabase SQL editor and run it once.
--
-- THE SECURITY MODEL, BECAUSE IT IS THE WHOLE POINT
-- --------------------------------------------------
-- The page is served from GitHub Pages and is public, so the publishable key
-- ships inside docs/index.html where anyone can read it. The schema therefore
-- assumes the key is public knowledge and gives it as little as possible.
--
-- `anon` gets NO privileges on the table at all. If it could select from the
-- table, row-level security would not save us: a policy has no view of the
-- client's WHERE clause, so `USING (true)` would let anyone list every row and
-- harvest every sync code. Instead the table is reachable only through two
-- SECURITY DEFINER functions, and `anon` may execute those and nothing else.
-- Knowing a code is then the only way to touch the row it names, and there is
-- no call that enumerates codes.
--
-- What this is NOT: a code is a bearer token, so anyone holding one can read
-- and write that person's notes. It is convenience-grade, not secret-grade.
-- Do not put anything in a note you would mind a friend reading.

create table if not exists public.shelves (
  code        text primary key,
  payload     jsonb       not null default '{}'::jsonb,
  updated_at  timestamptz not null default now()
);

-- Belt and braces. There are no policies, so even if a grant were added by
-- accident, RLS would still refuse direct access.
alter table public.shelves enable row level security;
revoke all on table public.shelves from anon, authenticated;

-- Read one row by its code. Returns {} for an unknown code rather than an
-- error, so a first sync from a new device is not a failure case.
create or replace function public.pull(p_code text)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare v jsonb;
begin
  -- Short codes would be worth brute-forcing. The client generates 12 chars
  -- of a 30-symbol alphabet, about 59 bits, which is not guessable over a
  -- network. Anything much shorter would be.
  if p_code is null or length(p_code) < 12 then
    raise exception 'invalid code';
  end if;
  select payload into v from shelves where code = p_code;
  return coalesce(v, '{}'::jsonb);
end;
$$;

-- Upsert one row. The client merges before calling this, so last write wins
-- only between two syncs that raced; ordinary use converges.
create or replace function public.push(p_code text, p_payload jsonb)
returns timestamptz
language plpgsql
security definer
set search_path = public
as $$
declare t timestamptz;
begin
  if p_code is null or length(p_code) < 12 then
    raise exception 'invalid code';
  end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
    raise exception 'payload must be an object';
  end if;
  -- 52 drinks of notes plus 57 bottles is a few KB. A cap stops the table
  -- being used as free storage by anyone who reads the key out of the page.
  if pg_column_size(p_payload) > 262144 then
    raise exception 'payload too large';
  end if;
  insert into shelves (code, payload, updated_at)
  values (p_code, p_payload, now())
  on conflict (code) do update
    set payload = excluded.payload, updated_at = now()
  returning updated_at into t;
  return t;
end;
$$;

-- Touched by the scheduled keep-alive so the free-tier project does not pause
-- after 7 days of inactivity. Reads a real row so it counts as database work.
create or replace function public.ping()
returns text
language sql
security definer
set search_path = public
as $$
  select 'ok:' || (select count(*)::text from shelves);
$$;

grant execute on function public.pull(text)          to anon;
grant execute on function public.push(text, jsonb)   to anon;
grant execute on function public.ping()              to anon;
