-- Who is using this, and how much.
--
-- Run in the Supabase SQL editor. NOT from the site: anything the page can do,
-- anyone can do, because the publishable key ships inside docs/index.html. A
-- summary endpoint reachable with that key would expose every tester's activity
-- to anyone who found it. The dashboard is already the privileged, authenticated
-- interface for this, so use it rather than inventing a second one.
--
-- Sync codes are deliberately truncated below. You own the table and could read
-- them in full, but a full code is a working key to someone's notes, and there
-- is no reason for one to end up in a screenshot or a scrollback.

select
  coalesce(payload->>'profile', '(unnamed)')                      as initials,

  (select count(*)
     from jsonb_each(coalesce(payload->'entries', '{}'::jsonb)) e
    where e.value->>'made' = 'true')                              as drinks_made,

  (select count(*)
     from jsonb_each(coalesce(payload->'entries', '{}'::jsonb)) e
    where coalesce(e.value->>'note', '') <> '')                   as notes_written,

  (select count(*)
     from jsonb_each(coalesce(payload->'bottles', '{}'::jsonb)) b
    where b.value = 'true'::jsonb)                                as bottles_owned,

  updated_at                                                      as last_sync,
  date_trunc('minute', now() - updated_at)                        as idle_for,

  -- Enough to tell two rows apart, not enough to be a key.
  left(code, 4) || '...'                                          as code,
  pg_size_pretty(pg_column_size(payload)::bigint)                 as size

from shelves
order by updated_at desc;


-- One row in detail, if you want to see what a payload actually looks like.
-- Replace the code with a real one.
--
--   select jsonb_pretty(payload) from shelves where code = 'K7MP2XQR9TVB';


-- Housekeeping: rows left behind by synccheck.html, which writes a throwaway
-- row each run. They are harmless, but they clutter the summary above.
--
--   delete from shelves
--    where payload->>'profile' = 'TST'
--      and updated_at < now() - interval '1 day';


-- WHAT THIS CANNOT TELL YOU
--
-- `last_sync` is the last time a device *pushed*, not the last time someone
-- opened the page. A push happens on load, so they are usually close - but a
-- profile with no sync code never appears here at all. Someone can use the site
-- happily for a year and leave no trace in this table, because the data lives
-- in their browser and only sync sends it anywhere.
--
-- So treat this as "who has set up sync and roughly how active they are",
-- not as attendance.
