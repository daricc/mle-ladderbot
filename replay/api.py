"""Ballchasing API client for uploading replays and fetching stats (MLE ReplayAI)."""
import aiohttp
from typing import Optional

import config


BALLCHASING_BASE = "https://ballchasing.com/api"
# Rate limits: 2 req/s, ~1000/hour (free tier). Be conservative.


async def upload_replay(file_bytes: bytes, filename: str) -> Optional[str]:
    """
    Upload a replay file to Ballchasing.
    Returns replay ID on success (201 or 409 duplicate), None on failure.
    """
    if not config.BALLCHASING_API_TOKEN:
        return None

    url = f"{BALLCHASING_BASE}/v2/upload"
    headers = {"Authorization": config.BALLCHASING_API_TOKEN}
    data = aiohttp.FormData()
    data.add_field("file", file_bytes, filename=filename or "replay.replay")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data, timeout=60) as resp:
                if resp.status in (201, 409):
                    body = await resp.json()
                    return body.get("id")
                return None
    except Exception:
        return None


async def get_replay(replay_id: str) -> Optional[dict]:
    """
    Fetch full replay details including player stats.
    GET /replays/{id}
    """
    if not config.BALLCHASING_API_TOKEN:
        return None

    url = f"{BALLCHASING_BASE}/replays/{replay_id}"
    headers = {"Authorization": config.BALLCHASING_API_TOKEN}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
    except Exception:
        return None


def extract_player_stats(replay: dict) -> list[dict]:
    """
    Extract flattened stats for each player from replay response.
    Maps Ballchasing fields to our schema for storage/ML.
    """
    players = []
    for team_key in ("blue", "orange"):
        team_data = replay.get(team_key, {})
        if not team_data:
            continue
        team_name = team_data.get("name", team_key)
        for p in team_data.get("players", []):
            stats = p.get("stats") or {}
            core = stats.get("core") or {}
            boost = stats.get("boost") or {}
            movement = stats.get("movement") or {}
            positioning = stats.get("positioning") or {}
            demo = stats.get("demo") or {}

            plat_id = (p.get("id") or {}).get("id", "")
            platform = (p.get("id") or {}).get("platform", "")

            player_stats = {
                "name": p.get("name", ""),
                "platform": platform,
                "platform_id": plat_id,
                "team": team_name,
                "team_color": team_key,
                # Core
                "goals": core.get("goals", 0),
                "assists": core.get("assists", 0),
                "saves": core.get("saves", 0),
                "shots": core.get("shots", 0),
                "shots_against": core.get("shots_against", 0),
                "shooting_percentage": core.get("shooting_percentage"),
                "score": core.get("score", 0),
                "mvp": core.get("mvp", False),
                # Boost
                "amount_collected": boost.get("amount_collected"),
                "bpm": boost.get("bpm"),
                "bcpm": boost.get("bcpm"),
                "amount_collected_big": boost.get("amount_collected_big"),
                "amount_collected_small": boost.get("amount_collected_small"),
                "amount_stolen": boost.get("amount_stolen"),
                "amount_used_while_supersonic": boost.get("amount_used_while_supersonic"),
                "percent_zero_boost": boost.get("percent_zero_boost"),
                "percent_full_boost": boost.get("percent_full_boost"),
                "avg_amount": boost.get("avg_amount"),
                # Movement
                "avg_speed": movement.get("avg_speed"),
                "total_distance": movement.get("total_distance"),
                "percent_supersonic_speed": movement.get("percent_supersonic_speed"),
                "percent_boost_speed": movement.get("percent_boost_speed"),
                "percent_slow_speed": movement.get("percent_slow_speed"),
                "percent_ground": movement.get("percent_ground"),
                "percent_low_air": movement.get("percent_low_air"),
                "percent_high_air": movement.get("percent_high_air"),
                "count_powerslide": movement.get("count_powerslide"),
                "avg_powerslide_duration": movement.get("avg_powerslide_duration"),
                # Positioning
                "percent_defensive_third": positioning.get("percent_defensive_third"),
                "percent_offensive_third": positioning.get("percent_offensive_third"),
                "percent_neutral_third": positioning.get("percent_neutral_third"),
                "percent_behind_ball": positioning.get("percent_behind_ball"),
                "percent_infront_ball": positioning.get("percent_infront_ball"),
                "avg_distance_to_ball": positioning.get("avg_distance_to_ball"),
                "avg_distance_to_mates": positioning.get("avg_distance_to_mates"),
                # Demos
                "demos_inflicted": demo.get("inflicted", 0),
                "demos_taken": demo.get("taken", 0),
            }
            players.append(player_stats)

    return players


def compute_boost_wasted_pct(player_stats: dict) -> Optional[float]:
    """
    Approximate boost waste: used while supersonic (could have coasted).
    percent_wasted = amount_used_while_supersonic / amount_collected * 100
    """
    collected = player_stats.get("amount_collected") or 0
    used_super = player_stats.get("amount_used_while_supersonic")
    if collected and used_super is not None:
        return min(100, round(100 * used_super / collected, 2))
    return None
