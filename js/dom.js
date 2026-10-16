export const $ = (s, el = document) => el.querySelector(s);
export const $$ = (s, el = document) => [...el.querySelectorAll(s)];
// dragging selected text makes the text node the event target, and text nodes have no closest()
export const elOf = node => (node?.nodeType === 1 ? node : node?.parentElement) || document.body;
export const rem = () => parseFloat(getComputedStyle(document.documentElement).fontSize);

// tiny element builder. strings become text nodes, so titles and urls never touch innerHTML
export function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style') el.style.cssText = v;
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k in el) el[k] = v; // properties take false too, draggable needs that
    else if (v !== false) el.setAttribute(k, v === true ? '' : v);
  }
  el.append(...kids.flat().filter(k => k != null && k !== false));
  return el;
}
