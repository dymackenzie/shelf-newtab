import { readTree, folderList, resolve, groupsOf } from './bookmarks.js';
import { favicon } from './icons.js';

const DEFAULTS = { folder: '', subShelves: true, ribbon: true, lean: true };

const state = {
  settings: { ...DEFAULTS },
  meta: {},       // url -> { s, ink }, synced so sizes follow you between computers
  icons: {},      // url -> data url, local only (too big for sync)
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

export const metaFor = (url, i) => ({ s: 2, ink: Math.max(i, 0) % 4, ...(state.meta[url] || {}) });
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
  await reloadTree();
}

export async function saveSettings(patch) {
  state.settings = { ...state.settings, ...patch };
  derive();
  touch();
  await chrome.storage.sync.set({ settings: state.settings });
}

export async function saveMeta(url, patch) {
  const next = { ...metaFor(url, state.books.findIndex(b => b.url === url)), ...patch };
  state.meta = { ...state.meta, [url]: next };
  touch();
  await chrome.storage.sync.set({ ['b:' + url]: next });
}

export async function saveIcon(url, data) {
  state.icons = { ...state.icons, [url]: data };
  touch();
  await chrome.storage.local.set({ ['i:' + url]: data });
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
  if (Object.keys(changes).every(k => k === 'weekly')) return;
  loadStorage();
});
