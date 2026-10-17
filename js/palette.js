// the page's colours all come from two picks: the paper and the accent. everything else (text, panels,
// grey text, the darker accent used for words) is worked out here so it always clears 5:1, even for a custom paper
export const PAPERS = [
  ['putty', 'Putty', '#DDDDD1'],
  ['linen', 'Linen', '#EDE8DD'],
  ['stone', 'Stone', '#D2CABD'],
  ['sage', 'Sage', '#CDD5C6'],
  ['blush', 'Blush', '#E7D6CF'],
  ['sky', 'Sky', '#D0DBE1'],
  ['night', 'Night', '#1B2027'],
];
export const ACCENTS = [
  ['magenta', 'Magenta', '#E2187F'],
  ['vermilion', 'Vermilion', '#E0452B'],
  ['cobalt', 'Cobalt', '#2F4BE0'],
  ['green', 'Green', '#1F9A55'],
  ['ochre', 'Ochre', '#D99A1C'],
];
const CACHE = 'shelf:theme';

const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
const toHex = c => '#' + c.map(v => Math.round(Math.min(255, Math.max(0, v))).toString(16).padStart(2, '0')).join('').toUpperCase();
const mix = (a, b, t) => toHex(rgb(a).map((v, i) => v + (rgb(b)[i] - v) * t));
export const lum = hex => {
  const [r, g, b] = rgb(hex).map(v => v / 255).map(x => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
export const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
export const isHex = v => /^#[0-9a-f]{6}$/i.test(v || '');

const pick = (list, v, fallback) => list.find(p => p[0] === v)?.[2] || (isHex(v) ? v.toUpperCase() : fallback);
export const paperHex = v => pick(PAPERS, v, PAPERS[0][2]);
export const accentHex = v => pick(ACCENTS, v, ACCENTS[0][2]);

// push a colour toward black or white in small steps until it clears min against every background given
function clear(colour, backs, toward, min = 5.1) {
  let c = colour;
  for (let i = 0; i <= 40 && backs.some(b => ratio(c, b) < min); i++) c = mix(colour, toward, i / 40);
  return c;
}

export function derive({ paper, accent, grain = true }) {
  const hot = accentHex(accent);
  let ground = paperHex(paper);
  // dark text or light text, whichever reads better. a loud paper (pure red, say) where neither clears 5:1
  // gets nudged lighter or darker until it does: the paper moves, never the text
  const dark = ratio('#EDE8DC', ground) > ratio('#141210', ground);
  const text = dark ? '#EDE8DC' : '#141210';
  ground = clear(ground, [text], dark ? '#000000' : '#FFFFFF', 5.4);
  const card = mix(ground, '#FFFFFF', dark ? 0.06 : 0.35);
  const field = ground;
  // grey text: as far toward the paper as it can go while staying readable on paper, panels and fields
  let dim = text;
  for (let t = 0.7; t >= 0; t -= 0.02) { const c = mix(text, ground, t); if ([ground, card, field].every(b => ratio(c, b) >= 5.15)) { dim = c; break; } }
  return {
    '--ground': ground, '--card': card, '--field': field, '--text': text, '--dim': dim,
    '--accent': hot, '--accent-text': clear(hot, [ground, card], dark ? '#FFFFFF' : '#000000'),
    '--track-on': text, '--knob-on': ground, '--track-off': mix(ground, text, dark ? 0.22 : 0.16), '--knob-off': card,
    '--shadow': dark ? '0, 0, 0' : '32, 30, 22',
    '--rule': dark ? 'rgba(237, 232, 220, .28)' : 'rgba(32, 30, 22, .45)',
    '--grain': grain ? (dark ? '.22' : '.1') : '0',
    'color-scheme': dark ? 'dark' : 'light',
  };
}

let last = '';
export function applyTheme(settings) {
  const vars = derive(settings);
  const key = JSON.stringify(vars);
  if (key === last) return;
  last = key;
  for (const [k, v] of Object.entries(vars)) document.documentElement.style.setProperty(k, v);
  // boot.js reads this before the page paints, so a new tab never flashes the default paper first
  localStorage.setItem(CACHE, key);
}
