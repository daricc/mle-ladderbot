"""Database models and operations for MLE LadderBot (Supabase/PostgreSQL)."""
import asyncpg
from datetime import datetime
from typing import Optional

import config


async def init_db() -> asyncpg.Pool:
    """Create connection pool to Supabase Postgres."""
    if not config.SUPABASE_DATABASE_URL:
        raise ValueError(
            "Set SUPABASE_DATABASE_URL in .env (from Supabase Dashboard → Project Settings → Database)"
        )
    pool = await asyncpg.create_pool(
        config.SUPABASE_DATABASE_URL,
        min_size=1,
        max_size=5,
        command_timeout=60,
        statement_cache_size=0,  # Required for Supabase/pgbouncer transaction pooler
    )
    return pool


async def get_player(pool: asyncpg.Pool, discord_id: str) -> Optional[dict]:
    """Fetch a player by Discord ID."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM players WHERE discord_id = $1",
            str(discord_id),
        )
        return dict(row) if row else None


async def register_player(
    pool: asyncpg.Pool,
    discord_id: str,
    epic_id: Optional[str] = None,
    steam_id: Optional[str] = None,
) -> dict:
    """Register or update a player. Returns the player record."""
    now = datetime.utcnow()
    player = await get_player(pool, discord_id)

    async with pool.acquire() as conn:
        if player:
            updates = []
            params = [discord_id]
            n = 1
            if epic_id is not None:
                n += 1
                updates.append(f"epic_id = ${n}")
                params.append(epic_id)
            if steam_id is not None:
                n += 1
                updates.append(f"steam_id = ${n}")
                params.append(steam_id)
            n += 1
            updates.append(f"updated_at = ${n}")
            params.append(now)

            await conn.execute(
                f"UPDATE players SET {', '.join(updates)} WHERE discord_id = $1",
                *params,
            )
        else:
            await conn.execute(
                """
                INSERT INTO players (discord_id, epic_id, steam_id, elo, last_activity, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $5, $5)
                """,
                discord_id,
                epic_id or "",
                steam_id or "",
                config.DEFAULT_ELO,
                now,
            )

    return (await get_player(pool, discord_id)) or {}


async def update_player_mmr(pool: asyncpg.Pool, discord_id: str, mmr: int) -> None:
    """Update a player's MMR from Tracker.gg sync."""
    now = datetime.utcnow()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET mmr = $1, last_activity = $2, updated_at = $2 WHERE discord_id = $3",
            mmr,
            now,
            str(discord_id),
        )


async def get_leaderboard(
    pool: asyncpg.Pool,
    limit: int = 10,
    sort_by: str = "elo",
) -> list[dict]:
    """Get top players. sort_by: elo, mmr, wins_1v1, wins_2v2, wins_3v3."""
    valid_sort = {"elo", "mmr", "wins_1v1", "wins_2v2", "wins_3v3"}
    col = sort_by if sort_by in valid_sort else "elo"

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM players ORDER BY {col} DESC NULLS LAST LIMIT $1",
            limit,
        )
        return [dict(r) for r in rows]


async def record_match(
    pool: asyncpg.Pool,
    playlist: str,
    winner_id: str,
    loser_id: str,
    winner_elo: float,
    loser_elo: float,
    elo_change: float,
) -> None:
    """Record a match result and update ELO."""
    now = datetime.utcnow()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE players SET
                elo = elo + $1,
                win_streak = win_streak + 1,
                last_activity = $2,
                updated_at = $2,
                wins_1v1 = wins_1v1 + CASE WHEN $3 = '1v1' THEN 1 ELSE 0 END,
                wins_2v2 = wins_2v2 + CASE WHEN $3 = '2v2' THEN 1 ELSE 0 END,
                wins_3v3 = wins_3v3 + CASE WHEN $3 = '3v3' THEN 1 ELSE 0 END
            WHERE discord_id = $4
            """,
            elo_change,
            now,
            playlist,
            winner_id,
        )

        await conn.execute(
            """
            UPDATE players SET
                elo = elo - $1,
                win_streak = 0,
                last_activity = $2,
                updated_at = $2,
                losses_1v1 = losses_1v1 + CASE WHEN $3 = '1v1' THEN 1 ELSE 0 END,
                losses_2v2 = losses_2v2 + CASE WHEN $3 = '2v2' THEN 1 ELSE 0 END,
                losses_3v3 = losses_3v3 + CASE WHEN $3 = '3v3' THEN 1 ELSE 0 END
            WHERE discord_id = $4
            """,
            elo_change,
            now,
            playlist,
            loser_id,
        )

        await conn.execute(
            """
            INSERT INTO matches (playlist, winner_discord_id, loser_discord_id, winner_elo_before, loser_elo_before, elo_change)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            playlist,
            winner_id,
            loser_id,
            winner_elo,
            loser_elo,
            elo_change,
        )


