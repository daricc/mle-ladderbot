"""MLE LadderBot - Server-exclusive ranking ladder for 1v1/2v2/3v3."""
import discord
from discord import app_commands
from discord.ext import commands
import asyncpg
import asyncio
from typing import Optional

import config
from database import (
    init_db,
    get_player,
    register_player,
    update_player_mmr,
    get_leaderboard,
    record_match,
    apply_elo_decay,
    get_weekly_challenges,
    insert_replay,
    insert_replay_stats,
    get_replay_by_ballchasing_id,
    get_replay_stats_for_replay,
)
from tracker_api import get_mmr
from elo_model import calculate_elo_change
from replay import (
    upload_replay,
    get_replay,
    extract_player_stats,
    compute_boost_wasted_pct,
    build_player_summary,
    generate_insights,
    parse_replay_bytes,
    replay_id_from_bytes,
)


class LadderBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.db: Optional[asyncpg.Pool] = None

    async def setup_hook(self):
        self.db = await init_db()
        await self.tree.sync()
        self.loop.create_task(self._periodic_tasks())

    async def close(self):
        if self.db:
            await self.db.close()
        await super().close()

    async def _periodic_tasks(self):
        """Background: MMR sync and ELO decay."""
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(3600)  # Every hour
            if self.db:
                try:
                    await apply_elo_decay(self.db)
                except Exception:
                    pass


bot = LadderBot()


@bot.tree.command(name="register", description="Link your Epic or Steam ID for MMR sync")
@app_commands.describe(
    platform="epic or steam",
    platform_id="Epic username (e.g. PlayerName) or Steam 64-bit ID"
)
async def register(
    interaction: discord.Interaction,
    platform: str,
    platform_id: str
):
    platform = platform.lower().strip()
    if platform not in ("epic", "steam"):
        await interaction.response.send_message(
            "❌ Platform must be `epic` or `steam`.",
            ephemeral=True
        )
        return

    if not bot.db:
        await interaction.response.send_message("Bot database not ready.", ephemeral=True)
        return

    discord_id = str(interaction.user.id)
    epic_id = platform_id if platform == "epic" else None
    steam_id = platform_id if platform == "steam" else None

    await register_player(bot.db, discord_id, epic_id=epic_id, steam_id=steam_id)

    # Try to fetch MMR from Tracker.gg
    mmr = None
    if config.TRACKER_GG_API_KEY:
        mmr = await get_mmr(platform, platform_id)
        if mmr is not None:
            await update_player_mmr(bot.db, discord_id, mmr)

    player = await get_player(bot.db, discord_id)
    msg = f"✅ Registered! Linked **{platform}** ID: `{platform_id}`"
    if mmr is not None:
        msg += f"\n📊 Current MMR: **{mmr}**"
    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="leaderboard", description="View the ladder leaderboard")
