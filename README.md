# Shelf

Your bookmarks as books on a shelf, on the new tab page. Colours come from the Hermes Collage Night skin.

## Install

1. Open `chrome://extensions` and turn on **Developer mode** (top right).
2. Click **Load unpacked** and choose this folder.
3. Open a new tab. If Chrome asks whether to keep the change, keep it.

This also works in Edge, Brave and Arc. The manifest has a fixed `key`, so the extension ID stays the same on every computer and your spine heights and inks sync through your Chrome account.

## Using it

- The shelf shows your bookmarks bar by default. Pick another folder under ⚙. Each subfolder gets its own labelled shelf.
- Press `1` to `9` to open a book. Hold Ctrl to open it in a background tab.
- Click ✎ to edit. Drag a book to move it (this moves the real bookmark). Click a book to rename it, change its height or ink, upload your own icon, or remove it.
- Click + to add a book to the current folder.
- The vermilion ribbon marks the site you opened most in the last seven days (at least three visits). You can turn it off under ⚙.
- Sites Chrome has never loaded show their first letter until it has their icon.

## Files

- `theme.css`: colours and fonts. Swap it to reskin.
- `newtab.js`: bookmarks, shelves, edit mode, ribbon.
- `fonts/`: Fraunces, Archivo Narrow and JetBrains Mono (latin subsets).
