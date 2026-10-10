import * as store from './store.js';
import { host } from './urls.js';

const WEEK = 7 * 864e5;

async function weeklyTop(books) {
  const { weekly } = await chrome.storage.local.get('weekly');
  if (weekly && Date.now() - weekly.at < 30 * 60e3) return weekly.top;
  const since = Date.now() - WEEK;
  const hosts = new Set(books.map(b => host(b.url)));
  const items = (await chrome.history.search({ text: '', startTime: since, maxResults: 3000 }))
    .filter(it => hosts.has(host(it.url))).slice(0, 500);
  const counts = {};
  await Promise.all(items.map(async it => {
    const visits = await chrome.history.getVisits({ url: it.url });
    const h = host(it.url);
    counts[h] = (counts[h] || 0) + visits.filter(v => v.visitTime >= since).length;
  }));
  let top = null;
  for (const [h, n] of Object.entries(counts)) if (n >= 3 && (!top || n > counts[top])) top = h;
  await chrome.storage.local.set({ weekly: { at: Date.now(), top } });
  return top;
}

// recount whenever the ribbon setting flips, using the 30 minute cache in between
export function watchRibbon() {
  let on = null;
  store.subscribe(async s => {
    if (!s.folder || s.settings.ribbon === on) return;
    on = s.settings.ribbon;
    if (!on) {
      store.setTop(null);
      await chrome.storage.local.remove('weekly');
      return;
    }
    const { weekly } = await chrome.storage.local.get('weekly');
    if (weekly) store.setTop(weekly.top);
    store.setTop(await weeklyTop(s.books));
  });
}