@app_commands.describe(
    limit="Number of players to show (default 10)",
    sort_by="Sort by: elo, mmr, wins_1v1, wins_2v2, wins_3v3"
)
async def leaderboard(
    interaction: discord.Interaction,
    limit: Optional[int] = 10,
    sort_by: Optional[str] = "elo"
):
    if not bot.db:
        await interaction.response.send_message("Bot database not ready.", ephemeral=True)
        return

    limit = min(25, max(1, limit or 10))
    players = await get_leaderboard(bot.db, limit=limit, sort_by=sort_by or "elo")

    if not players:
        await interaction.response.send_message("No players on the ladder yet. Use `/register` to join!")
        return

    lines = []
    for i, p in enumerate(players, 1):
        elo = int(p.get("elo", 0))
        mmr = p.get("mmr") or "—"
        discord_id = p.get("discord_id", "")
        # Resolve user if in guild
        try:
            user = await bot.fetch_user(int(discord_id))
            name = user.display_name
        except Exception:
            name = f"<@{discord_id}>"
        lines.append(f"**{i}.** {name} — ELO: **{elo}** | MMR: {mmr}")

    embed = discord.Embed(
        title="🏆 MLE Ladder Leaderboard",
        description="\n".join(lines),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Sorted by {sort_by or 'elo'}")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="profile", description="View your ladder profile")
async def profile(interaction: discord.Interaction):
    if not bot.db:
        await interaction.response.send_message("Bot database not ready.", ephemeral=True)
        return

    discord_id = str(interaction.user.id)
    player = await get_player(bot.db, discord_id)

    if not player:
        await interaction.response.send_message(
            "You're not registered. Use `/register` to join the ladder!",
            ephemeral=True
        )
        return

    elo = int(player.get("elo", 0))
    mmr = player.get("mmr") or "—"
    w1, l1 = player.get("wins_1v1", 0), player.get("losses_1v1", 0)
    w2, l2 = player.get("wins_2v2", 0), player.get("losses_2v2", 0)
    w3, l3 = player.get("wins_3v3", 0), player.get("losses_3v3", 0)
    streak = player.get("win_streak", 0)

    embed = discord.Embed(
        title=f"📊 {interaction.user.display_name}'s Ladder Profile",
        color=discord.Color.blue()
    )
    embed.add_field(name="ELO", value=str(elo), inline=True)
    embed.add_field(name="MMR (Tracker.gg)", value=str(mmr), inline=True)
    embed.add_field(name="Win Streak", value=str(streak), inline=True)
    embed.add_field(name="1v1", value=f"{w1}W - {l1}L", inline=True)
    embed.add_field(name="2v2", value=f"{w2}W - {l2}L", inline=True)
    embed.add_field(name="3v3", value=f"{w3}W - {l3}L", inline=True)

    if player.get("epic_id"):
        embed.add_field(name="Epic", value=player["epic_id"], inline=False)
    if player.get("steam_id"):
        embed.add_field(name="Steam", value=player["steam_id"], inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="report", description="Report a match result (winner only)")
@app_commands.describe(
    opponent="The Discord user who lost",
    playlist="1v1, 2v2, or 3v3"
)
async def report(
    interaction: discord.Interaction,
    opponent: discord.Member,
    playlist: str
):
    if not bot.db:
        await interaction.response.send_message("Bot database not ready.", ephemeral=True)
        return

    playlist = playlist.strip().lower()
    if playlist not in ("1v1", "2v2", "3v3"):
        await interaction.response.send_message(
            "❌ Playlist must be `1v1`, `2v2`, or `3v3`.",
            ephemeral=True
        )
        return

    winner_id = str(interaction.user.id)
    loser_id = str(opponent.id)

    if winner_id == loser_id:
        await interaction.response.send_message("You can't report a win against yourself!", ephemeral=True)
        return

    winner = await get_player(bot.db, winner_id)
    loser = await get_player(bot.db, loser_id)

    if not winner:
        await interaction.response.send_message(
            "You must be registered first. Use `/register`!",
            ephemeral=True
        )
        return
    if not loser:
        await interaction.response.send_message(
            f"{opponent.display_name} is not on the ladder. They need to `/register` first!",
            ephemeral=True
        )
        return

    winner_elo = float(winner.get("elo", config.DEFAULT_ELO))
    loser_elo = float(loser.get("elo", config.DEFAULT_ELO))
    winner_streak = winner.get("win_streak", 0)

    gain, loss = calculate_elo_change(winner_elo, loser_elo, winner_streak, playlist)

    await record_match(
        bot.db, playlist, winner_id, loser_id,
        winner_elo, loser_elo, gain
    )

    new_winner_elo = int(winner_elo + gain)
    new_loser_elo = int(loser_elo - loss)

    embed = discord.Embed(
        title="✅ Match Recorded",
        description=f"**{interaction.user.display_name}** def. **{opponent.display_name}** ({playlist})",
        color=discord.Color.green()
    )
    embed.add_field(name="ELO Change", value=f"+{gain:.1f} / -{loss:.1f}", inline=True)
    embed.add_field(name="New Ratings", value=f"{new_winner_elo} / {new_loser_elo}", inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="challenges", description="View weekly ladder challenges")
async def challenges(interaction: discord.Interaction):
    """Show active weekly challenges."""
    if not bot.db:
        await interaction.response.send_message("Bot database not ready.", ephemeral=True)
        return

    rows = await get_weekly_challenges(bot.db)

    if not rows:
        await interaction.response.send_message(
            "No active weekly challenges this week. Check back later!",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="📅 Weekly Ladder Challenges",
        color=discord.Color.purple()
    )
    for row in rows:
        name = row.get("name", "Challenge")
        desc = row.get("description", "Complete for ELO bonus!")
        reward = row.get("reward_elo", 0)
        embed.add_field(
            name=f"🏆 {name}",
            value=f"{desc}\n**Reward:** +{reward} ELO",
            inline=False
        )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="sync", description="Manually sync your MMR from Tracker.gg")
