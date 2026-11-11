"""Store screenshots (1280x800), the 440x280 promo tile and the README crops, all from the demo shelf.
Same headless setup as tests/looks.py, so it needs the test venv with playwright:
    <venv python> tools/store_shots.py
"""
import json, os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests'))
from cdp_test import ROOT, PROF, EXT_ID, PORT, HELPERS, seed, chromium
# same demo shelf as tests/looks.py (that file runs on import, so it's copied here)
DEMO = [('recent.design', 'https://recent.design/'), ('Are.na', 'https://www.are.na/'), ('Figma', 'https://www.figma.com/'),
        ('Pinterest', 'https://www.pinterest.com/'), ('Spotify', 'https://open.spotify.com/'), ('Letterboxd', 'https://letterboxd.com/'),
        ('Substack', 'https://substack.com/'), ('Wikipedia', 'https://www.wikipedia.org/'), ('YouTube', 'https://www.youtube.com/'),
        ('Dribbble', 'https://dribbble.com/'), ('Claude', 'https://claude.ai/'), ('Piazza', 'https://piazza.com/')]

STORE = os.path.join(ROOT, 'store')
DOCS = os.path.join(ROOT, 'docs')
HEIGHTS = {'https://calendar.google.com/calendar/u/0/r': 4, 'https://www.notion.so/': 3, 'https://canvas.ubc.ca/': 4,
           'https://claude.ai/new': 3, 'https://www.wikipedia.org/': 4, 'https://open.spotify.com/': 3, 'https://recent.design/': 3}
FIGMA = {'text/uri-list': 'https://www.figma.com/community', 'text/html': '<a href="https://www.figma.com/community">Figma Community</a>'}


def box(page, sel, pad=0):
    # union of every match, padded, kept inside the viewport
    r = page.evaluate("""([sel, pad]) => { const rs = [...document.querySelectorAll(sel)].map(e => e.getBoundingClientRect()).filter(r => r.width);
      const x = Math.max(0, Math.min(...rs.map(r => r.left)) - pad), y = Math.max(0, Math.min(...rs.map(r => r.top)) - pad);
      return { x, y, width: Math.min(innerWidth, Math.max(...rs.map(r => r.right)) + pad) - x, height: Math.min(innerHeight, Math.max(...rs.map(r => r.bottom)) + pad) - y } }""", [sel, pad])
    return r


def main():
    seed()
    bm = os.path.join(PROF, 'Default', 'Bookmarks'); data = json.load(open(bm))
    data['roots']['other']['children'][0]['children'] = [
        {'type': 'url', 'name': t, 'url': u, 'id': str(500 + i), 'guid': f'00000000-0000-4000-8000-{i:012d}', 'date_added': '13370000000000000'}
        for i, (t, u) in enumerate(DEMO)]
    json.dump(data, open(bm, 'w'))
    proc = subprocess.Popen([chromium(), '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={PROF}',
                             f'--load-extension={ROOT}', f'--disable-extensions-except={ROOT}', '--disable-sync',
                             '--no-first-run', '--no-default-browser-check', '--window-size=1280,800', '--hide-scrollbars', 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    errors = []
    try:
        for _ in range(60):
            try: urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version'); break
            except OSError: time.sleep(.5)
        with sync_playwright() as pw:
            ctx = pw.chromium.connect_over_cdp(f'http://127.0.0.1:{PORT}').contexts[0]
            hp = ctx.new_page()
            # visit everything so chrome has the icons, and piazza three times so it gets the ribbon
            for u in [u for _, u in DEMO] + ['https://piazza.com/'] * 3:
                try: hp.goto(u, wait_until='load', timeout=20000)
                except Exception: pass
                hp.wait_for_timeout(1500)
            hp.close()
            page = ctx.new_page()
            page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))

            def load(w, h, look='2d'):
                page.set_viewport_size({'width': w, 'height': h})
                page.goto(f'chrome-extension://{EXT_ID}/newtab.html'); page.wait_for_timeout(1500)
                page.evaluate("([h, look]) => chrome.storage.sync.set(Object.fromEntries(Object.entries(h).map(([u, s]) => ['b:' + u, { s }])))"
                              ".then(() => chrome.storage.sync.get('settings')).then(r => chrome.storage.sync.set({ settings: { ...r.settings, look } })).then(() => 1)",
                              [HEIGHTS, look])
                page.reload(); page.wait_for_timeout(2500); page.evaluate(HELPERS); page.wait_for_timeout(500)

            def states(shoot):
                shoot('shelf')
                page.evaluate("d => T.dropLink(T.names()[1], T.names()[2], d)", FIGMA); page.wait_for_timeout(900)
                shoot('add')
                page.evaluate("document.querySelector('#card .undo').click()"); page.wait_for_timeout(600)
                page.evaluate("document.querySelector('#edit').click()"); page.wait_for_timeout(300)
                page.evaluate("T.books()[2].click()"); page.wait_for_timeout(500)
                shoot('edit')
                page.keyboard.press('Escape'); page.keyboard.press('Escape'); page.wait_for_timeout(400)
                page.evaluate("document.querySelector('#gear').click()"); page.wait_for_timeout(500)
                shoot('settings')
                page.keyboard.press('Escape'); page.wait_for_timeout(300)

            # store: full 1280x800 frames
            shots = os.path.join(STORE, 'screenshots')
            load(1280, 800)
            names = {'shelf': '1-shelf-2d', 'add': '2-add', 'edit': '3-edit', 'settings': '4-settings'}
            states(lambda n: page.screenshot(path=os.path.join(shots, names[n] + '.png')))
            # promo tile: the shelf alone, cropped to 440:280 and scaled down
            b = box(page, '.book, .plank', 40)
            cx, cy = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
            w = max(b['width'], b['height'] * 440 / 280); h = w * 280 / 440
            raw = os.path.join(STORE, 'promo-raw.png')
            page.screenshot(path=raw, clip={'x': cx - w / 2, 'y': cy - h / 2, 'width': w, 'height': h})
            subprocess.run(['sips', '-z', '280', '440', raw, '--out', os.path.join(STORE, 'promo-440x280.png')], capture_output=True)
            os.remove(raw)
            load(1280, 800, '3d')
            page.screenshot(path=os.path.join(shots, '5-shelf-3d.png'))
            page.wait_for_timeout(200)
            # readme crops at 1440x900
            load(1440, 900, '3d')
            page.screenshot(path=os.path.join(DOCS, 'shelf-3d.png'), clip=box(page, '.book, .plank', 60))
            load(1440, 900)
            crops = {'shelf': ('.book, .plank', 'shelf-2d'), 'add': ('.book, .plank, #card', 'add'),
                     'edit': ('.book, .plank, #panel', 'edit'), 'settings': ('#panel, .dock', 'settings')}
            states(lambda n: page.screenshot(path=os.path.join(DOCS, crops[n][1] + '.png'), clip=box(page, crops[n][0], 24)))
    finally:
        proc.kill() if os.name != 'nt' else subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)
    print('errors:', errors or 'none')


main()
