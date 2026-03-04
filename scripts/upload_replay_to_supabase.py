"""
Upload a replay file to Supabase. Parses locally and inserts into replays + replay_stats.
Usage: python scripts/upload_replay_to_supabase.py "path/to/replay.replay" [discord_id]
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_replay_to_supabase.py <replay_path> [discord_id]")
        return 1

    replay_path = Path(sys.argv[1])
    discord_id = sys.argv[2] if len(sys.argv) > 2 else "0"

    if not replay_path.exists():
        print(f"File not found: {replay_path}")
        return 1

    from database import init_db, insert_replay, insert_replay_stats
    from replay.parser import parse_replay_bytes, replay_id_from_bytes

    data = replay_path.read_bytes()
    result = parse_replay_bytes(data)
    if not result:
        print("Failed to parse replay")
        return 1

    meta, players = result
    replay_id = replay_id_from_bytes(data)

    url = os.getenv("SUPABASE_DATABASE_URL")
    if not url:
        print("Set SUPABASE_DATABASE_URL in .env")
        return 1

    pool = await init_db()
    try:
        from database import get_replay_by_ballchasing_id
        existing = await get_replay_by_ballchasing_id(pool, replay_id)
        if existing:
            print(f"Replay already in Supabase: id={existing['id']}, key={replay_id}")
            return 0

        db_replay_id = await insert_replay(
            pool,
            ballchasing_id=replay_id,
            discord_uploader_id=str(discord_id),
            title=meta.get("title") or replay_path.stem,
            map_code=meta.get("map_code", ""),
            playlist_id="",
            team_size=meta.get("team_size"),
            duration=meta.get("duration"),
            overtime=meta.get("overtime", False),
        )
        for p in players:
            await insert_replay_stats(pool, db_replay_id, p)
        print(f"Uploaded to Supabase: replay_id={db_replay_id}, replay_key={replay_id}")
        print(f"  {len(players)} players, duration {meta.get('duration', 0)}s")
    finally:
        await pool.close()
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
