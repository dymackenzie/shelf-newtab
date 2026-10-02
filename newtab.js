const $ = (s, el = document) => el.querySelector(s);
const SIZES = { 1: { w: 3.9, h: 14.5 }, 2: { w: 4.3, h: 17 }, 3: { w: 5.1, h: 19.5 }, 4: { w: 6.4, h: 22.5 } };
const GAP = 0.35, LEAN_ROOM = 2.7, WEEK = 7 * 864e5;
const DEFAULTS = { folder: '', ribbon: true, lean: true };

const state = {
  settings: { ...DEFAULTS },
  meta: {},      // url -> { s, ink }, synced so sizes follow you between computers
  icons: {},     // url -> data url, local only (too big for sync)
  folder: null,  // resolved bookmark folder node
  folders: [],   // every folder, for the settings dropdown
  books: [],     // flat list in shelf order
  top: null,     // host with the most visits this week
  editing: false,
};

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const host = url => { try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; } };
const favicon = url => chrome.runtime.getURL(`/_favicon/?pageUrl=${encodeURIComponent(url)}&size=64`);
const iconFor = url => state.icons[url] || favicon(url);
const metaFor = (url, i) => ({ s: 2, ink: Math.max(i, 0) % 4, ...(state.meta[url] || {}) });
const rem = () => parseFloat(getComputedStyle(document.documentElement).fontSize);

// chrome hands back a grey page icon for sites it has never visited. spot it and use a letter instead
async function sigOf(src) {
  const img = new Image();
  img.src = src;
  await img.decode();
  const c = document.createElement('canvas');
  c.width = c.height = 32;
  c.getContext('2d').drawImage(img, 0, 0, 32, 32);
  return c.toDataURL();
}
const blankSig = sigOf(favicon('https://shelf-no-icon.invalid/')).catch(() => null);
async function letterIfBlank(img, letter) {
  if (img.src.startsWith('data:')) return;
  try {
    const [blank, mine] = await Promise.all([blankSig, sigOf(img.src)]);
    if (blank && blank === mine) { img.hidden = true; letter.hidden = false; }
  } catch {}
}


async function loadStorage() {
  const sync = await chrome.storage.sync.get(null);
  state.settings = { ...DEFAULTS, ...(sync.settings || {}) };
  state.meta = {};
  for (const [k, v] of Object.entries(sync)) if (k.startsWith('b:')) state.meta[k.slice(2)] = v;
  const local = await chrome.storage.local.get(null);
  state.icons = {};
  for (const [k, v] of Object.entries(local)) if (k.startsWith('i:')) state.icons[k.slice(2)] = v;
}

async function loadBookmarks() {
  const [root] = await chrome.bookmarks.getTree();
  state.folders = [];
  const walk = (node, path) => {
    for (const c of node.children || []) {
      if (c.url) continue;
      const p = path ? `${path} / ${c.title}` : c.title;
      state.folders.push({ id: c.id, path: p, node: c });
      walk(c, p);
    }
  };
  walk(root, '');
  // folder is saved by its path, since bookmark ids differ between computers
  const hit = state.folders.find(f => f.path === state.settings.folder);
  state.folder = (hit || state.folders[0]).node;
}

// direct links make the first shelf, each subfolder gets its own labelled shelf
function groups() {
  const out = [{ label: null, items: [] }];
  for (const c of state.folder.children || []) {
    if (c.url) out[0].items.push(c);
    else out.push({ label: c.title, items: (c.children || []).filter(x => x.url) });
  }
  if (!out[0].items.length && out.length > 1) out.shift();
  return out;
}

