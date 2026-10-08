import { $, rem } from './dom.js';

const panel = $('#panel');
let kind = null, onClose = null;

export const panelKind = () => kind;

export function openPanel(k, kids, anchor, closed) {
  closePanel();
  kind = k;
  onClose = closed;
  panel.className = 'panel';
  panel.dataset.kind = k; // not a class, "book" would pick up the spine styles
  panel.replaceChildren(...kids);
  place(anchor);
}

export const hidePanel = () => { panel.hidden = true; };

export function closePanel() {
  if (!kind) return;
  panel.hidden = true;
  panel.replaceChildren();
  const fn = onClose;
  kind = onClose = null;
  fn?.();
}

function place(anchor) {
  panel.hidden = false;
  const p = panel.getBoundingClientRect();
  if (!anchor) { // dock panels sit above the dock
    panel.style.left = `${innerWidth - p.width - 2.4 * rem()}px`;
    panel.style.top = `${innerHeight - p.height - 5.6 * rem()}px`;
    return;
  }
  const r = anchor.getBoundingClientRect(), pad = 16;
  let left = r.right + pad;
  if (left + p.width > innerWidth - pad) left = r.left - p.width - pad;
  const top = Math.min(Math.max(pad, r.top - 20), innerHeight - p.height - pad);
  panel.style.left = `${Math.max(pad, left)}px`;
  panel.style.top = `${top}px`;
}

document.addEventListener('mousedown', e => {
  if (!kind || panel.contains(e.target) || e.target.closest('.dock')) return;
  if (kind === 'book' && e.target.closest('.book')) return;
  closePanel();
});
