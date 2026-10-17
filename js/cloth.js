import * as store from './store.js';

// a book's cloth comes from its site's icon: the main colour, dyed darker and duller like a real cover
const CREAM = '#F1EADB', INK = '#1A1612';

function hsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2, d = max - min;
  if (!d) return [0, 0, l];
  const s = d / (1 - Math.abs(2 * l - 1));
  const h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [(h * 60 + 360) % 360, s, l];
}

function hex(h, s, l) {
  const k = n => (n + h / 30) % 12, a = s * Math.min(l, 1 - l);
  const f = n => Math.round(255 * (l - a * Math.max(-1, Math.min(k(n) - 3, 9 - k(n), 1))));
  return '#' + [f(0), f(8), f(4)].map(v => v.toString(16).padStart(2, '0')).join('');
}

const lum = c => {
  const v = [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16) / 255).map(x => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
  return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
};
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

// the hue most of the coloured pixels share. icons that are only black and white become black or cream cloth
function mainColour(img) {
  const c = document.createElement('canvas');
  c.width = c.height = 24;
  const g = c.getContext('2d', { willReadFrequently: true });
  g.drawImage(img, 0, 0, 24, 24);
  const px = g.getImageData(0, 0, 24, 24).data;
  const bins = new Map();
  let n = 0, light = 0;
  for (let i = 0; i < px.length; i += 4) {
    if (px[i + 3] < 160) continue;
    const [h, s, l] = hsl(px[i], px[i + 1], px[i + 2]);
    n++; light += l;
    if (s < 0.25 || l < 0.12 || l > 0.92) continue;
    const k = Math.round(h / 20) % 18, b = bins.get(k) || { n: 0, s: 0, l: 0 };
    b.n++; b.s += s; b.l += l;
    bins.set(k, b);
  }
  if (!n) return null;
  const glyph = n < 24 * 24 * 0.55; // see-through icon, just a mark with no square behind it
  const [k, best] = [...bins].sort((a, b) => b[1].n - a[1].n)[0] || [];
  if (best && best.n >= n * 0.12) return [k * 20, best.s / best.n, best.l / best.n];
  // a white mark with nothing behind it was drawn for dark backgrounds, so give it dark cloth
  return light / n < 0.5 || glyph ? [40, 0.06, 0.13] : [42, 0.25, 0.88];
}

function dye([h, s, l]) {
  // mostly white icons (wikipedia) make cream paper boards with dark titles
  const paper = l > 0.75 && s < 0.4;
  if (paper) { s = Math.min(s, 0.3); l = 0.88; }
  else if (s >= 0.1) {
    s = Math.min(s, 0.7) * 0.72;
    l = Math.min(Math.max(l * 0.7, 0.2), 0.36);
    if (h > 38 && h < 70) l = Math.max(l, 0.46); // darkened yellow turns to mud, so let it stay ochre
  }
  // same 5:1 rule as the rest of the page: walk the cloth away from the title colour until it passes.
  // coloured cloth always takes cream titles and gets darker, so bright icons can't end up as neon covers
  const fg = paper || (h > 38 && h < 70 && s >= 0.1) ? INK : CREAM;
  let bg = hex(h, s, l);
  for (let i = 0; i < 20 && ratio(fg, bg) < 5; i++) {
    l = Math.min(Math.max(l + (fg === CREAM ? -0.03 : 0.03), 0), 1);
    bg = hex(h, s, l);
  }
  return { bg, fg };
}

// null when the image can't be read (a linked icon from a site that doesn't allow it)
export async function coverFrom(img) {
  try {
    await img.decode();
    const c = mainColour(img);
    return c ? dye(c) : null;
  } catch {
    return null;
  }
}

export async function learnCloth(url, img) {
  const c = await coverFrom(img);
  if (c) store.saveCloth(url, c);
}
