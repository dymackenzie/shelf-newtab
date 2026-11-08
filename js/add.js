import { $, h, rem, elOf } from './dom.js';
import * as store from './store.js';
import { targetAt, mark, clearMark } from './drop.js';
import { reordering } from './reorder.js';
import { createIconField } from './iconfield.js';
import { createPreview } from './preview.js';
import { bookEl } from './shelf.js';
import { closePanel } from './panel.js';
import { readDrag, urlFromDrop, titleFor, hostName, normalise, isWeb } from './urls.js';

let card = null; // { el, well, mode: 'drop' | 'ghost', id, placed }

export const cardOpen = () => card !== null;

const DROP_TYPES = ['text/uri-list', 'text/plain', 'Files'];
const ignore = e => reordering() || elOf(e.target).closest('#card, .panel') || !DROP_TYPES.some(t => e.dataTransfer?.types.includes(t));

export function initAdd() {
  document.addEventListener('dragover', e => {
    if (ignore(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    mark(targetAt(e.clientX, e.clientY));
  });
  document.addEventListener('dragleave', e => {
    if (!e.relatedTarget && !reordering()) clearMark();
  });
  document.addEventListener('drop', e => {
    if (ignore(e)) return;
    // always take the drop, otherwise chrome navigates the new tab to the link
    e.preventDefault();
    const t = targetAt(e.clientX, e.clientY);
    clearMark();
    if (t) dropped(t, readDrag(e.dataTransfer));
  });
  $('#add').addEventListener('click', () => (card?.mode === 'ghost' ? dismissCard() : startGhost()));
  document.addEventListener('mousedown', e => {
    if (card && !card.el.contains(e.target) && !e.target.closest('.dock, .book.fresh, .book.ghost')) dismissCard();
  });
  store.subscribe(placeCard);
}

async function dropped(t, raw) {
  const url = await urlFromDrop(raw);
  if (!url) return;
  if (card) dismissCard();
  closePanel();
  const title = await titleFor(url, raw.html);
  const node = await chrome.bookmarks.create({ parentId: t.parentId, index: t.index, title, url });
  await store.reloadTree();
  openDropCard(node);
}

// the card reads as a sentence, one line per thing to set
const line = (...kids) => h('p', { class: 'line' }, ...kids);

function openDropCard(node) {
  const { url } = node;
  const before = store.get().icons[url]; // put back on undo
  let changedIcon = false;
  const preview = createPreview();
  const name = h('input', { type: 'text', class: 'name', value: node.title, 'aria-label': 'Name', spellcheck: false });
  const icon = createIconField({
    src: before,
    onImage: v => { changedIcon = true; store.saveIcon(url, v); preview.set({ icon: v }); },
  });
  name.addEventListener('input', () => preview.set({ title: name.value }));
  preview.set({ title: node.title, url, icon: before || '' });

  const finish = async () => {
    const title = name.value.trim() || hostName(url);
    if (title !== node.title) await chrome.bookmarks.update(node.id, { title });
    close(node.id);
  };
  const undo = async () => {
    close(null);
    await chrome.bookmarks.remove(node.id);
    if (changedIcon) await (before ? store.saveIcon(url, before) : store.clearIcon(url));
  };
  name.addEventListener('keydown', e => { if (e.key === 'Enter') finish(); });

  show('drop', node.id, icon, preview, [
    line('Added', h('span', { class: 'url' }, url.replace(/^https?:\/\/(www\.)?/, '')), 'called', name),
    line('with the icon from', icon.square, icon.input, icon.pickFile),
  ], h('button', { type: 'button', class: 'link undo', onclick: undo }, 'Undo'),
  h('button', { type: 'button', class: 'primary', onclick: finish }, 'Done'));
  card.first = () => { name.focus(); name.select(); };
  store.setFresh(node.id);
}

function startGhost() {
  closePanel();
  if (card) dismissCard();
  const s = store.get();
  const g = s.groups[0];
  const last = g?.items.at(-1);
  const at = last ? { parentId: last.parentId, index: last.index + 1 } : { parentId: g?.parentId ?? s.folder.id };

  const preview = createPreview();
  const address = h('input', { type: 'text', class: 'address', placeholder: 'paste a link', 'aria-label': 'Address', spellcheck: false });
  const name = h('input', { type: 'text', class: 'name', placeholder: 'a name', 'aria-label': 'Name', spellcheck: false });
  let pending = null, html = '', named = false, timer;
  const icon = createIconField({ onImage: v => { pending = v; preview.set({ icon: v }); } });

  const fill = async () => {
    const url = normalise(address.value);
    preview.set({ url: isWeb(url) ? url : '' });
    if (named || !isWeb(url)) return;
    const title = await titleFor(url, html);
    if (!named && normalise(address.value) === url) { name.value = title; preview.set({ title }); }
  };
  address.addEventListener('paste', e => { html = e.clipboardData.getData('text/html'); });
  address.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(fill, 200); });
  name.addEventListener('input', () => { named = true; preview.set({ title: name.value }); });

  const finish = async () => {
    const url = normalise(address.value);
    if (!url) return address.focus();
    clearTimeout(timer);
    const title = name.value.trim() || await titleFor(url, html);
    const node = await chrome.bookmarks.create({ ...at, title, url });
    // chrome tidies the address (adds a trailing slash), so key the icon by what it actually saved
    if (pending) await store.saveIcon(node.url, pending);
    await store.reloadTree();
    close(node.id);
  };
  for (const inp of [address, name]) inp.addEventListener('keydown', e => { if (e.key === 'Enter') finish(); });

  show('ghost', null, icon, preview, [
    line('Add', address, 'called', name),
    line('with the icon from', icon.square, icon.input, icon.pickFile),
  ], h('span', { class: 'hint' }, 'Esc to cancel'),
  h('button', { type: 'button', class: 'primary', onclick: finish }, 'Done'));
  card.first = () => address.focus();
  store.setGhost(at);
}

