"""Tracker.gg API integration for MMR and profile lookup."""
import aiohttp
from typing import Optional

import config


# Tracker.gg Public API: https://public-api.tracker.gg/api/v1/{title}/standard/profile/{platform}/{id}
# RL v2 deprecated Apr 2023; check tracker.gg/developers for current endpoints
# Platforms: epic, steam, xbl, psn
TRACKER_PROFILE_URL = "https://public-api.tracker.gg/api/v2/rocket-league/standard/profile"


async def fetch_profile(platform: str, platform_user_id: str) -> Optional[dict]:
    """
    Fetch a player profile from Tracker.gg.
    platform: 'epic' or 'steam'
    platform_user_id: Epic username or Steam ID (e.g. steam 64-bit ID)
    """
    if not config.TRACKER_GG_API_KEY:
        return None

    url = f"{TRACKER_PROFILE_URL}/{platform}/{platform_user_id}"
    headers = {"TRN-Api-Key": config.TRACKER_GG_API_KEY}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data
    except Exception:
        return None


def extract_mmr_from_profile(profile: dict) -> Optional[int]:
    """Extract MMR from Tracker.gg profile response."""
    try:
        segments = profile.get("data", {}).get("segments", [])
        for seg in segments:
            stats = seg.get("stats", {})
            if "rating" in stats:
                return int(stats["rating"].get("value", 0))
            if "mmr" in stats:
                return int(stats["mmr"].get("value", 0))
        return None
    except (KeyError, TypeError):
        return None


async def get_mmr(platform: str, platform_user_id: str) -> Optional[int]:
    """Convenience: fetch profile and return MMR."""
    profile = await fetch_profile(platform, platform_user_id)
    if profile:
        return extract_mmr_from_profile(profile)
    return None
