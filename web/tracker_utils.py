"""Tracker.gg URL parsing and replay verification."""
import re
from typing import Optional

# tracker.gg/rocketleague/profile/epic/Username
# tracker.gg/rocketleague/profile/steam/76561198123456789
TRACKER_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?tracker\.gg/rocketleague/profile/(?P<platform>epic|steam)/(?P<id>[^/?#\s]+)",
    re.I,
)


def parse_tracker_url(url: str) -> Optional[tuple[str, str]]:
    """
    Parse a Tracker.gg RL profile URL.
    Returns (platform, identifier) e.g. ('epic', 'MyUsername') or ('steam', '76561198...').
    """
    if not url or not url.strip():
        return None
    url = url.strip()
    m = TRACKER_PATTERN.search(url)
    if not m:
        return None
    platform = m.group("platform").lower()
    identifier = m.group("id").strip()
    if not identifier:
        return None
    return (platform, identifier)


def replay_verifies_user(players: list[dict], rl_platform: str, rl_identifier: str) -> bool:
    """
    Check if any player in the parsed replay matches the user's RL Tracker registration.
    Uses name matching (case-insensitive) for Epic, and platform_id for Steam when available.
    """
    identifier_lower = rl_identifier.lower().strip()

    for p in players:
        name = (p.get("name") or "").strip()
        platform_id = (p.get("platform_id") or "").strip()
        platform = (p.get("platform") or "").lower()

        # Steam: match by 64-bit ID if we have it
        if rl_platform == "steam" and platform_id and platform == "steam":
            if platform_id == rl_identifier or platform_id == identifier_lower:
                return True

        # Epic or Steam: match by display name (replay shows in-game name)
        if name and identifier_lower:
            # Exact or close match - Tracker uses Epic username, replay uses display name
            if name.lower() == identifier_lower:
                return True
            # Handle Epic usernames with optional discriminator/suffix
            if name.lower().startswith(identifier_lower) or identifier_lower.startswith(name.lower()):
                return True

    return False
