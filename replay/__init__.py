"""ReplayAI module - local parser, Ballchasing (optional), stats extraction, and insights."""
from replay.api import (
    upload_replay,
    get_replay,
    extract_player_stats,
    compute_boost_wasted_pct,
)
from replay.parser import (
    parse_replay_bytes,
    replay_id_from_bytes,
)
from replay.insights import (
    build_player_summary,
    generate_insights,
)

__all__ = [
    "upload_replay",
    "get_replay",
    "extract_player_stats",
    "compute_boost_wasted_pct",
    "parse_replay_bytes",
    "replay_id_from_bytes",
    "build_player_summary",
    "generate_insights",
]
