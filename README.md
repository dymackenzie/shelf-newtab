# Shelf

Your bookmarks as books on a shelf, on the new tab page. Colours come from the Hermes Collage Night skin.

## Install

1. Open `chrome://extensions` and turn on **Developer mode** (top right).
2. Click **Load unpacked** and choose this folder.
3. Open a new tab. If Chrome asks whether to keep the change, keep it.

This also works in Edge, Brave and Arc. The manifest has a fixed `key`, so the extension ID stays the same on every computer and your spine heights and inks sync through your Chrome account.

## Using it

- The shelf shows your bookmarks bar by default. Pick another folder under ⚙. Each subfolder gets its own labelled shelf, unless you turn that off.
- Press `1` to `9` to open a book. Hold Ctrl to open it in a background tab.
- To add a book, drag a link, the site icon from the address bar, a bookmark from the bookmarks bar, or a `.url` shortcut onto the shelf. It lands where the vermilion bar shows. A small card opens under it: rename it, paste an image for its icon, or Undo.
- For an icon, right-click any image in Chrome, choose Copy image, and press Ctrl+V while the card is open. You can also drop an image file on the square, or click it to pick one. Dropping an image straight from another site asks for permission first.
- Click + to add a book by typing or pasting its address instead.
- Click ✎ to edit. Drag a book to move it (this moves the real bookmark). Click a book to rename it, change its height, ink or icon, or remove it.
- The vermilion ribbon marks the site you opened most in the last seven days (at least three visits). You can turn it off under ⚙.
- Sites Chrome has never loaded show their first letter until it has their icon.

## Files

- `theme.css`: colours and fonts. Swap it to reskin.
- `newtab.css`: layout and components.
- `js/main.js` starts everything. `store.js` owns the state, `bookmarks.js` reads the tree, `shelf.js` draws it, `drop.js` works out where a drop lands, `reorder.js` and `add.js` handle dragging and adding, `well.js` is the image square, `bookpanel.js` and `settings.js` are the two panels, `icons.js` and `ribbon.js` do favicons and the ribbon.
- `fonts/`: Fraunces, Archivo Narrow and JetBrains Mono (latin subsets).

## Tests

Headless, in Playwright's Chromium with a seeded profile. Branded Chrome no longer loads unpacked extensions from the command line, so the tests don't use it.

```
py -m venv C:/dev/.venvs/shelf-newtab
C:/dev/.venvs/shelf-newtab/Scripts/python -m pip install playwright
C:/dev/.venvs/shelf-newtab/Scripts/python tests/cdp_test.py
```

The venv lives outside this folder because Chrome refuses to load an extension that contains files starting with `_`. Screenshots land in `tests/shots/`.