async function weeklyTop() {
  if (!state.settings.ribbon || !chrome.history) return null;
  const { weekly } = await chrome.storage.local.get('weekly');
  if (weekly && Date.now() - weekly.at < 30 * 60e3) return weekly.top;
  const since = Date.now() - WEEK;
  const hosts = new Set(state.books.map(b => host(b.url)));
  const items = (await chrome.history.search({ text: '', startTime: since, maxResults: 3000 }))
    .filter(it => hosts.has(host(it.url))).slice(0, 500);
  const counts = {};
  await Promise.all(items.map(async it => {
    const visits = await chrome.history.getVisits({ url: it.url });
    const h = host(it.url);
    counts[h] = (counts[h] || 0) + visits.filter(v => v.visitTime >= since).length;
  }));
  let top = null;
  for (const [h, n] of Object.entries(counts)) if (n >= 3 && (!top || n > counts[top])) top = h;
  await chrome.storage.local.set({ weekly: { at: Date.now(), top } });
  return top;
}


function render() {
  const main = $('#shelves');
  main.textContent = '';
  const avail = main.clientWidth / rem();
  const gs = groups();
  state.books = gs.flatMap(g => g.items);
  document.body.classList.toggle('editing', state.editing);
  $('#hint').hidden = !state.editing;
  $('#edit').classList.toggle('on', state.editing);

  if (!state.books.length) {
    main.innerHTML = `<div class="empty">Nothing in ${esc(state.folder.title)} yet. Press + to add a book, or pick another folder in settings.</div><div class="plank"></div>`;
    return;
  }

  let n = 0, last = null, lastRow = null, lastRowW = 0;
  for (const g of gs) {
    const sec = document.createElement('section');
    sec.className = 'group';
    if (g.label) sec.innerHTML = `<h2>${esc(g.label)}</h2>`;
    let row = null, rowW = 0;
    const newRow = () => {
      row = document.createElement('div'); row.className = 'row';
      const plank = document.createElement('div'); plank.className = 'plank';
      sec.append(row, plank); rowW = 0;
    };
    newRow();
    if (!g.items.length) row.innerHTML = '<span class="empty">empty shelf</span>';
    for (const b of g.items) {
      const m = metaFor(b.url, n);
      const w = SIZES[m.s].w;
      if (rowW && rowW + GAP + w > avail) newRow();
      const el = spine(b, m, n++);
      row.append(el);
      rowW += (rowW ? GAP : 0) + w;
      last = el; lastRow = row; lastRowW = rowW;
    }
    main.append(sec);
  }
  if (state.settings.lean && !state.editing && state.books.length > 1 && lastRow.children.length > 1 && lastRowW + LEAN_ROOM <= avail) {
    last.classList.add('lean');
  }
}

function spine(b, m, i) {
  const a = document.createElement('a');
  const { w, h } = SIZES[m.s];
  a.className = 'book';
  a.href = b.url;
  a.dataset.id = b.id;
  a.title = `${b.title}\n${host(b.url)}`;
  a.style.cssText = `width:${w}rem;height:${h}rem;--bg:var(--ink${m.ink}-bg);--fg:var(--ink${m.ink}-fg)`;
  a.draggable = state.editing;
  a.innerHTML = `${state.top && host(b.url) === state.top ? '<i class="ribbon"></i>' : ''}
    <span class="chip"><img alt=""><span class="letter" hidden></span></span><span class="nm"></span><span class="k mono">${i < 9 ? i + 1 : ''}</span>`;
  const name = b.title || host(b.url);
  $('img', a).src = iconFor(b.url);
  $('.letter', a).textContent = name.trim().charAt(0).toUpperCase();
  $('.nm', a).textContent = name;
  letterIfBlank($('img', a), $('.letter', a));
  return a;
}

let queued = false;
function refresh(reload = true) {
  if (queued) return;
  queued = true;
  requestAnimationFrame(async () => {
    queued = false;
    if (reload) { await loadStorage(); await loadBookmarks(); }
    render();
  });
}


function open(url, background) {
  // chrome:// and file:// links can't be followed from a page, so go through the tabs api
  if (background) chrome.tabs.create({ url, active: false });
  else if (/^(https?|ftp):/.test(url)) location.href = url;
  else chrome.tabs.update({ url });
}