async def sync(interaction: discord.Interaction):
    if not bot.db or not config.TRACKER_GG_API_KEY:
        await interaction.response.send_message(
            "MMR sync is not configured (missing Tracker.gg API key).",
            ephemeral=True
        )
        return

    player = await get_player(bot.db, str(interaction.user.id))
    if not player:
        await interaction.response.send_message(
            "Register first with `/register`!",
            ephemeral=True
        )
        return

    mmr = None
    if player.get("epic_id"):
        mmr = await get_mmr("epic", player["epic_id"])
    if mmr is None and player.get("steam_id"):
        mmr = await get_mmr("steam", player["steam_id"])

    if mmr is None:
        await interaction.response.send_message(
            "Could not fetch MMR. Check your linked Epic/Steam ID.",
            ephemeral=True
        )
        return

    await update_player_mmr(bot.db, str(interaction.user.id), mmr)
    await interaction.response.send_message(f"✅ MMR synced: **{mmr}**", ephemeral=True)


# ---- ReplayAI (local parser, Ballchasing optional) ----

@bot.tree.command(name="upload_replay", description="Parse a Rocket League replay for stats & insights")
@app_commands.describe(replay_file=".replay file from RL")
async def upload_replay_cmd(
    interaction: discord.Interaction,
    replay_file: discord.Attachment,
):
    """Parse replay locally (or via Ballchasing if local fails). No API key needed."""
    if not replay_file.filename or not replay_file.filename.lower().endswith(".replay"):
        await interaction.response.send_message(
            "Please attach a `.replay` file from Rocket League.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=False)

    try:
        file_bytes = await replay_file.read()
    except Exception:
        await interaction.followup.send("Failed to read attachment.", ephemeral=True)
        return

    # Try local parser first (no API needed)
    result = await asyncio.to_thread(parse_replay_bytes, file_bytes)
    replay_id = None
    meta = {}
    players = []

    if result:
        meta, players = result
        replay_id = replay_id_from_bytes(file_bytes)
    elif config.BALLCHASING_API_TOKEN:
        # Fallback to Ballchasing
        replay_id = await upload_replay(file_bytes, replay_file.filename)
        if replay_id:
            for attempt in range(6):
                await asyncio.sleep(3)
                replay_data = await get_replay(replay_id)
                if replay_data and replay_data.get("status") == "ok":
                    players = extract_player_stats(replay_data)
                    meta = {
                        "title": replay_data.get("title"),
                        "map_code": replay_data.get("map_code"),
                        "team_size": replay_data.get("team_size"),
                        "duration": replay_data.get("duration"),
                        "overtime": replay_data.get("overtime", False),
                    }
                    break
            else:
                await interaction.followup.send(
                    f"Upload succeeded but replay is still processing. "
                    f"Check back: https://ballchasing.com/replay/{replay_id}",
                    ephemeral=True,
                )
                return

    if not players:
        await interaction.followup.send(
            "Could not parse replay. Ensure it's a valid .replay file. "
            "(First upload downloads rattletrap ~12MB)",
            ephemeral=True,
        )
        return

    # Store in DB
    if bot.db and replay_id:
        try:
            db_replay_id = await insert_replay(
                bot.db,
                ballchasing_id=replay_id,
                discord_uploader_id=str(interaction.user.id),
                title=meta.get("title"),
                map_code=meta.get("map_code"),
                playlist_id="",
                team_size=meta.get("team_size"),
                duration=meta.get("duration"),
                overtime=meta.get("overtime", False),
            )
            for p in players:
                await insert_replay_stats(bot.db, db_replay_id, p)
        except Exception:
            pass

    # Build embed
    duration = meta.get("duration", 0) or 0
    mins = duration // 60 if duration else 0
    secs = duration % 60 if duration else 0
    title = meta.get("title", "Replay") or "Replay"

    desc = f"**{title}**\n⏱ {mins}:{secs:02d}"
    if replay_id and not replay_id.startswith("local-"):
        desc += f" | [View on Ballchasing](https://ballchasing.com/replay/{replay_id})"
    embed = discord.Embed(title="🎮 Replay Stats", description=desc, color=discord.Color.blue())

    blue_players = [p for p in players if p.get("team_color") == "blue"]
    orange_players = [p for p in players if p.get("team_color") == "orange"]

    def add_team(team_players: list, team_name: str):
        if team_players:
            lines = [build_player_summary(p) for p in team_players]
            embed.add_field(name=team_name, value="\n".join(lines), inline=False)

    add_team(blue_players, "🔵 Blue")
    add_team(orange_players, "🟠 Orange")

    waste_pcts = {i: compute_boost_wasted_pct(p) for i, p in enumerate(players)}
    insights = generate_insights(players, waste_pcts)
    if insights:
        embed.add_field(name="💡 Insights", value="\n".join(insights), inline=False)

    embed.set_footer(text=f"ID: {replay_id[:20] if replay_id else 'local'}... | Use /replay_stats <id> for full stats")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="replay_stats", description="View stored stats for a replay")
