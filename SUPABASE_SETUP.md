# Supabase Connection Setup

The bot needs your **exact** database connection string from Supabase. **Never commit real credentials to the repo.**

## Steps

1. Open: **Supabase Dashboard** → your project → **Settings** → **Database**
2. Scroll to **Connection string**
3. Select **URI** tab
4. Choose **Transaction** (port 6543) or **Session** (port 5432)
5. Copy the full string - it looks like:
   ```
   postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
6. Replace `[YOUR-PASSWORD]` with your database password.
   - Special chars in URLs: `!` → `%21`, `@` → `%40`, `#` → `%23`
7. Paste into `.env` as `SUPABASE_DATABASE_URL=...` (or set in Render/env - **never in code**)

## Test

Run: `python scripts/test_db.py`

If it prints `OK: Connected!`, the bot will work.
