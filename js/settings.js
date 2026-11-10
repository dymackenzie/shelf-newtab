import { h } from './dom.js';
import * as store from './store.js';
import { openPanel } from './panel.js';
import { PAPERS, ACCENTS, paperHex, isHex } from './palette.js';

const SWITCHES = [
  ['subShelves', 'Give each subfolder its own shelf'],
  ['ribbon', 'Put a ribbon on the book I open most'],
  ['lean', 'Let the last book lean'],
  ['grain', 'Give the paper a fine grain'],
];

// a row of colour dots. the paper row also gets a picker for any colour
function swatches(key, list, current, custom) {
  const dots = [];
  const mark = v => dots.forEach(d => d.classList.toggle('on',
    d.dataset.v === v || (d.classList.contains('own') && isHex(v) && !list.some(p => p[0] === v))));
  const choose = v => { mark(v); store.saveSettings({ [key]: v }); };
  for (const [v, name, hex] of list) {
    dots.push(h('button', {
      type: 'button', class: 'dot', title: name, 'aria-label': name, dataset: { v }, style: `--c:${hex}`, onclick: () => choose(v),
    }));
  }
  if (custom) {
    let t;
    const input = h('input', { type: 'color', value: paperHex(current), 'aria-label': 'Any colour' });
    // the picker fires input on every drag step, so only save on a pause
    input.addEventListener('input', () => {
      own.style.setProperty('--c', input.value);
      own.dataset.v = input.value;
      clearTimeout(t); t = setTimeout(() => choose(input.value), 120);
    });
    const own = h('label', {
      class: 'dot own', title: 'Any colour', dataset: { v: isHex(current) ? current : '' }, style: isHex(current) ? `--c:${current}` : '',
    }, input);
    dots.push(own);
  }
  mark(current);
  return h('span', { class: 'dots', role: 'group' }, dots);
}

// 3D or 2D, as a two-way switch. radios underneath, so arrow keys flip it like any radio group
function lookSwitch(current) {
  const opt = (v, text) => h('label', {},
    h('input', { type: 'radio', name: 'look', value: v, checked: current === v, onchange: () => store.saveSettings({ look: v }) }),
    h('span', {}, text));
  return h('span', { class: 'seg', role: 'radiogroup', 'aria-label': 'Draw the books in' }, opt('3d', '3D'), opt('2d', '2D'));
}

export function openSettings() {
  const s = store.get();
  const select = h('select', { id: 's-folder', onchange: e => store.saveSettings({ folder: e.target.value }) },
    s.folders.map(f => h('option', { value: f.path }, f.path)));
  select.value = s.folders.find(f => f.node.id === s.folder?.id)?.path ?? '';

  const sentences = SWITCHES.map(([key, text]) => h('label', { class: 'sentence' },
    h('span', {}, text),
    h('input', {
      type: 'checkbox', role: 'switch', checked: s.settings[key], dataset: { key },
      onchange: e => store.saveSettings({ [key]: e.target.checked }),
    })));

  openPanel('settings', [
    h('h3', {}, 'Shelf'),
    h('label', { class: 'sentence' }, 'Show', h('span', { class: 'pick' }, select), 'on the shelf.'),
    h('div', { class: 'sentence look' }, h('span', {}, 'Draw the books in'), lookSwitch(s.settings.look)),
    h('div', { class: 'sentence colours' }, h('span', {}, 'The paper is'), swatches('paper', PAPERS, s.settings.paper, true)),
    h('div', { class: 'sentence colours' }, h('span', {}, 'The accent is'), swatches('accent', ACCENTS, s.settings.accent, false)),
    ...sentences,
  ]);
  select.focus();
}
