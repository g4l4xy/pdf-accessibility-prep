# Developer notes

## Implementation choice

The brief preferred C#/.NET but allowed reasonable implementation decisions. This implementation uses Python 3.12 with Qt Widgets (PySide6 Essentials), pikepdf/QPDF, and PyMuPDF/MuPDF. It is a desktop application, not an Electron page or web upload service. PyInstaller packages the interpreter and native libraries. The tradeoff is a larger executable and copyleft redistribution obligations. This is an explicit deviation from the preferred native C# implementation.

No user-installed .NET, Java, Python, OCR application, Office, or Acrobat is intended to be required by the Windows artifact. That requires successful Windows packaging and the separate clean-machine test; it is not established merely by a PyInstaller flag.

The Windows executable was built inside a Parallels Windows 11 ARM64 VM using Python 3.13.15 x64 and the supplied build script. Its PE header is AMD64, and it runs under Windows x64 emulation in that VM. The GitHub workflow remains available for native Windows x64 build runners; no remote CI job was dispatched.

## Components

- `app.py`: one Qt window, queue and conditional review panel. Native dialogs are used for file/folder choices. QThread keeps processing and saving off the event loop.
- `model.py`: source-file identity and content hashing; separate state for queue status and saved output hash.
- `batch.py`: bounded serial scheduler and spawned worker process, per-file failure isolation, cancellation, timeout and RSS monitoring. Password values travel in process IPC, not arguments or routine logs.
- `engine.py`: source snapshot, inspection, consent/password handling, metadata, OCR, structure, visual comparison, independent validation, and transactional review candidate creation.
- `structure.py`: actual content BDC/EMC MCIDs, StructTreeRoot, StructElem, ParentTree, page references, selected role/Alt/ActualText edits, selected artifact conversion, sibling order, simple Table/TR/TH/TD and L/LI/LBody.
- `validation.py`: bundled Java classpath and veraPDF CLI, forced `ua1`, namespace-tolerant XML parser, conservative pass handling. No PDF/A fallback.
- `saving.py`: exclusive output-pair reservation, no-overwrite suffixes, saved hash check, separate escaped HTML reports, per-file save isolation.
- `selftest.py`: packaged runtime test that exercises actual frozen process spawning, English OCR, independent positive PDF/UA validation, corrupted-file continuation, and Save All.

Worker PDFs never invoke embedded JavaScript, attachments, or document URLs. The process is a crash/resource boundary, not a hostile-document OS sandbox. Keep native libraries updated and treat source PDFs as untrusted.

## Dependency versions

Both tested native stacks reported MuPDF 1.28.2 and QPDF 12.3.2; the versions are recorded here. Pinned direct Python dependencies: pikepdf 10.13.0.post1; PyMuPDF 1.28.2; PySide6 Essentials 6.11.2; psutil 7.2.2. Build/test: pytest 9.1.1; PyInstaller 6.22.3. The installed-transitive snapshot is included in `resources/python-dependencies.json`; Windows builds regenerate the platform snapshot.

Pinned resource versions and exact download hashes are in `dependencies.lock.json`: veraPDF 1.28.2, English tessdata_fast 4.1.0, a commit-pinned Noto Sans font, and a Windows x64 Eclipse Temurin 21 JRE release. Java on the macOS test host was Temurin 25.0.4.1 and was not bundled into the source archive. The Windows assembly downloads the pinned x64 JRE. Do not mistake the macOS test runtime for Windows validation evidence.

There is no commercial-license dependency or trial watermark. The application is AGPL-3.0-or-later; see root notices for redistribution terms. Runtime resource downloads do not occur. Only `scripts/build_resources.py` downloads build inputs; it fails on mismatched hashes.

## Reproducibility and packaging

`scripts/build.ps1` installs pinned direct packages, assembles verified resources, collects third-party notices, tests, builds one file, runs a frozen self-test, and records the executable hash. `.github/workflows/windows.yml` runs the script on Windows x64. Direct packages/resources are pinned; Python patch updates, transitive dependencies, runner images, PyInstaller hooks and code-signing timestamps can affect byte-for-byte builds. Bit-identical reproducibility is not claimed.

