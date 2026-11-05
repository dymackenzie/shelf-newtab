# Shelf

A shelf of books on the new tab page, separate from your bookmarks bar. Light putty paper so it sits with Chrome's light toolbar; ground sampled from Shopify Editions, spines after Grokipedia's shelf.

![The shelf in 3D](docs/shelf-3d.png)

The same shelf in 2D, which you can switch to in Settings:

![The shelf in 2D](docs/shelf-2d.png)

## Install

1. Open `chrome://extensions` and turn on **Developer mode** (top right).
2. Click **Load unpacked** and choose this folder.
3. Open a new tab. If Chrome asks whether to keep the change, keep it.

This also works in Edge, Brave and Arc. The manifest has a fixed `key`, so the extension ID stays the same on every computer and your spine heights and inks sync through your Chrome account.

## Using it

- Shelf keeps its own books in a **Shelf** folder under Other bookmarks, which Chrome doesn't show on the bookmarks bar. It's made the first time you open a new tab and starts empty. It syncs like any bookmark folder. You can still point the shelf at another folder under Settings (top right). Each subfolder gets its own labelled shelf, unless you turn that off.
- The books are drawn as solid blocks, with page edges on top and the back going away to the right, standing on an oak plank. It's an oblique drawing made of flat shapes, not a CSS 3D turn, because the 3D turn made Chrome stretch the shelf and blurred the titles. Hover a book to lift it.
- In 2D (Settings, "Draw the books in 3D / 2D") each book is one flat rounded block of its colour, lit a little from the top, with the site's icon at the foot, after Apple's newer app icons. The shelf is a plain rounded bar.
- Press `1` to `9` to open a book. Hold Ctrl to open it in a background tab.
- To add a book, drag a link, the site icon from the address bar, a bookmark from the bookmarks bar, or a `.url` shortcut onto the shelf. It lands where the pink bar shows. A small card opens under it: rename it, paste an image for its icon, or Undo.
- The add card reads as a sentence ("Add ___ called ___ with the icon from ___") beside a small preview of the book, which fills in and changes colour as you type.
- For an icon, right-click any image on the web, choose **Copy image address**, and paste it into the icon field. If the site allows it, Shelf copies the image ("Copied.") so it works offline and colours the cover. If not, it links the image instead ("Linked, not copied."). Click **Keep a copy** to give Shelf permission for that one site and copy it. You can also paste a copied image, drop an image anywhere on the card, or pick a file.
- Click **Add a book** to add one by typing or pasting its address instead.
- Click **Edit** to edit. Drag a book to move it (this moves the real bookmark). Click a book to rename it, change its height, colour or icon, or remove it. The first colour swatch (with the dot) means "match the icon".
- Settings also sets the colours: pick a paper (Chalk, White, Putty, Linen, Stone, Sage, Blush, Sky or Night) or any colour from the + picker, and an accent for the ribbon and highlights. Text, panels and grey labels are worked out from the paper and always stay readable (5:1); a very loud paper gets nudged just enough to pass. You can also turn off the grain. Colours sync with your other settings.
- The pink ribbon marks the site you opened most in the last seven days (at least three visits). You can turn it off in Settings.
- Each cover is dyed from its site's icon: the icon's main colour, darker and duller like book cloth, always at least 5:1 against its title. Mostly-white icons get cream boards, white marks with no background get black cloth.
- Sites Chrome has never loaded show their first letter and a stand-in colour until it has their icon.

## Files

- `theme.css`: colours and fonts. Swap it to reskin.
- `newtab.css`: layout and components.
- `js/main.js` starts everything. `store.js` owns the state, `bookmarks.js` reads the tree, `shelf.js` draws it, `drop.js` works out where a drop lands, `reorder.js` and `add.js` handle dragging and adding, `iconfield.js` is the icon square and image address field, `preview.js` is the little book in the add card, `bookpanel.js` and `settings.js` are the two panels, `icons.js` and `ribbon.js` do favicons and the ribbon, `cloth.js` reads a cover colour off each icon, `palette.js` works out every colour from the paper and accent, `boot.js` puts them and the 3D/2D look back before the page paints.
- `docs/`: the screenshots in this readme.
- `fonts/`: Fraunces (upright and italic), Archivo (variable, covers narrow widths too) and JetBrains Mono, latin subsets.
- Until its icon colour is known, a book's stand-in ink comes from its address, so it keeps the same colour wherever it sits. Two stand-in neighbours that would match get nudged apart. Thickness varies a little per address too, like real books.

## Tests

Headless, in Playwright's Chromium with a seeded profile. Branded Chrome no longer loads unpacked extensions from the command line, so the tests don't use it.

```
py -m venv C:/dev/.venvs/shelf-newtab
C:/dev/.venvs/shelf-newtab/Scripts/python -m pip install playwright
C:/dev/.venvs/shelf-newtab/Scripts/python tests/cdp_test.py
```

The venv lives outside this folder because Chrome refuses to load an extension that contains files starting with `_`. Screenshots land in `tests/shots/`.

`tests/looks.py <out> [demo] [states] [fresh] [2d]` takes quick screenshots: `demo` fills the shelf with twelve visited sites so their icons and cloth colours show, `states` adds settings, edit panel and add card, `fresh` starts with no Shelf folder to check first run, `2d` draws it flat. The readme shots are `demo` and `demo 2d` at 1440, cropped to the shelf.
