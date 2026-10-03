export const host = url => { try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; } };

export function isWeb(v) {
  try { return /^https?:$/.test(new URL(v).protocol); } catch { return false; }
}

export function normalise(v) {
  v = v.trim();
  if (!v) return '';
  return /^[a-z][a-z0-9+.-]*:/i.test(v) ? v : `https://${v}`;
}

// figma.com -> Figma, calendar.google.com -> Calendar, en.wikipedia.org -> Wikipedia
const FILLER = new Set(['www', 'm', 'en', 'app', 'web', 'my']);
export function hostName(url) {
  const h = host(url);
  const word = h.split('.').find(p => !FILLER.has(p));
  if (!word || /^\d+$/.test(word)) return h;
  return word.charAt(0).toUpperCase() + word.slice(1);
}

// drag data is only readable inside the event handler, so grab everything up front
export const readDrag = dt => ({
  list: dt.getData('text/uri-list'),
  plain: dt.getData('text/plain'),
  html: dt.getData('text/html'),
  files: [...dt.files],
});

export const firstUri = list => (list || '').split(/\r?\n/).map(l => l.trim()).find(l => l && !l.startsWith('#')) || '';

export async function urlFromDrop(raw) {
  for (const c of [firstUri(raw.list), raw.plain.trim()]) if (isWeb(c)) return c;
  // .url shortcuts from explorer show up as files with a URL= line
  const f = raw.files.find(f => /\.url$/i.test(f.name));
  const m = f && (await f.text()).match(/^URL=(.+)$/mi);
  return m && isWeb(m[1].trim()) ? m[1].trim() : '';
}

export function linkText(html) {
  if (!html) return '';
  const a = new DOMParser().parseFromString(html, 'text/html').querySelector('a');
  return (a?.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 200);
}

// link text, then the title from history, then a tidied hostname
export async function titleFor(url, html) {
  const text = linkText(html);
  if (text) return text;
  const [hit] = await chrome.history.search({ text: url, startTime: 0, maxResults: 1 });
  if (hit && hit.url === url && hit.title) return hit.title;
  return hostName(url);
}
