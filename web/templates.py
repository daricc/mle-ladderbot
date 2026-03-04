"""HTML templates for Crossbar League website."""

from html import escape

LAYOUT_HEAD = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{description}">
  <meta name="theme-color" content="#0a0e14">
  <meta property="og:site_name" content="Crossbar League">
  <meta property="og:type" content="{og_type}">
  <meta property="og:title" content="{title} | Crossbar League">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:image" content="{og_image}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} | Crossbar League">
  <meta name="twitter:description" content="{description}">
  <meta name="twitter:image" content="{og_image}">
  {robots_meta}
  <link rel="canonical" href="{canonical_url}">
  <link rel="icon" type="image/svg+xml" href="/static/images/crossbar-logo-icon.svg">
  <title>{title} | Crossbar League</title>
  <link rel="stylesheet" href="/static/site.css">
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <a href="#main-content" class="skip-link">Skip to main content</a>
  <header class="site-header">
    <nav class="nav" aria-label="Primary">
      <a href="/" class="brand-link" aria-label="Crossbar League home">
        <img src="/static/images/crossbar-logo.svg" alt="Crossbar League" class="brand-logo brand-logo-desktop">
        <img src="/static/images/crossbar-logo-icon.svg" alt="" class="brand-logo brand-logo-mobile">
      </a>
      <button
        type="button"
        class="nav-toggle"
        aria-expanded="false"
        aria-controls="primary-nav"
        aria-label="Toggle navigation menu">
        <span class="nav-toggle-line"></span>
        <span class="nav-toggle-line"></span>
        <span class="nav-toggle-line"></span>
      </button>
      <div class="nav-panel" id="primary-nav">
        <ul class="nav-links">
          <li><a href="/" class="{home_active}">Home</a></li>
          <li><a href="/about" class="{about_active}">About</a></li>
          <li><a href="/stats" class="{stats_active}">Stats</a></li>
          <li><a href="/upload" class="{upload_active}">Upload Replay</a></li>
          {auth_nav}
        </ul>
      </div>
    </nav>
  </header>
  <main id="main-content" tabindex="-1">
'''

LAYOUT_TAIL = '''
  </main>
  <footer class="site-footer">
    <img src="/static/images/crossbar-logo.svg" alt="" class="footer-logo"> Crossbar League - Draft-first Rocket League competition with seasonal circuits.
  </footer>
  <script src="/static/site.js"></script>
