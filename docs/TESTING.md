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