Windows testing exposed and fixed long-path cleanup of upstream installer reference files using extended Windows paths. The CLI validation profiles are embedded in the verified veraPDF JAR; optional extracted reference profiles are removed before packaging. The complete `resources` tree is explicitly listed in the PyInstaller spec. Java is invoked directly by bundled executable path and classpath; it does not rely on PATH or a separately installed Java. The executable's working directory need not be writable. PyInstaller extraction and document sessions use user temporary storage.

The frozen self-test must pass before an executable artifact is published. Clean Windows 11 with networking disabled, no developer tools/runtimes, standard-user/USB operation, screen readers, high contrast, and text scaling are separate manual gates. GitHub's build runner is not a clean-user-machine substitute.

## Verified official sources

Researched September 16–17, 2026. These sources define targets and informed the design; they are not evidence that arbitrary outputs conform.

- [DOJ Title II web rule fact sheet](https://www.ada.gov/resources/2024-03-08-web-rule/): WCAG 2.1 Level AA baseline for applicable public-entity web content, including documents. Do not substitute a PDF/UA check for WCAG evaluation or legal analysis.
- [DOJ first steps](https://www.ada.gov/resources/web-rule-first-steps/): inventory, remediation and institutional responsibilities. Consult the current official pages for applicability and deadlines; this app does not adjudicate exceptions.
- [W3C PDF1](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF1): meaningful image alternatives through Alt entries.
- [W3C PDF3](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF3): logical reading/tab order and human checking.
- [W3C PDF6](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF6): real table structure and header relationships.
- [W3C PDF7](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF7): OCR adds actual text and requires accuracy checks. These WCAG 2.2-hosted technique pages inform implementation; the requested legal target remains WCAG 2.1 AA.
- [D2L supported content files](https://community.d2l.com/brightspace/kb/articles/23030-what-types-of-files-can-i-use-for-course-content): PDF as course content.
- [D2L add and organize course content](https://community.d2l.com/brightspace/kb/articles/4983-add-and-organize-course-content): current Content upload/browse workflows; interfaces vary.
- [D2L PDF upload guidance](https://community.d2l.com/brightspace/discussion/6850/how-to-embed-a-pdf-file): Upload/Create → Upload Files route.
- [veraPDF](https://verapdf.org/home/) and [CLI validation documentation](https://docs.verapdf.org/cli/validation/): explicit PDF/UA profile selection, machine-readable actual results. Default validation can be PDF/A, so this app always supplies `--flavour ua1`.
- [veraPDF installation](https://docs.verapdf.org/install/) and [official installer template](https://github.com/veraPDF/veraPDF-apps/blob/v1.28.2/auto-install-tmp.xml): unattended build-time assembly.
- [Microsoft single-file deployment](https://learn.microsoft.com/en-us/dotnet/core/deploying/single-file/overview): reviewed as requested; it does not govern this Python/Qt implementation or prove resource bundling.
- [Qt/PyInstaller deployment](https://doc.qt.io/qtforpython-6/deployment/deployment-pyinstaller.html): the selected desktop packaging route.
- [pikepdf content streams](https://pikepdf.readthedocs.io/en/latest/api/filters.html): parsed content operators used for real tagging associations.
- [PyMuPDF OCR](https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html): integrated local Tesseract OCR and explicit trained data.

## Proof of tagging and independent validation

Before GUI acceptance testing, the engine generated real MCID/ParentTree associations in a small text fixture. veraPDF exposed a missing CIDToGIDMap in the fixture generator's embedded font. The fixture was corrected with the identity mapping known to its generator; no general font-map guess was added to production inputs. The corrected fixture and its prepared derivative both passed veraPDF 1.28.2's PDF/UA-1 profile. An untagged source derivative remained failed where required metadata/font conditions were unresolved.

Tests inspect associations independently with pikepdf and validate with veraPDF's separate implementation. Visual checks use MuPDF; a second rendering engine is not included in the production pipeline. Explicit limitations are in `COVERAGE.md`.
