import { h } from './dom.js';
import { readDrag } from './urls.js';
import { shrink, imageFile, imageUrlFrom, canRead, fetchImage } from './icons.js';

// only one well is ever on screen, and it takes any image pasted on the page
let active = null;

document.addEventListener('paste', e => {
  const f = active && imageFile(e.clipboardData?.files);
  if (!f) return;
  e.preventDefault();
  active.take(f);
});

export function createWell({ src, onImage }) {
  const img = h('img', { alt: '', draggable: false });
  const hint = h('span', {}, 'paste image');
  const pick = h('button', { type: 'button', class: 'pick-img mono', title: 'Paste, drop, or click to choose an image' }, img, hint);
  const allow = h('button', { type: 'button', class: 'allow' }, 'Allow images from websites');
  const note = h('span', { class: 'note mono' }, 'Copy the image and paste it instead');
  const file = h('input', { type: 'file', accept: 'image/*', hidden: true });
  const el = h('div', { class: 'well', dataset: { mode: 'idle' } }, pick, allow, note, file);
  let waiting = null; // a web image waiting on the host permission

  const mode = m => { el.dataset.mode = m; };
  const show = s => {
    img.hidden = !s;
    hint.hidden = !!s;
    if (s) img.src = s;
  };

  async function take(blob) {
    const data = await shrink(blob);
    show(data);
    mode('idle');
    onImage(data);
  }

  async function fromWeb(url) {
    let blob;
    try {
      blob = await fetchImage(url);
    } catch {
      // dead link, wrong type, blocked. pasting still works so point him there
      return mode('nope');
    }
    await take(blob);
  }

  pick.addEventListener('click', () => file.click());
  file.addEventListener('change', () => {
    const f = imageFile(file.files);
    file.value = '';
    if (f) take(f);
  });

  el.addEventListener('dragover', e => {
    e.preventDefault();
    e.stopPropagation();
    el.classList.add('over');
  });
  el.addEventListener('dragleave', () => el.classList.remove('over'));
  el.addEventListener('drop', async e => {
    e.preventDefault();
    e.stopPropagation();
    el.classList.remove('over');
    const raw = readDrag(e.dataTransfer);
    const f = imageFile(raw.files);
    if (f) return take(f);
    const url = imageUrlFrom(raw);
    if (!url) return;
    if (url.startsWith('data:')) return take(url);
    if (await canRead(url)) return fromWeb(url);
    // a drop isn't a user gesture, so the permission ask has to wait for a click
    waiting = url;
    mode('ask');
  });
  allow.addEventListener('click', async () => {
    const ok = await chrome.permissions.request({ origins: ['<all_urls>'] });
    if (ok) fromWeb(waiting);
    else mode('nope');
  });

  show(src);
  const well = {
    el, take, show,
    destroy() { if (active === well) active = null; },
  };
  active = well;
  return well;
}
