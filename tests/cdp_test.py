"""Shelf tests. Playwright's Chromium, headless, with the unpacked extension and a seeded Bookmarks file.

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

# a tiny local image host: one image any page may read, one it may only show, so both icon paths run offline
IMG_PORT = 9352
IMG = f'http://127.0.0.1:{IMG_PORT}'
def serve_images():
    import base64, http.server, threading
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAGElEQVR4nGP4z8BAFmIY1TiqcVTjsNIIAA6x/AFjW9XCAAAAAElFTkSuQmCC')
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ('/cors.png', '/plain.png'): self.send_response(404); self.end_headers(); return
            self.send_response(200); self.send_header('Content-Type', 'image/png')
            if self.path == '/cors.png': self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers(); self.wfile.write(png)
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', IMG_PORT), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
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
    # shelf's books live in its own folder; the bar gets one link that must never show up on the shelf
    shelf = [url(*l) for l in LINKS] + [folder('Later', [url(*l) for l in LATER])]
    bar = [url('Bar only', 'https://example.com/bar-only')]
    data = {'roots': {'bookmark_bar': folder('Bookmarks bar', bar, '1'), 'other': folder('Other bookmarks', [folder('Shelf', shelf, '9')], '2'),
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
  async kids(id = '9') { return (await chrome.bookmarks.getChildren(id)).map(c => ({ id: c.id, title: c.title, url: c.url || null, index: c.index })); },
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
    check('fonts load', len(fonts) == 4 and all(f.endswith(':loaded') for f in fonts), ', '.join(fonts))
    names = ev('T.names()')
    check('seeded books render in order', [n for n in names if n in SEEDED] == SEEDED, ', '.join(names))
    groups = ev("[...document.querySelectorAll('.group')].map(g => (g.querySelector('h2')?.textContent || '-') + ':' + g.querySelectorAll('.book').length)")
    check('Later gets its own labelled shelf', 'Later:2' in groups, ', '.join(groups))
    ribbon = ev("[...document.querySelectorAll('.book')].filter(b => b.querySelector('.ribbon')).map(b => b.querySelector('.nm').textContent)")
    check('ribbon on the most opened book', ribbon == ['Piazza'], ribbon)
    check('bookmarks bar stays off the shelf', 'Bar only' not in names)
    check('2D is the default look', ev("chrome.storage.sync.get('settings').then(r => r.settings.look)") == '2d' and ev("document.documentElement.classList.contains('flat')"))
    # the depth checks are about the 3D shelf, 7c switches back to 2D
    ev("chrome.storage.sync.get('settings').then(r => chrome.storage.sync.set({ settings: { ...r.settings, look: '3d' } })).then(() => 1)"); sleep(600)

    print('\n# 1b depth')
    lifted = lambda: ev("T.books().filter(b => getComputedStyle(b.querySelector('.box')).transform !== 'none').map(b => b.querySelector('.nm').textContent)")
    tilt = lambda: ev("getComputedStyle(document.querySelector('#shelves')).transform")
    page.mouse.move(5, 5); sleep(700); t1 = tilt()
    # a real 3D turn blurred every title, so the depth is drawn with flat shapes and nothing on the shelf is 3D
    three_d = ev("[...document.querySelectorAll('#shelves, #shelves *')].filter(e => getComputedStyle(e).transform.startsWith('matrix3d')).length")
    check('nothing on the shelf uses a 3D transform (titles stay sharp)', t1 == 'none' and three_d == 0, f'{t1[:30]} / {three_d}')
    check('every book shows its page edges on top', ev("T.books().every(b => T.vis(b.querySelector('.tp')))"))
    x, y = ev("T.center(T.book('Calendar'))"); page.mouse.move(x, y); sleep(700)
    check('hovering lifts just that book', lifted() == ['Calendar'], lifted())
    check('the shelf stays put when the mouse moves', tilt() == t1)
    check('a small move inside the spine keeps it lifted', (page.mouse.move(x + 4, y + 30), sleep(300), lifted())[2] == ['Calendar'])
    page.mouse.move(5, 5); sleep(500)
    check('moving away sets it back down', lifted() == [])
    # every point down the middle of every spine has to belong to that book. a tie with the row left dead spots
    holes = ev("""T.books().flatMap(b => { const r = b.getBoundingClientRect(), x = r.left + r.width / 2, out = [];
      for (let y = r.top + 8; y < r.bottom - 8; y += 12) if (document.elementFromPoint(x, y)?.closest('.book') !== b) out.push(b.querySelector('.nm').textContent + '@' + Math.round(y - r.top));
      return out; })""")
    check('no dead spots on any spine', not holes, holes[:8])
    where = ev("chrome.storage.sync.get('settings').then(r => r.settings.folder)")
    check("shelf reads its own folder by default", where == 'Other bookmarks / Shelf', where)
    page_bits = ev("['#index', '#date', '.plate', 'h1'].filter(q => document.querySelector(q))")
    check('just the shelf: no date, contents or painting on the page', page_bits == [], page_bits)
    gap = ev("""(() => { const tops = [...document.querySelectorAll('.book')].map(b => b.getBoundingClientRect().top);
      const planks = [...document.querySelectorAll('.plank')]; const end = planks[planks.length - 1].getBoundingClientRect().bottom;
      return { above: Math.round(Math.min(...tops)), below: Math.round(innerHeight - end), scrolls: document.documentElement.scrollHeight > innerHeight } })()""")
    check('the shelves sit in the middle of the window, no scrollbar', abs(gap['above'] - gap['below']) < 0.15 * ev('innerHeight') and not gap['scrolls'], gap)

    sleep(800)
    cloth = ev("""(async () => { const k = 'c:https://piazza.com/', c = (await chrome.storage.local.get(k))[k];
      return { c, bg: T.book('Piazza').style.getPropertyValue('--bg') } })()""")
    check('a visited site dyes its cover from its icon', cloth['c'] and cloth['bg'] == cloth['c']['bg'], cloth)
    if cloth['c']: check('icon-dyed cover still clears 5:1', ratio(cloth['c']['fg'], cloth['c']['bg']) >= 5, f"{ratio(cloth['c']['fg'], cloth['c']['bg']):.2f}")

    # mixed sizes so the shots look like a used shelf
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
    check('card shows the url, not editable', st['url'] == 'figma.com/community')

    print('\n# 3 paste an image')
    ev('T.paste()'); sleep(800)
    icon = ev("chrome.storage.local.get('i:https://www.figma.com/community').then(r => r['i:https://www.figma.com/community'] || '')")
    check('i:<url> is a png data url', icon.startswith('data:image/png;base64,'), icon[:40])
    check('icon is at most about 12 KB', 0 < len(icon) <= 12 * 1024, f'{len(icon)} bytes')
    shows = ev("({ book: T.book('Figma Community').querySelector('img').src, well: document.querySelector('#card .sq img').src })")
    check('book shows the pasted image', shows['book'] == icon)
    check('icon square shows the pasted image', shows['well'] == icon)
    check('preview book shows it too', ev("document.querySelector('#card .mini img').src") == icon)

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

    print('\n# 6 icon from a file or an image address')
    ev("document.querySelector('#add').click()"); sleep(400)
    ev('''async () => { const d = new DataTransfer(); d.items.add(await T.png()); const c = document.querySelector('#card');
      const [x, y] = T.center(c); T.fire('dragover', x, y, d, c); T.fire('drop', x, y, d, c); }''')
    sleep(600)
    check('dropping a file on the card sets the icon', ev("document.querySelector('#card .sq img').src.startsWith('data:image/png')"))
    def address(u):
        ev(f'''(() => {{ const i = document.querySelector('#card .iconaddr'); i.value = '{u}'; i.dispatchEvent(new Event('input', {{ bubbles: true }})); }})()''')
        sleep(1500)
        return ev("({ status: document.querySelector('#card .status').textContent, src: document.querySelector('#card .sq img').src, mini: document.querySelector('#card .mini img').src })")
    got = address(f'{IMG}/cors.png')
    check('an image address that allows it gets copied', got['status'] == 'Copied.' and got['src'].startswith('data:image/png') and got['mini'] == got['src'], got)
    got = address(f'{IMG}/plain.png')
    check("one that doesn't is linked, with Keep a copy", got['status'].startswith('Linked, not copied.') and got['src'] == f'{IMG}/plain.png'
          and ev("!!document.querySelector('#card .status .keep')"), got)
    check('linking asks for no permission', not ev(f"chrome.permissions.contains({{ origins: ['{IMG}/*'] }})"))
    shot('1440x900-5-image-address.png')
    got = address(f'{IMG}/nope.png')
    check('a dead address says so', "didn't open as an image" in got['status'], got)
    got = address(f'{IMG}/plain.png'.replace('http://', ''))
    check('an address without https:// still works', got['src'] == f'{IMG}/plain.png' or got['src'].startswith('data:'), got)
    ev("document.querySelector('#card .address').value = 'linked.example'; document.querySelector('#card .address').dispatchEvent(new Event('input', { bubbles: true }))")
    sleep(600)
    ev("document.querySelector('#card .primary').click()"); sleep(1000)
    linked = ev("chrome.storage.local.get('i:https://linked.example/').then(r => r['i:https://linked.example/'] || '')")
    check('Done keeps a linked icon as its address', linked == f'{IMG}/plain.png', linked)
    check('the new book shows the linked icon', ev(f"T.books().some(b => b.querySelector('img').src === '{IMG}/plain.png')"))
    check('a dropped web image does not add a book', 'Example' not in ev('T.names()') and not ev("!!document.querySelector('.book.ghost')"))

    print('\n# 7 settings')
    ev("document.querySelector('#gear').click()"); sleep(400)
    txt = ev("[...document.querySelectorAll('#panel h3, #panel .sentence')].map(e => e.textContent.replace(/\\s+/g, ' ').trim())")
    check('panel reads as written', txt[0] == 'Shelf' and txt[1].startswith('Show') and txt[1].endswith('on the shelf.')
          and txt[2] == 'Draw the books in3D2D' and txt[3] == 'The paper is' and txt[4] == 'The accent is'
          and txt[5:] == ['Give each subfolder its own shelf', 'Put a ribbon on the book I open most', 'Let the last book lean', 'Give the paper a fine grain'], txt)
    check('title is Archivo, like the top bar', 'Archivo' in ev("getComputedStyle(document.querySelector('#panel h3')).fontFamily"))
    check('each sentence sits on one line', ev("[...document.querySelectorAll('#panel .sentence')].every(l => l.getBoundingClientRect().height < 2.6 * parseFloat(getComputedStyle(l).fontSize))"))
    sw = ev("[...document.querySelectorAll('#panel input[role=switch]')].map(i => i.type + ':' + i.checked + ':' + (i.closest('label.sentence') ? 'label' : '-'))")
    check('four real switches inside their sentence labels, on by default', sw == ['checkbox:true:label'] * 4, sw)
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
    page.select_option('#s-folder', 'Other bookmarks / Shelf / Later'); sleep(600)
    check('changing the folder re-renders the shelf', ev('T.names()') == ['Are.na', 'recent.design'])
    stored = ev("chrome.storage.sync.get('settings').then(r => r.settings.folder)")
    check('folder persists by path', stored == 'Other bookmarks / Shelf / Later', stored)
    page.select_option('#s-folder', 'Other bookmarks / Shelf'); sleep(600)
    page.focus('#s-folder')
    order = []
    for _ in range(20):  # the 3D/2D pair (one stop), 9 papers, the picker, 5 accents, 4 switches
        key('Tab')
        order.append(ev("document.activeElement.dataset.key || document.activeElement.dataset.v || (document.activeElement.type === 'radio' ? document.activeElement.value : document.activeElement.type) || document.activeElement.id"))
    check('Tab walks the look, the colours, then the switches', order[0] == '3d' and order[1:10] == ['chalk', 'white', 'putty', 'linen', 'stone', 'sage', 'blush', 'sky', 'night'] and order[-4:] == ['subShelves', 'ribbon', 'lean', 'grain'], order)
    key('Space')
    check('Space toggles the focused switch', ev("!document.activeElement.checked"))
    key('Space')

    print('\n# 7b colours')
    rgb = lambda v: ev(f"getComputedStyle(document.documentElement).getPropertyValue('{v}').trim()")
    ev("document.querySelector('#panel .dot[data-v=night]').click()"); sleep(500)
    st = ev("chrome.storage.sync.get('settings').then(r => r.settings.paper)")
    check('picking Night paper saves it and repaints the page', st == 'night' and rgb('--ground') == '#1B2027'
          and ev("getComputedStyle(document.body).backgroundColor") == 'rgb(27, 32, 39)', (st, rgb('--ground')))
    check('dark paper flips the text light', rgb('--text') == '#EDE8DC' and rgb('color-scheme') == 'dark')
    shot('1440x900-7-night.png')
    page.reload(); sleep(150)
    early = ev("document.documentElement.style.getPropertyValue('--ground')")
    check('a new tab opens straight in the saved paper (no flash of the default)', early == '#1B2027', early)
    held = ev("[document.documentElement.className, getComputedStyle(document.querySelector('.top')).opacity]")
    check('the page waits hidden until it can open in one go', 'wait' in held[0] or 'intro' in held[0], held)
    sleep(1900); ev(HELPERS)
    after = ev("""[document.documentElement.classList.contains('wait') || document.documentElement.classList.contains('intro'),
      [...document.querySelectorAll('.box, .plank, .top')].every(e => getComputedStyle(e).opacity === '1')]""")
    check('after the opening everything is shown and settled', after == [False, True], after)
    ev("dispatchEvent(new Event('resize'))"); sleep(200)
    check('a re-render later does not replay the opening', ev('document.getAnimations().length') == 0, ev('document.getAnimations().length'))
    ev("document.querySelector('#gear').click()"); sleep(400)
    ev("""(() => { const i = document.querySelector('#panel .dot.own input'); i.value = '#a4c9e8'; i.dispatchEvent(new Event('input', { bubbles: true })); })()""")
    sleep(700)
    st = ev("chrome.storage.sync.get('settings').then(r => r.settings.paper)")
    check('any colour from the picker becomes the paper', st == '#a4c9e8' and rgb('--ground') == '#A4C9E8', (st, rgb('--ground')))
    check('the picker dot is the one marked', ev("document.querySelector('#panel .dot.own').classList.contains('on') && document.querySelectorAll('#panel .dots .dot.on').length === 2"))
    ev("document.querySelector('#panel .dot[data-v=cobalt]').click()"); sleep(400)
    silk = ev("getComputedStyle(document.querySelector('.ribbon')).getPropertyValue('--silk')")
    check('picking an accent re-dyes the ribbon', rgb('--accent') == '#2F4BE0' and '2F4BE0' in silk.upper(), silk)
    # every preset, and a spread of odd custom papers, must keep all text at 5:1
    bad = ev("""import('./js/palette.js').then(m => {
      const papers = [...m.PAPERS.map(p => p[0]), '#ffffff', '#000000', '#ff0000', '#ffff00', '#00ff88', '#7a7a7a', '#5b3c88', '#c08040', '#e0e0ff', '#202020'];
      const out = [];
      for (const paper of papers) for (const [accent] of m.ACCENTS) {
        const v = m.derive({ paper, accent });
        for (const [fg, bg] of [['--text', '--ground'], ['--text', '--card'], ['--dim', '--ground'], ['--dim', '--card'], ['--dim', '--field'], ['--accent-text', '--ground'], ['--accent-text', '--card']]) {
          const r = m.ratio(v[fg], v[bg]); if (r < 5) out.push(`${paper}/${accent} ${fg} on ${bg} ${r.toFixed(2)}`);
        }
      }
      return out; })""")
    check('every paper and accent keeps text at 5:1, custom papers too', not bad, bad[:6])
    ev("document.querySelector('#panel input[data-key=grain]').click()"); sleep(300)
    check('grain switch turns the grain off', rgb('--grain') == '0')
    ev("document.querySelector('#panel input[data-key=grain]').click()"); sleep(300)
    ev("document.querySelector('#panel .dot[data-v=putty]').click()"); sleep(200)
    ev("document.querySelector('#panel .dot[data-v=magenta]').click()"); sleep(400)
    check('back to putty and magenta', rgb('--ground') == '#DDDDD1' and rgb('--accent') == '#E2187F')
    ev("document.querySelector('#panel input[data-key=lean]').focus()")
    key('Escape')
    esc = ev("({ open: !document.querySelector('#panel').hidden, focus: document.activeElement.id })")
    check('Esc closes settings and focus returns to the gear', not esc['open'] and esc['focus'] == 'gear', esc)

    print('\n# 7c 2D')
    ev("document.querySelector('#gear').click()"); sleep(400)
    x, y = ev("T.center(document.querySelector('#panel .seg input[value=\"2d\"]').nextElementSibling)")
    page.mouse.click(x, y); sleep(500)
    flat = ev("""chrome.storage.sync.get('settings').then(r => ({ stored: r.settings.look, cls: document.documentElement.classList.contains('flat'),
      cached: localStorage.getItem('shelf:look'), on: document.querySelector('#panel .seg input:checked').value }))""")
    check('clicking 2D flattens the shelf and persists to storage.sync', flat == {'stored': '2d', 'cls': True, 'cached': '2d', 'on': '2d'}, flat)
    drawn = ev("""(() => { const b = T.book('Docs'), box = b.querySelector('.box'), cs = getComputedStyle(box);
      return { depth: T.vis(b.querySelector('.tp')) || T.vis(b.querySelector('.bk')), bands: T.vis(b.querySelector('.band')), site: T.vis(b.querySelector('.au')),
        round: parseFloat(cs.borderTopLeftRadius) === parseFloat(cs.borderBottomLeftRadius) && parseFloat(cs.borderBottomLeftRadius) > 8,
        tile: getComputedStyle(b.querySelector('.chip')).backgroundColor, title: getComputedStyle(b.querySelector('.nm')).fontFamily } })()""")
    check('2D books are single rounded blocks: no page edges, back, bands or site line', not drawn['depth'] and not drawn['bands'] and not drawn['site'] and drawn['round'], drawn)
    check('2D icons sit straight on the book (no tile), titles in the sans', drawn['tile'] == 'rgba(0, 0, 0, 0)' and drawn['title'].startswith('Archivo'), drawn)
    check('still no 3D transforms in 2D', ev("[...document.querySelectorAll('#shelves, #shelves *')].filter(e => getComputedStyle(e).transform.startsWith('matrix3d')).length") == 0)
    key('Escape')
    x, y = ev("T.center(T.book('Calendar'))"); page.mouse.move(x, y); sleep(500)
    check('hover still lifts a book in 2D', lifted() == ['Calendar'], lifted())
    page.mouse.move(5, 5); sleep(400)
    check('the ribbon stays on in 2D', ev("document.querySelectorAll('.ribbon').length") == 1)
    for w, hgt in SIZES:
        size(w, hgt)
        check(f'{w}x{hgt} 2D no horizontal overflow', not ev('document.documentElement.scrollWidth > innerWidth'))
        shot(f'{w}x{hgt}-8-2d.png')
    size(1440, 900)
    page.reload(); sleep(150)
    check('a new tab opens straight into 2D (no flash of the 3D shelf)', ev("document.documentElement.classList.contains('flat')"))
    sleep(1900); ev(HELPERS)
    ev("document.querySelector('#gear').click()"); sleep(400)
    ev("document.querySelector('#panel .seg input:checked').focus()")
    key('ArrowLeft'); sleep(300)
    back = ev("chrome.storage.sync.get('settings').then(r => ({ stored: r.settings.look, cls: document.documentElement.classList.contains('flat'), tp: T.vis(T.book('Docs').querySelector('.tp')) }))")
    check('arrow keys flip it back to 3D', back == {'stored': '3d', 'cls': False, 'tp': True}, back)
    key('Escape')

    print('\n# 8 edit mode')
    ev("document.querySelector('#edit').click()"); sleep(400)
    # a drag that starts on text (a selected title) has a text node as its target. it used to throw
    before_err = len(errors)
    marked = ev("""() => { const txt = T.book('Docs').querySelector('.nm').firstChild, d = new DataTransfer();
      txt.dispatchEvent(new DragEvent('dragstart', { bubbles: true, cancelable: true, dataTransfer: d }));
      const on = T.book('Docs').classList.contains('dragging');
      document.dispatchEvent(new DragEvent('dragend', { bubbles: true, dataTransfer: d }));
      return { text: txt.nodeType === 3, on }; }""")
    sleep(300)
    check('a drag starting on text does not throw', marked['text'] and len(errors) == before_err, errors[before_err:])
    check('and it still drags that book', marked['on'], marked)
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
    check('book panel has the icon field', ev("T.vis(document.querySelector('#panel .sq')) && T.vis(document.querySelector('#panel .iconaddr'))"))
    lay = ev("""(() => { const p = document.querySelector('#panel'), r = p.getBoundingClientRect(), n = document.querySelector('#p-name').getBoundingClientRect();
      const done = p.querySelector('.actions .primary').getBoundingClientRect(), rm = p.querySelector('.actions .danger').getBoundingClientRect();
      return { notBook: !p.matches('.book'), fullInput: n.width > r.width * 0.8, apart: rm.right <= done.left, left: getComputedStyle(p.querySelector('.lb')).textAlign } })()""")
    check('book panel lays out as a form (inputs full width, Remove and Done apart)', lay['notBook'] and lay['fullInput'] and lay['apart'], lay)
    ev('T.paste()'); sleep(800)
    docs = ev("""async () => { const k = 'i:https://docs.google.com/document/u/0/', v = (await chrome.storage.local.get(k))[k] || '';
      return { stored: v.slice(0, 22), same: document.querySelector('#panel .sq img').src === v && T.book('Docs').querySelector('img').src === v } }""")
    check('book panel icon field takes a pasted image', docs['stored'] == 'data:image/png;base64,' and docs['same'], docs)
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
    serve_images()
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
            # the dead and no-copy test images log network errors on purpose; anything else still fails the run
            def on_console(m):
                if m.type in ('error', 'warning') and IMG not in m.text and IMG not in str(m.location.get('url', '')):
                    errors.append(f'{m.type}: {m.text} @ {m.location}')
            page.on('console', on_console)
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
