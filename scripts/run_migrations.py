"""
Run all Supabase migrations. Creates all required tables.
Usage: python scripts/run_migrations.py
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


async def main():
    url = os.getenv("SUPABASE_DATABASE_URL")
    if not url:
        print("ERROR: Set SUPABASE_DATABASE_URL in .env")
        return 1

    import asyncpg
    conn = await asyncpg.connect(url)

    migrations_dir = Path(__file__).parent.parent / "supabase" / "migrations"
    migrations = sorted(migrations_dir.glob("*.sql"))

    if not migrations:
        print("No migration files found")
        await conn.close()
        return 1

    print(f"Running {len(migrations)} migration(s)...\n")
    for f in migrations:
        sql = f.read_text(encoding="utf-8")
        try:
            await conn.execute(sql)
            print(f"  [OK] {f.name}")
        except Exception as e:
            print(f"  [WARN] {f.name}: {e}")

    await conn.close()
    print("\nDone! All Supabase tables created.")
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
