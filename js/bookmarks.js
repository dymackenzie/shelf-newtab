export async function readTree() {
  const [root] = await chrome.bookmarks.getTree();
  return root;
}

export function folderList(root) {
  const out = [];
  const walk = (node, path) => {
    for (const c of node.children || []) {
      if (c.url) continue;
      const p = path ? `${path} / ${c.title}` : c.title;
      out.push({ id: c.id, path: p, node: c });
      walk(c, p);
    }
  };
  walk(root, '');
  return out;
}

// folder is saved by its path, since bookmark ids differ between computers
export const resolve = (folders, path) => (folders.find(f => f.path === path) || folders[0])?.node ?? null;

const links = node => (node.children || []).filter(x => x.url);

// direct links make the first shelf, each subfolder gets its own labelled shelf.
// with subShelves off everything lands on one shelf in folder order
export function groupsOf(folder, subShelves) {
  const kids = folder.children || [];
  if (!subShelves) return [{ label: null, parentId: folder.id, items: kids.flatMap(c => (c.url ? [c] : links(c))) }];
  const out = [{ label: null, parentId: folder.id, items: kids.filter(c => c.url) }];
  for (const c of kids) if (!c.url) out.push({ label: c.title, parentId: c.id, items: links(c) });
  if (!out[0].items.length && out.length > 1) out.shift();
  return out;
}

// shelf keeps its books in its own folder under Other bookmarks, so they never show on the bookmarks bar
export async function ownFolderPath() {
  const root = await readTree();
  const kids = root.children || [];
  const other = kids.find(c => c.folderType === 'other') || kids.find(c => c.id === '2') || kids[1];
  if (!other.children?.some(c => !c.url && c.title === 'Shelf')) await chrome.bookmarks.create({ parentId: other.id, title: 'Shelf' });
  return `${other.title} / Shelf`;
}
