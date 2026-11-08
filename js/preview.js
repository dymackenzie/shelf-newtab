import { h } from './dom.js';
import * as store from './store.js';
import { favicon } from './icons.js';
import { coverFrom } from './cloth.js';
import { host } from './urls.js';

// the small book in the add card, same face as a spine on the shelf
const TALL = { 1: 10.5, 2: 12, 3: 13.5, 4: 15 };

export function createPreview() {
  const nm = h('span', { class: 'nm' });
  const au = h('span', { class: 'au' });
  const img = h('img', { alt: '', draggable: false });
  const letter = h('span', { class: 'letter', hidden: true });
  const el = h('div', { class: 'mini', 'aria-hidden': 'true' },
    h('i', { class: 'band head' }), h('i', { class: 'band foot' }), nm, au, h('span', { class: 'chip' }, img, letter));
  const cur = { title: '', url: '', icon: '', size: 2 };
  let ask = 0;

  const paint = c => { el.style.setProperty('--bg', c.bg); el.style.setProperty('--fg', c.fg); };
  const fallback = url => { const k = store.inkOf(url || 'new'); return { bg: `var(--ink${k}-bg)`, fg: `var(--ink${k}-fg)` }; };

  async function recolour() {
    const n = ++ask;
    const known = cur.url && store.get().cloth[cur.url];
    if (!cur.icon && known) return paint(known);
    const probe = new Image();
    probe.src = cur.icon || (cur.url ? favicon(cur.url) : '');
    const c = probe.src ? await coverFrom(probe) : null;
    if (n === ask) paint(c || known || fallback(cur.url));
  }

  function set(patch) {
    Object.assign(cur, patch);
    const name = cur.title.trim() || (cur.url ? host(cur.url) : 'New book');
    nm.textContent = name;
    au.textContent = cur.url ? host(cur.url) : '';
    letter.textContent = name.charAt(0).toUpperCase();
    const src = cur.icon || (cur.url ? favicon(cur.url) : '');
    img.hidden = !src; letter.hidden = !!src;
    if (src && img.getAttribute('src') !== src) img.src = src;
    el.style.height = `${TALL[cur.size] || TALL[2]}rem`;
    if ('icon' in patch || 'url' in patch) recolour();
  }

  set({});
  return { el, set };
}
