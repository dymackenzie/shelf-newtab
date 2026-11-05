import { $, h, rem } from './dom.js';
import { metaFor, iconFor, takeFocus, hashOf, inkOf, INKS } from './store.js';
import { host } from './urls.js';
import { letterIfBlank } from './icons.js';
import { learnCloth } from './cloth.js';
import { introVars } from './intro.js';

export const SIZES = { 1: { w: 3.3, h: 15 }, 2: { w: 3.6, h: 17.5 }, 3: { w: 4, h: 20 }, 4: { w: 4.5, h: 23 } };
const GAP = 0.16, LEAN_ROOM = 2.7;

const NUMERALS = ['M', 1000, 'CM', 900, 'D', 500, 'CD', 400, 'C', 100, 'XC', 90, 'L', 50, 'XL', 40, 'X', 10, 'IX', 9, 'V', 5, 'IV', 4, 'I', 1];
export function roman(n) {
  let out = '';
  for (let i = 0; i < NUMERALS.length; i += 2) while (n >= NUMERALS[i + 1]) { out += NUMERALS[i]; n -= NUMERALS[i + 1]; }
  return out;
}

export const bookEl = id => $(`#shelves .book[data-id="${CSS.escape(id)}"]`);

// real books are never exactly the same thickness, so each one gets a little more or less paper
const widthOf = (url, s) => SIZES[s].w + ((hashOf(url) >> 3) % 5 - 2) * 0.12;

// he picked an ink > the icon's colour > a fallback ink
export function coverOf(b, m, s) {
  if (m.ink != null) return { bg: `var(--ink${m.ink}-bg)`, fg: `var(--ink${m.ink}-fg)`, ink: m.ink };
  if (s.cloth[b.url]) return { ...s.cloth[b.url], ink: null };
  const k = inkOf(b.url);
  return { bg: `var(--ink${k}-bg)`, fg: `var(--ink${k}-fg)`, ink: k };
}

export function render(s) {
  const main = $('#shelves');
  document.body.classList.toggle('editing', s.editing);
  $('#hint').hidden = !s.editing;
  $('#edit').classList.toggle('on', s.editing);
  $('#edit').textContent = s.editing ? 'Done' : 'Edit';
  if (!s.folder) return;
  const n0 = s.books.length;
  $('#where').textContent = (s.folder.title === 'Shelf' ? '' : `${s.folder.title}, `) + `${n0} book${n0 === 1 ? '' : 's'}`;

  const avail = main.clientWidth / rem();
  const groups = s.groups.length ? s.groups : [{ label: null, parentId: s.folder.id, items: [] }];
  const emptyAll = !s.books.length && !s.ghost;
  let n = 0, last = null, lastRow = null, lastRowW = 0;

  checks = [];
  const sections = groups.map((g, gi) => {
    const sec = h('section', { class: 'group', dataset: { parent: g.parentId } }, g.label ? h('h2', { dataset: { n: roman(gi + 1) } }, g.label) : null);
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
    let prevInk = -1;
    for (const b of g.items) {
      const m = metaFor(b.url), cover = coverOf(b, m, s);
      // two fallback neighbours on the same ink read as one fat book, so nudge the second along
      if (m.ink == null && cover.ink != null && cover.ink === prevInk) {
        const k = (cover.ink + 1) % INKS;
        Object.assign(cover, { bg: `var(--ink${k}-bg)`, fg: `var(--ink${k}-fg)`, ink: k });
      }
      prevInk = cover.ink ?? -1;
      const w = widthOf(b.url, m.s);
      put(spine(b, m, cover, w, s, n), w);
      n++;
    }
    if (gi === 0 && s.ghost) put(h('div', { class: 'book ghost', style: `width:${SIZES[2].w}rem;height:${SIZES[2].h}rem` }), SIZES[2].w);
    if (!row.children.length) {
      row.append(h('span', { class: 'empty' }, emptyAll
        ? 'Nothing on the shelf yet. Drag a link here, or click Add a book.'
        : 'empty shelf'));
    }
    return sec;
  });

  const leans = s.settings.lean && !s.editing && !s.ghost && s.books.length > 1 && last?.dataset.id !== s.fresh;
  if (leans && lastRow.children.length > 1 && lastRowW + LEAN_ROOM <= avail) last.classList.add('lean');
  main.style.cssText = introVars(n);
  main.replaceChildren(...sections);

  const focus = takeFocus();
  if (focus) bookEl(focus)?.focus({ preventScroll: true });
}

// icons already found blank this page load, so a re-render shows their letter straight away instead of flashing grey
const blanks = new Set();
let checks = [];
// resolves once every icon on the shelf is known to be real or swapped for its letter
export const iconsSettled = () => Promise.all(checks);

function spine(b, m, cover, w, s, i) {
  const name = b.title || host(b.url);
  const site = host(b.url).replace(/^(open|app|en)\./, '');
  const img = h('img', { alt: '', src: iconFor(b.url), draggable: false });
  const letter = h('span', { class: 'letter', hidden: true }, name.trim().charAt(0).toUpperCase());
  const cls = ['book', s.fresh === b.id && 'fresh', s.selected === b.id && 'selected'].filter(Boolean).join(' ');
  const a = h('a', {
    class: cls, href: b.url, title: `${b.title}\n${host(b.url)}`, draggable: s.editing, dataset: { id: b.id },
    style: `width:${w}rem;height:${SIZES[m.s].h}rem;--bg:${cover.bg};--fg:${cover.fg};--i:${i}`,
  },
  h('span', { class: 'box' },
    s.top && host(b.url) === s.top ? h('i', { class: 'ribbon' }) : null,
    h('i', { class: 'bk' }), h('i', { class: 'tp' }),
    h('i', { class: 'band head' }), h('i', { class: 'band foot' }),
    h('span', { class: 'nm' }, name),
    h('span', { class: 'au' }, site),
    h('span', { class: 'chip' }, img, letter)));
  // chrome's grey "never visited" icon would dye every cover grey, so only real icons get to pick the colour
  if (blanks.has(img.src)) { img.hidden = true; letter.hidden = false; return a; }
  checks.push(letterIfBlank(img, letter).then(blank => { if (blank) blanks.add(img.src); else learnCloth(b.url, img); }));
  return a;
}
