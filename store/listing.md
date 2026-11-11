# Chrome Web Store listing

Everything the developer dashboard asks for, in the order it asks. Upload `dist/shelf-1.0.0.zip` (run `python3 tools/pack.py` first).

## Store listing

**Name:** Shelf (from the manifest)

**Summary** (from the manifest, 132 max):
A shelf of books on your new tab, separate from the bookmarks bar.

**Description:**

Every link on Shelf is a book on your new tab, and the cover colour comes from the site's icon, so Spotify is green and Wikipedia is cream with dark letters. The books are bookmarks in their own folder under Other bookmarks, so your bookmarks bar stays the same.

To add a book you drag a link onto the shelf. That can be the little icon to the left of the address bar, a link on another page or something off the bookmarks bar. Tabs don't work, because Chrome pulls them out into a new window. When you let go a card opens under the book where you can rename it or paste in a different icon, and if Chrome hasn't loaded the site yet the book shows its first letter until the icon comes in.

It opens on a flat shelf. In Settings you can switch to a 3D one with cloth spines and page edges on an oak plank, and change the paper and accent colours. There's also a ribbon that goes on the site you opened most this week and the last book leans on the others, and both can be turned off.

The putty paper colour came from Shopify Editions and the 3D spines are based on Grokipedia's shelf. There's no account or server, everything stays in your bookmarks and Chrome sync.

**Category:** Make Chrome Yours > Functionality & UI

**Language:** English

**Store icon:** `icons/128.png`

**Screenshots** (1280x800): `store/screenshots/1-shelf-2d.png` to `5-shelf-3d.png`, in that order

**Small promo tile** (440x280): `store/promo-440x280.png`

**Homepage / support URL:** https://github.com/dymackenzie/shelf-newtab

## Privacy practices

**Single purpose:**
Replaces the new tab page with a shelf of your bookmarks.

**Permission justifications:**

- `bookmarks`: The books on the shelf are bookmarks in Shelf's own folder, so it reads them to draw the shelf and adds, moves, renames or removes one when you do that on the shelf.
- `history`: Counts which site on the shelf you opened most in the last week to put the ribbon on it, and looks up a page's title when you add a link without one. The count stays on your computer.
- `favicon`: Each book shows its site's icon, and the cover colour comes from that icon.
- `storage`: Saves your settings, each book's height and colour, and any icon you paste in.
- `<all_urls>` (optional host permission): Never asked for up front. Shelf only asks for one site, when you paste an image address for an icon, that site won't share the image, and you click Keep a copy. That lets it save a copy of that one image.

**Remote code:** No, everything is in the package.

**Data usage:** tick Web history (it reads history to place the ribbon and find titles). Then tick all three certifications: not sold, not used for anything unrelated, not used for credit.

**Privacy policy URL:** https://github.com/dymackenzie/shelf-newtab/blob/main/PRIVACY.md