$('#shelves').addEventListener('click', e => {
  const a = e.target.closest('.book');
  if (!a) return;
  const b = state.books.find(x => x.id === a.dataset.id);
  if (state.editing) { e.preventDefault(); bookPanel(b, a); return; }
  if (!/^(https?|ftp):/.test(b.url)) { e.preventDefault(); open(b.url, e.ctrlKey || e.metaKey); }
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { if (!$('#panel').hidden) closePanel(); else if (state.editing) toggleEdit(); return; }
  if (e.target.closest('input, select, textarea') || !$('#panel').hidden || e.altKey) return;
  if (/^[1-9]$/.test(e.key)) {
    const b = state.books[+e.key - 1];
    if (b) { e.preventDefault(); open(b.url, e.ctrlKey || e.metaKey); }
  }
});


function toggleEdit() {
  state.editing = !state.editing;
  closePanel();
  render();
}
$('#edit').addEventListener('click', toggleEdit);

let dragId = null;
const clearDrop = () => document.querySelectorAll('.drop-before, .drop-after').forEach(el => el.classList.remove('drop-before', 'drop-after'));
$('#shelves').addEventListener('dragstart', e => {
  const a = e.target.closest('.book');
  if (!a || !state.editing) return;
  dragId = a.dataset.id;
  a.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
  closePanel();
});
$('#shelves').addEventListener('dragover', e => {
  const a = e.target.closest('.book');
  if (!dragId || !a || a.dataset.id === dragId) return;
  e.preventDefault();
  clearDrop();
  const r = a.getBoundingClientRect();
  a.classList.add(e.clientX < r.left + r.width / 2 ? 'drop-before' : 'drop-after');
});
$('#shelves').addEventListener('drop', async e => {
  const a = e.target.closest('.book');
  if (!dragId || !a) return;
  e.preventDefault();
  const after = a.classList.contains('drop-after');
  const [t] = await chrome.bookmarks.get(a.dataset.id);
  // index is counted before the moved book is taken out, which is what move() expects
  await chrome.bookmarks.move(dragId, { parentId: t.parentId, index: t.index + (after ? 1 : 0) });
});
$('#shelves').addEventListener('dragend', () => {
  dragId = null;
  clearDrop();
  document.querySelectorAll('.dragging').forEach(el => el.classList.remove('dragging'));
});


const panel = $('#panel');
let panelFor = null;

function closePanel() {
  panel.hidden = true;
  panel.innerHTML = '';
  panelFor = null;
  document.querySelectorAll('.book.selected').forEach(el => el.classList.remove('selected'));
}

function place(anchor) {
  panel.hidden = false;
  const p = panel.getBoundingClientRect();
  if (!anchor) { // dock panels sit above the dock
    panel.style.left = `${innerWidth - p.width - 2.4 * rem()}px`;
    panel.style.top = `${innerHeight - p.height - 5.6 * rem()}px`;
    return;
  }
  const r = anchor.getBoundingClientRect(), pad = 16;
  let left = r.right + pad;
  if (left + p.width > innerWidth - pad) left = r.left - p.width - pad;
  const top = Math.min(Math.max(pad, r.top - 20), innerHeight - p.height - pad);
  panel.style.left = `${Math.max(pad, left)}px`;
  panel.style.top = `${top}px`;
}

const sizeButtons = cur => [1, 2, 3, 4].map(s =>
  `<button data-size="${s}" class="${s === cur ? 'on' : ''}" title="Height ${s}"><i style="height:${0.5 + s * 0.38}rem"></i></button>`).join('');
const inkButtons = cur => [0, 1, 2, 3].map(k =>
  `<button data-ink="${k}" class="${k === cur ? 'on' : ''}" style="--bg:var(--ink${k}-bg)" title="Ink ${k + 1}"></button>`).join('');

