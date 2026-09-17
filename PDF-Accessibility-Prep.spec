# Windows x64 only; one-file extraction includes Java, validator, native PDF/OCR,
# Qt platform/accessibility plugins, English recognition data, font, and licenses.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all
root = Path(SPECPATH)
datas = [(str(root / 'resources'), 'resources'), (str(root / 'README.md'), '.'),
         (str(root / 'LICENSE'), '.'), (str(root / 'THIRD-PARTY-NOTICES.md'), '.')]
binaries = []
hiddenimports = ['pdfprep.app', 'pdfprep.batch', 'pdfprep.engine', 'pdfprep.structure',
                 'pdfprep.selftest', 'pdfprep.fixtures']
for package in ('pymupdf', 'pikepdf'):
    d, b, h = collect_all(package)
    datas += d; binaries += b; hiddenimports += h
# The Qt hooks collect QtWidgets/QtGui platform plugins and native dependencies.
a = Analysis([str(root / 'main.py')], pathex=[str(root)], binaries=binaries, datas=datas,
             hiddenimports=hiddenimports, excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='PDF-Accessibility-Prep',
          debug=False, strip=False, upx=False, console=False, disable_windowed_traceback=True)
