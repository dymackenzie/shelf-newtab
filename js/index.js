import { $, h } from './dom.js';
import { roman, bookEl } from './shelf.js';
import { next } from './paintings.js';

// one painting per page load: picked once and built once, so re-renders (adding a book, say) keep the same one
let plate = null;
function platePicked() {
  if (!plate) {
    const p = next();
    plate = h('figure', { class: 'plate', dataset: { key: p.key } },
      h('img', { src: p.src, alt: `${p.title} by ${p.artist}`, draggable: false, style: `object-position:${p.focus}` }),
      h('figcaption', {}, `${p.artist}, `, h('i', {}, p.title), `, ${p.year}`));
  }
  return plate;
}

// the contents page beside the shelf. hovering a line pulls its book off the shelf a little
export function renderIndex(s) {
  const box = $('#index');
  if (!s.folder || getComputedStyle(box).display === 'none') return box.replaceChildren();
  const d = new Date();
  const items = [];
  let n = 0;
  s.groups.forEach((g, gi) => {
    if (g.label) items.push(h('li', { class: 'gh' }, `${g.label}, ${roman(gi + 1)}`));
    for (const b of g.items) {
      const i = n++;
      items.push(h('li', {}, h('a', {
        href: b.url, tabindex: -1,
        onmouseenter: () => bookEl(b.id)?.classList.add('peek'),
        onmouseleave: () => bookEl(b.id)?.classList.remove('peek'),
        // chrome:// and file:// can't be followed from a page, same as the spines
        onclick: e => { if (!/^(https?|ftp):/.test(b.url)) { e.preventDefault(); chrome.tabs.update({ url: b.url }); } },
      }, b.title, h('i', {}, i < 9 ? roman(i + 1) : ''))));
    }
  });
  const count = s.books.length;
  box.replaceChildren(
    ...(s.settings.painting ? [platePicked()] : []),
    ...(s.settings.date ? [h('p', { class: 'ttl' }, h('em', {}, d.toLocaleDateString(undefined, { weekday: 'long' })), ' ', d.toLocaleDateString(undefined, { month: 'long', day: 'numeric' }))] : []),
    h('p', { class: 'sub' }, count ? `${count} book${count === 1 ? '' : 's'} on the shelf.` : 'No books yet.'),
    ...(count ? [h('ol', {}, items)] : []));
}
