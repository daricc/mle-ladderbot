# Supabase Connection Setup

The bot needs your **exact** database connection string from Supabase.

## Steps

1. Open: **https://supabase.com/dashboard/project/oafsyyzjqpgmijglutor/settings/database**
2. Scroll to **Connection string**
3. Select **URI** tab
4. Choose **Transaction** (port 6543) or **Session** (port 5432)
5. Copy the full string - it looks like:
   ```
   postgresql://postgres.oafsyyzjqpgmijglutor:[YOUR-PASSWORD]@aws-0-XX-XXXX.pooler.supabase.com:6543/postgres
   ```
6. Replace `[YOUR-PASSWORD]` with your database password: `Jona1212!!@@`
   - Special chars in URLs: `!` = `%21`, `@` = `%40`
   - So encoded: `Jona1212%21%21%40%40`
7. Paste into `.env` as `SUPABASE_DATABASE_URL=...`

## Test

Run: `python scripts/test_db.py`

If it prints `OK: Connected!`, the bot will work.
