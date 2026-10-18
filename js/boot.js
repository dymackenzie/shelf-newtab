// runs before anything paints: put back the last colours so a new tab opens in his paper, not the default
try {
  const vars = JSON.parse(localStorage.getItem('shelf:theme') || '{}');
  for (const k in vars) document.documentElement.style.setProperty(k, vars[k]);
} catch {}
const hide = localStorage.getItem('shelf:hide');
if (hide) document.documentElement.classList.add(...hide.split(' '));
