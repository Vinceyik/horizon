'use strict';

const THEME_KEY = 'briefing-theme';
const HK = 'Asia/Hong_Kong';

const byId = (id) => document.getElementById(id);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function safeUrl(value) {
  try {
    const url = new URL(String(value), location.href);
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
  } catch (err) {
    return null;
  }
}

/* ---------- theme ---------- */

function applyTheme(theme, persist) {
  document.documentElement.dataset.theme = theme;
  if (persist) {
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (err) {
      /* storage disabled */
    }
  }
  const button = byId('theme-toggle');
  if (!button) return;
  button.textContent = theme === 'dark' ? '☀️' : '🌙';
  button.setAttribute('aria-label', theme === 'dark' ? '切換淺色模式' : '切換深色模式');
}

function initTheme() {
  let stored = null;
  try {
    stored = localStorage.getItem(THEME_KEY);
  } catch (err) {
    stored = null;
  }
  const prefersDark =
    window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  // The OS preference is followed until the reader makes an explicit choice,
  // so a later system change still applies.
  applyTheme(stored || (prefersDark ? 'dark' : 'light'), false);
  const button = byId('theme-toggle');
  if (button) {
    button.addEventListener('click', () => {
      applyTheme(
        document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark',
        true
      );
    });
  }
}

/* ---------- formatting ---------- */

