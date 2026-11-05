import { $ } from './dom.js';
import * as store from './store.js';
import { render } from './shelf.js';
import { initReorder } from './reorder.js';
import { initAdd, cardOpen, dismissCard } from './add.js';
import { openBookPanel } from './bookpanel.js';
import { openSettings } from './settings.js';
import { panelKind, closePanel } from './panel.js';
import { watchRibbon } from './ribbon.js';
import { applyTheme } from './palette.js';
import { reveal, decoded } from './intro.js';
import { iconsSettled } from './shelf.js';
import { ribbonPlaced } from './ribbon.js';

// 2d is a class on <html>. boot.js puts it back before paint so a new tab doesn't flash the 3d shelf
store.subscribe(s => {
  const flat = s.settings.look === '2d';
  document.documentElement.classList.toggle('flat', flat);
  localStorage.setItem('shelf:look', flat ? '2d' : '3d');
});
// render goes first so the card and ribbon see the fresh shelf
store.subscribe(s => applyTheme(s.settings));
store.subscribe(render);
initAdd();
initReorder();
watchRibbon();

function open(url, background) {
  // chrome:// and file:// links can't be followed from a page, so go through the tabs api
  if (background) chrome.tabs.create({ url, active: false });
  else if (/^(https?|ftp):/.test(url)) location.href = url;
  else chrome.tabs.update({ url });
}

function toggleEdit() {
  closePanel();
  if (cardOpen()) dismissCard();
  store.setEditing(!store.get().editing);
}

$('#shelves').addEventListener('click', e => {
  const a = e.target.closest('.book');
  const b = a && store.get().books.find(x => x.id === a.dataset.id);
  if (!b) return;
  if (store.get().editing) { e.preventDefault(); openBookPanel(b, a); return; }
  if (!/^(https?|ftp):/.test(b.url)) { e.preventDefault(); open(b.url, e.ctrlKey || e.metaKey); }
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    const kind = panelKind();
    if (cardOpen()) dismissCard();
    else if (kind) {
      closePanel();
      if (kind === 'settings') $('#gear').focus();
    } else if (store.get().editing) toggleEdit();
    return;
  }
  if (e.target.closest('input, select, textarea') || panelKind() || cardOpen() || e.altKey) return;
  if (/^[1-9]$/.test(e.key)) {
    const b = store.get().books[+e.key - 1];
    if (b) { e.preventDefault(); open(b.url, e.ctrlKey || e.metaKey); }
  }
});

$('#edit').addEventListener('click', toggleEdit);
$('#gear').addEventListener('click', () => {
  if (cardOpen()) dismissCard();
  if (panelKind() === 'settings') closePanel();
  else openSettings();
});

let resizeT;
addEventListener('resize', () => { clearTimeout(resizeT); resizeT = setTimeout(store.touch, 80); });

await store.load();
// wait for the render store.load queued (and the one the ribbon queues), then open the page in one go
await Promise.race([ribbonPlaced, new Promise(r => setTimeout(r, 400))]);
await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
reveal(iconsSettled(), decoded(document.body));
