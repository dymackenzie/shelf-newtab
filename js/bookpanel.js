import { h } from './dom.js';
import * as store from './store.js';
import { openPanel, closePanel } from './panel.js';
import { createIconField } from './iconfield.js';
import { favicon } from './icons.js';
import { host, normalise } from './urls.js';
import { coverOf } from './shelf.js';

export function openBookPanel(b, anchor) {
  const s = store.get();
  const m = store.metaFor(b.url);
  const name = h('input', { type: 'text', id: 'p-name', value: b.title });
  const addr = h('input', { type: 'text', id: 'p-url', value: b.url });

  const choose = (list, at, patch) => {
    list.forEach((x, j) => x.classList.toggle('on', j === at));
    store.saveMeta(b.url, patch);
  };
  const sizes = [1, 2, 3, 4].map((n, j) => h('button', {
    type: 'button', class: n === m.s ? 'on' : '', title: `Height ${n}`, onclick: () => choose(sizes, j, { s: n }),
  }, h('i', { style: `height:${0.5 + n * 0.38}rem` })));
  // the first swatch is "whatever the icon says", the rest are fixed inks
  const auto = coverOf(b, {}, s);
  const inks = [h('button', {
    type: 'button', class: `auto${m.ink == null ? ' on' : ''}`, title: 'Match the icon', style: `--bg:${auto.bg}`,
    onclick: () => choose(inks, 0, { ink: null }),
  }), ...Array.from({ length: store.INKS }, (_, k) => h('button', {
    type: 'button', class: k === m.ink ? 'on' : '', title: `Ink ${k + 1}`, style: `--bg:var(--ink${k}-bg)`,
    onclick: () => choose(inks, k + 1, { ink: k }),
  }))];

  const reset = h('button', { type: 'button', class: 'link', hidden: !s.icons[b.url] }, 'Reset');
  const well = createIconField({
    src: store.iconFor(b.url),
    onImage: v => { store.saveIcon(b.url, v); reset.hidden = false; },
  });
  reset.addEventListener('click', async () => {
    await store.clearIcon(b.url);
    well.show(favicon(b.url));
    well.input.value = '';
    reset.hidden = true;
  });

  const remove = h('button', { type: 'button', class: 'link danger' }, 'Remove');
  remove.addEventListener('click', async () => {
    if (!remove.classList.contains('armed')) {
      remove.classList.add('armed');
      remove.textContent = 'Click again to remove';
      return;
    }
    closePanel();
    await chrome.bookmarks.remove(b.id);
  });

  const done = async () => {
    const title = name.value.trim();
    const url = normalise(addr.value);
    if (url && url !== b.url) await store.moveKeys(b.url, url);
    closePanel();
    await chrome.bookmarks.update(b.id, { title: title || host(url || b.url), ...(url ? { url } : {}) });
  };
  for (const inp of [name, addr]) inp.addEventListener('keydown', e => { if (e.key === 'Enter') done(); });

  openPanel('book', [
    h('label', { class: 'lb', for: 'p-name' }, 'Name'), name,
    h('label', { class: 'lb', for: 'p-url' }, 'Address'), addr,
    h('span', { class: 'lb' }, 'Height'), h('div', { class: 'opts sizes' }, sizes),
    h('span', { class: 'lb' }, 'Ink'), h('div', { class: 'opts inks' }, inks),
    h('span', { class: 'lb' }, 'Icon'), h('div', { class: 'iconrow' }, well.square, well.input),
    h('div', { class: 'iconmore' }, well.pickFile, reset), well.status, well.file,
    h('div', { class: 'actions' }, remove, h('button', { type: 'button', class: 'primary', onclick: done }, 'Done')),
  ], anchor, () => {
    well.destroy();
    store.setSelected(null);
  });
  well.dropOn(document.querySelector('#panel'));
  // after openPanel, since opening closes the last panel and that clears the selection
  store.setSelected(b.id);
}
