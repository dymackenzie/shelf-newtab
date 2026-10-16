# Shelf, what's next

v0.2 is built and the headless suite passes (84 checks). Not committed. Mackenzie names the commit.

## Before it goes to Mackenzie
- Matisse checks the build against the sketches (newtab-sketches.html option C, shelf-add-settings.html A + A).
- Try the real drags by hand in Chrome: a link from another page, the address bar site icon, a bookmarks bar item, a `.url` file from Explorer. The tests only fire synthetic drag events.
- Try "Allow images from websites" for real. Headless can't show the permission prompt, so neither the yes nor the no path has been clicked.

## Open questions
- Default inks are picked by position, so adding a book in the middle recolours every book after it. Drop-to-add makes that visible on every add. Pinning an ink to each new book's meta when it's created would stop it.
- Esc on the slim card keeps the book but drops an unsaved rename. That's how the brief reads, but it's worth a second look.
- The dock buttons still use the browser's default focus outline. The books use the vermilion ring.
