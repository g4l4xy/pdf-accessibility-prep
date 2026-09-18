# Automatic preparation and optional manual review

Version 0.2.0 puts the routine path first: **Add PDFs → Prepare PDFs → Save prepared PDFs…**. The final button shows the number of available PDFs; it opens one folder picker and saves separate PDF/report pairs. It does not download files from a server. Originals are preserved and matching output names receive a suffix.

## What happens automatically

The app performs supported metadata, text recognition, tagging, preservation, and independent validation work for each file. An existing tagged PDF that passes the checks can be saved without completing a generic human checklist. Titles and existing language tags are retained; missing titles use recognizable filenames and missing language uses the language selected in the main window.

General title/language confirmation and visual-accessibility advice remain available through **Manual review…**. These optional suggestions are not treated as failures, and the software does not invent human-review confirmations. A conservative uniform-text layout check distinguishes simple newly tagged text from ambiguous layouts; it does not claim to understand all semantics.

## If automatic preparation cannot finish everything

The batch continues through the other PDFs. Afterward, one in-window message explains the remaining problems and asks whether to review now. **Not now — keep drafts** dismisses it; selecting a file, refreshing the list, or saving does not ask again. Newly prepared files can produce a new notice on their next batch.

Missing picture descriptions, uncertain OCR, complex reading order, unsupported source structures, missing fonts, and failed or unavailable validation remain explicit. Existing described/tagged graphics do not require a new description merely because the page contains vector paths. A page with a picture does not automatically receive an OCR-accuracy question if no recognized text was added.

**Review now** presents required items only. **Manual review…** also makes optional checks available. Review uses the main window space and has a clear **Back to files** button. Saved answers are revalidated. Unapplied answers are retained when leaving the review and must be finished before saving; a report-only review change is offered for saving even when PDF bytes are unchanged.

## What a pass means

“Automatic checks passed” is a machine-check result, not a certification of WCAG compliance, the correctness of a drawing, or publication readiness. Failed or unavailable validation cannot be dismissed with a checkbox. The app does not add a PDF/UA conformance claim merely to suppress a validation failure. Drafts remain labeled in the queue and individual reports.
