"""Test Supabase database connection. Run: python scripts/test_db.py"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    url = os.getenv("SUPABASE_DATABASE_URL", "")
    if not url:
        print("No SUPABASE_DATABASE_URL in .env")
        return

    # Mask password in print
    safe = url.split("@")[-1] if "@" in url else "???"
    print(f"Connecting to ...@{safe}")

    try:
        import asyncpg
        conn = await asyncpg.connect(url)
        row = await conn.fetchrow("SELECT 1 as ok")
        print("OK: Connected!", row)
        await conn.close()
    except Exception as e:
        print("FAILED:", type(e).__name__, str(e))
        print("\nGet the exact connection string from:")
        print("  Supabase Dashboard > Project Settings > Database > Connection string (URI)")
        print("  Copy 'Transaction' or 'Session' pooler string")

if __name__ == "__main__":
    asyncio.run(test())
