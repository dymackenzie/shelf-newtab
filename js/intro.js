// the page opens in one go instead of in bits: boot.js hides it, and once the fonts, icons and ribbon are in,
// the text comes up, the shelf fades in, then the books go on one at a time.
// render() rebuilds the shelf, so every render gets told how far into the opening it is (--late)
const STEP = 45, SPREAD = 650, LENGTH = 1800;
let t0 = null;

// start the faces loading now, before anything on the page asks for them
const fonts = Promise.all(['420 1em Fraunces', 'italic 380 1em Fraunces', '500 1em Archivo', '400 1em "JetBrains Mono"']
  .map(f => document.fonts.load(f))).catch(() => {});

const cap = (p, ms) => Promise.race([p, new Promise(r => setTimeout(r, ms))]);

export function introVars(n) {
  if (t0 == null || performance.now() - t0 > LENGTH) return '';
  return `--late:${Math.round(t0 - performance.now())}ms;--step:${Math.min(STEP, SPREAD / Math.max(n, 1)).toFixed(1)}ms`;
}

export async function reveal(...waits) {
  const html = document.documentElement;
  await cap(Promise.all([fonts, ...waits]), 900);
  await new Promise(r => requestAnimationFrame(r));
  // boot.js's safety net already showed the page, so playing the opening now would flash it
  if (!html.classList.contains('wait')) return;
  t0 = performance.now();
  // the shelf rendered while hidden, so give it the clock before it shows
  const shelves = document.getElementById('shelves');
  const n = shelves.querySelectorAll('.book').length;
  shelves.style.cssText = introVars(n);
  html.classList.add('intro');
  html.classList.remove('wait');
  setTimeout(() => { html.classList.remove('intro'); shelves.style.cssText = ''; }, LENGTH);
}

// images that are already on the page, decoded (or given up on)
export const decoded = root => Promise.all([...root.querySelectorAll('img')].map(i => i.decode().catch(() => {})));
