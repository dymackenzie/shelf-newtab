export const favicon = url => chrome.runtime.getURL(`/_favicon/?pageUrl=${encodeURIComponent(url)}&size=64`);

// chrome hands back a grey page icon for sites it has never visited. spot it and use a letter instead
async function sigOf(src) {
  const img = new Image();
  img.src = src;
  await img.decode();
  const c = document.createElement('canvas');
  c.width = c.height = 32;
  c.getContext('2d').drawImage(img, 0, 0, 32, 32);
  return c.toDataURL();
}
// without a sample of the blank icon we just never swap in letters
const blankSig = sigOf(favicon('https://shelf-no-icon.invalid/')).catch(() => null);

export async function letterIfBlank(img, letter) {
  if (img.src.startsWith('data:')) return false;
  try {
    const [blank, mine] = await Promise.all([blankSig, sigOf(img.src)]);
    if (blank && blank === mine) { img.hidden = true; letter.hidden = false; return true; }
  } catch {
    // an icon that won't decode keeps showing whatever chrome gave us
  }
  return false;
}

// every image gets squashed to a 64px png so storage stays small
export function shrink(src) {
  const isBlob = typeof src !== 'string';
  const url = isBlob ? URL.createObjectURL(src) : src;
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const c = document.createElement('canvas');
      c.width = c.height = 64;
      const s = Math.min(64 / img.width, 64 / img.height);
      const w = img.width * s, h = img.height * s;
      c.getContext('2d').drawImage(img, (64 - w) / 2, (64 - h) / 2, w, h);
      if (isBlob) URL.revokeObjectURL(url);
      resolve(c.toDataURL('image/png'));
    };
    img.onerror = () => {
      if (isBlob) URL.revokeObjectURL(url);
      reject(new Error('Shelf could not read that image'));
    };
    img.src = url;
  });
}

export const imageFile = files => [...(files || [])].find(f => f.type.startsWith('image/'));

// an image dragged off a web page arrives as html with an <img>, or just its url
export function imageUrlFrom({ html, list, plain }) {
  const src = html && new DOMParser().parseFromString(html, 'text/html').querySelector('img[src]')?.getAttribute('src');
  const first = (list || '').split(/\r?\n/).find(l => l && !l.startsWith('#'));
  return [src, first, plain].map(x => x?.trim()).find(x => x && (/^https?:\/\//i.test(x) || x.startsWith('data:image/'))) || '';
}

export const canRead = url => chrome.permissions.contains({ origins: [`${new URL(url).origin}/*`] });

export async function fetchImage(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} for ${url}`);
  const blob = await res.blob();
  if (!blob.type.startsWith('image/')) throw new Error(`${url} is not an image`);
  return blob;
}
