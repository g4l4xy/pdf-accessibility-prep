# Dependency source access and binary distribution

This repository supplies the application's source, pinned requirements, resource hashes, packaging specification, and build scripts. Third-party software remains under its own licenses. See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) and `resources/licenses`.

## Upstream source locations

| Component | Source location |
|---|---|
| PyMuPDF 1.28.2 and its MuPDF source acquisition/build configuration | https://pypi.org/project/PyMuPDF/1.28.2/#files and https://github.com/pymupdf/PyMuPDF |
| MuPDF and bundled native dependencies | https://github.com/ArtifexSoftware/mupdf |
| PySide / Shiboken 6.11.2 | https://code.qt.io/pyside/pyside-setup.git/ |
| Qt 6.11.2 | https://download.qt.io/archive/qt/ and https://code.qt.io/ |
| pikepdf 10.13.0.post1 | https://pypi.org/project/pikepdf/10.13.0.post1/#files |
| QPDF | https://github.com/qpdf/qpdf |
| Python 3.13.15 | https://www.python.org/downloads/source/ |
| Pillow 12.3.0 | https://pypi.org/project/Pillow/12.3.0/#files |
| lxml 6.1.3 | https://pypi.org/project/lxml/6.1.3/#files |
| psutil 7.2.2 | https://pypi.org/project/psutil/7.2.2/#files |
| veraPDF 1.28.2 | https://github.com/veraPDF/veraPDF-apps/tree/v1.28.2 |
| Temurin / OpenJDK 21 | https://github.com/adoptium/temurin21-binaries/releases and https://github.com/adoptium/jdk21u |
| English OCR data 4.1.0 | https://github.com/tesseract-ocr/tessdata_fast/tree/4.1.0 |
| Noto fonts | https://github.com/notofonts/noto-fonts |
| PyInstaller 6.22.3 | https://pypi.org/project/pyinstaller/6.22.3/#files |

Exact downloaded resource URLs and checksums are recorded in `dependencies.lock.json`. Python packages are pinned in `requirements.txt` and `requirements-dev.txt`. Keep the exact source revisions, submodules, build materials, and notices applicable to any native components you distribute.

## Before distributing a rebuilt executable

A general upstream project link is not, by itself, a declaration that every corresponding-source obligation has been fulfilled. Distributors must provide the exact corresponding source and required build materials for their actual covered binaries through a method permitted by each applicable license. Preserve the Qt replacement/rebuilding rights and third-party notices. Retain the JRE legal directory and wheel-provided component notices. Review native transitive dependencies as well as Python wrappers.

No prebuilt Windows executable accompanies this initial public source repository. The local executable test record is retained as development evidence. Public binary packaging needs its own matching dependency-source distribution review.
