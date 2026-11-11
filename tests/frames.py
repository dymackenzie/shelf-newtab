"""Films a new tab opening, frame by frame, so flicker on load shows up as a strip of stills.
Warms the demo sites first (real icons, cloth cached), then screencasts a fresh new tab.
    C:/dev/.venvs/shelf-newtab/Scripts/python tests/frames.py [out_dir]
"""
import base64, io, json, os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp_test
from cdp_test import ROOT, EXT_ID, seed, chromium
PROF = cdp_test.PROF = cdp_test.PROF + '-frames'

# same shelf as looks.py demo (importing looks would run it)
DEMO = [('recent.design', 'https://recent.design/'), ('Are.na', 'https://www.are.na/'), ('Figma', 'https://www.figma.com/'),
        ('Pinterest', 'https://www.pinterest.com/'), ('Spotify', 'https://open.spotify.com/'), ('Letterboxd', 'https://letterboxd.com/'),
        ('Substack', 'https://substack.com/'), ('Wikipedia', 'https://www.wikipedia.org/'), ('YouTube', 'https://www.youtube.com/'),
        ('Dribbble', 'https://dribbble.com/'), ('Claude', 'https://claude.ai/'), ('Piazza', 'https://piazza.com/')]

SCRUB = [0, 120, 240, 360, 480, 600, 750, 900, 1100, 1400]
if os.environ.get('GIF'): SCRUB = list(range(0, 1450, 40))  # fine steps for a gif of the opening
PORT = 9347  # its own port, so it never grabs another run's browser
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'tests', 'shots', 'frames')


def main():
    os.makedirs(OUT, exist_ok=True)
    seed()
    bm = os.path.join(PROF, 'Default', 'Bookmarks'); data = json.load(open(bm))
    data['roots']['other']['children'][0]['children'] = [
        {'type': 'url', 'name': t, 'url': u, 'id': str(500 + i), 'guid': f'00000000-0000-4000-8000-{i:012d}', 'date_added': '13370000000000000'}
        for i, (t, u) in enumerate(DEMO)]
    json.dump(data, open(bm, 'w'))
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
            for u in [u for _, u in DEMO] + ['https://piazza.com/'] * 3:
                try: hp.goto(u, wait_until='domcontentloaded', timeout=20000)
                except Exception: pass
                hp.wait_for_timeout(1200)
            hp.close()
            # first open learns every cloth and the ribbon, like a real browser after a day
            warm = ctx.new_page(); warm.set_viewport_size({'width': 1440, 'height': 900})
            warm.goto(f'chrome-extension://{EXT_ID}/newtab.html'); warm.wait_for_timeout(4000); warm.close()

            page = ctx.new_page()
            page.on('console', lambda m: m.type in ('error', 'warning') and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.set_viewport_size({'width': 1440, 'height': 900})
            # land on the extension first: crossing from about:blank swaps renderers and ends the screencast
            page.goto(f'chrome-extension://{EXT_ID}/newtab.html'); page.wait_for_timeout(1500)
            cdp = ctx.new_cdp_session(page)
            frames = []
            def got(f):
                frames.append((f['metadata']['timestamp'], f['data']))
                try: cdp.send('Page.screencastAck', {'sessionId': f['sessionId']})
                except Exception: pass
            cdp.on('Page.screencastFrame', got)
            cdp.send('Page.startScreencast', {'format': 'jpeg', 'quality': 70, 'everyNthFrame': 1, 'maxWidth': 1440, 'maxHeight': 900})
            t0 = time.time()
            page.goto(f'chrome-extension://{EXT_ID}/newtab.html')
            page.wait_for_timeout(2500)
            cdp.send('Page.stopScreencast')
            # then scrub the opening: freeze every animation the moment it starts and step through by hand
            page.reload(wait_until='commit')
            # wait_for_function evals a string, which the extension's CSP refuses, so poll instead
            for _ in range(500):
                if page.evaluate("document.documentElement.classList.contains('intro')"): break
                time.sleep(.005)
            page.evaluate("""(() => { const r = DOMTokenList.prototype.remove;
              DOMTokenList.prototype.remove = function (...a) { if (!a.includes('intro')) return r.apply(this, a); };
              document.getAnimations().forEach(a => a.pause()); })()""")
            print('animations:', page.evaluate('document.getAnimations().length'))
            for t in SCRUB:
                page.evaluate(f'document.getAnimations().forEach(a => a.currentTime = {t})')
                page.screenshot(path=os.path.join(OUT, f'scrub-{t:04d}.png'))
    finally:
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)

    if not frames: sys.exit('no frames')
    base = frames[0][0]
    ims = []
    for ts, b64 in frames:
        im = Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGB')
        ims.append((int((ts - base) * 1000), im))
    # contact sheet, 4 across, each frame labelled with ms since the first paint
    tw, th = 480, 300
    cols = 4; rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * tw, rows * (th + 22)), 'white')
    d = ImageDraw.Draw(sheet)
    for i, (ms, im) in enumerate(ims):
        x, y = (i % cols) * tw, (i // cols) * (th + 22)
        sheet.paste(im.resize((tw, th)), (x, y + 22))
        d.text((x + 6, y + 5), f'#{i}  +{ms}ms', fill='black')
        im.save(os.path.join(OUT, f'f{i:02d}.jpg'))
    p = os.path.join(OUT, 'sheet.png'); sheet.save(p)
    if os.environ.get('GIF'):
        gif = [Image.open(os.path.join(OUT, f'scrub-{t:04d}.png')).convert('RGB').resize((960, 600)) for t in SCRUB]
        gif[0].save(os.path.join(OUT, 'opening.gif'), save_all=True, append_images=gif[1:] + [gif[-1]] * 20, duration=40, loop=0)
        print(os.path.join(OUT, 'opening.gif')); return
    sc = Image.new('RGB', (5 * tw, 2 * (th + 22)), 'white'); d2 = ImageDraw.Draw(sc)
    for i, t in enumerate(SCRUB):
        x, y = (i % 5) * tw, (i // 5) * (th + 22)
        sc.paste(Image.open(os.path.join(OUT, f'scrub-{t:04d}.png')).convert('RGB').resize((tw, th)), (x, y + 22))
        d2.text((x + 6, y + 5), f'{t}ms into the opening', fill='black')
    sc.save(os.path.join(OUT, 'scrub.png')); print(os.path.join(OUT, 'scrub.png'))
    print('frames:', len(ims), '| times:', [ms for ms, _ in ims])
    print(p)
    print('errors:', errors or 'none')


main()
