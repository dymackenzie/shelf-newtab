# Shelf, what's next

Getting it on the Chrome Web Store. Everything for the upload is committed: `tools/pack.py` (builds dist/shelf-1.0.0.zip without `key`), `PRIVACY.md`, `store/listing.md`, `store/screenshots/`, `store/promo-440x280.png`. The packed zip loads in a clean Chromium (2D, 11 books, no errors).

## Mackenzie
- Read `PRIVACY.md` and the description in `store/listing.md`. Both score 100% on ZeroGPT, but so does the README intro, so the checker flags this kind of copy whatever's in it. Real details would help (why you made it, what you use it for).
- Developer account ($5 one-time) at chrome.google.com/webstore/devconsole, then upload the zip and fill the fields from `store/listing.md`.
- After it's live: README still says it isn't on the store, and the store ID is new, so unpacked installs won't share synced heights/colours with the store install.

## Tests
- `tests/*.py` only run on Windows as written (LOCALAPPDATA, chrome-win64, taskkill).
- On Mac Chromium the folder is "Other Bookmarks", so "shelf reads its own folder by default" fails and the settings checks time out on `select_option`. With that name patched, 131/131 pass.

## Open questions (from v0.2, still open)
- Esc on the slim card keeps the book but drops an unsaved rename.
- The dock buttons still use the browser's default focus outline.
