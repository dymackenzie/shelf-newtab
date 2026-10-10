import { $, $$ } from './dom.js';
import { get } from './store.js';
import { targetAt, mark, clearMark } from './drop.js';
import { hidePanel, closePanel } from './panel.js';

let dragId = null;
export const reordering = () => dragId !== null;

function end() {
  if (dragId === null) return;
  dragId = null;
  clearMark();
  for (const el of $$('.dragging')) el.classList.remove('dragging');
  closePanel();
}

export function initReorder() {
  $('#shelves').addEventListener('dragstart', e => {
    const a = e.target.closest('.book');
    if (!a || !get().editing || !a.dataset.id) return;
    dragId = a.dataset.id;
    a.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    // only hide it for now. closing re-renders the shelf, and that would pull the book out from under the drag
    hidePanel();
  });
  document.addEventListener('dragover', e => {
    if (!dragId) return;
    e.preventDefault();
    mark(targetAt(e.clientX, e.clientY));
  });
  document.addEventListener('drop', async e => {
    if (!dragId) return;
    e.preventDefault();
    const id = dragId, t = targetAt(e.clientX, e.clientY);
    end();
    // index is counted before the moved book is taken out, which is what move() expects
    if (t) await chrome.bookmarks.move(id, { parentId: t.parentId, index: t.index });
  });
  document.addEventListener('dragend', end);
}