function formatTimestamp(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return String(iso || '');
  return new Intl.DateTimeFormat('zh-HK', {
    timeZone: HK,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
}

function formatShort(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('zh-HK', {
    timeZone: HK,
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
}

function formatDayLabel(value) {
  const date = new Date(String(value) + 'T00:00:00+08:00');
  if (Number.isNaN(date.getTime())) return String(value || '');
  return new Intl.DateTimeFormat('zh-HK', {
    timeZone: HK,
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(date);
}

function hkDay(offsetDays) {  const now = new Date();
  const shifted = new Date(now.getTime() - offsetDays * 86400000);
  return new Intl.DateTimeFormat('sv-SE', { timeZone: HK }).format(shifted);
}

/* ---------- rendering ---------- */

function renderItem(item) {
  const card = el('article', 'card');

  const heading = el('h2');
  const link = el('a', null, item.title || '（無標題）');
  const url = safeUrl(item.url);
  link.href = url || '#';
  if (url) {
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
  }
  heading.appendChild(link);
  card.appendChild(heading);

  if (item.originalTitle && item.originalTitle !== item.title) {
    card.appendChild(el('p', 'original-title', item.originalTitle));
  }

  const meta = el('p', 'card-meta');
  if (item.source) meta.appendChild(el('span', null, item.source));
  if (item.publishedAt) meta.appendChild(el('span', null, formatShort(item.publishedAt)));
  if (typeof item.score === 'number' && Number.isFinite(item.score)) {
    meta.appendChild(el('span', 'badge', item.score.toFixed(1) + ' / 10'));
  }
  if (meta.childNodes.length) card.appendChild(meta);

  if (item.blurb) card.appendChild(el('p', 'blurb', item.blurb));

  if (item.summary) {
    card.appendChild(el('p', 'detail-body', item.summary));
  }

  if (Array.isArray(item.dataPoints) && item.dataPoints.length) {
    const list = el('ul', 'data-points');
    item.dataPoints.forEach((point) => list.appendChild(el('li', null, point)));
    card.appendChild(list);
  }

  return card;
}

function renderGroup(group, index) {
  const section = el('section', 'group');
  section.id = 'panel-' + group.id;
  section.setAttribute('role', 'tabpanel');
  section.setAttribute('aria-labelledby', 'tab-' + group.id);
  section.dataset.index = String(index);

  if (group.overview) {
    section.appendChild(el('p', 'overview', group.overview));
  }

  if (group.status === 'failed') {
    const notice = el('p', 'notice', group.note || '來源暫時無法讀取');
    notice.dataset.tone = 'warn';
    section.appendChild(notice);
  } else if (!group.items || !group.items.length) {
    section.appendChild(el('p', 'notice', group.note || '今日無新內容'));
  } else {
    group.items.forEach((item) => section.appendChild(renderItem(item)));
  }

  return section;
}

function renderDay(data, groups) {
  const day = el('section', 'day');

  const header = el('div', 'day-header');
  const toggle = el('button', 'day-toggle');
  toggle.type = 'button';
  toggle.setAttribute('aria-expanded', 'true');
  toggle.appendChild(el('span', 'day-label', formatDayLabel(data.date)));
  toggle.appendChild(el('span', 'day-count', (Number(data.selected) || 0) + ' 條'));

  const body = el('div', 'day-body');
  groups.forEach((group, index) => body.appendChild(renderGroup(group, index)));

  toggle.addEventListener('click', () => {
    const expanded = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
    body.hidden = expanded;
  });

  header.appendChild(toggle);
  day.appendChild(header);
  day.appendChild(body);
  return day;
}

function selectTab(groupId) {
  const tabs = Array.from(document.querySelectorAll('.tab'));
  const panels = Array.from(document.querySelectorAll('.group'));
  if (!tabs.length) return;

  let target = tabs.find((tab) => tab.dataset.group === groupId);
  if (!target) target = tabs[0];

  tabs.forEach((tab) => {
    const selected = tab === target;
    tab.setAttribute('aria-selected', selected ? 'true' : 'false');
    tab.tabIndex = selected ? 0 : -1;
  });
  panels.forEach((panel) => {
    panel.hidden = panel.id !== 'panel-' + target.dataset.group;
  });

  if (location.hash.slice(1) !== target.dataset.group) {
    history.replaceState(null, '', '#' + target.dataset.group);
  }
}

function buildTabs(groups) {
  const nav = byId('tabs');
  nav.replaceChildren();

  groups.forEach((group) => {
    const tab = el('button', 'tab', group.name || group.id);
    tab.type = 'button';
    tab.id = 'tab-' + group.id;
    tab.dataset.group = group.id;
    tab.setAttribute('role', 'tab');
    tab.setAttribute('aria-controls', 'panel-' + group.id);
    tab.setAttribute('aria-selected', 'false');
    tab.tabIndex = -1;
    tab.addEventListener('click', () => selectTab(group.id));
    nav.appendChild(tab);
  });

  nav.addEventListener('keydown', (event) => {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
    const tabs = Array.from(nav.querySelectorAll('.tab'));
    const current = tabs.findIndex((tab) => tab.getAttribute('aria-selected') === 'true');
    if (current === -1) return;
    event.preventDefault();
    const delta = event.key === 'ArrowRight' ? 1 : -1;
    const next = (current + delta + tabs.length) % tabs.length;
    tabs[next].focus();
    selectTab(tabs[next].dataset.group);
  });
}

function renderFailures(failures) {
  const status = byId('status');
  status.replaceChildren();
  if (!Array.isArray(failures) || !failures.length) return;
  const parts = failures.map((failure) => {
    const source = failure && failure.source ? failure.source : '未知來源';
    const reason = failure && failure.reason ? failure.reason : '未提供原因';
    return source + '：' + reason;
  });
  status.textContent = '部分來源讀取失敗 · ' + parts.join(' · ');
}

function render(data) {
  byId('last-updated').textContent = data.generatedAt
    ? '最後更新：' + formatTimestamp(data.generatedAt)
    : '未有更新時間';

  const counts = byId('counts');
  const selected = Number(data.selected) || 0;
  const total = Number(data.totalFetched) || 0;
  counts.textContent = selected + ' / ' + total + ' 條';

  const groups = Array.isArray(data.groups) ? data.groups : [];
  const panels = byId('panels');
  panels.replaceChildren();
  if (groups.length) {
    panels.appendChild(renderDay(data, groups));
  } else {
    panels.appendChild(el('p', 'notice', '今日無新內容'));
  }

  buildTabs(groups);
  renderFailures(data.failures);

  const wanted = location.hash.slice(1);
  selectTab(wanted && groups.some((g) => g.id === wanted) ? wanted : groups[0] && groups[0].id);
}

function errorState() {
  const panels = byId('panels');
  panels.replaceChildren();
  const notice = el('p', 'notice', '無法載入簡報資料。');
  notice.dataset.tone = 'warn';
  panels.appendChild(notice);

  const retry = el('button', 'retry', '重試');
  retry.type = 'button';
  retry.addEventListener('click', () => window.location.reload());
  panels.appendChild(retry);

  byId('tabs').replaceChildren();
  byId('last-updated').textContent = '未更新';
  byId('counts').textContent = '';
  byId('status').textContent = '';
}

/* ---------- archive ---------- */

async function probeArchive() {
  const days = [];
  for (let i = 0; i < 30; i += 1) days.push(hkDay(i));
  const results = await Promise.all(
    days.map(async (day) => {
      try {
        const res = await fetch('archive/' + day + '.json', { method: 'HEAD' });
        return res.ok ? day : null;
      } catch (err) {
        return null;
      }
    })
  );
  return results.filter(Boolean);
}

async function initWithArchive(selectedDay) {
  const row = byId('date-row');
  const select = byId('date-select');
  const available = await probeArchive();
  if (!available.length) return;

  select.replaceChildren();
  available.forEach((day) => {
    const option = el('option', null, day);
    option.value = day;
    if (day === selectedDay) option.selected = true;
    select.appendChild(option);
  });

  select.addEventListener('change', () => {
    window.location.search = '?date=' + encodeURIComponent(select.value);
  });

  row.hidden = false;
}

/* ---------- boot ---------- */

async function load() {
  const params = new URLSearchParams(window.location.search);
  const day = params.get('date');
  const url = day ? 'archive/' + day + '.json' : 'data.json';

  try {
    const response = await fetch(url, { cache: 'no-cache' });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const data = await response.json();
    render(data);
  } catch (err) {
    errorState();
  }

  initWithArchive(day).catch(() => {});
}

initTheme();
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', load);
} else {
  load();
}