async function saveMeta(url, patch) {
  const i = state.books.findIndex(b => b.url === url);
  const next = { ...metaFor(url, i), ...patch };
  state.meta[url] = next;
  await chrome.storage.sync.set({ ['b:' + url]: next });
}

function bookPanel(b, anchor) {
  closePanel();
  panelFor = b.id;
  anchor.classList.add('selected');
  const i = state.books.indexOf(b);
  const m = metaFor(b.url, i);
  panel.innerHTML = `
    <label>Name</label><input type="text" id="p-name">
    <label>Address</label><input type="text" id="p-url">
    <label>Height</label><div class="opts sizes">${sizeButtons(m.s)}</div>
    <label>Ink</label><div class="opts inks">${inkButtons(m.ink)}</div>
    <label>Icon</label>
    <div class="iconrow"><span class="chip"><img id="p-icon" alt=""></span>
      <button class="link" id="p-upload">Upload</button>
      <button class="link" id="p-reset" ${state.icons[b.url] ? '' : 'hidden'}>Reset</button>
      <input type="file" id="p-file" accept="image/*" hidden></div>
    <div class="actions"><button class="link danger" id="p-remove">Remove</button><button class="primary" id="p-done">Done</button></div>`;
  $('#p-name').value = b.title;
  $('#p-url').value = b.url;
  $('#p-icon').src = iconFor(b.url);
  place(anchor);

  panel.querySelectorAll('[data-size]').forEach(btn => btn.onclick = async () => {
    panel.querySelectorAll('[data-size]').forEach(x => x.classList.toggle('on', x === btn));
    await saveMeta(b.url, { s: +btn.dataset.size });
  });
  panel.querySelectorAll('[data-ink]').forEach(btn => btn.onclick = async () => {
    panel.querySelectorAll('[data-ink]').forEach(x => x.classList.toggle('on', x === btn));
    await saveMeta(b.url, { ink: +btn.dataset.ink });
  });
  $('#p-upload').onclick = () => $('#p-file').click();
  $('#p-file').onchange = async e => {
    const file = e.target.files[0];
    if (!file) return;
    const data = await shrink(file);
    await chrome.storage.local.set({ ['i:' + b.url]: data });
    $('#p-icon').src = data;
    $('#p-reset').hidden = false;
  };
  $('#p-reset').onclick = async () => {
    await chrome.storage.local.remove('i:' + b.url);
    $('#p-icon').src = favicon(b.url);
    $('#p-reset').hidden = true;
  };
  $('#p-remove').onclick = async e => {
    const btn = e.currentTarget;
    if (!btn.classList.contains('armed')) { btn.classList.add('armed'); btn.textContent = 'Click again to remove'; return; }
    await chrome.bookmarks.remove(b.id);
    closePanel();
  };
  const done = async () => {
    const title = $('#p-name').value.trim();
    const url = normalise($('#p-url').value);
    if (url && url !== b.url) await moveKeys(b.url, url);
    await chrome.bookmarks.update(b.id, { title: title || host(url || b.url), ...(url ? { url } : {}) });
    closePanel();
  };
  $('#p-done').onclick = done;
  panel.querySelectorAll('input[type=text]').forEach(inp => inp.onkeydown = e => { if (e.key === 'Enter') done(); });
}

function addPanel() {
  closePanel();
  panel.innerHTML = `<h3>New book</h3>
    <label>Name</label><input type="text" id="p-name" placeholder="Canvas">
    <label>Address</label><input type="text" id="p-url" placeholder="canvas.ubc.ca">
    <div class="actions"><span></span><button class="primary" id="p-add">Add to shelf</button></div>`;
  place(null);
  $('#p-name').focus();
  const add = async () => {
    const url = normalise($('#p-url').value);
    if (!url) { $('#p-url').focus(); return; }
    await chrome.bookmarks.create({ parentId: state.folder.id, title: $('#p-name').value.trim() || host(url), url });
    closePanel();
  };
  $('#p-add').onclick = add;
  panel.querySelectorAll('input').forEach(inp => inp.onkeydown = e => { if (e.key === 'Enter') add(); });
}

