"""Quick screenshots of the shelf at 1440 and 900, plus settings, edit panel and add card with `states`.
Same profile setup as cdp_test.py.
    C:/dev/.venvs/shelf-newtab/Scripts/python tests/looks.py [out_dir] [demo] [states] [hover] [fresh] [flat] [3d] [nograin] [paper=..] [accent=..]
"""
import os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from cdp_test import ROOT, PROF, EXT_ID, PORT, HELPERS, seed, chromium

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'tests', 'shots', 'looks')
LOOKS = ['shelf']
os.makedirs(OUT, exist_ok=True)
DEMO = [('recent.design', 'https://recent.design/'), ('Are.na', 'https://www.are.na/'), ('Figma', 'https://www.figma.com/'),
        ('Pinterest', 'https://www.pinterest.com/'), ('Spotify', 'https://open.spotify.com/'), ('Letterboxd', 'https://letterboxd.com/'),
        ('Substack', 'https://substack.com/'), ('Wikipedia', 'https://www.wikipedia.org/'), ('YouTube', 'https://www.youtube.com/'),
        ('Dribbble', 'https://dribbble.com/'), ('Claude', 'https://claude.ai/'), ('Piazza', 'https://piazza.com/')]

def main():
    seed()
    if 'demo' in sys.argv:  # a design shelf like the sketch, with every site visited so chrome has its icon
        bm = os.path.join(PROF, 'Default', 'Bookmarks'); data = json.load(open(bm))
        shelf = data['roots']['other']['children'][0]
        shelf['children'] = [{'type': 'url', 'name': t, 'url': u, 'id': str(500 + i), 'guid': f'00000000-0000-4000-8000-{i:012d}', 'date_added': '13370000000000000'}
                             for i, (t, u) in enumerate(DEMO)]
        json.dump(data, open(bm, 'w'))
    if 'fresh' in sys.argv:  # no Shelf folder yet, like a first install
        bm = os.path.join(PROF, 'Default', 'Bookmarks'); data = json.load(open(bm))
        data['roots']['other']['children'] = []; json.dump(data, open(bm, 'w'))
    proc = subprocess.Popen([chromium(), '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={PROF}',
                             f'--load-extension={ROOT}', f'--disable-extensions-except={ROOT}', '--disable-sync',
                             '--no-first-run', '--no-default-browser-check', '--window-size=1440,900', '--hide-scrollbars', 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    errors = []
    try:
        for _ in range(60):
            try: urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version'); break
            except OSError: time.sleep(.5)
        with sync_playwright() as pw:
            ctx = pw.chromium.connect_over_cdp(f'http://127.0.0.1:{PORT}').contexts[0]
            hp = ctx.new_page()
            for u in ([u for _, u in DEMO] if 'demo' in sys.argv else []) + ['https://piazza.com/'] * 3:
                try: hp.goto(u, wait_until='load', timeout=20000)
                except Exception: pass
                hp.wait_for_timeout(1500)
            hp.close()
            page = ctx.new_page()
            page.on('console', lambda m: m.type in ('error', 'warning') and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(f'chrome-extension://{EXT_ID}/newtab.html')
            page.wait_for_timeout(2000)
            page.evaluate(HELPERS)
            page.evaluate("""chrome.storage.sync.set({'b:https://calendar.google.com/calendar/u/0/r': {s: 4},
              'b:https://www.notion.so/': {s: 3}, 'b:https://canvas.ubc.ca/': {s: 4}, 'b:https://claude.ai/new': {s: 3},
              'b:https://www.wikipedia.org/': {s: 4}, 'b:https://open.spotify.com/': {s: 3}, 'b:https://recent.design/': {s: 3}}).then(() => 1)""")
            off = {k: False for k, flag in (('subShelves', 'flat'), ('grain', 'nograin')) if flag in sys.argv}
            if '3d' in sys.argv: off['look'] = '3d'
            off.update({a.split('=')[0]: a.split('=', 1)[1] for a in sys.argv if a.startswith(('paper=', 'accent='))})  # e.g. paper=white
            if off:  # parts switched off in settings
                page.evaluate("off => chrome.storage.sync.get('settings').then(r => chrome.storage.sync.set({ settings: { ...r.settings, ...off } })).then(() => 1)", off)
            page.reload(); page.wait_for_timeout(2500); page.evaluate(HELPERS)
            page.wait_for_timeout(1000)
            if 'fresh' in sys.argv:
                made = page.evaluate("chrome.bookmarks.search({ title: 'Shelf' }).then(r => r.filter(f => !f.url).length)")
                print('Shelf folders after first load:', made, '| books on shelf:', page.evaluate('T.books().length'))
            for look in LOOKS:
                for w, h in [(1440, 900), (900, 800)]:
                    page.set_viewport_size({'width': w, 'height': h})
                    page.evaluate("dispatchEvent(new Event('resize'))")
                    page.wait_for_timeout(700)
                    over = page.evaluate('document.documentElement.scrollWidth > innerWidth')
                    p = os.path.join(OUT, f'{look}-{w}.png'); page.screenshot(path=p); print(p, 'OVERFLOW' if over else '')
                    print('  gaps:', page.evaluate("""(() => { const t = Math.min(...[...document.querySelectorAll('.book')].map(b => b.getBoundingClientRect().top));
                      const pl = [...document.querySelectorAll('.plank')].pop().getBoundingClientRect().bottom;
                      return { above: Math.round(t), below: Math.round(innerHeight - pl), scrolls: document.documentElement.scrollHeight > innerHeight } })()"""))
                if 'hover' in sys.argv:
                    # hover two books with the real mouse and shoot both
                    page.set_viewport_size({'width': 1440, 'height': 900}); page.wait_for_timeout(300)
                    for k, name in ((2, 'hover'), (7, 'hover-2')):
                        r = page.evaluate(f"(() => {{ const r = T.books()[{k}].getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] }})()")
                        page.mouse.move(*r); page.wait_for_timeout(700)
                        page.screenshot(path=os.path.join(OUT, f'{name}.png'))
                        # nudge inside the spine's footprint: the book must stay pulled out, no flicker
                        page.mouse.move(r[0] + 6, r[1] + 40); page.wait_for_timeout(300)
                        print(name, 'still out after a nudge:', page.evaluate(f"getComputedStyle(T.books()[{k}].querySelector('.box')).transform !== 'none'"),
                              '| under the mouse:', page.evaluate(f"(e => e ? e.tagName + '.' + e.className + ' in ' + (e.closest('.book')?.querySelector('.nm')?.textContent || '-') : 'null')(document.elementFromPoint({r[0] + 6}, {r[1] + 40}))"),
                              '| probe:', page.evaluate(f"""(() => {{ const b = T.books()[{k}].getBoundingClientRect(); const out = [];
                                for (let y = b.top + 5; y < b.bottom; y += 25) {{ const e = document.elementFromPoint({r[0] + 6}, y); out.push(Math.round(y - b.top) + ':' + (e ? e.className || e.tagName : 'null')); }} return out.join(' ') }})()"""),
                              '| hovered book:', page.evaluate(f"T.books()[{k}].querySelector('.nm').textContent"))
                    page.mouse.move(5, 890); page.wait_for_timeout(400)
                if 'states' in sys.argv:
                    page.set_viewport_size({'width': 1440, 'height': 900}); page.wait_for_timeout(400)
                    page.evaluate("document.querySelector('#gear').click()"); page.wait_for_timeout(400)
                    page.screenshot(path=os.path.join(OUT, 'settings.png')); page.keyboard.press('Escape')
                    page.evaluate("document.querySelector('#edit').click()"); page.wait_for_timeout(300)
                    page.evaluate("T.books()[2].click()"); page.wait_for_timeout(500)
                    page.screenshot(path=os.path.join(OUT, 'edit.png')); page.keyboard.press('Escape'); page.keyboard.press('Escape')
                    page.wait_for_timeout(300)
                    page.evaluate("d => T.dropLink(T.names()[1], T.names()[2], d)", {'text/uri-list': 'https://www.figma.com/community', 'text/html': '<a href="https://www.figma.com/community">Figma Community</a>'})
                    page.wait_for_timeout(900)
                    page.screenshot(path=os.path.join(OUT, 'card.png'))
                    page.evaluate("document.querySelector('#card .undo').click()"); page.wait_for_timeout(500)
    finally:
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)
    print('errors:', errors or 'none')

main()
