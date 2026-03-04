"""
Crossbar League - Web upload service.
Host this online so players can upload .replay files and get stats.
Run: uvicorn web.main:app --host 0.0.0.0 --port 8000
"""
import asyncio
import os
import sys
from pathlib import Path

# Project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Crossbar League", description="Rocket League competitive league", version="1.0.0")
app.add_middleware(GZipMiddleware, minimum_size=500)
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
SITE_URL = os.getenv("SITE_URL", "https://crossbarleague.gg").rstrip("/")
DEFAULT_OG_IMAGE = f"{SITE_URL}/static/images/crossbar-logo.svg"

# DB pool (lazy init)
_db_pool = None


async def get_db():
    global _db_pool
    if _db_pool is None:
        url = os.getenv("SUPABASE_DATABASE_URL")
        if not url:
            return None
        try:
            import asyncpg
            _db_pool = await asyncpg.create_pool(
                url,
                min_size=1,
                max_size=5,
                command_timeout=60,
                statement_cache_size=0,
            )
        except Exception:
            return None
    return _db_pool


from web.templates import page, HOME_PAGE, ABOUT_PAGE, UPLOAD_PAGE


def page_url(path: str) -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{SITE_URL}{normalized}"


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.get("/", response_class=HTMLResponse)
async def home():
    """Home page - league overview."""
    return HTMLResponse(
        page(
            "Home",
            HOME_PAGE,
            active="home",
            description="Crossbar League is a draft-first Rocket League competition with circuit tiers, standings, and replay-powered stats.",
            canonical_url=page_url("/"),
            og_image=DEFAULT_OG_IMAGE,
        )
    )


@app.get("/about", response_class=HTMLResponse)
async def about():
    """About page - organization details."""
    return HTMLResponse(
        page(
            "About",
            ABOUT_PAGE,
            active="about",
            description="Learn how Crossbar League runs its Rocket League draft, seasonal circuits, promotions, and team competition format.",
            canonical_url=page_url("/about"),
            og_image=DEFAULT_OG_IMAGE,
        )
    )


@app.get("/stats", response_class=HTMLResponse)
async def stats():
    """Stats page - leaderboards from Supabase."""
    pool = await get_db()
    players = []
    replays_count = 0
    if pool:
        try:
            from database import get_leaderboard
            players = await get_leaderboard(pool, limit=50, sort_by="elo")
            async with pool.acquire() as conn:
                row = await conn.fetchrow("SELECT COUNT(*) as n FROM replays")
                replays_count = row["n"] if row else 0
        except Exception:
            pass

    rows_html = ""
    if players:
        for i, p in enumerate(players, 1):
            elo = int(p.get("elo", 0))
            mmr = p.get("mmr") or "—"
            wins = (p.get("wins_1v1", 0) or 0) + (p.get("wins_2v2", 0) or 0) + (p.get("wins_3v3", 0) or 0)
            losses = (p.get("losses_1v1", 0) or 0) + (p.get("losses_2v2", 0) or 0) + (p.get("losses_3v3", 0) or 0)
            name = f"Player {str(p.get('discord_id', ''))[-6:]}" if p.get("discord_id") else "—"
            rows_html += f'<tr><td class="rank">{i}</td><td>{name}</td><td class="elo">{elo}</td><td class="mmr">{mmr}</td><td>{wins}W {losses}L</td></tr>'
    else:
        rows_html = '<tr><td colspan="5" class="stats-empty" style="border:none;">No players on the ladder yet. Join our Discord and register!</td></tr>'

    stats_body = f'''
    <section class="hero hero-stats"><h1>Leaderboards & Stats</h1>
    <p>Live standings from Supabase. ELO and MMR from league matches.</p>
    <p class="hero-meta">Replays uploaded: <strong>{replays_count}</strong> — Click column headers to sort</p>
    <div class="mmr-calc reveal">
      <h3>Which division am I in?</h3>
      <div class="mmr-calc-row">
        <input type="number" id="mmr-input" placeholder="Enter your MMR" min="0" max="2500" value="">
        <button type="button" id="mmr-check" class="btn btn-secondary">Check</button>
      </div>
      <p id="mmr-result" class="mmr-result"></p>
    </div></section>
    <section class="stats-section reveal"><h2>Ladder Rankings</h2>
    <table class="stats-table"><thead><tr><th class="rank">#</th><th data-sort="player">Player <span class="sort-icon"></span></th><th data-sort="elo">ELO <span class="sort-icon"></span></th><th data-sort="mmr">MMR <span class="sort-icon"></span></th><th data-sort="record">Record <span class="sort-icon"></span></th></tr></thead><tbody>{rows_html}</tbody></table></section>'''
    return HTMLResponse(
        page(
            "Stats",
            stats_body,
            active="stats",
            description="Live Crossbar League leaderboards with ELO, MMR, and replay volume from seasonal competition.",
            canonical_url=page_url("/stats"),
            og_image=DEFAULT_OG_IMAGE,
        )
    )


@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    """Replay upload page."""
    return HTMLResponse(
        page(
            "Upload Replay",
            UPLOAD_PAGE,
            active="upload",
            description="Upload a Rocket League replay to parse player stats, match insights, and shareable replay pages.",
            canonical_url=page_url("/upload"),
            og_image=DEFAULT_OG_IMAGE,
        )
    )


