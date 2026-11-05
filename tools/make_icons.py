# Draws the tab icon (option A, a leaning book with the ribbon) and writes icons/<size>.png.
# Run with the test venv: C:/dev/.venvs/shelf-newtab/Scripts/python.exe tools/make_icons.py
import base64, pathlib
from playwright.sync_api import sync_playwright

ICONS = pathlib.Path(__file__).resolve().parent.parent / 'icons'

# drawn on a 16-unit grid so every size is the same picture, only sharper
DRAW = """
const SILK='#C4166F', MAG='#E2187F';
function rr(c,x,y,w,h,r){c.beginPath();c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+h,r);c.arcTo(x+w,y+h,x,y+h,r);c.arcTo(x,y+h,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath();}
function book(c,S,x,y,w,h,bg,lean){
  const det=S>=3, r=Math.min(.55,w*.2)*S;
  c.save();
  c.translate(x*S,(y+h)*S);c.rotate(lean*Math.PI/180);c.translate(-x*S,-(y+h)*S);
  // silk ribbon poking out the top, notched like the one on the shelf
  const rw=1.5, rx=x+w*.62-rw/2, top=y-2.6;
  c.fillStyle=SILK;c.beginPath();c.moveTo(rx*S,top*S);c.lineTo((rx+rw/2)*S,(top+.7)*S);c.lineTo((rx+rw)*S,top*S);c.lineTo((rx+rw)*S,(y+1)*S);c.lineTo(rx*S,(y+1)*S);c.closePath();c.fill();
  c.fillStyle=MAG;c.fillRect(rx*S,(top+.5)*S,rw*S*.55,2.6*S);
  rr(c,x*S,y*S,w*S,h*S,r);c.fillStyle=bg;c.fill();
  if(det){
    const g=c.createLinearGradient(x*S,0,(x+w)*S,0);
    g.addColorStop(0,'rgba(0,0,0,.30)');g.addColorStop(.17,'rgba(255,255,255,.13)');g.addColorStop(.5,'rgba(0,0,0,0)');g.addColorStop(1,'rgba(0,0,0,.34)');
    rr(c,x*S,y*S,w*S,h*S,r);c.fillStyle=g;c.fill();
  }
  c.fillStyle='rgba(236,232,220,.45)';
  const t=det?.12:.7/S, gap=det?.28:0;
  [y+1.1,y+h-1.5].forEach(yy=>{c.fillRect((x+.35)*S,yy*S,(w-.7)*S,t*S);if(gap)c.fillRect((x+.35)*S,(yy+gap)*S,(w-.7)*S,t*S);});
  c.restore();
}
function icon(size){
  const cv=document.createElement('canvas');cv.width=cv.height=size;const c=cv.getContext('2d'),S=size/16;
  book(c,S,4.2,3.2,6.4,10.8,'#23211D',9);
  c.fillStyle='#D6C3A0';c.fillRect(1.5*S,14*S,13*S,.55*S);
  c.fillStyle='#B89D72';c.fillRect(1.5*S,14.5*S,13*S,1*S);
  return cv.toDataURL('image/png');
}
"""

with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_page()
    page.set_content('<script>' + DRAW + '</script>')
    for size in (16, 32, 48, 128):
        url = page.evaluate(f'icon({size})')
        (ICONS / f'{size}.png').write_bytes(base64.b64decode(url.split(',', 1)[1]))
        print('wrote', ICONS / f'{size}.png')
    b.close()