</body>
</html>
'''


def page(
    title: str,
    body: str,
    active: str = "home",
    description: str = "Crossbar League is a draft-first Rocket League competition with seasonal circuits and standings.",
    canonical_url: str = "https://crossbarleague.gg/",
    og_image: str = "https://crossbarleague.gg/static/images/crossbar-logo.svg",
    noindex: bool = False,
    og_type: str = "website",
    user_display: str | None = None,
    is_management: bool = False,
) -> str:
    safe_title = escape(title, quote=True)
    safe_description = escape(description, quote=True)
    safe_canonical_url = escape(canonical_url, quote=True)
    safe_og_image = escape(og_image, quote=True)
    safe_og_type = escape(og_type, quote=True)
    robots_meta = '<meta name="robots" content="noindex, nofollow">' if noindex else '<meta name="robots" content="index, follow">'
    active_home = "active" if active == "home" else ""
    active_about = "active" if active == "about" else ""
    active_stats = "active" if active == "stats" else ""
    active_upload = "active" if active == "upload" else ""
    if user_display:
        mgmt = '<li><a href="/management">Management</a></li>' if is_management else ''
        auth_nav = f'<li><a href="/register">Register</a></li>{mgmt}<li class="nav-user"><span>{escape(user_display)}</span> <a href="/auth/logout">Logout</a></li>'
    else:
        auth_nav = '<li><a href="/auth/discord" class="nav-login">Login with Discord</a></li>'
    return (
        LAYOUT_HEAD.format(
            title=safe_title,
            description=safe_description,
            canonical_url=safe_canonical_url,
            og_image=safe_og_image,
            robots_meta=robots_meta,
            og_type=safe_og_type,
            home_active=active_home,
            about_active=active_about,
            stats_active=active_stats,
            upload_active=active_upload,
            auth_nav=auth_nav,
        )
        + body
        + LAYOUT_TAIL
    )


HOME_PAGE = '''
    <section class="hero hero-home">
      <div class="hero-bg"></div>
      <span class="hero-badge">Rocket League Competitive League</span>
      <h1>Compete in a seasonal circuit built for team chemistry and smart play</h1>
      <p>Crossbar League is a player-led Rocket League ecosystem where captains draft balanced rosters, teams scrim with intent, and standings evolve weekly through five competitive circuits.</p>
      <img
        src="/static/images/hero-controller.svg"
        alt="Rocket League style controller and field line illustration"
        class="hero-illustration"
      >
      <div class="cta-group">
        <a href="/about" class="btn btn-primary">Learn How It Works</a>
        <a href="/stats" class="btn btn-secondary">View Leaderboards</a>
      </div>
    </section>

    <section class="section reveal">
      <h2>League Circuits</h2>
      <p>Players enter the circuit that matches their current MMR range. Open any card for details on pacing, expectations, and style of play.</p>
      <div class="league-tiers">
        <div class="tier-card" data-tier="foundation">
          <div class="tier-icon"><img src="/static/images/tier-foundation.svg" alt=""></div>
          <h3>Open Circuit</h3>
          <div class="mmr-range">0 – 1,100 MMR</div>
          <p>Entry point for rising players focusing on confidence and clean touches.</p>
          <p class="tier-detail">Perfect for developing rotations, spacing habits, and calm decision-making under pressure.</p>
        </div>
        <div class="tier-card" data-tier="academy">
          <div class="tier-icon"><img src="/static/images/tier-academy.svg" alt=""></div>
          <h3>Rival Circuit</h3>
          <div class="mmr-range">1,100 – 1,300 MMR</div>
          <p>Fast intermediate competition where mechanics and teamwork start to click.</p>
          <p class="tier-detail">Players sharpen recoveries, passing lanes, and controlled challenges in structured series play.</p>
        </div>
        <div class="tier-card" data-tier="champion">
          <div class="tier-icon"><img src="/static/images/tier-champion.svg" alt=""></div>
          <h3>Elite Circuit</h3>
          <div class="mmr-range">1,300 – 1,500 MMR</div>
          <p>High-tempo lobbies with reliable mechanics and coordinated pressure.</p>
          <p class="tier-detail">Promotion and relegation battles become central as teams fight for every point.</p>
        </div>
        <div class="tier-card" data-tier="master">
          <div class="tier-icon"><img src="/static/images/tier-master.svg" alt=""></div>
          <h3>Ascendant Circuit</h3>
          <div class="mmr-range">1,500 – 1,700 MMR</div>
          <p>Elite bracket where reads are faster and mistakes are punished quickly.</p>
          <p class="tier-detail">Refined team systems, disciplined boost control, and advanced setup plays define this level.</p>
        </div>
        <div class="tier-card" data-tier="premier">
          <div class="tier-icon"><img src="/static/images/tier-premier.svg" alt=""></div>
          <h3>Apex Circuit</h3>
          <div class="mmr-range">1,700+ MMR</div>
          <p>Top flight competition featuring the strongest rosters in Crossbar League.</p>
          <p class="tier-detail">The best teams chase circuit titles, playoff seeding, and the seasonal crown.</p>
        </div>
      </div>
    </section>
