# Third-party notices

Application source is licensed under GNU AGPL version 3 or later; see LICENSE. Distributed builds must retain applicable notices and provide the corresponding source and build materials required by their licenses. This package contains the complete application source. It does not assume a commercial PyMuPDF license. No trial watermark is used.

| Component | Version | License / source |
|---|---|---|
| Python | 3.12 macOS tests / 3.13.15 Windows build | PSF and included notices; https://github.com/python/cpython |
| PySide6 Essentials / Shiboken / Qt | 6.11.2 | LGPL-3.0 / GPL options and Qt component notices; https://code.qt.io/pyside/pyside-setup.git/ and https://code.qt.io/qt/qtbase.git/ |
| PyMuPDF / MuPDF | 1.28.2 wrapper, bundled native build | AGPL-3.0-or-later; https://github.com/pymupdf/PyMuPDF and https://mupdf.com/licensing/ |
| pikepdf / QPDF | 10.13.0.post1 wrapper | MPL-2.0; QPDF Apache-2.0 and bundled native-library notices; https://github.com/pikepdf/pikepdf |
| Pillow | 12.3.0 | HPND and included component notices; https://github.com/python-pillow/Pillow |
| psutil | 7.2.2 | BSD-3-Clause; https://github.com/giampaolo/psutil |
| lxml | 6.1.3 local test snapshot | BSD and libxml2/libxslt notices; https://github.com/lxml/lxml |
| veraPDF | 1.28.2 | GPL-3.0-or-later / MPL-2.0 options; https://github.com/veraPDF/veraPDF-apps/tree/v1.28.2 |
| Eclipse Temurin / OpenJDK JRE | Exact Windows asset in dependencies.lock.json | GPL-2.0 with Classpath Exception and included legal notices; https://github.com/adoptium/temurin21-binaries |
| Tesseract / Leptonica OCR | Native components bundled by MuPDF | Apache-2.0 / BSD-style component terms; https://github.com/tesseract-ocr/tesseract and https://github.com/DanBloomberg/leptonica |
| English tessdata_fast | 4.1.0 | Apache-2.0; https://github.com/tesseract-ocr/tessdata_fast/tree/4.1.0 |
| Noto Sans | Commit pinned in dependencies.lock.json | SIL Open Font License 1.1; https://github.com/notofonts/noto-fonts |
| PyInstaller | 6.22.3, build-time | GPL-2.0-or-later with bootloader exception; https://github.com/pyinstaller/pyinstaller |

Full copied license texts and wheel-provided notices are under `resources/licenses`. Windows builds copy wheel notices again for their platform and preserve the JRE's legal directory. The veraPDF executable JAR retains its embedded third-party license and notice resources. Test/build packages have their own copied notices in that directory.

Qt dynamic libraries remain bundled as separate libraries during runtime extraction. The complete source, spec, pinned requirements and build script permit rebuilding with a compatible modified Qt/PySide distribution. Do not prohibit reverse engineering needed for debugging modified LGPL libraries. An end-user's ordinary use does not require buying a commercial Qt or MuPDF license; redistributors must comply with the applicable open-source terms.

Before public distribution of a Windows binary, complete the Windows build's notice collection and retain the source package and upstream corresponding-source access for the exact bundled versions. This notice is not a certified licensing audit. Consult the test record for the release verification status.
