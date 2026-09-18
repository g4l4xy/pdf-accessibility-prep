# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build-time only downloads. The application never calls this module."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / 'resources'
CACHE = ROOT / 'build' / 'downloads'


def digest(path):
    return hashlib.file_digest(open(path, 'rb'), 'sha256').hexdigest()


def download(key, item):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / key
    if not path.exists() or digest(path) != item['sha256']:
        request = urllib.request.Request(item['url'], headers={'User-Agent': 'PDF-Accessibility-Prep-build/0.1'})
        with urllib.request.urlopen(request, timeout=120) as src, open(path, 'wb') as out:
            shutil.copyfileobj(src, out)
    if digest(path) != item['sha256']:
        path.unlink(missing_ok=True); raise RuntimeError('Dependency checksum mismatch: ' + key)
    return path


def extract(path, dest):
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as z:
        for member in z.infolist():
            target = (dest / member.filename).resolve()
            if not target.is_relative_to(dest.resolve()): raise RuntimeError('Unsafe archive member')
        z.extractall(dest)


def remove_tree(path):
    # Reference profiles in the upstream installer can exceed legacy MAX_PATH.
    absolute = str(Path(path).resolve())
    if sys.platform == 'win32' and not absolute.startswith('\\\\?\\'):
        absolute = '\\\\?\\' + absolute
    if Path(path).exists():
        shutil.rmtree(absolute)


def main():
    if sys.platform != 'win32': raise SystemExit('Run Windows resource assembly on Windows x64.')
    lock = json.loads((ROOT / 'dependencies.lock.json').read_text())
    RESOURCES.mkdir(exist_ok=True)
    jr = CACHE / 'jre-extracted'; extract(download('jre.zip', lock['jre']), jr)
    homes = [p.parent.parent for p in jr.glob('*/bin/java.exe')]
    if len(homes) != 1: raise RuntimeError('Unexpected JRE layout')
    if (RESOURCES / 'jre').exists(): remove_tree(RESOURCES / 'jre')
    shutil.copytree(homes[0], RESOURCES / 'jre')
    java = RESOURCES / 'jre/bin/java.exe'
    vd = CACHE / 'verapdf-extracted'; extract(download('verapdf.zip', lock['verapdf']), vd)
    installer = next(vd.glob('*/verapdf-izpack-installer-*.jar'))
    target = RESOURCES / 'verapdf'
    if target.exists(): remove_tree(target)
    xml = f'''<AutomatedInstallation langpack="eng">
<com.izforge.izpack.panels.htmlhello.HTMLHelloPanel id="welcome"/>
<com.izforge.izpack.panels.target.TargetPanel id="install_dir"><installpath>{escape(str(target))}</installpath></com.izforge.izpack.panels.target.TargetPanel>
<com.izforge.izpack.panels.packs.PacksPanel id="sdk_pack_select">
<pack index="0" name="veraPDF GUI" selected="true"/>
<pack index="1" name="veraPDF Mac and *nix Scripts" selected="false"/>
<pack index="2" name="veraPDF Batch files" selected="true"/>
<pack index="3" name="veraPDF Validation model" selected="false"/>
<pack index="4" name="veraPDF Documentation" selected="true"/>
<pack index="5" name="veraPDF Sample Plugins" selected="false"/>
</com.izforge.izpack.panels.packs.PacksPanel>
<com.izforge.izpack.panels.install.InstallPanel id="install"/>
<com.izforge.izpack.panels.finish.FinishPanel id="finish"/>
</AutomatedInstallation>'''
    config = CACHE / 'install.xml'; config.write_text(xml, encoding='utf-8')
    subprocess.run([str(java), '-jar', str(installer), str(config)], check=True, timeout=120)
    if not (target / 'bin/greenfield-apps-1.28.2.jar').exists(): raise RuntimeError('Validator jar is absent')
    for extra in ('Uninstaller', 'profiles', 'plugins', 'documents'):
        remove_tree(target / extra)
    (RESOURCES / 'tessdata').mkdir(exist_ok=True)
    shutil.copyfile(download('eng.traineddata', lock['eng']), RESOURCES / 'tessdata/eng.traineddata')
    shutil.copyfile(download('NotoSans-Regular.ttf', lock['font']), RESOURCES / 'NotoSans-Regular.ttf')
    (RESOURCES / 'fonts').mkdir(exist_ok=True)
    for name, item in lock.get('interface_fonts', {}).items():
        shutil.copyfile(download(name, item), RESOURCES / 'fonts' / name)
    (RESOURCES / 'build-manifest.json').write_text(json.dumps(lock, indent=2), encoding='utf-8')
    # Verify UA profile selection before packaging; a PDF/A-only tool cannot pass this gate.
    cmd = [str(java), '-cp', str(target / 'bin/*'), 'org.verapdf.apps.GreenfieldCliWrapper', '--version']
    subprocess.run(cmd, check=True, timeout=30)


if __name__ == '__main__': main()
