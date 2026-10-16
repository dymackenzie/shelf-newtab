"""Shelf v0.2 tests. Playwright's Chromium, headless, with the unpacked extension and a seeded Bookmarks file.

Chromium instead of Chrome because branded Chrome stopped honouring --load-extension in 137, and a
throwaway Chromium profile never signs into an account, so nothing here can sync anywhere.

Setup, once (the venv lives outside the extension because Chrome won't load a folder with _ files in it):
    py -m venv C:/dev/.venvs/shelf-newtab
    C:/dev/.venvs/shelf-newtab/Scripts/python -m pip install playwright
    C:/dev/.venvs/shelf-newtab/Scripts/python -m playwright install chromium   (skip if ms-playwright already has one)
Run:
    C:/dev/.venvs/shelf-newtab/Scripts/python tests/cdp_test.py      exit code 1 if anything fails
"""
import glob, json, os, re, shutil, subprocess, sys, time, urllib.request, uuid
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, 'tests', 'shots')
TMP = os.environ.get('TMPDIR') or os.path.join(os.environ['LOCALAPPDATA'], 'Temp')
PROF = os.path.join(TMP, 'shelf-prof-v02')
EXT_ID = 'emgclpndjmgfkfkmaggaeefeockeddhh'  # fixed by manifest.key
PORT = 9341

LINKS = [('Calendar', 'https://calendar.google.com/calendar/u/0/r'), ('Docs', 'https://docs.google.com/document/u/0/'),
         ('Notion', 'https://www.notion.so/'), ('Photos', 'https://photos.google.com/'), ('Canvas', 'https://canvas.ubc.ca/'),
         ('Piazza', 'https://piazza.com/'), ('UBC', 'https://www.ubc.ca/'), ('Gemini', 'https://gemini.google.com/app'),
         ('Claude', 'https://claude.ai/new')]
LATER = [('Are.na', 'https://www.are.na/'), ('recent.design', 'https://recent.design/')]
SEEDED = [n for n, _ in LINKS + LATER]
SIZES = [(1440, 900), (1280, 720), (900, 800)]
FIGMA = {'text/uri-list': 'https://www.figma.com/community', 'text/html': '<a href="https://www.figma.com/community">Figma Community</a>'}

results = []
def check(name, ok, detail=''):
    results.append((name, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail != '' else ''), flush=True)


def chromium():
    exes = glob.glob(os.path.join(os.environ['LOCALAPPDATA'], 'ms-playwright', 'chromium-*', 'chrome-win64', 'chrome.exe'))
    if not exes: sys.exit('no Playwright Chromium found, run: python -m playwright install chromium')
    return max(exes, key=lambda p: int(re.search(r'chromium-(\d+)', p).group(1)))


def seed():
    shutil.rmtree(PROF, ignore_errors=True)
    os.makedirs(os.path.join(PROF, 'Default'))
    nid = iter(range(10, 999))
    def url(t, u): return {'type': 'url', 'name': t, 'url': u, 'id': str(next(nid)), 'guid': str(uuid.uuid4()), 'date_added': '13370000000000000'}
    def folder(t, kids, i=None): return {'type': 'folder', 'name': t, 'children': kids, 'id': i or str(next(nid)), 'guid': str(uuid.uuid4()), 'date_added': '13370000000000000', 'date_modified': '0'}
    bar = [url(*l) for l in LINKS] + [folder('Later', [url(*l) for l in LATER])]
    data = {'roots': {'bookmark_bar': folder('Bookmarks bar', bar, '1'), 'other': folder('Other bookmarks', [], '2'),
                      'synced': folder('Mobile bookmarks', [], '3')}, 'version': 1}
    json.dump(data, open(os.path.join(PROF, 'Default', 'Bookmarks'), 'w'))


# contrast, straight from theme.css
def theme_pairs():
    css = open(os.path.join(ROOT, 'theme.css'), encoding='utf-8').read()
    tokens = dict(re.findall(r'--([\w-]+):\s*([^;]+);', css))
    def colour(name, depth=0):
        v = tokens[name].strip()
        m = re.fullmatch(r'var\(--([\w-]+)\)', v)
        return colour(m.group(1), depth + 1) if m and depth < 5 else v
    pairs = [tuple(p.split('/')) for p in re.search(r'pairs:([^*]+)\*/', css).group(1).split()]
    pairs += [(f'ink{i}-fg', f'ink{i}-bg') for i in range(10) if f'ink{i}-fg' in tokens]
    return [(fg, bg, colour(fg), colour(bg)) for fg, bg in pairs]