function settingsPanel() {
  closePanel();
  const cur = state.folders.find(f => f.node.id === state.folder.id);
  panel.innerHTML = `<h3>Shelf</h3>
    <label>Folder</label>
    <select id="p-folder">${state.folders.map(f => `<option value="${esc(f.path)}" ${f === cur ? 'selected' : ''}>${esc(f.path)}</option>`).join('')}</select>
    <label class="check"><input type="checkbox" id="p-ribbon" ${state.settings.ribbon ? 'checked' : ''}> Ribbon on your most opened this week</label>
    <label class="check"><input type="checkbox" id="p-lean" ${state.settings.lean ? 'checked' : ''}> Lean the last book</label>`;
  place(null);
  const save = patch => chrome.storage.sync.set({ settings: { ...state.settings, ...patch } });
  $('#p-folder').onchange = e => save({ folder: e.target.value });
  $('#p-ribbon').onchange = async e => { await chrome.storage.local.remove('weekly'); save({ ribbon: e.target.checked }); };
  $('#p-lean').onchange = e => save({ lean: e.target.checked });
}

$('#add').addEventListener('click', () => panel.hidden ? addPanel() : closePanel());
$('#gear').addEventListener('click', () => panel.hidden ? settingsPanel() : closePanel());
document.addEventListener('mousedown', e => {
  if (panel.hidden || panel.contains(e.target) || e.target.closest('.dock')) return;
  if (state.editing && e.target.closest('.book')) return;
  closePanel();
});

function normalise(v) {
  v = v.trim();
  if (!v) return '';
  return /^[a-z][a-z0-9+.-]*:/i.test(v) ? v : `https://${v}`;
}

async function moveKeys(from, to) {
  if (state.meta[from]) {
    await chrome.storage.sync.set({ ['b:' + to]: state.meta[from] });
    await chrome.storage.sync.remove('b:' + from);
  }
  if (state.icons[from]) {
    await chrome.storage.local.set({ ['i:' + to]: state.icons[from] });
    await chrome.storage.local.remove('i:' + from);
  }
}

// uploaded icons get squashed to 64px so storage stays small
function shrink(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const c = document.createElement('canvas');
      c.width = c.height = 64;
      const s = Math.min(64 / img.width, 64 / img.height);
      const w = img.width * s, h = img.height * s;
      c.getContext('2d').drawImage(img, (64 - w) / 2, (64 - h) / 2, w, h);
      URL.revokeObjectURL(img.src);
      resolve(c.toDataURL('image/png'));
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}


function setDate() {
  $('#date').textContent = new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
}

async function start() {
  setDate();
  setInterval(setDate, 60e3);
  await loadStorage();
  await loadBookmarks();
  const { weekly } = await chrome.storage.local.get('weekly');
  if (state.settings.ribbon && weekly) state.top = weekly.top;
  render();
  const top = await weeklyTop();
  if (top !== state.top) { state.top = top; render(); }
}

for (const ev of ['onCreated', 'onRemoved', 'onChanged', 'onMoved', 'onChildrenReordered']) {
  chrome.bookmarks[ev].addListener(() => refresh());
}
chrome.storage.onChanged.addListener(async (changes, area) => {
  if (area === 'local' && Object.keys(changes).every(k => k === 'weekly')) return;
  if (changes.settings && changes.settings.newValue?.ribbon !== state.settings.ribbon) {
    await loadStorage();
    state.top = state.settings.ribbon ? await weeklyTop() : null;
  }
  refresh();
});
let resizeT;
addEventListener('resize', () => { clearTimeout(resizeT); resizeT = setTimeout(() => render(), 80); });

start();