@app.post("/api/upload")
async def upload_replay(file: UploadFile = File(...)):
    """
    Upload a .replay file. Parses it, stores in Supabase, returns stats and replay ID.
    """
    if not file.filename or not file.filename.lower().endswith(".replay"):
        raise HTTPException(400, "Please upload a .replay file from Rocket League")

    # 25MB max
    contents = await file.read()
    if len(contents) > 25 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 25MB)")

    # Parse in thread pool (blocking)
    from replay.parser import parse_replay_bytes, replay_id_from_bytes
    result = await asyncio.to_thread(parse_replay_bytes, contents)
    if not result:
        raise HTTPException(422, "Could not parse replay. Ensure it's a valid Rocket League .replay file.")

    meta, players = result
    replay_id = replay_id_from_bytes(contents)

    # Store in Supabase
    pool = await get_db()
    if pool:
        try:
            from database import insert_replay, insert_replay_stats, get_replay_by_ballchasing_id
            existing = await get_replay_by_ballchasing_id(pool, replay_id)
            if not existing:
                db_replay_id = await insert_replay(
                    pool,
                    ballchasing_id=replay_id,
                    discord_uploader_id="web",
                    title=meta.get("title") or file.filename,
                    map_code=meta.get("map_code", ""),
                    playlist_id="",
                    team_size=meta.get("team_size"),
                    duration=meta.get("duration"),
                    overtime=meta.get("overtime", False),
                )
                for p in players:
                    await insert_replay_stats(pool, db_replay_id, p)
        except Exception as e:
            pass  # Still return parsed data even if DB fails

    return {
        "replay_id": replay_id,
        "meta": meta,
        "players": players,
        "url": f"/replay/{replay_id}",
    }


@app.get("/replay/{replay_id}", response_class=HTMLResponse)
async def replay_results(replay_id: str):
    """Show replay stats page."""
    pool = await get_db()
    players = []
    meta = {}

    if pool:
        try:
            from database import get_replay_by_ballchasing_id, get_replay_stats_for_replay
            replay = await get_replay_by_ballchasing_id(pool, replay_id)
            if replay:
                meta = {
                    "title": replay.get("title", ""),
                    "duration": replay.get("duration", 0),
                    "team_size": replay.get("team_size", 3),
                }
                rows = await get_replay_stats_for_replay(pool, replay["id"])
                players = [dict(r) for r in rows]
        except Exception:
            pass

    if not players:
        body = f"""
        <section class="section"><div class="card">
        <h1>Replay not found</h1>
        <p>ID: {replay_id}</p>
        <a href="/upload">Upload a replay</a>
        </div></section>"""
        return HTMLResponse(
            page(
                "Replay Not Found",
                body,
                active="upload",
                description="The requested replay page could not be found.",
                canonical_url=page_url(f"/replay/{replay_id}"),
                og_image=DEFAULT_OG_IMAGE,
                noindex=True,
            )
        )

    from replay.insights import build_player_summary
    blue = [p for p in players if p.get("team_color") == "blue"]
    orange = [p for p in players if p.get("team_color") == "orange"]

    lines_blue = "\n".join(f"<li>{build_player_summary(p)}</li>" for p in blue)
    lines_orange = "\n".join(f"<li>{build_player_summary(p)}</li>" for p in orange)
    title = meta.get("title", "Replay") or "Replay"
    dur = meta.get("duration", 0)
    mins, secs = dur // 60, dur % 60

    body = f"""
    <section class="section"><div class="card">
    <h1>{title}</h1>
    <p class="meta">Duration: {mins}:{secs:02d} | Team size: {meta.get('team_size', 3)}v{meta.get('team_size', 3)}</p>
    <div class="teams">
    <section><h2>Blue</h2><ul>{lines_blue}</ul></section>
    <section><h2>Orange</h2><ul>{lines_orange}</ul></section>
    </div>
    <a href="/upload">Upload another</a>
    </div></section>"""
    return HTMLResponse(
        page(
            title or "Replay",
            body,
            active="upload",
            description=f"Replay breakdown for {title or 'Crossbar League match'} with per-player summaries and team splits.",
            canonical_url=page_url(f"/replay/{replay_id}"),
            og_image=DEFAULT_OG_IMAGE,
            noindex=True,
        )
    )


@app.get("/api/replay/{replay_id}")
async def api_replay(replay_id: str):
    """JSON API for replay stats."""
    pool = await get_db()
    if not pool:
        raise HTTPException(503, "Database not configured")

    from database import get_replay_by_ballchasing_id, get_replay_stats_for_replay
    replay = await get_replay_by_ballchasing_id(pool, replay_id)
    if not replay:
        raise HTTPException(404, "Replay not found")

    stats = await get_replay_stats_for_replay(pool, replay["id"])
    return {
        "replay": dict(replay),
        "players": [dict(r) for r in stats],
    }


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return PlainTextResponse(
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        f"Sitemap: {page_url('/sitemap.xml')}\n"
    )


@app.get("/sitemap.xml")
async def sitemap_xml():
    pages = [
        ("/", "daily", "1.0"),
        ("/about", "weekly", "0.8"),
        ("/stats", "hourly", "0.9"),
        ("/upload", "weekly", "0.8"),
    ]
    urls = "".join(
        f"<url><loc>{page_url(path)}</loc><changefreq>{freq}</changefreq><priority>{priority}</priority></url>"
        for path, freq, priority in pages
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}"
        "</urlset>"
    )
    return Response(content=xml, media_type="application/xml")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    body = """
    <section class="section">
      <div class="card">
        <h1>Page not found</h1>
        <p>The page you requested does not exist or was moved.</p>
        <div class="cta-group">
          <a class="btn btn-primary" href="/">Go Home</a>
          <a class="btn btn-secondary" href="/stats">View Stats</a>
        </div>
      </div>
    </section>
    """
    return HTMLResponse(
        page(
            "Not Found",
            body,
            active="home",
            description="Crossbar League page not found.",
            canonical_url=page_url(request.url.path),
            og_image=DEFAULT_OG_IMAGE,
            noindex=True,
        ),
        status_code=404,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