'''

ABOUT_PAGE = '''
    <section class="hero hero-about">
      <h1>About Crossbar League</h1>
      <p>Crossbar League is a competitive Rocket League community centered on a captain draft and five skill-banded circuits designed for steady progression.</p>
      <img
        src="/static/images/about-structure.svg"
        alt="A visual showing draft board, standings, and league format"
        class="hero-illustration hero-illustration-about"
      >
    </section>

    <section class="section reveal">
      <h2>Our Structure</h2>
      <p>Crossbar League runs in focused seasonal splits. Before each split, eligible players enter the draft pool and captains build rosters through a snake draft. Teams then compete on a fixed weekly schedule, with standings, tiebreakers, and movement between circuits based on results.</p>
    </section>

    <section class="section reveal">
      <h2>Circuit Breakdown</h2>
      <p>Placement is determined by your MMR at registration. Every circuit runs its own schedule, standings table, and postseason race.</p>
      <div class="about-grid">
        <div class="division-detail">
          <div class="division-icon"><img src="/static/images/tier-foundation.svg" alt=""></div>
          <h3>Open Circuit <span class="mmr-badge">0 – 1,100 MMR</span></h3>
          <p>Open Circuit is the launchpad for organized play. Teams focus on stable rotations, communication basics, and confidence on the ball while building match habits that transfer to higher circuits.</p>
        </div>
        <div class="division-detail">
          <div class="division-icon"><img src="/static/images/tier-academy.svg" alt=""></div>
          <h3>Rival Circuit <span class="mmr-badge">1,100 – 1,300 MMR</span></h3>
          <p>Rival Circuit connects development to serious contention. Players combine improving mechanics with better support positioning, and teams begin to run intentional passing patterns and kickoff plans.</p>
        </div>
        <div class="division-detail">
          <div class="division-icon"><img src="/static/images/tier-champion.svg" alt=""></div>
          <h3>Elite Circuit <span class="mmr-badge">1,300 – 1,500 MMR</span></h3>
          <p>Elite Circuit features reliable mechanics, high-pressure saves, and faster transitions. Teams are expected to punish gaps quickly, and movement between circuits creates real seasonal stakes.</p>
        </div>
        <div class="division-detail">
          <div class="division-icon"><img src="/static/images/tier-master.svg" alt=""></div>
          <h3>Ascendant Circuit <span class="mmr-badge">1,500 – 1,700 MMR</span></h3>
          <p>Ascendant Circuit is where advanced mechanics meet disciplined systems. Small tactical edges decide results, and teams must maintain composure through long possession and high-speed counterattacks.</p>
        </div>
        <div class="division-detail">
          <div class="division-icon"><img src="/static/images/tier-premier.svg" alt=""></div>
          <h3>Apex Circuit <span class="mmr-badge">1,700+ MMR</span></h3>
          <p>Apex Circuit is the top competitive layer in Crossbar League. It showcases high-IQ rotations, mechanical consistency at pace, and championship-level execution across every matchday.</p>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>The Draft Process</h2>
      <p>Before each split, players register and are placed into a draft pool based on their circuit-eligible MMR. Captains draft in snake order (for example: 1-2-3-4-5-5-4-3-2-1) to create balanced rosters. Once selected, players compete with that squad through the regular season and playoffs, with roster moves handled under league policy.</p>
    </section>

    <section class="section">
      <h2>How to Join</h2>
      <p>Join our Discord server to register for the upcoming season. You will need to link your Rocket League account (Epic or Steam) so we can verify your MMR. Once registered, you will be placed in the appropriate division and entered into the draft pool. Stay active, communicate with your team, and compete.</p>
      <img
        src="/static/images/join-discord.svg"
        alt="Discord and competition inspired join the league illustration"
        class="inline-feature-image"
      >
      <div class="cta-group">
        <a href="/stats" class="btn btn-primary">View Current Stats</a>
        <a href="/upload" class="btn btn-secondary">Upload a Replay</a>
      </div>
    </section>
