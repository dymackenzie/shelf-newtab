# Zips the extension for the Chrome Web Store into dist/shelf-<version>.zip.
# The store rejects a manifest with "key", so it only comes out of the zipped copy. The repo keeps it for unpacked installs.
import json, pathlib, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHIP = ['newtab.html', 'newtab.css', 'theme.css', 'js', 'fonts', 'icons']

manifest = json.loads((ROOT / 'manifest.json').read_text())
manifest.pop('key', None)
out = ROOT / 'dist' / f"shelf-{manifest['version']}.zip"
out.parent.mkdir(exist_ok=True)

with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('manifest.json', json.dumps(manifest, indent=2) + '\n')
    for name in SHIP:
        p = ROOT / name
        for f in sorted([p] if p.is_file() else p.rglob('*')):
            if f.is_file() and not f.name.startswith('.'):
                z.write(f, f.relative_to(ROOT).as_posix())
print(out)
