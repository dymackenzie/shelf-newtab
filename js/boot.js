// runs before paint, so a new tab opens in the saved colours instead of the default
try {
  const vars = JSON.parse(localStorage.getItem('shelf:theme') || '{}');
  for (const k in vars) document.documentElement.style.setProperty(k, vars[k]);
} catch {}
// hidden until main.js has the fonts and books ready so text doesn't pop in bit by bit.
// the timer is a safety net in case something breaks first
document.documentElement.classList.add('wait');
setTimeout(() => document.documentElement.classList.remove('wait'), 2000);
// ribbon style, a b or c
document.documentElement.dataset.ribbon = localStorage.getItem('shelf:ribbon') || 'a';
// 2d is a class too, so a flat shelf never opens as a 3d one for a frame
if (localStorage.getItem('shelf:look') === '2d') document.documentElement.classList.add('flat');
// keys from features that got cut
for (const k of ['shelf:hide', 'shelf:paintings']) localStorage.removeItem(k);