'''

REGISTER_PAGE = '''
    <section class="section">
      <h1>Register</h1>
      <p>Link your RL Tracker profile and upload a replay to verify it&apos;s you. Once verified, captains and management can add replays to the league.</p>
      <div class="card" style="margin-top:1.5rem;">
        <h2>1. Link RL Tracker</h2>
        <p class="text-muted">Paste your Tracker.gg Rocket League profile URL (e.g. tracker.gg/rocketleague/profile/epic/YourName)</p>
        <form id="tracker-form">
          <input type="url" name="tracker_url" id="tracker-url" placeholder="https://tracker.gg/rocketleague/profile/epic/YourName" class="form-input" style="width:100%;max-width:480px;">
          <button type="submit" class="btn btn-primary" style="margin-top:0.5rem;">Save Tracker Link</button>
        </form>
        <p id="tracker-status" class="meta" style="margin-top:0.5rem;"></p>
      </div>
      <div class="card" style="margin-top:1.5rem;">
        <h2>2. Verify with Replay</h2>
        <p class="text-muted">Upload a replay where you played. We&apos;ll check it matches your Tracker profile.</p>
        <form id="verify-form">
          <label class="dropzone" id="verify-dropzone">
            <input type="file" name="file" accept=".replay" id="verify-file-input">
            <div class="icon">🎮</div>
            <p>Drop your .replay file here</p>
          </label>
          <button type="submit" class="btn btn-primary" id="verify-btn" disabled>Verify Identity</button>
        </form>
        <p id="verify-status" class="meta" style="margin-top:0.5rem;"></p>
      </div>
    </section>
    <script>
      const trackerForm = document.getElementById('tracker-form');
      const trackerUrl = document.getElementById('tracker-url');
      const trackerStatus = document.getElementById('tracker-status');
      const verifyForm = document.getElementById('verify-form');
      const verifyInput = document.getElementById('verify-file-input');
      const verifyBtn = document.getElementById('verify-btn');
      const verifyStatus = document.getElementById('verify-status');
      verifyInput.addEventListener('change', () => { verifyBtn.disabled = !verifyInput.files.length; });
      trackerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const res = await fetch('/api/register-tracker', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({url: trackerUrl.value}) });
        const d = await res.json().catch(() => ({}));
        trackerStatus.textContent = res.ok ? 'Saved. Now upload a replay to verify.' : (d.detail || 'Failed');
      });
      verifyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!verifyInput.files.length) return;
        const fd = new FormData(); fd.append('file', verifyInput.files[0]);
        verifyBtn.disabled = true;
        const res = await fetch('/api/verify-replay', { method: 'POST', body: fd });
        const d = await res.json().catch(() => ({}));
        verifyStatus.textContent = res.ok ? 'Verified! You can now upload replays (if you are captain or management).' : (d.detail || 'Verification failed. Make sure the replay contains you.');
        verifyBtn.disabled = false;
      });
    </script>
