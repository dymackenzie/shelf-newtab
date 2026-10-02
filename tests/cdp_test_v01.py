"""Load the Shelf extension in headless Edge with seeded bookmarks and screenshot it."""
import asyncio, base64, json, os, shutil, subprocess, sys, time, urllib.request, uuid
import websockets

EXT = r'C:\Users\macke\Hermes\outputs\designer\shelf-newtab'
TMP = os.environ.get('TMPDIR') or r'C:\Users\macke\AppData\Local\Temp'
PROF = os.path.join(TMP, 'shelf-prof')
OUT = os.path.join(TMP, 'shelf-shots')
EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
EXT_ID = 'emgclpndjmgfkfkmaggaeefeockeddhh'  # fixed by manifest.key
PORT = 9339

LINKS = [('Calendar', 'https://calendar.google.com/calendar/u/0/r'), ('Docs', 'https://docs.google.com/document/u/0/'),
         ('Notion', 'https://www.notion.so/'), ('Photos', 'https://photos.google.com/'), ('Canvas', 'https://canvas.ubc.ca/'),
         ('Piazza', 'https://piazza.com/'), ('UBC', 'https://www.ubc.ca/'), ('Gemini', 'https://gemini.google.com/app'),
         ('Claude', 'https://claude.ai/new')]
LATER = [('Are.na', 'https://www.are.na/'), ('recent.design', 'https://recent.design/')]

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

class CDP:
    def __init__(self, ws): self.ws, self.n, self.events = ws, 0, []
    async def call(self, method, sid=None, **params):
        self.n += 1; mid = self.n
        msg = {'id': mid, 'method': method, 'params': params}
        if sid: msg['sessionId'] = sid
        await self.ws.send(json.dumps(msg))
        while True:
            r = json.loads(await self.ws.recv())
            if r.get('id') == mid:
                if 'error' in r: raise RuntimeError(f"{method}: {r['error']}")
                return r.get('result', {})
            self.events.append(r)

async def main():
    os.makedirs(OUT, exist_ok=True)
    seed()
    proc = subprocess.Popen([EDGE, '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={PROF}',
                             f'--load-extension={EXT}', f'--disable-extensions-except={EXT}', '--no-first-run',
                             '--window-size=1440,900', '--hide-scrollbars', 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                ver = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version')); break
            except Exception: time.sleep(.5)
        async with websockets.connect(ver['webSocketDebuggerUrl'], max_size=50_000_000) as ws:
            c = CDP(ws)
            async def tab(url):
                t = await c.call('Target.createTarget', url=url)
                s = (await c.call('Target.attachToTarget', targetId=t['targetId'], flatten=True))['sessionId']
                await c.call('Runtime.enable', s); await c.call('Page.enable', s)
                await c.call('Emulation.setDeviceMetricsOverride', s, width=1440, height=900, deviceScaleFactor=1, mobile=False)
                return t['targetId'], s
            async def ev(s, expr):
                r = await c.call('Runtime.evaluate', s, expression=expr, awaitPromise=True, returnByValue=True)
                if 'exceptionDetails' in r: return 'EXC ' + json.dumps(r['exceptionDetails'])[:400]
                return r['result'].get('value')
            async def shot(s, name):
                d = await c.call('Page.captureScreenshot', s, format='png')
                p = os.path.join(OUT, name); open(p, 'wb').write(base64.b64decode(d['data'])); print('shot', p)

            # a few real visits so the ribbon has something to count
            _, hs = await tab('about:blank')
            for _ in range(4):
                await c.call('Page.navigate', hs, url='https://piazza.com/'); await asyncio.sleep(2.5)

            _, s = await tab(f'chrome-extension://{EXT_ID}/newtab.html')
            await asyncio.sleep(3)
            print('fonts', await ev(s, "Promise.all([...document.fonts].map(f=>f.load().then(()=>f.family+':'+f.status,()=>f.family+':fail')))"))
            print('books', await ev(s, "[...document.querySelectorAll('.book')].map(b=>b.querySelector('.nm').textContent+(b.querySelector('.ribbon')?'*':'')+(b.classList.contains('lean')?'/':''))"))
            print('groups', await ev(s, "[...document.querySelectorAll('.group')].map(g=>(g.querySelector('h2')?.textContent||'-')+':'+g.querySelectorAll('.book').length)"))
            await shot(s, '1-default.png')

            # his screenshot's sizes: calendar + notion tall, canvas wide
            await ev(s, """chrome.storage.sync.set({
              'b:https://calendar.google.com/calendar/u/0/r':{s:4,ink:0},'b:https://www.notion.so/':{s:3,ink:2},
              'b:https://canvas.ubc.ca/':{s:4,ink:1}}).then(()=>1)""")
            await asyncio.sleep(1.2)
            await shot(s, '2-sized.png')

            # hover, then edit mode with a panel open
            box = await ev(s, "(()=>{const r=[...document.querySelectorAll('.book')][4].getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()")
            await c.call('Input.dispatchMouseEvent', s, type='mouseMoved', x=box[0], y=box[1]); await asyncio.sleep(.4)
            await shot(s, '3-hover.png')
            await ev(s, "document.querySelector('#edit').click()")
            await ev(s, "document.querySelectorAll('.book')[2].click()"); await asyncio.sleep(.5)
            await shot(s, '4-edit-panel.png')

            # move: put Claude first, via the same api the drop handler uses
            await ev(s, "document.querySelector('#edit').click()")
            print('move', await ev(s, """(async()=>{const b=[...document.querySelectorAll('.book')];const t=(await chrome.bookmarks.get(b[0].dataset.id))[0];
              await chrome.bookmarks.move(b[8].dataset.id,{parentId:t.parentId,index:t.index});await new Promise(r=>setTimeout(r,400));
              return [...document.querySelectorAll('.book .nm')].map(n=>n.textContent).join(',')})()"""))
            # add via the + panel
            await ev(s, "document.querySelector('#add').click()")
            await ev(s, "document.querySelector('#p-name').value='Figma';document.querySelector('#p-url').value='figma.com';document.querySelector('#p-add').click()")
            await asyncio.sleep(.6)
            print('after add', await ev(s, "[...document.querySelectorAll('.book .nm')].map(n=>n.textContent).join(',')"))
            await ev(s, "document.querySelector('#gear').click()"); await asyncio.sleep(.3)
            await shot(s, '5-settings.png')
            await c.call('Emulation.setDeviceMetricsOverride', s, width=900, height=800, deviceScaleFactor=1, mobile=False)
            await ev(s, "document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}))"); await ev(s, "dispatchEvent(new Event('resize'))")
            await asyncio.sleep(.6)
            await shot(s, '6-narrow.png')
            errs = [e for e in c.events if e.get('method') in ('Runtime.exceptionThrown',) or (e.get('method') == 'Runtime.consoleAPICalled' and e['params']['type'] in ('error', 'warning'))]
            print('errors', json.dumps(errs)[:1500] if errs else 'none')
    finally:
        subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)

asyncio.run(main())
