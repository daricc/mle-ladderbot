/**
 * MLE Site - Interactive enhancements
 */

document.addEventListener('DOMContentLoaded', () => {
  initHeaderInteractivity();
  initScrollReveal();
  initSortableStats();
  initTierCards();
  initSmoothNav();
  initMmrCalculator();
});

/** Header scroll + mobile menu interactions */
function initHeaderInteractivity() {
  const header = document.querySelector('.site-header');
  const nav = document.querySelector('.nav');
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (!header || !nav) return;

  const activeLink = navLinks?.querySelector('a.active');
  if (activeLink) activeLink.setAttribute('aria-current', 'page');

  const onScroll = () => {
    header.classList.toggle('is-scrolled', window.scrollY > 12);
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  if (!navToggle) return;
  const navPanelId = navToggle.getAttribute('aria-controls');
  const navPanel = navPanelId ? document.getElementById(navPanelId) : navToggle.nextElementSibling;
  if (!navPanel) return;

  const setMenuState = (isExpanded) => {
    navToggle.setAttribute('aria-expanded', String(isExpanded));
    navPanel.classList.toggle('is-open', isExpanded);
    document.body.classList.toggle('nav-open', isExpanded);
  };

  const closeMenu = () => {
    setMenuState(false);
    navToggle.focus();
  };

  navToggle.addEventListener('click', () => {
    const isExpanded = navToggle.getAttribute('aria-expanded') === 'true';
    setMenuState(!isExpanded);
  });

  document.addEventListener('click', (event) => {
    const isExpanded = navToggle.getAttribute('aria-expanded') === 'true';
    if (!isExpanded) return;
    if (!nav.contains(event.target)) setMenuState(false);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    const isExpanded = navToggle.getAttribute('aria-expanded') === 'true';
    if (isExpanded) closeMenu();
  });

  navPanel.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => setMenuState(false));
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 768) setMenuState(false);
  });
}

/** Fade-in elements on scroll */
function initScrollReveal() {
  const els = document.querySelectorAll('.reveal, .tier-card, .division-detail, .section');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
  els.forEach(el => observer.observe(el));
}

/** Sortable stats table */
function initSortableStats() {
  const table = document.querySelector('.stats-table');
  if (!table) return;
  const tbody = table.querySelector('tbody');
  const thead = table.querySelector('thead tr');
  if (!tbody || !thead || tbody.querySelector('.stats-empty')) return;

  const headers = thead.querySelectorAll('th[data-sort]');
  headers.forEach(th => {
    th.style.cursor = 'pointer';
    th.classList.add('sortable');
    th.addEventListener('click', () => {
      const col = th.dataset.sort;
      const dir = th.dataset.dir === 'asc' ? 'desc' : 'asc';
      headers.forEach(h => h.removeAttribute('data-dir'));
      th.dataset.dir = dir;
      sortTable(tbody, col, dir);
    });
  });
}

function sortTable(tbody, col, dir) {
  const rows = [...tbody.querySelectorAll('tr')];
  const idx = { rank: 0, player: 1, elo: 2, mmr: 3, record: 4 }[col] ?? 0;
  const mult = dir === 'asc' ? 1 : -1;
  rows.sort((a, b) => {
    let va = a.cells[idx]?.textContent?.trim() ?? '';
    let vb = b.cells[idx]?.textContent?.trim() ?? '';
    if (idx === 0 || idx === 2 || idx === 3) {
      va = parseInt(va.replace(/\D/g, '')) || 0;
      vb = parseInt(vb.replace(/\D/g, '')) || 0;
      return mult * (va - vb);
    }
    return mult * va.localeCompare(vb);
  });
  rows.forEach(r => tbody.appendChild(r));
  rows.forEach((r, i) => {
    const rankCell = r.querySelector('.rank');
    if (rankCell) rankCell.textContent = i + 1;
  });
}

/** Tier cards - expand on click for more info */
function initTierCards() {
  document.querySelectorAll('.tier-card').forEach(card => {
    card.addEventListener('click', () => {
      const open = card.classList.contains('expanded');
      document.querySelectorAll('.tier-card.expanded').forEach(c => c.classList.remove('expanded'));
      if (!open) card.classList.add('expanded');
    });
  });
}

/** MMR division calculator */
function initMmrCalculator() {
  const input = document.getElementById('mmr-input');
  const btn = document.getElementById('mmr-check');
  const result = document.getElementById('mmr-result');
  if (!input || !btn || !result) return;

  const divisions = [
    { name: 'Apex Circuit', min: 1700, max: 9999 },
    { name: 'Ascendant Circuit', min: 1500, max: 1700 },
    { name: 'Elite Circuit', min: 1300, max: 1500 },
    { name: 'Rival Circuit', min: 1100, max: 1300 },
    { name: 'Open Circuit', min: 0, max: 1100 },
  ];

  btn.addEventListener('click', () => {
    const mmr = parseInt(input.value, 10) || 0;
    if (mmr < 0) { result.textContent = 'Enter a valid MMR.'; return; }
    const div = divisions.find(d => mmr >= d.min && mmr < d.max);
    result.textContent = div
      ? `You're in ${div.name}`
      : `MMR ${mmr} -> Open Circuit (entry tier)`;
    result.classList.add('show');
  });

  input.addEventListener('keydown', e => { if (e.key === 'Enter') btn.click(); });
}

/** Smooth scroll for anchor links */
function initSmoothNav() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const id = a.getAttribute('href').slice(1);
      const target = document.getElementById(id);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' });
      }
    });
  });
}
