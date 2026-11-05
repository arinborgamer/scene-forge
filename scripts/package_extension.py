"""Bundle source files only; no user projects or model weights."""
from pathlib import Path
import zipfile
import tomllib

ROOT = Path(__file__).resolve().parent.parent
version = tomllib.loads((ROOT / 'blender_extension' / 'blender_manifest.toml').read_text())['version']
destination = ROOT / 'dist' / f'scene_forge-{version}.zip'
destination.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in (ROOT / "blender_extension").glob("*"):
        if path.is_file():
            archive.write(path, path.name)
    for path in (ROOT / "scene_forge").glob("*.py"):
        archive.write(path, "scene_forge/" + path.name)
print(destination)