@app_commands.describe(replay_id="Replay ID (from /upload_replay footer, or Ballchasing ID)")
async def replay_stats_cmd(interaction: discord.Interaction, replay_id: str):
    """Show replay stats from DB or fetch from Ballchasing if not stored."""
    replay_id = replay_id.strip()
    if not replay_id:
        await interaction.response.send_message("Provide a replay ID.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)

    # Try DB first
    if bot.db:
        replay = await get_replay_by_ballchasing_id(bot.db, replay_id)
        if replay:
            stats_rows = await get_replay_stats_for_replay(bot.db, replay["id"])
            if stats_rows:
                embed = discord.Embed(
                    title=f"📊 Replay Stats — {replay.get('title', 'Replay')}",
                    url=f"https://ballchasing.com/replay/{replay_id}",
                    color=discord.Color.blue(),
                )
                for row in stats_rows:
                    line = build_player_summary(dict(row))
                    embed.add_field(
                        name=row.get("player_name", "Player"),
                        value=line,
                        inline=False,
                    )
                await interaction.followup.send(embed=embed)
                return

    # Fallback: fetch from Ballchasing
    if not config.BALLCHASING_API_TOKEN:
        await interaction.followup.send(
            "Replay not in DB and Ballchasing API not configured.",
            ephemeral=True,
        )
        return

    replay_data = await get_replay(replay_id)
    if not replay_data or replay_data.get("status") != "ok":
        await interaction.followup.send(
            "Replay not found or still processing. Check the ID.",
            ephemeral=True,
        )
        return

    players = extract_player_stats(replay_data)
    embed = discord.Embed(
        title=f"📊 Replay Stats — {replay_data.get('title', 'Replay')}",
        url=f"https://ballchasing.com/replay/{replay_id}",
        color=discord.Color.blue(),
    )
    for p in players:
        embed.add_field(
            name=p.get("name", "Player"),
            value=build_player_summary(p),
            inline=False,
        )
    await interaction.followup.send(embed=embed)


def main():
    if not config.DISCORD_TOKEN:
        print("Set DISCORD_TOKEN in .env")
        return
    bot.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
