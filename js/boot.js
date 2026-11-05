// runs before anything paints: put back the last colours so a new tab opens in his paper, not the default
try {
  const vars = JSON.parse(localStorage.getItem('shelf:theme') || '{}');
  for (const k in vars) document.documentElement.style.setProperty(k, vars[k]);
} catch {}
// hidden until main.js has the fonts and the books ready, so text doesn't pop in a piece at a time.
// the timer is a safety net in case something breaks before then
document.documentElement.classList.add('wait');
setTimeout(() => document.documentElement.classList.remove('wait'), 2000);
// ribbon look while he picks one (a, b or c)
document.documentElement.dataset.ribbon = localStorage.getItem('shelf:ribbon') || 'a';
// 2d is a class too, so a flat shelf never opens as a 3d one for a frame
if (localStorage.getItem('shelf:look') === '2d') document.documentElement.classList.add('flat');
// left over from the date, contents and painting, which are gone
for (const k of ['shelf:hide', 'shelf:paintings']) localStorage.removeItem(k);