def lum(hexv):
    h = hexv.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

def ratio(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


HELPERS = r"""() => {
window.T = {
  books: () => [...document.querySelectorAll('#shelves .book:not(.ghost)')],
  names: () => T.books().map(b => b.querySelector('.nm').textContent),
  book: name => T.books().find(b => b.querySelector('.nm').textContent === name),
  dt(data) { const d = new DataTransfer(); for (const [k, v] of Object.entries(data || {})) d.setData(k, v); return d; },
  fire(type, x, y, dt, el) {
    el = el || document.elementFromPoint(x, y) || document.body;
    const e = new DragEvent(type, { bubbles: true, cancelable: true, composed: true, clientX: x, clientY: y, dataTransfer: dt });
    el.dispatchEvent(e);
    return e.defaultPrevented;
  },
  between(a, b) {
    const ra = T.book(a).getBoundingClientRect(), rb = T.book(b).getBoundingClientRect();
    return [(ra.right + rb.left) / 2, rb.top + rb.height / 2];
  },
  dropLink(a, b, data, overOnly) {
    const [x, y] = T.between(a, b), d = T.dt(data);
    const over = T.fire('dragover', x, y, d);
    return overOnly ? over : [over, T.fire('drop', x, y, d)];
  },
  async png() {
    const c = document.createElement('canvas'); c.width = c.height = 200;
    const g = c.getContext('2d'), gr = g.createLinearGradient(0, 0, 200, 200);
    gr.addColorStop(0, 'rgb(242,115,88)'); gr.addColorStop(1, 'rgb(70,96,111)');
    g.fillStyle = gr; g.fillRect(0, 0, 200, 200);
    g.fillStyle = 'rgb(23,34,46)'; g.fillRect(60, 60, 80, 80);
    const blob = await new Promise(r => c.toBlob(r, 'image/png'));
    return new File([blob], 'icon.png', { type: 'image/png' });
  },
  async paste(el) {
    const d = new DataTransfer(); d.items.add(await T.png());
    (el || document.activeElement || document.body).dispatchEvent(new ClipboardEvent('paste', { bubbles: true, cancelable: true, clipboardData: d }));
  },
  async kids(id = '1') { return (await chrome.bookmarks.getChildren(id)).map(c => ({ id: c.id, title: c.title, url: c.url || null, index: c.index })); },
  vis: el => !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden',
  center(el) { const r = el.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; },
};
return true;
}"""


def run(page, cdp, errors):
    ev = page.evaluate
    sleep = page.wait_for_timeout
    def key(k): page.keyboard.press(k); sleep(250)
    def size(w, hgt): page.set_viewport_size({'width': w, 'height': hgt}); sleep(600)
    def shot(name):
        p = os.path.join(SHOTS, name); page.screenshot(path=p); return p

    ev(HELPERS)

    print('\n# 1 load')
    fonts = ev("Promise.all([...document.fonts].map(f => f.load().then(() => f.family + ':' + f.status, () => f.family + ':fail')))")
    check('fonts load', len(fonts) == 3 and all(f.endswith(':loaded') for f in fonts), ', '.join(fonts))
    names = ev('T.names()')
    check('seeded books render in order', [n for n in names if n in SEEDED] == SEEDED, ', '.join(names))
    groups = ev("[...document.querySelectorAll('.group')].map(g => (g.querySelector('h2')?.textContent || '-') + ':' + g.querySelectorAll('.book').length)")
    check('Later gets its own labelled shelf', 'Later:2' in groups, ', '.join(groups))
    ribbon = ev("[...document.querySelectorAll('.book')].filter(b => b.querySelector('.ribbon')).map(b => b.querySelector('.nm').textContent)")
    check('ribbon on the most opened book', ribbon == ['Piazza'], ribbon)

    # his sizes, so the shots look like his shelf
    ev("""chrome.storage.sync.set({'b:https://calendar.google.com/calendar/u/0/r': {s: 4, ink: 0},
      'b:https://www.notion.so/': {s: 3, ink: 2}, 'b:https://canvas.ubc.ca/': {s: 4, ink: 1}}).then(() => 1)""")
    sleep(1000)

    print('\n# 10 screenshots')
    shots = []
    for w, hgt in SIZES:
        size(w, hgt)
        tag = f'{w}x{hgt}'
        check(f'{tag} no horizontal overflow', not ev('document.documentElement.scrollWidth > innerWidth'))
        shots.append(shot(f'{tag}-1-shelf.png'))
        ev("d => T.dropLink('Docs', 'Notion', d, true)", FIGMA)
        check(f'{tag} insertion bar shows while dragging', ev("document.querySelectorAll('.drop-before, .drop-after').length") == 1)
        shots.append(shot(f'{tag}-2-dropping.png'))
        ev("d => T.dropLink('Docs', 'Notion', d)", FIGMA)
        sleep(800)
        check(f'{tag} slim card opens inside the window', ev("T.vis(document.querySelector('#card')) && document.querySelector('#card').getBoundingClientRect().right <= innerWidth"))
        shots.append(shot(f'{tag}-3-card.png'))
        ev("document.querySelector('#card .undo').click()"); sleep(600)
        ev("document.querySelector('#gear').click()"); sleep(400)
        fits = ev("(() => { const r = document.querySelector('#panel').getBoundingClientRect(); return r.left >= 0 && r.top >= 0 && r.right <= innerWidth })()")
        check(f'{tag} settings panel fits', fits)
        shots.append(shot(f'{tag}-4-settings.png'))
        key('Escape')
    size(1440, 900)
    check('screenshot drops were all undone', ev("T.names().filter(n => n === 'Figma Community').length") == 0)

    print('\n# 2 drop a link')
    fired = ev("d => T.dropLink('Docs', 'Notion', d)", FIGMA)
    sleep(800)
    check('dragover and drop are accepted', fired == [True, True], fired)
    kids = ev('T.kids()')
    new = next((k for k in kids if k['url'] == 'https://www.figma.com/community'), None)
    docs = next(k for k in kids if k['title'] == 'Docs')
    check('bookmark created at index 2 with the link text', new and new['index'] == 2 == docs['index'] + 1 and new['title'] == 'Figma Community', new)
    check('new book sits between Docs and Notion', ev('T.names()')[1:4] == ['Docs', 'Figma Community', 'Notion'])
    st = ev("""(() => { const a = document.activeElement, card = document.querySelector('#card');
      return { open: T.vis(card), focused: !!card && card.contains(a) && a.classList.contains('name'),
        selected: a.selectionStart === 0 && a.selectionEnd === a.value.length && a.value.length > 0,
        url: card?.querySelector('.url')?.textContent, fresh: T.book('Figma Community')?.classList.contains('fresh'),
        raised: getComputedStyle(T.book('Figma Community')).transform !== 'none' } })()""")
    check('slim card open, name focused and selected', st['open'] and st['focused'] and st['selected'], st)
    check('new book is raised with the ring', st['fresh'] and st['raised'])
    check('card shows the url, not editable', st['url'] == 'https://www.figma.com/community')

    print('\n# 3 paste an image')
    ev('T.paste()'); sleep(800)
    icon = ev("chrome.storage.local.get('i:https://www.figma.com/community').then(r => r['i:https://www.figma.com/community'] || '')")
    check('i:<url> is a png data url', icon.startswith('data:image/png;base64,'), icon[:40])
    check('icon is at most about 12 KB', 0 < len(icon) <= 12 * 1024, f'{len(icon)} bytes')
    shows = ev("({ book: T.book('Figma Community').querySelector('img').src, well: document.querySelector('#card .well img').src })")
    check('book shows the pasted image', shows['book'] == icon)
    check('well shows the pasted image', shows['well'] == icon)

    print('\n# 4 undo and esc')
    ev("document.querySelector('#card .undo').click()"); sleep(800)
    check('Undo deletes the bookmark', ev("chrome.bookmarks.search({ url: 'https://www.figma.com/community' }).then(r => r.length)") == 0)
    check('Undo clears its icon', not ev("chrome.storage.local.get('i:https://www.figma.com/community').then(r => !!r['i:https://www.figma.com/community'])"))
    check('Undo closes the card', not ev("T.vis(document.querySelector('#card'))"))
    ev("d => T.dropLink('Notion', 'Photos', d)", {'text/uri-list': 'https://example.org/kept', 'text/html': '<a href="https://example.org/kept">Kept book</a>'})
    sleep(800)
    ev("document.activeElement.value = 'Not saved'")
    key('Escape'); sleep(400)
    kept = ev("chrome.bookmarks.search({ url: 'https://example.org/kept' }).then(r => r.map(b => b.title))")
    check('Esc keeps the book', kept == ['Kept book'], kept)
    foc = ev("({ card: T.vis(document.querySelector('#card')), focus: document.activeElement === T.book('Kept book'), fresh: document.querySelectorAll('.book.fresh').length })")
    check('Esc closes the card and focus returns to the new book', not foc['card'] and foc['focus'] and foc['fresh'] == 0, foc)

    # no link text, so the title should come from history
    ev("d => T.dropLink('Photos', 'Canvas', d)", {'text/uri-list': 'https://piazza.com/'}); sleep(1000)
    hist = ev("chrome.history.search({ text: 'https://piazza.com/', startTime: 0, maxResults: 1 }).then(r => r[0] ? { url: r[0].url, title: r[0].title } : null)")
    got = ev("document.querySelector('#card .name')?.value")
    expect = hist['title'] if hist and hist['url'] == 'https://piazza.com/' and hist['title'] else 'Piazza'
    check('no link text: title comes from history, else the hostname', got == expect, f'{got!r}, history has {hist}')
    ev("document.querySelector('#card .undo').click()"); sleep(600)

    print('\n# 5 + flow')
    ev("document.querySelector('#add').click()"); sleep(500)
    g = ev("""(() => { const gh = document.querySelector('.book.ghost'), a = document.activeElement;
      return { ghost: !!gh, inFirst: gh?.closest('.group') === document.querySelector('.group'), last: gh?.parentElement.lastElementChild === gh,
        focus: a.classList.contains('address'), ph: a.placeholder, card: T.vis(document.querySelector('#card')) } })()""")
    check('ghost book at the end of the first shelf', g['ghost'] and g['inFirst'] and g['last'], g)
    check('address input focused with "paste a link"', g['focus'] and g['ph'] == 'paste a link' and g['card'], g)
    page.keyboard.insert_text('figma.com'); sleep(800)
    filled = ev("document.querySelector('#card .name').value")
    check('entering an address fills the name from the hostname', filled == 'Figma', filled)
    ev("document.querySelector('#card .primary').click()"); sleep(900)
    kids = ev('T.kids()')
    links = [k for k in kids if k['url']]
    fig = next((k for k in kids if k['url'] == 'https://figma.com/'), None)
    check('Done creates the bookmark at the end of the shelf', fig and links[-1]['id'] == fig['id'] and fig['title'] == 'Figma', fig)
    after = ev("""({ ghost: !!document.querySelector('.book.ghost'), focus: document.activeElement === T.book('Figma'),
      last: T.books().filter(b => b.closest('.group') === document.querySelector('.group')).at(-1).querySelector('.nm').textContent })""")
    check('ghost gone, Figma is the last book, focus on it', not after['ghost'] and after['last'] == 'Figma' and after['focus'], after)
    ev("document.querySelector('#add').click()"); sleep(400)
    key('Escape')
    check('Esc removes the ghost', not ev("!!document.querySelector('.book.ghost') || T.vis(document.querySelector('#card'))"))

    print('\n# 6 image well')
    ev("document.querySelector('#add').click()"); sleep(400)
    ev("""async () => { const d = new DataTransfer(); d.items.add(await T.png()); const w = document.querySelector('#card .well');
      const [x, y] = T.center(w); T.fire('dragover', x, y, d, w); T.fire('drop', x, y, d, w); }""")
    sleep(600)
    check('dropping a file on the well sets the image', ev("document.querySelector('#card .well img').src.startsWith('data:image/png')"))
    ev("() => { window.__fetches = []; const f0 = window.fetch; window.fetch = (...a) => { window.__fetches.push(String(a[0])); return f0(...a); }; }")
    ev("""() => { const w = document.querySelector('#card .well'), [x, y] = T.center(w);
      const d = T.dt({ 'text/uri-list': 'https://example.com/cat.png', 'text/html': '<img src="https://example.com/cat.png">' });
      T.fire('dragover', x, y, d, w); T.fire('drop', x, y, d, w); }""")
    sleep(800)
    w6 = ev("""(() => { const w = document.querySelector('#card .well'), b = w.querySelector('.allow');
      return { mode: w.dataset.mode, allow: T.vis(b) ? b.textContent : null, note: T.vis(w.querySelector('.note')), fetches: window.__fetches.length } })()""")
    check('web image: well shows "Allow images from websites"', w6['allow'] == 'Allow images from websites' and not w6['note'], w6)
    check('web image: no fetch without permission', w6['fetches'] == 0, w6['fetches'])
    check('host permission is still not granted', not ev("chrome.permissions.contains({ origins: ['https://example.com/*'] })"))
    shot('1440x900-5-allow-images.png')
    key('Escape')
    check('web image drop did not add a book', 'Example' not in ev('T.names()') and not ev("!!document.querySelector('.book.ghost')"))

    print('\n# 7 settings')
    ev("document.querySelector('#gear').click()"); sleep(400)
    txt = ev("[...document.querySelectorAll('#panel h3, #panel .sentence')].map(e => e.textContent.replace(/\\s+/g, ' ').trim())")
    check('panel reads as written', txt[0] == 'Shelf' and txt[2:] == ['Give each subfolder its own shelf', 'Put a ribbon on the book I open most', 'Let the last book lean']
          and txt[1].startswith('Show') and txt[1].endswith('on the shelf.'), txt)
    check('title is Fraunces', 'Fraunces' in ev("getComputedStyle(document.querySelector('#panel h3')).fontFamily"))
    check('each sentence sits on one line', ev("[...document.querySelectorAll('#panel .sentence')].every(l => l.getBoundingClientRect().height < 2.6 * parseFloat(getComputedStyle(l).fontSize))"))
    sw = ev("[...document.querySelectorAll('#panel input')].map(i => i.type + ':' + i.getAttribute('role') + ':' + i.checked + ':' + (i.closest('label.sentence') ? 'label' : '-'))")
    check('three real switches inside their sentence labels, on by default', sw == ['checkbox:switch:true:label'] * 3, sw)
    before = ev('T.names()')
    for k in ('subShelves', 'ribbon', 'lean'):
        x, y = ev(f"T.center(document.querySelector('#panel input[data-key={k}]').previousElementSibling)")
        page.mouse.click(x, y); sleep(400)
        st = ev(f"chrome.storage.sync.get('settings').then(r => ({{ stored: r.settings && r.settings['{k}'], box: document.querySelector('#panel input[data-key={k}]').checked }}))")
        check(f'clicking the words turns {k} off and it persists to storage.sync', st['stored'] is False and st['box'] is False, st)
        if k == 'subShelves':
            flat = ev("({ h2: document.querySelectorAll('#shelves h2').length, n: T.books().length, names: T.names() })")
            check('subfolder shelves off: no labels, same books in folder order', flat['h2'] == 0 and flat['names'] == before, flat)
        if k == 'ribbon':
            check('ribbon off hides it', ev("document.querySelectorAll('.ribbon').length") == 0)
        page.mouse.click(x, y); sleep(400)
        check(f'{k} back on', ev(f"chrome.storage.sync.get('settings').then(r => r.settings['{k}'])") is True)
    check('subfolder shelves on again', ev("document.querySelectorAll('#shelves h2').length") == 1)
    check('ribbon back after turning it on', ev("document.querySelectorAll('.ribbon').length") == 1)
    page.select_option('#s-folder', 'Bookmarks bar / Later'); sleep(600)
    check('changing the folder re-renders the shelf', ev('T.names()') == ['Are.na', 'recent.design'])
    stored = ev("chrome.storage.sync.get('settings').then(r => r.settings.folder)")
    check('folder persists by path', stored == 'Bookmarks bar / Later', stored)
    page.select_option('#s-folder', 'Bookmarks bar'); sleep(600)
    page.focus('#s-folder')
    order = []
    for _ in range(3):
        key('Tab')
        order.append(ev("document.activeElement.dataset.key || document.activeElement.id"))
    check('Tab walks the three switches after the select', order == ['subShelves', 'ribbon', 'lean'], order)
    key('Space')
    check('Space toggles the focused switch', ev("!document.activeElement.checked"))
    key('Space')
    key('Escape')
    esc = ev("({ open: !document.querySelector('#panel').hidden, focus: document.activeElement.id })")
    check('Esc closes settings and focus returns to the gear', not esc['open'] and esc['focus'] == 'gear', esc)

    print('\n# 8 edit mode')
    ev("document.querySelector('#edit').click()"); sleep(400)
    ev("""() => { const src = T.book('Claude'), dst = T.book('Calendar'), d = new DataTransfer();
      const r = dst.getBoundingClientRect(), x = r.left + 4, y = r.top + r.height / 2;
      src.dispatchEvent(new DragEvent('dragstart', { bubbles: true, cancelable: true, dataTransfer: d }));
      T.fire('dragover', x, y, d); T.fire('drop', x, y, d);
      document.dispatchEvent(new DragEvent('dragend', { bubbles: true, dataTransfer: d })); }""")
    sleep(800)
    order = [k['title'] for k in ev('T.kids()') if k['url']]
    check('dragging a book moves the real bookmark', order.index('Claude') + 1 == order.index('Calendar'), order[:4])
    check('the shelf follows', ev('T.names()')[:2] == ['Claude', 'Calendar'])
    ev("T.book('Docs').click()"); sleep(400)
    check('book panel has an image well', ev("T.vis(document.querySelector('#panel .well'))"))
    lay = ev("""(() => { const p = document.querySelector('#panel'), r = p.getBoundingClientRect(), n = document.querySelector('#p-name').getBoundingClientRect();
      const done = p.querySelector('.actions .primary').getBoundingClientRect(), rm = p.querySelector('.actions .danger').getBoundingClientRect();
      return { notBook: !p.matches('.book'), fullInput: n.width > r.width * 0.8, apart: rm.right <= done.left, left: getComputedStyle(p.querySelector('.lb')).textAlign } })()""")
    check('book panel lays out as a form (inputs full width, Remove and Done apart)', lay['notBook'] and lay['fullInput'] and lay['apart'], lay)
    ev('T.paste()'); sleep(800)
    docs = ev("""async () => { const k = 'i:https://docs.google.com/document/u/0/', v = (await chrome.storage.local.get(k))[k] || '';
      return { stored: v.slice(0, 22), same: document.querySelector('#panel .well img').src === v && T.book('Docs').querySelector('img').src === v } }""")
    check('book panel well takes a pasted image', docs['stored'] == 'data:image/png;base64,' and docs['same'], docs)
    shot('1440x900-6-edit-panel.png')
    key('Escape'); key('Escape')
    check('Esc leaves edit mode', not ev("document.body.classList.contains('editing')"))

    print('\n# 9 contrast')
    for fg, bg, a, b in theme_pairs():
        r = ratio(a, b)
        check(f'{fg} on {bg} is at least 5:1', r >= 5, f'{r:.2f}')

    print()
    check('no console errors or exceptions across the run', not errors, json.dumps(errors)[:1500] if errors else 'none')
    print('\nscreenshots:')
    for p in sorted(glob.glob(os.path.join(SHOTS, '*.png'))): print('  ' + p)


def main():
    shutil.rmtree(SHOTS, ignore_errors=True)
    os.makedirs(SHOTS)
    seed()
    exe = chromium()
    print('browser', exe)
    proc = subprocess.Popen([exe, '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={PROF}',
                             f'--load-extension={ROOT}', f'--disable-extensions-except={ROOT}', '--disable-sync',
                             '--no-first-run', '--no-default-browser-check', '--window-size=1440,900', '--hide-scrollbars', 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version'); break
            except OSError:
                time.sleep(.5)
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(f'http://127.0.0.1:{PORT}')
            ctx = browser.contexts[0]

            # a few real visits so the ribbon and the history title have something to read
            hp = ctx.new_page()
            for _ in range(4):
                try:
                    hp.goto('https://piazza.com/', wait_until='domcontentloaded', timeout=15000)
                except Exception as e:
                    print('piazza visit failed, the ribbon and history checks will say so:', str(e).splitlines()[0])
                hp.wait_for_timeout(1500)
            hp.close()

            page = ctx.new_page()
            errors = []
            page.on('console', lambda m: m.type in ('error', 'warning') and errors.append(f'{m.type}: {m.text} @ {m.location}'))
            page.on('pageerror', lambda e: errors.append(f'exception: {e}'))
            page.set_viewport_size({'width': 1440, 'height': 900})
            cdp = ctx.new_cdp_session(page)
            cdp.send('Emulation.setFocusEmulationEnabled', {'enabled': True})
            page.goto(f'chrome-extension://{EXT_ID}/newtab.html')
            page.bring_to_front()
            page.wait_for_timeout(2500)
            run(page, cdp, errors)
    finally:
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed" + (f"; failed: {failed}" if failed else ''))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