'''

MANAGEMENT_PAGE = '''
    <section class="section">
      <h1>Management</h1>
      <p>Edit league settings and manage user roles. Only management can access this.</p>
      <div class="card" style="margin-top:1.5rem;">
        <h2>Announcement</h2>
        <form id="settings-form">
          <label><textarea name="announcement" id="setting-announcement" rows="3" style="width:100%;max-width:560px;"></textarea></label>
          <button type="submit" class="btn btn-primary" style="margin-top:0.5rem;">Save</button>
        </form>
      </div>
      <div class="card" style="margin-top:1.5rem;">
        <h2>User Roles</h2>
        <p class="text-muted">Set role: player, captain (can store replays), or management.</p>
        <table class="stats-table" style="margin-top:0.5rem;">
          <thead><tr><th>User</th><th>Tracker</th><th>Verified</th><th>Role</th><th>Action</th></tr></thead>
          <tbody id="users-tbody"></tbody>
        </table>
      </div>
    </section>
    <script>
      (async () => {
        const r = await fetch('/api/league-settings');
        if (r.ok) { const d = await r.json(); document.getElementById('setting-announcement').value = d.announcement || ''; }
      })();
      document.getElementById('settings-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const val = document.getElementById('setting-announcement').value;
        await fetch('/api/league-settings', { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({announcement: val}) });
      });
      (async () => {
        const r = await fetch('/api/site-users');
        if (!r.ok) return;
        const d = await r.json();
        const tbody = document.getElementById('users-tbody');
        for (const u of d.users || []) {
          const tr = document.createElement('tr');
          const verified = u.verified_at ? 'Yes' : 'No';
          const roleSelect = document.createElement('select');
          ['player','captain','management'].forEach(role => {
            const o = document.createElement('option'); o.value = role; o.textContent = role; if (u.role === role) o.selected = true; roleSelect.appendChild(o);
          });
          roleSelect.addEventListener('change', async () => {
            await fetch('/api/site-users/' + encodeURIComponent(u.discord_id) + '/role', { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({role: roleSelect.value}) });
          });
          tr.innerHTML = '<td>' + (u.display_name || u.discord_id) + '</td><td>' + (u.rl_identifier || '—') + '</td><td>' + verified + '</td><td></td><td></td>';
          tr.querySelector('td:nth-child(4)').appendChild(roleSelect);
          tbody.appendChild(tr);
        }
      })();
    </script>
'''

UPLOAD_PAGE = '''
    <section class="section">
      <h1>Upload Replay</h1>
      <p>Parse your Rocket League .replay file to get stats & insights. Max 25MB.</p>
      <img
        src="/static/images/upload-replay.svg"
        alt="Upload replay illustration with file and chart"
        class="inline-feature-image upload-feature-image"
      >
      <div class="card" style="margin-top:1.5rem;">
        <form id="upload-form">
          <label class="dropzone" id="dropzone">
            <input type="file" name="file" accept=".replay" id="file-input">
            <div class="icon">🎮</div>
            <p>Drop your .replay file here or click to browse</p>
            <p style="font-size: 0.8rem; margin-top: 0.5rem;">Goals, assists, saves, shots, score</p>
          </label>
          <div class="form-row">
            <button type="submit" class="btn btn-primary" id="submit-btn" disabled>Parse Replay</button>
          </div>
        </form>
        <div id="error" class="error" style="display: none;"></div>
      </div>
    </section>
    <script>
      const dropzone = document.getElementById('dropzone');
      const fileInput = document.getElementById('file-input');
      const form = document.getElementById('upload-form');
      const submitBtn = document.getElementById('submit-btn');
      const errorEl = document.getElementById('error');
      function showError(msg) { errorEl.textContent = msg; errorEl.style.display = 'block'; }
      function hideError() { errorEl.style.display = 'none'; }
      dropzone.addEventListener('click', () => fileInput.click());
      dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
      dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
      dropzone.addEventListener('drop', (e) => {
        e.preventDefault(); dropzone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length && files[0].name.toLowerCase().endsWith('.replay')) {
          fileInput.files = files; submitBtn.disabled = false; hideError();
        } else { showError('Please drop a .replay file'); }
      });
      fileInput.addEventListener('change', () => { submitBtn.disabled = !fileInput.files.length; hideError(); });
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!fileInput.files.length) return;
        submitBtn.disabled = true; submitBtn.innerHTML = '<span class="spinner"></span> Parsing...'; hideError();
        const formData = new FormData(); formData.append('file', fileInput.files[0]);
        try {
          const res = await fetch('/api/upload', { method: 'POST', body: formData });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(data.detail || data.message || 'Error ' + res.status);
          window.location.href = data.url || '/replay/' + data.replay_id;
        } catch (err) {
          showError(err.message || 'Upload failed. Try again.');
          submitBtn.disabled = false; submitBtn.textContent = 'Parse Replay';
        }
      });
    </script>
'''
