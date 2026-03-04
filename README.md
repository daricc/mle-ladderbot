# MLE LadderBot

Server-exclusive ranking ladder for 1v1/2v2/3v3 with ML-adjusted ELO. Built for competitive MLE (Minor League Esports) communities—replaces generic ladders like Ladder of DOOM!

## Features

- **`/register`** — Link your Epic or Steam ID via Tracker.gg for MMR sync
- **Auto MMR sync** — Background sync + manual `/sync` command
- **Leaderboards** — Sort by ELO, MMR, or wins per playlist
- **ML ELO model** — Win streak bonuses, playlist-specific K-factors (1v1 more volatile)
- **ELO decay** — Inactive players decay after 14 days
- **Match reporting** — `/report` to record 1v1/2v2/3v3 results
- **Weekly challenges** — Framework for reset challenges (add via DB)
- **ReplayAI (Ballchasing)** — Upload replays, fetch stats, store for ML, basic insights

## Setup

### 1. Install dependencies

```bash
cd mle-ladderbot
pip install -r requirements.txt
```

### 2. Set up Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **Project Settings → Database** and copy the **Connection string (URI)** — use "Transaction" or "Session" pooler
3. In **SQL Editor**, run the migrations in order:
   - `supabase/migrations/001_initial_schema.sql` (players, matches, challenges)
   - `supabase/migrations/002_replay_stats_schema.sql` (optional, for ReplayAI)

### 3. Configure environment

Copy `.env.example` to `.env` and fill in:

```
DISCORD_TOKEN=your_discord_bot_token
SUPABASE_DATABASE_URL=postgresql://...
TRACKER_GG_API_KEY=your_tracker_gg_api_key
BALLCHASING_API_TOKEN=your_ballchasing_api_token  # Optional: for /upload_replay
```

- **DISCORD_TOKEN**: Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
- **SUPABASE_DATABASE_URL**: Supabase Dashboard → Project Settings → Database → Connection string (URI)
- **TRACKER_GG_API_KEY**: Sign up at [tracker.gg/developers](https://tracker.gg/developers) (free tier: 100 req/min)
- **BALLCHASING_API_TOKEN**: Get at [ballchasing.com/upload](https://ballchasing.com/upload) (free: ~2 req/s, ~1k/hour)

### 4. Run the bot

```bash
python bot.py
```

## Commands

| Command | Description |
|--------|-------------|
| `/register platform platform_id` | Link Epic or Steam ID |
| `/leaderboard [limit] [sort_by]` | View ladder (sort: elo, mmr, wins_1v1, etc.) |
| `/profile` | View your ladder stats |
| `/report opponent playlist` | Report a match (1v1, 2v2, 3v3) |
| `/sync` | Manually sync MMR from Tracker.gg |
| `/challenges` | View weekly challenges |
| `/upload_replay replay_file` | Upload .replay file for stats & insights |
| `/replay_stats replay_id` | View stored stats for a Ballchasing replay |

## ReplayAI (Local Parser)

Parse Rocket League `.replay` files **locally** — no Ballchasing API needed. Uses [rattletrap](https://github.com/tfausak/rattletrap) (auto-downloaded on first upload).

- **Core stats**: goals, assists, saves, shots, shooting %, score
- **Optional**: Ballchasing fallback for richer stats (boost, movement, positioning) when API key is set
- **Insights**: boost waste, rotation, shooting efficiency

Run migration `supabase/migrations/002_replay_stats_schema.sql` in Supabase SQL Editor to enable storage.

## Site Auth & Registration

The web app supports **Discord OAuth** login, **RL Tracker** linking, and **replay verification**:

1. **Login**: Users sign in with Discord. Configure `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `SESSION_SECRET` in `.env`.
2. **Register**: Link RL Tracker URL (tracker.gg/rocketleague/profile/epic/... or steam/...), then upload a replay to verify identity.
3. **Roles**: `player` (default), `captain` (can store replays), `management` (can edit settings and assign roles).
4. **Replay storage**: Only verified captains and management have replays written to Supabase. Others get parsed stats but no DB storage.

Run migration `supabase/migrations/003_site_auth_and_roles.sql` in Supabase SQL Editor.

**First management user**: Set `INITIAL_MANAGEMENT_DISCORD_IDS=your_discord_id` in env, then log in once.

## Web Replay Parser (Host Online)

A standalone web app for players to upload replays without Discord:

```bash
# Install: pip install fastapi uvicorn python-multipart
uvicorn web.main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000`. Requires `SUPABASE_DATABASE_URL` in `.env`.

### Deploy to Render / Railway / Fly.io

1. Push repo to GitHub
2. Create a new Web Service
3. Set **Build**: `pip install -r requirements.txt`
4. Set **Start**: `uvicorn web.main:app --host 0.0.0.0 --port $PORT`
5. Add env var: `SUPABASE_DATABASE_URL` (and `PYTHONPATH=.` if needed)

**Docker**: `docker build -f web/Dockerfile .` then run the image.

## Tech Stack

- **Discord.py** — Bot framework
- **Supabase** — PostgreSQL database (asyncpg)
- **Tracker.gg API** — MMR/lookup (Rocket League)
- **Scikit-learn** — ELO model foundation (streak adjustments, K-factors)

## Tracker.gg API Note

Rocket League's public API availability may vary. Check [tracker.gg/developers](https://tracker.gg/developers) for current endpoints. If v2 RL is deprecated, update `TRACKER_PROFILE_URL` in `tracker_api.py` to the v1 format:

```
https://public-api.tracker.gg/api/v1/rocket-league/standard/profile/{platform}/{id}
```

## Adding Weekly Challenges

Insert into `weekly_challenges`:

```sql
INSERT INTO weekly_challenges (name, description, reward_elo, week_start, week_end)
VALUES ('Win 5 in a row', 'Get a 5-game win streak', 25, date('now'), date('now', '+7 days'));
```