async def apply_elo_decay(pool: asyncpg.Pool) -> int:
    """Apply ELO decay to inactive players. Returns count of affected players."""
    min_elo = config.DEFAULT_ELO - 200

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            UPDATE players SET
                elo = GREATEST($1::real, elo - $2 * EXTRACT(EPOCH FROM (NOW() - last_activity)) / 86400),
                updated_at = NOW()
            WHERE last_activity IS NOT NULL
              AND EXTRACT(EPOCH FROM (NOW() - last_activity)) / 86400 > $3
            RETURNING id
            """,
            min_elo,
            config.DECAY_PER_DAY,
            config.DECAY_DAYS_INACTIVE,
        )
        return len(rows)


async def get_weekly_challenges(pool: asyncpg.Pool) -> list[dict]:
    """Get active weekly challenges."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM weekly_challenges
            WHERE CURRENT_DATE BETWEEN week_start AND week_end
            ORDER BY id
            """
        )
        return [dict(r) for r in rows]


# ---- Replay stats (Ballchasing / ReplayAI) ----

async def insert_replay(
    pool: asyncpg.Pool,
    ballchasing_id: str,
    discord_uploader_id: str,
    title: Optional[str] = None,
    map_code: Optional[str] = None,
    playlist_id: Optional[str] = None,
    team_size: Optional[int] = None,
    duration: Optional[int] = None,
    overtime: bool = False,
) -> int:
    """Insert a replay row, return replay_id."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO replays (ballchasing_id, discord_uploader_id, title, map_code, playlist_id, team_size, duration, overtime)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """,
            ballchasing_id,
            discord_uploader_id,
            title or "",
            map_code or "",
            playlist_id or "",
            team_size,
            duration,
            overtime,
        )
        return row["id"]


async def insert_replay_stats(pool: asyncpg.Pool, replay_id: int, player_stats: dict) -> None:
    """Insert a single player's stats for a replay."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO replay_stats (
                replay_id, player_name, platform, platform_id, team, team_color,
                goals, assists, saves, shots, shots_against, shooting_percentage, score, mvp,
                amount_collected, bpm, bcpm, amount_collected_big, amount_collected_small,
                amount_stolen, amount_used_while_supersonic, percent_zero_boost, percent_full_boost, avg_amount,
                avg_speed, total_distance, percent_supersonic_speed, percent_boost_speed, percent_slow_speed,
                percent_ground, percent_low_air, percent_high_air, count_powerslide, avg_powerslide_duration,
                percent_defensive_third, percent_offensive_third, percent_neutral_third,
                percent_behind_ball, percent_infront_ball, avg_distance_to_ball, avg_distance_to_mates,
                demos_inflicted, demos_taken
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                $15, $16, $17, $18, $19, $20, $21, $22, $23, $24,
                $25, $26, $27, $28, $29, $30, $31, $32, $33, $34,
                $35, $36, $37, $38, $39, $40, $41, $42, $43
            )
            """,
            replay_id,
            player_stats.get("name", ""),
            player_stats.get("platform") or "",
            player_stats.get("platform_id") or "",
            player_stats.get("team", ""),
            player_stats.get("team_color", ""),
            player_stats.get("goals", 0),
            player_stats.get("assists", 0),
            player_stats.get("saves", 0),
            player_stats.get("shots", 0),
            player_stats.get("shots_against", 0),
            player_stats.get("shooting_percentage"),
            player_stats.get("score", 0),
            player_stats.get("mvp", False),
            player_stats.get("amount_collected"),
            player_stats.get("bpm"),
            player_stats.get("bcpm"),
            player_stats.get("amount_collected_big"),
            player_stats.get("amount_collected_small"),
            player_stats.get("amount_stolen"),
            player_stats.get("amount_used_while_supersonic"),
            player_stats.get("percent_zero_boost"),
            player_stats.get("percent_full_boost"),
            player_stats.get("avg_amount"),
            player_stats.get("avg_speed"),
            player_stats.get("total_distance"),
            player_stats.get("percent_supersonic_speed"),
            player_stats.get("percent_boost_speed"),
            player_stats.get("percent_slow_speed"),
            player_stats.get("percent_ground"),
            player_stats.get("percent_low_air"),
            player_stats.get("percent_high_air"),
            player_stats.get("count_powerslide"),
            player_stats.get("avg_powerslide_duration"),
            player_stats.get("percent_defensive_third"),
            player_stats.get("percent_offensive_third"),
            player_stats.get("percent_neutral_third"),
            player_stats.get("percent_behind_ball"),
            player_stats.get("percent_infront_ball"),
            player_stats.get("avg_distance_to_ball"),
            player_stats.get("avg_distance_to_mates"),
            player_stats.get("demos_inflicted", 0),
            player_stats.get("demos_taken", 0),
        )


async def get_replay_by_ballchasing_id(pool: asyncpg.Pool, ballchasing_id: str) -> Optional[dict]:
    """Fetch replay by Ballchasing ID."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM replays WHERE ballchasing_id = $1",
            ballchasing_id,
        )
        return dict(row) if row else None


async def get_replay_stats_for_replay(pool: asyncpg.Pool, replay_id: int) -> list[dict]:
    """Get all player stats for a replay."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM replay_stats WHERE replay_id = $1 ORDER BY team, player_name",
            replay_id,
        )
        return [dict(r) for r in rows]
