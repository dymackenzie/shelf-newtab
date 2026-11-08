import { h } from './dom.js';
import { readDrag } from './urls.js';
import { shrink, imageFile, imageUrlFrom, fetchImage } from './icons.js';

// one icon field on screen at a time, and it takes any image pasted on the page
let active = null;
document.addEventListener('paste', e => {
  const f = active && imageFile(e.clipboardData?.files);
  if (!f) return;
  e.preventDefault();
  active.take(f);
});

const PIC = '<svg viewBox="0 0 24 24"><rect x="3.5" y="4.5" width="17" height="15" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M4 18l5-5 4 4 3-3 4 4"/></svg>';
const isAddress = v => /^https?:\/\//i.test(v) || v.startsWith('data:image/');
const loads = src => new Promise(ok => { const i = new Image(); i.onload = () => ok(i.naturalWidth > 0); i.onerror = () => ok(false); i.src = src; });

// an icon from an image address, a pasted or dropped file, or the file picker.
// onImage gets a png data url when shelf could copy the image, or the address itself when it could only link it
export function createIconField({ src, onImage }) {
  const img = h('img', { alt: '', draggable: false, hidden: !src, src: src || '' });
  const glyph = h('span', { class: 'glyph', hidden: !!src });
  glyph.innerHTML = PIC;
  const file = h('input', { type: 'file', accept: 'image/*', hidden: true });
  const square = h('button', { type: 'button', class: 'sq', title: 'Choose an image file' }, img, glyph);
  const input = h('input', { type: 'text', class: 'iconaddr', placeholder: 'an image address', 'aria-label': 'Image address', spellcheck: false });
  const pickFile = h('button', { type: 'button', class: 'link file' }, 'or a file');
  const status = h('span', { class: 'status', hidden: true });
  let tried = '', timer;

  const show = s => { img.hidden = !s; glyph.hidden = !!s; if (s) img.src = s; };
  const say = (...kids) => { status.replaceChildren(...kids); status.hidden = !kids.length; };

  async function take(blob) {
    const data = await shrink(blob);
    show(data);
    say();
    onImage(data);
  }

  async function copy(url) {
    const data = await shrink(await fetchImage(url));
    show(data);
    say('Copied.');
    onImage(data);
  }

  async function fromAddress(url) {
    if (url === tried) return;
    tried = url;
    if (url.startsWith('data:image/')) return take(url);
    say('Getting it\u2026');
    try {
      // most image hosts let any page read their files, and a granted site always does
      return await copy(url);
    } catch {
      // the site won't hand the file over, so fall back to just showing it from there
    }
    if (url !== tried) return;
    if (!(await loads(url))) return say("That address didn't open as an image.");
    show(url);
    onImage(url);
    const keep = h('button', { type: 'button', class: 'link keep' }, 'Keep a copy');
    keep.addEventListener('click', async () => {
      const origin = `${new URL(url).origin}/*`;
      // just this one site, and only after a click
      if (!(await chrome.permissions.request({ origins: [origin] }))) return say('Still linked. Copy the image itself and paste it to keep a copy.');
      try { await copy(url); } catch { say("Couldn't copy it. Copy the image itself and paste it instead."); }
    });
    say('Linked, not copied. ', keep);
  }

  const check = () => {
    let v = input.value.trim();
    if (!v) { tried = ''; return say(); }
    // copied from the address bar without the https:// part
    if (/^[\w-]+(\.[\w-]+)+\//.test(v)) v = `https://${v}`;
    if (isAddress(v)) fromAddress(v);
    else say('Paste the image address, starting with https://');
  };
  input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(check, 250); });
  input.addEventListener('paste', () => { clearTimeout(timer); timer = setTimeout(check, 0); });
  square.addEventListener('click', () => file.click());
  pickFile.addEventListener('click', () => file.click());
  file.addEventListener('change', () => {
    const f = imageFile(file.files);
    file.value = '';
    if (f) { input.value = ''; tried = ''; take(f); }
  });

  // drop zone is whatever element the caller hands over (the whole card, say)
  const offs = [];
  function dropOn(zone) {
    const on = (type, fn) => { zone.addEventListener(type, fn); offs.push(() => zone.removeEventListener(type, fn)); };
    on('dragover', e => {
      if (![...e.dataTransfer.types].some(t => t === 'Files' || t === 'text/uri-list' || t === 'text/html')) return;
      e.preventDefault();
      e.stopPropagation();
      zone.classList.add('over');
    });
    on('dragleave', e => { if (!zone.contains(e.relatedTarget)) zone.classList.remove('over'); });
    on('drop', e => {
      e.preventDefault();
      e.stopPropagation();
      zone.classList.remove('over');
      const raw = readDrag(e.dataTransfer);
      const f = imageFile(raw.files);
      if (f) { input.value = ''; tried = ''; return take(f); }
      // an image dragged off a web page arrives as its address
      const url = imageUrlFrom(raw);
      if (url) { input.value = url.startsWith('data:') ? '' : url; fromAddress(url); }
    });
  }

  const field = {
    square, input, pickFile, status, file, take, show, dropOn, fromAddress,
    // the panel element outlives the field, so its drop listeners have to come off
    destroy() { clearTimeout(timer); offs.splice(0).forEach(f => f()); if (active === field) active = null; },
  };
  active = field;
  return field;
}
