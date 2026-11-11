import { readTree, folderList, resolve, groupsOf, ownFolderPath } from './bookmarks.js';
import { favicon } from './icons.js';

const DEFAULTS = { folder: '', subShelves: true, ribbon: true, lean: true, paper: 'white', accent: 'magenta', grain: true, look: '2d' };

const state = {
  settings: { ...DEFAULTS },
  meta: {},       // url -> { s, ink }, synced so sizes follow you between computers
  icons: {},      // url -> data url, local only (too big for sync)
  cloth: {},      // url -> { bg, fg } read off its icon, local only
  folders: [],
  folder: null,
  groups: [],
  books: [],      // flat list in shelf order
  top: null,      // host with the most visits this week
  editing: false,
  selected: null, // book open in the edit panel
  fresh: null,    // book a drop just made, while its card is open
  ghost: null,    // { parentId, index } while the + card is open
};
let focusId = null;
const subs = [];

// everyone reads from here, nobody writes to it directly
export const get = () => state;
export const subscribe = fn => subs.push(fn);

let queued = false;
export function touch() {
  if (queued) return;
  queued = true;
  requestAnimationFrame(() => {
    queued = false;
    for (const fn of subs) fn(state);
  });
}

const set = patch => { Object.assign(state, patch); touch(); };
export const setEditing = editing => set({ editing });
export const setSelected = selected => set({ selected });
export const setFresh = fresh => set({ fresh });
export const setGhost = ghost => set({ ghost });
export const setTop = top => { if (top !== state.top) set({ top }); };
export const focusAfter = id => { focusId = id; touch(); };
export const takeFocus = () => { const id = focusId; focusId = null; return id; };

export const INKS = 8;
// stable number per address. picks the fallback ink until the icon colour is known, and the book's thickness
export const hashOf = url => [...(url || '')].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
export const inkOf = url => hashOf(url) % INKS;
// ink is only set if one was picked, otherwise the cover follows the icon
export const metaFor = url => ({ s: 2, ...(state.meta[url] || {}) });
export const iconFor = url => state.icons[url] || favicon(url);

function derive() {
  state.folder = resolve(state.folders, state.settings.folder);
  state.groups = state.folder ? groupsOf(state.folder, state.settings.subShelves) : [];
  state.books = state.groups.flatMap(g => g.items);
}

async function loadStorage() {
  const sync = await chrome.storage.sync.get(null);
  const local = await chrome.storage.local.get(null);
  const pick = (all, prefix) => Object.fromEntries(Object.entries(all).filter(([k]) => k.startsWith(prefix)).map(([k, v]) => [k.slice(2), v]));
  state.settings = { ...DEFAULTS, ...(sync.settings || {}) };
  state.meta = pick(sync, 'b:');
  state.icons = pick(local, 'i:');
  state.cloth = pick(local, 'c:');
  derive();
  touch();
}

export async function reloadTree() {
  state.folders = folderList(await readTree());
  derive();
  touch();
}

export async function load() {
  await loadStorage();
  if (!state.settings.folder) {
    // first run: start on shelf's own empty folder
    state.settings.folder = await ownFolderPath();
    await chrome.storage.sync.set({ settings: state.settings });
  }
  await reloadTree();
}

export async function saveSettings(patch) {
  state.settings = { ...state.settings, ...patch };
  derive();
  touch();
  await chrome.storage.sync.set({ settings: state.settings });
}

export async function saveMeta(url, patch) {
  const next = { ...(state.meta[url] || {}), ...patch };
  for (const k of Object.keys(next)) if (next[k] == null) delete next[k];
  state.meta = { ...state.meta, [url]: next };
  touch();
  await chrome.storage.sync.set({ ['b:' + url]: next });
}

export async function saveIcon(url, data) {
  state.icons = { ...state.icons, [url]: data };
  touch();
  await chrome.storage.local.set({ ['i:' + url]: data });
}

export async function saveCloth(url, c) {
  if (state.cloth[url]?.bg === c.bg && state.cloth[url]?.fg === c.fg) return;
  state.cloth = { ...state.cloth, [url]: c };
  touch();
  await chrome.storage.local.set({ ['c:' + url]: c });
}

export async function clearIcon(url) {
  const { [url]: _, ...rest } = state.icons;
  state.icons = rest;
  touch();
  await chrome.storage.local.remove('i:' + url);
}

// a book's sizes and icon are keyed by url, so they follow it when the address changes
export async function moveKeys(from, to) {
  if (state.meta[from]) {
    await chrome.storage.sync.set({ ['b:' + to]: state.meta[from] });
    await chrome.storage.sync.remove('b:' + from);
  }
  if (state.icons[from]) {
    await chrome.storage.local.set({ ['i:' + to]: state.icons[from] });
    await chrome.storage.local.remove('i:' + from);
  }
}

for (const ev of ['onCreated', 'onRemoved', 'onChanged', 'onMoved', 'onChildrenReordered']) {
  chrome.bookmarks[ev].addListener(() => reloadTree());
}
chrome.storage.onChanged.addListener(changes => {
  if (Object.keys(changes).every(k => k === 'weekly' || k.startsWith('c:'))) return;
  loadStorage();
});
