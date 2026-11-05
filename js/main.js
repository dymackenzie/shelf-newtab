import { $, h } from './dom.js';
import * as store from './store.js';
import { render } from './shelf.js';
import { initReorder } from './reorder.js';
import { initAdd, cardOpen, dismissCard } from './add.js';
import { openBookPanel } from './bookpanel.js';
import { openSettings } from './settings.js';
import { panelKind, closePanel } from './panel.js';
import { watchRibbon } from './ribbon.js';
import { renderIndex } from './index.js';
import { applyTheme } from './palette.js';
import { reveal, decoded } from './intro.js';
import { iconsSettled } from './shelf.js';
import { ribbonPlaced } from './ribbon.js';

// switched-off parts hide by a class on <html>. boot.js puts them back before paint so new tabs don't flash them
store.subscribe(s => {
  const hide = [['no-index', !s.settings.contents], ['no-date', !s.settings.date]];
  for (const [c, on] of hide) document.documentElement.classList.toggle(c, on);
  localStorage.setItem('shelf:hide', hide.filter(x => x[1]).map(x => x[0]).join(' '));
});
// render goes first so the card and ribbon see the fresh shelf
store.subscribe(s => applyTheme(s.settings));
store.subscribe(render);
store.subscribe(renderIndex);
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

const setDate = () => {
  const d = new Date();
  $('#date').replaceChildren(h('em', {}, d.toLocaleDateString(undefined, { weekday: 'long' })), ' ',
    d.toLocaleDateString(undefined, { month: 'long', day: 'numeric' }));
};
setDate();
setInterval(setDate, 60e3);

await store.load();
// wait for the render store.load queued (and the one the ribbon queues), then open the page in one go
await Promise.race([ribbonPlaced, new Promise(r => setTimeout(r, 400))]);
await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
reveal(iconsSettled(), decoded(document.body));
