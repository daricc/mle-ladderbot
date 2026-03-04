-- MLE LadderBot - Initial schema for Supabase
-- Run this in Supabase SQL Editor: Dashboard → SQL Editor → New query

CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    discord_id TEXT UNIQUE NOT NULL,
    epic_id TEXT,
    steam_id TEXT,
    epic_platform_id TEXT,
    steam_platform_id TEXT,
    mmr INTEGER DEFAULT 0,
    elo REAL DEFAULT 1000,
    wins_1v1 INTEGER DEFAULT 0,
    losses_1v1 INTEGER DEFAULT 0,
    wins_2v2 INTEGER DEFAULT 0,
    losses_2v2 INTEGER DEFAULT 0,
    wins_3v3 INTEGER DEFAULT 0,
    losses_3v3 INTEGER DEFAULT 0,
    win_streak INTEGER DEFAULT 0,
    last_activity TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    playlist TEXT NOT NULL,
    winner_discord_id TEXT NOT NULL,
    loser_discord_id TEXT NOT NULL,
    winner_elo_before REAL,
    loser_elo_before REAL,
    elo_change REAL,
    played_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS weekly_challenges (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    target_type TEXT,
    target_value INTEGER,
    reward_elo INTEGER DEFAULT 0,
    week_start DATE,
    week_end DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS challenge_completions (
    id SERIAL PRIMARY KEY,
    challenge_id INTEGER REFERENCES weekly_challenges(id),
    discord_id TEXT,
    completed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_players_discord ON players(discord_id);
CREATE INDEX IF NOT EXISTS idx_players_elo ON players(elo DESC);
CREATE INDEX IF NOT EXISTS idx_matches_played ON matches(played_at);
