"""Basic and ML-inspired replay insights for MLE ReplayAI."""
from typing import Optional


def format_stat(value, fmt: str = "int") -> str:
    """Format stat for display."""
    if value is None:
        return "—"
    if fmt == "int":
        return str(int(value))
    if fmt == "pct":
        return f"{value:.1f}%"
    if fmt == "dec":
        return f"{value:.2f}"
    return str(value)


def build_player_summary(player: dict, player_index: int = 0) -> str:
    """Build a readable one-line summary for a player."""
    name = player.get("name", "Player")
    goals = player.get("goals", 0) or 0
    assists = player.get("assists", 0) or 0
    saves = player.get("saves", 0) or 0
    shots = player.get("shots", 0) or 0
    shot_pct = player.get("shooting_percentage")
    score = player.get("score", 0) or 0
    bpm = player.get("bpm")
    supersonic = player.get("percent_supersonic_speed")
    zero_boost = player.get("percent_zero_boost")

    line = f"**{name}**: {goals}G / {assists}A / {saves}S"
    if shots:
        line += f" | {shots} shots"
        if shot_pct is not None:
            line += f" ({shot_pct:.0f}%)"
    if score:
        line += f" | {score} pts"
    if bpm is not None:
        line += f" | {bpm:.0f} BPM"
    if supersonic is not None:
        line += f" | {supersonic:.1f}% supersonic"
    if zero_boost is not None:
        line += f" | {zero_boost:.1f}% zero boost"

    return line


def boost_waste_insight(player: dict, wasted_pct: Optional[float]) -> Optional[str]:
    """
    Basic insight: "You wasted X% boost (top 20% inefficiency)".
    Uses simple threshold for now; can swap for percentile vs server avg later.
    """
    if wasted_pct is None:
        return None
    if wasted_pct >= 15:
        return f"⚠️ **{player.get('name', 'You')}** wasted **{wasted_pct:.1f}%** boost while supersonic (could've coasted more)."
    if wasted_pct >= 10:
        return f"💡 **{player.get('name', 'You')}**: {wasted_pct:.1f}% boost used while supersonic — room to improve efficiency."
    return None


def rotation_insight(player: dict) -> Optional[str]:
    """Over-rotation / defensive third insight."""
    def_pct = player.get("percent_defensive_third")
    if def_pct is None:
        return None
    if def_pct > 60:
        return f"🔄 **{player.get('name', 'You')}** spent {def_pct:.1f}% of time in defensive third — consider pushing up on rotations."
    return None


def shooting_insight(player: dict) -> Optional[str]:
    """Shooting efficiency insight."""
    shot_pct = player.get("shooting_percentage")
    shots = player.get("shots", 0) or 0
    if shot_pct is None or shots < 2:
        return None
    if shot_pct < 20 and shots >= 3:
        return f"🎯 **{player.get('name', 'You')}**: {shot_pct:.0f}% shooting ({shots} shots) — focus on shot placement."
    return None


def generate_insights(players: list[dict], waste_pcts: dict[int, Optional[float]]) -> list[str]:
    """Generate all applicable insights for a replay."""
    insights = []
    for i, p in enumerate(players):
        w = waste_pcts.get(i)
        for fn in (boost_waste_insight, rotation_insight, shooting_insight):
            if fn == boost_waste_insight:
                ins = boost_waste_insight(p, w)
            else:
                ins = fn(p)
            if ins:
                insights.append(ins)
    return insights[:5]  # Cap to 5 to avoid spam
