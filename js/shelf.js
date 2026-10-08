import { $, h, rem } from './dom.js';
import { metaFor, iconFor, takeFocus } from './store.js';
import { host } from './urls.js';
import { letterIfBlank } from './icons.js';

export const SIZES = { 1: { w: 3.9, h: 14.5 }, 2: { w: 4.3, h: 17 }, 3: { w: 5.1, h: 19.5 }, 4: { w: 6.4, h: 22.5 } };
const GAP = 0.35, LEAN_ROOM = 2.7;

export const bookEl = id => $(`#shelves .book[data-id="${CSS.escape(id)}"]`);

export function render(s) {
  const main = $('#shelves');
  document.body.classList.toggle('editing', s.editing);
  $('#hint').hidden = !s.editing;
  $('#edit').classList.toggle('on', s.editing);
  if (!s.folder) return;

  const avail = main.clientWidth / rem();
  const groups = s.groups.length ? s.groups : [{ label: null, parentId: s.folder.id, items: [] }];
  const emptyAll = !s.books.length && !s.ghost;
  let n = 0, last = null, lastRow = null, lastRowW = 0;

  const sections = groups.map((g, gi) => {
    const sec = h('section', { class: 'group', dataset: { parent: g.parentId } }, g.label ? h('h2', {}, g.label) : null);
    let row, rowW;
    const newRow = () => {
      row = h('div', { class: 'row' });
      sec.append(row, h('div', { class: 'plank' }));
      rowW = 0;
    };
    const put = (el, w) => {
      if (rowW && rowW + GAP + w > avail) newRow();
      row.append(el);
      rowW += (rowW ? GAP : 0) + w;
      last = el; lastRow = row; lastRowW = rowW;
    };
    newRow();
    for (const b of g.items) {
      const m = metaFor(b.url, n);
      put(spine(b, m, n++, s), SIZES[m.s].w);
    }
    if (gi === 0 && s.ghost) put(h('div', { class: 'book ghost', style: `width:${SIZES[2].w}rem;height:${SIZES[2].h}rem` }), SIZES[2].w);
    if (!row.children.length) {
      row.append(h('span', { class: 'empty' }, emptyAll
        ? `Nothing in ${s.folder.title} yet. Press + to add a book, or pick another folder in settings.`
        : 'empty shelf'));
    }
    return sec;
  });

  const leans = s.settings.lean && !s.editing && !s.ghost && s.books.length > 1 && last?.dataset.id !== s.fresh;
  if (leans && lastRow.children.length > 1 && lastRowW + LEAN_ROOM <= avail) last.classList.add('lean');
  main.replaceChildren(...sections);

  const focus = takeFocus();
  if (focus) bookEl(focus)?.focus({ preventScroll: true });
}

function spine(b, m, i, s) {
  const { w, h: tall } = SIZES[m.s];
  const name = b.title || host(b.url);
  const img = h('img', { alt: '', src: iconFor(b.url), draggable: false });
  const letter = h('span', { class: 'letter', hidden: true }, name.trim().charAt(0).toUpperCase());
  const cls = ['book', s.fresh === b.id && 'fresh', s.selected === b.id && 'selected'].filter(Boolean).join(' ');
  const a = h('a', {
    class: cls, href: b.url, title: `${b.title}\n${host(b.url)}`, draggable: s.editing, dataset: { id: b.id },
    style: `width:${w}rem;height:${tall}rem;--bg:var(--ink${m.ink}-bg);--fg:var(--ink${m.ink}-fg)`,
  },
  s.top && host(b.url) === s.top ? h('i', { class: 'ribbon' }) : null,
  h('span', { class: 'chip' }, img, letter),
  h('span', { class: 'nm' }, name),
  h('span', { class: 'k mono' }, i < 9 ? String(i + 1) : ''));
  letterIfBlank(img, letter);
  return a;
}
