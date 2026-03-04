-- Site users, RL Tracker registration, roles, and replay verification
-- Uses Discord OAuth (discord_id) for login - no Supabase Auth dependency

CREATE TABLE IF NOT EXISTS site_users (
    id SERIAL PRIMARY KEY,
    discord_id TEXT UNIQUE NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    -- RL Tracker registration
    rl_platform TEXT,           -- 'epic' or 'steam'
    rl_identifier TEXT,        -- Epic username or Steam 64-bit ID
    rl_tracker_url TEXT,       -- Full Tracker.gg profile URL for display
    verified_at TIMESTAMPTZ,    -- Set after replay confirms identity
    -- Role: player (default), captain (team captain), management
    role TEXT NOT NULL DEFAULT 'player' CHECK (role IN ('player', 'captain', 'management')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- League/site content editable by management (announcements, rules, etc.)
CREATE TABLE IF NOT EXISTS league_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by_discord_id TEXT
);

-- Replays: track uploader discord_id for audit (replays.discord_uploader_id already exists)
-- Add stored_by_role to know if captain or management stored it
ALTER TABLE replays ADD COLUMN IF NOT EXISTS stored_by_role TEXT;

CREATE INDEX IF NOT EXISTS idx_site_users_discord ON site_users(discord_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_site_users_rl_lookup ON site_users(rl_platform, rl_identifier) WHERE rl_platform IS NOT NULL AND rl_identifier IS NOT NULL;
