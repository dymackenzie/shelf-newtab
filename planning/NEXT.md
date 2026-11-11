# Shelf, what's next

Getting it on the Chrome Web Store. Comment cleanup, ribbon A only, 2D as the default and new README shots are done (uncommitted). Full suite passes on Mac with the folder-name patch.

## Before uploading
- The store rejects a manifest with `key`. Zip a copy without it, and only the extension files: `manifest.json`, `newtab.html`, `newtab.css`, `theme.css`, `js/`, `fonts/`, `icons/`. Leave out `tests/`, `docs/`, `planning/`, `tools/`, `README.md`.
- The store gives it a new ID, so unpacked installs won't share synced heights/colours with the store install.
- Listing needs a reason for each permission (`history` for the ribbon and titles, `bookmarks`, `favicon`, `storage`) and a privacy policy, since it reads history.
- README still says it isn't on the store.

## Tests
- `tests/*.py` only run on Windows as written (LOCALAPPDATA, chrome-win64, taskkill).
- On Mac Chromium the folder is "Other Bookmarks", so "shelf reads its own folder by default" fails and the settings check times out on `select_option`.

## Open questions (from v0.2, still open)
- Esc on the slim card keeps the book but drops an unsaved rename.
- The dock buttons still use the browser's default focus outline.
