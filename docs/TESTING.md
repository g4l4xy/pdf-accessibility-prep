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
