-- Replay stats for MLE ReplayAI (Ballchasing)
-- Stores replay metadata + flattened player stats for ML/insights

CREATE TABLE IF NOT EXISTS replays (
    id SERIAL PRIMARY KEY,
    ballchasing_id TEXT UNIQUE NOT NULL,
    discord_uploader_id TEXT NOT NULL,
    title TEXT,
    map_code TEXT,
    playlist_id TEXT,
    team_size INTEGER,
    duration INTEGER,
    overtime BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS replay_stats (
    id SERIAL PRIMARY KEY,
    replay_id INTEGER REFERENCES replays(id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    platform TEXT,
    platform_id TEXT,
    team TEXT,
    team_color TEXT,
    -- Core
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    shots INTEGER DEFAULT 0,
    shots_against INTEGER DEFAULT 0,
    shooting_percentage REAL,
    score INTEGER DEFAULT 0,
    mvp BOOLEAN DEFAULT FALSE,
    -- Boost
    amount_collected INTEGER,
    bpm REAL,
    bcpm REAL,
    amount_collected_big INTEGER,
    amount_collected_small INTEGER,
    amount_stolen INTEGER,
    amount_used_while_supersonic INTEGER,
    percent_zero_boost REAL,
    percent_full_boost REAL,
    avg_amount REAL,
    -- Movement
    avg_speed INTEGER,
    total_distance INTEGER,
    percent_supersonic_speed REAL,
    percent_boost_speed REAL,
    percent_slow_speed REAL,
    percent_ground REAL,
    percent_low_air REAL,
    percent_high_air REAL,
    count_powerslide INTEGER,
    avg_powerslide_duration REAL,
    -- Positioning
    percent_defensive_third REAL,
    percent_offensive_third REAL,
    percent_neutral_third REAL,
    percent_behind_ball REAL,
    percent_infront_ball REAL,
    avg_distance_to_ball INTEGER,
    avg_distance_to_mates INTEGER,
    -- Demos
    demos_inflicted INTEGER DEFAULT 0,
    demos_taken INTEGER DEFAULT 0,
    -- Link to ladder player if matched
    discord_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_replays_ballchasing ON replays(ballchasing_id);
CREATE INDEX IF NOT EXISTS idx_replays_uploader ON replays(discord_uploader_id);
CREATE INDEX IF NOT EXISTS idx_replay_stats_replay ON replay_stats(replay_id);
CREATE INDEX IF NOT EXISTS idx_replay_stats_platform_id ON replay_stats(platform, platform_id);
