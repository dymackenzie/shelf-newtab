# Draws the tab icon (a flat book leaning on the shelf, like the 2d look) and writes icons/<size>.png.
# Run with the test venv: <venv python> tools/make_icons.py
import base64, glob, os, pathlib
from playwright.sync_api import sync_playwright

ICONS = pathlib.Path(__file__).resolve().parent.parent / 'icons'

# drawn on a 16-unit grid so every size is the same picture, only sharper
DRAW = """
const MAG='#E2187F';
function rr(c,x,y,w,h,r){c.beginPath();c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+h,r);c.arcTo(x+w,y+h,x,y+h,r);c.arcTo(x,y+h,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath();}
function shade(hex,t){const n=parseInt(hex.slice(1),16),ch=[n>>16,n>>8&255,n&255];return 'rgb('+ch.map(v=>Math.round(t>0?v+(255-v)*t:v*(1+t))).join(',')+')';}
// same as a 2d book: rounded, a touch lighter at the top and darker at the bottom, thin light rim
function book(c,S,x,y,w,h,bg,lean){
  const r=Math.min(w*.22,1.3)*S;
  c.save();
  c.translate((x+w)*S,(y+h)*S);c.rotate(lean*Math.PI/180);c.translate(-(x+w)*S,-(y+h)*S);
  // flat ribbon tab poking out the top, notched like the one on the shelf
  const rw=Math.max(w*.2,1.1), rx=x+w-rw-Math.max(w*.16,.8), top=y-2.1;
  c.fillStyle=MAG;c.beginPath();c.moveTo(rx*S,top*S);c.lineTo((rx+rw/2)*S,(top+.55)*S);c.lineTo((rx+rw)*S,top*S);c.lineTo((rx+rw)*S,(y+1)*S);c.lineTo(rx*S,(y+1)*S);c.closePath();c.fill();
  const g=c.createLinearGradient(0,y*S,0,(y+h)*S);
  g.addColorStop(0,shade(bg,.08));g.addColorStop(.45,bg);g.addColorStop(1,shade(bg,-.08));
  rr(c,x*S,y*S,w*S,h*S,r);c.fillStyle=g;c.fill();
  if(S>=3){rr(c,(x+.04)*S,(y+.04)*S,(w-.08)*S,(h-.08)*S,r);c.strokeStyle='rgba(255,255,255,.14)';c.lineWidth=.08*S;c.stroke();}
  c.restore();
}
function icon(size){
  const cv=document.createElement('canvas');cv.width=cv.height=size;const c=cv.getContext('2d'),S=size/16;
  // clipped at the bar so the leaning corner doesn't poke out underneath it
  c.save();c.beginPath();c.rect(0,0,16*S,14.4*S);c.clip();
  book(c,S,4.2,3.6,6.2,10.6,'#23211D',9);
  c.restore();
  rr(c,1.5*S,13.8*S,13*S,.75*S,.375*S);c.fillStyle='#D6D6D4';c.fill();
  return cv.toDataURL('image/png');
}
"""

# whichever chromium build is in the mac cache, otherwise playwright's default
mac = glob.glob(os.path.expanduser('~/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/*.app/Contents/MacOS/*'))
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=mac[0]) if mac else pw.chromium.launch()
    page = b.new_page()
    page.set_content('<script>' + DRAW + '</script>')
    for size in (16, 32, 48, 128):
        url = page.evaluate(f'icon({size})')
        (ICONS / f'{size}.png').write_bytes(base64.b64decode(url.split(',', 1)[1]))
        print('wrote', ICONS / f'{size}.png')
    b.close()
