import { h } from './dom.js';
import * as store from './store.js';
import { openPanel } from './panel.js';

const SWITCHES = [
  ['subShelves', 'Give each subfolder its own shelf'],
  ['ribbon', 'Put a ribbon on the book I open most'],
  ['lean', 'Let the last book lean'],
];

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
    ...sentences,
  ]);
  select.focus();
}
