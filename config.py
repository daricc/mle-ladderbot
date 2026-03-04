"""Configuration for MLE LadderBot."""
import os

from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_IDS = [int(x) for x in os.getenv("GUILD_IDS", "").split(",") if x.strip()]

# Tracker.gg API (free tier: 100 req/min)
TRACKER_GG_API_KEY = os.getenv("TRACKER_GG_API_KEY", "")
TRACKER_GG_BASE_URL = "https://api.tracker.gg/api/v2/rocket-league/standard/profile"

# Ballchasing API (free: ~2 req/s, ~1k/hour)
# Get token: https://ballchasing.com/upload → create API key
BALLCHASING_API_TOKEN = os.getenv("BALLCHASING_API_TOKEN", "")

# Supabase (PostgreSQL)
# Get from: Supabase Dashboard → Project Settings → Database → Connection string (URI)
# COPY the exact "Connection string (URI)" from Dashboard - pooler host varies by region
SUPABASE_DATABASE_URL = os.getenv(
    "SUPABASE_DATABASE_URL",
    os.getenv("DATABASE_URL", ""),
)

# ELO & ML
DEFAULT_ELO = 1000
ELO_K_FACTOR = 32
DECAY_DAYS_INACTIVE = 14
DECAY_PER_DAY = 5
MAX_WIN_STREAK_BONUS = 50