function show(mode, id, icon, preview, lines, left, done) {
  const say = h('div', { class: 'say' }, ...lines, icon.status, h('div', { class: 'foot' }, left, done));
  const el = h('div', { class: 'card', id: 'card', role: 'dialog', 'aria-label': 'New book', style: 'visibility:hidden' },
    preview.el, say, icon.file);
  icon.dropOn(el);
  document.body.append(el);
  card = { el, well: icon, mode, id, placed: false };
}

function close(focusId) {
  if (!card) return;
  card.well.destroy();
  card.el.remove();
  card = null;
  store.setFresh(null);
  store.setGhost(null);
  if (focusId) store.focusAfter(focusId);
}

// esc and clicking away keep a dropped book but throw away the ghost
export function dismissCard() {
  if (card) close(card.mode === 'drop' ? card.id : null);
}

// the card hangs under the plank, lined up with the new book
function placeCard() {
  if (!card) return;
  const book = card.mode === 'ghost' ? $('#shelves .book.ghost') : bookEl(card.id);
  if (!book) return close(null); // the book went away, say the folder changed
  const plank = book.closest('.row').nextElementSibling.getBoundingClientRect();
  const r = book.getBoundingClientRect(), pad = rem();
  const left = Math.max(pad, Math.min(r.left, innerWidth - card.el.offsetWidth - pad));
  card.el.style.left = `${left + scrollX}px`;
  // the little notch on top points at the book, wherever the card had to slide to
  card.el.style.setProperty('--notch', `${Math.max(14, Math.min(r.left + r.width / 2 - left, card.el.offsetWidth - 14))}px`);
  card.el.style.top = `${plank.bottom + scrollY + 0.9 * rem()}px`;
  card.el.style.visibility = '';
  // hidden elements can't take focus, so this waits until the card is placed and visible
  if (!card.placed) {
    card.placed = true;
    card.el.scrollIntoView({ block: 'nearest' });
    card.first();
  }
}
