"""ML-adjusted ELO model with win streaks and playlist factors."""
import numpy as np
from sklearn.linear_model import LinearRegression
from typing import Tuple

import config


def expected_score(elo_a: float, elo_b: float) -> float:
    """Standard ELO expected score for player A vs B."""
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400))


def base_elo_change(
    winner_elo: float,
    loser_elo: float,
    k: float = None
) -> float:
    """Calculate base ELO change. Winner gains, loser loses same amount."""
    k = k or config.ELO_K_FACTOR
    expected = expected_score(winner_elo, loser_elo)
    return k * (1.0 - expected)


def streak_adjustment(win_streak: int) -> float:
    """
    ML-inspired adjustment: win streaks reduce K (less volatile) or
    we can add a small bonus for momentum. Using bonus for engagement.
    """
    if win_streak <= 1:
        return 0
    bonus = min(config.MAX_WIN_STREAK_BONUS, (win_streak - 1) * 2)
    return bonus


def playlist_k_factor(playlist: str) -> float:
    """Different K for different playlists (1v1 more volatile)."""
    factors = {"1v1": 40, "2v2": 32, "3v3": 28}
    return factors.get(playlist.lower(), config.ELO_K_FACTOR)


def calculate_elo_change(
    winner_elo: float,
    loser_elo: float,
    winner_streak: int = 0,
    playlist: str = "1v1"
) -> Tuple[float, float]:
    """
    Calculate ML-adjusted ELO change.
    Returns (winner_gain, loser_loss) - symmetric for ladder integrity.
    """
    k = playlist_k_factor(playlist)
    base = base_elo_change(winner_elo, loser_elo, k)
    streak_bonus = streak_adjustment(winner_streak)

    # Cap swing
    change = min(50, max(4, base + streak_bonus * 0.5))
    return (change, change)
