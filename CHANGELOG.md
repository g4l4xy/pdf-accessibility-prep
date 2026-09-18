# Changes

## 0.3.0

- Add 12 offline interface languages, a saved language preference, and first-launch system-language selection with English fallback.
- Translate batch controls, progress, review guidance, and accessible labels while preserving document content and machine validation states.
- Add Arabic right-to-left layout, bundled non-Latin fonts, and stacked primary actions for narrow windows.
- Expand the separate PDF language menu; clearly distinguish metadata from interface translation and English-only OCR.
- Verify 92 local tests, 51 Windows regressions, 69 final Windows interface checks, and 18 packaged checks. Initial translations still welcome native-speaker review.


## 0.2.0 — Automatic preparation first

- Make generic metadata, visual, and supported reading-order checks optional instead of marking every PDF as needing manual review.
- Preserve mandatory attention for missing descriptions, uncertain OCR, ambiguous layouts, unsupported features, and failed or unavailable validation.
- Explain remaining problems once after the batch, with Review now and Not now choices; never open manual review merely by selecting a file.
- Replace vague saving labels with a count-aware Save prepared PDFs button and a clear explanation of the one-folder PDF/report save.
- Give manual review the main window space and a clear Back to files action; keep answers across mode changes.
- Offer updated reports for saving after report-only review changes.
- Load the bundled Noto Sans font for a consistent, readable interface.

## 0.1.0 — Initial public source

Local batch preparation, guided review, drawing preservation, independent validation, per-document reports, AGPL licensing, and Eathan Huber attribution.
