import { $$ } from './dom.js';
import { get } from './store.js';

// where a drop at (x, y) lands: the nearest shelf row, then between the two books around x.
// past the last book it goes after it, an empty shelf takes it at the start
export function targetAt(x, y) {
  const rows = $$('#shelves .row');
  if (!rows.length) return null;
  const gap = row => {
    const top = row.getBoundingClientRect().top;
    const bottom = row.nextElementSibling.getBoundingClientRect().bottom;
    return y < top ? top - y : y > bottom ? y - bottom : 0;
  };
  const row = rows.reduce((a, b) => (gap(b) < gap(a) ? b : a));
  const books = $$('.book:not(.ghost)', row);
  if (!books.length) return { row, parentId: row.closest('.group').dataset.parent, index: 0 };

  const before = books.find(b => { const r = b.getBoundingClientRect(); return x < r.left + r.width / 2; });
  const el = before || books.at(-1);
  const node = get().books.find(b => b.id === el.dataset.id);
  if (!node) return null;
  return { el, after: !before, parentId: node.parentId, index: node.index + (before ? 0 : 1) };
}

export function clearMark() {
  for (const el of $$('.drop-before, .drop-after, .drop-empty')) el.classList.remove('drop-before', 'drop-after', 'drop-empty');
}

export function mark(t) {
  clearMark();
  if (!t) return;
  if (t.el) t.el.classList.add(t.after ? 'drop-after' : 'drop-before');
  else t.row.classList.add('drop-empty');
}
