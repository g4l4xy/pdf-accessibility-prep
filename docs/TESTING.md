# Public test record

These are recorded local results, not a claim of universal PDF support or accessibility certification.

| Scope | Recorded result | Evidence |
|---|---|---|
| Drawing-build regression, including mixed batches of 1, 10, 50, and 100 PDFs | 32 tests passed | [JUnit](drawing-update-tests.xml) |
| Final guided-review checks on Windows | 5 tests passed | [JUnit](guided-final-targeted.xml) |
| Guided-review checks on macOS | 5 tests passed | [JUnit](guided-review-mac.xml) |
| Final packaged Windows executable checks | 11 checks passed | [Results](guided-final-packaged.json) |

Windows testing used Windows 11 ARM64 in Parallels with the x64 executable running under emulation. Batch checks exercised independent outputs, preservation of page count and page order, duplicate handling, and damaged-input isolation. Review tests cover the guided interface and preservation of pending answers.

The [executable manifest](executable-manifest.json) identifies the tested local executable. It is evidence for that build, not a claim that a newly rebuilt executable has an identical hash. Documentation and attribution were subsequently prepared for public distribution.

Earlier offline checks passed for the drawing build. The final guided-review executable was not separately retested offline. Native manual Windows interaction, screen-reader acceptance, and a pristine native-x64 Windows run remain unverified. Screenshots in this repository are actual Qt widgets rendered offscreen on macOS with synthetic documents.

Brightspace compatibility was checked against official documentation and local PDF checks. No institutional Brightspace upload was performed. See [BRIGHTSPACE.md](BRIGHTSPACE.md).

The GitHub Actions workflow is available for manual execution. These local results do not assert a successful GitHub Actions run.


## Automatic-first update — version 0.2.0

The local portable artifact is **PDF-Accessibility-Prep-Automatic.exe**. Its exact hash is recorded in [the manifest](automatic-executable-manifest.json) and [the packaged test report](automatic-packaged.json). It is not attached as a public GitHub binary release.

- **48 macOS regression tests passed**, including batches of 1, 10, 50, and 100 PDFs, duplicate filenames, damaged inputs, page counts and page order: [results](automatic-full-mac.xml).
- **48 Windows regression tests passed** using real isolated workers in Parallels: [results](automatic-windows.xml).
- **16 final UI tests passed on macOS** and **16 on Windows** after the final behavior and font changes: [Mac](automatic-final-ui-mac.xml), [Windows](automatic-final-ui-windows.xml). These overlap with the regression tests and are not additional independent full-suite counts. The final label-only simplification was visually inspected separately.
- **15 checks passed in the packaged Windows EXE**, including frozen workers, OCR, independent validation, drawing preservation, separate PDF/report saving, automatic passes without forced review, draft retention, explicit review consent, and readable bundled interface font.

The required batch tests verify that every successful output retains its own page count and ordered page content. One damaged file does not stop the batch. The added UI checks verify that selecting a row never opens manual review, a declined notice stays dismissed, optional checks do not block a genuine machine pass, real failed/unavailable validation remains a draft, answers survive view changes, and report-only changes can be saved.

Windows screenshots in this update come from the actual Qt interface rendered offscreen in Windows 11 / Parallels with the bundled font. They were visually inspected; they are not a claim of a manual native walkthrough or screen-reader acceptance. The final font is deliberately loaded from the app's bundled Noto Sans resource to avoid unavailable platform-font fallbacks.

No new offline, pristine native-x64, screen-reader, or institutional Brightspace upload test is claimed. See [the workflow notes](AUTOMATIC-WORKFLOW.md) for the exact behavior and limits. Public source changed only in documentation/evidence after these checks, apart from the visually inspected final label simplification described above.


## Version 0.3.0 — translated interfaces

- Initial full local suite, before the final RTL selection fix: **92 passed** (`languages-local.xml`).
- Windows: **51 existing regression cases passed** in the full run, including batches of 1, 10, 50, and 100 PDFs, mixed fixtures, duplicates, damaged input, and page count/order checks. **69 final interface cases passed** (53 localization and 16 existing UI checks) in the final focused run (`languages-windows-final.xml`). Environment: Windows 11 ARM64 in Parallels using x64 emulation.
- The initial Windows run (`languages-windows-initial.xml`) exposed a test-harness error: the catalog source audit used the legacy Windows encoding instead of explicit UTF-8. The application already read catalogs as UTF-8. A subsequent visual review also found that Qt row selection could skip the first file in an RTL window. The app now sets the current cell explicitly; 12 additional tests verify that Review now opens the first file without a prior click. Final runs of all 53 localization cases plus 16 existing UI cases passed both locally and on Windows (`languages-local-final.xml`, `languages-windows-final.xml`). The 51 regression plus 53 localization cases represent 104 distinct passing cases across these runs, not a single final full-suite run.
- Packaged executable: **18 checks passed**, including complete language catalogs, translated window construction with independent PDF language metadata, and interface glyph rendering (`languages-packaged.json`).
- Source and catalog hashes matched the Windows build (`languages-source-manifest.json`). Executable identity is in `languages-executable-manifest.json`.
- Source tests include **53 localization checks** across 12 languages. These overlap with the full suite; do not add their counts to claim distinct tests.
- Rendered Windows overview/review images were inspected for Arabic, Hindi, Japanese, and longer German labels. Arabic direction and non-Latin glyphs are covered automatically as well.
- No new offline test, native x64 hardware run, live LMS upload, full native-speaker review, or manual screen-reader acceptance is claimed. OCR remains English-only; reports and detailed validator diagnostics remain English.


## Version 0.3.1 — English startup, automatic identification, and simpler review

- A 126-test local suite passed (`hotfix-final-local.xml`), including mixed batches of 1, 10, 50, and 100 PDFs, duplicates, damaged-input continuation, individual page count/order, OCR, drawing preservation, saving, and review.
- After the final layout adjustments, 91 targeted interface/localization/repair tests passed locally and on Windows (`language-hotfix-local.xml`, `language-hotfix-windows.xml`). These overlap the full local suite. They verify fresh English startup despite a legacy Arabic preference and developer override, all-language live switching, persistence, English recovery, queue/review retention, real PDF reorder changes, readable label retention, automatic export repairs, and the help/save card without technical question steps.
- 23 checks passed inside the frozen Windows executable (`language-hotfix-packaged.json`), including independent validation, OCR, workers, separate saving, automatic font/layer repair, automatic PDF/UA identification, draft retention for unresolved descriptions, and live language recovery.
- A normal frozen launch displayed English despite an Arabic developer environment override, with an English recovery control (`language-hotfix-normal-launch.json`).
- A separate frozen self-test was observed on the interactive Windows desktop every 20 ms. No new visible ConsoleWindowClass or Windows Terminal windows were observed (`console-window-smoke.json`). Existing terminal windows were excluded. The validator now prefers the bundled windowless JVM and retains no-console process flags. Build/test commands also run without visible consoles. This check does not prove absence of every possible OS dialog or sub-20-ms event.
- The user-reported worksheet was checked privately. Its one-page count, rotation, 425 vector paths, and comparison render were preserved. Missing font-map, layer-configuration-name, and PDF/UA-identification failures cleared; the missing Figure description remained a failed check and draft. The private document and images are not in the repository. A synthetic worksheet also passed independent validation after its descriptions and review answers were supplied.
- Final Python/catalog hashes matched the Windows build (`language-hotfix-source-manifest.json`). Windows offscreen English, Arabic, and German review views were inspected; `simple-*.png` uses synthetic documents. Tests explicitly isolate preferences from the user's settings store.
- Windows environment: Windows 11 ARM64 in Parallels using x64 emulation. No new native-x64 hardware, offline, native-speaker approval, institutional LMS upload, or manual screen-reader acceptance test is claimed.
