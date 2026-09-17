# Brightspace compatibility: documented file requirements

Documentation checked September 17, 2026. Scope follows the user's instruction to use D2L documentation, without signing in or uploading to an institution.

D2L lists PDF as supported course Content. It recommends PDF for non-HTML documents because its document conversion step is unnecessary for PDFs. The New Content Experience also lists PDF among embedded-viewer formats. The app saves ordinary separate `.pdf` files, with recognizable safe filenames, rather than an archive, merged document, or proprietary wrapper.

Sources:

- [D2L: What types of files can I use for course content?](https://community.d2l.com/brightspace/kb/articles/23030-what-types-of-files-can-i-use-for-course-content)
- [D2L: Add and organize learning materials in the New Content Experience](https://community.d2l.com/brightspace/kb/articles/5356-add-and-organize-learning-materials-in-the-new-content-experience)
- [D2L February 2026 release notes: restricted assignment extensions](https://community.d2l.com/brightspace/kb/articles/33623-february-2026-20-26-02)

Every prepared or reviewed file is checked locally for:

1. A `.pdf` extension and successful strict PDF parsing.
2. At least one page.
3. No output password encryption.
4. No warnings returned by QPDF's syntax check.
5. The exact output byte size, recorded in the per-file report.

These checks appear as **PDF format checks passed**, separately from accessibility validation and human review. Saved files must retain the validated SHA-256. A compatibility check does not turn a draft into a publication-ready file.

No universal institutional size cap is assumed. Course storage, upload size configuration, permissions, and assignment-specific allowed extensions can restrict otherwise valid PDFs. An assignment's file policy is separate from course Content format support. This app's 512 MB input limit is a local resource safeguard, not a D2L requirement. There is no evidence that every institutional configuration will accept every resulting file, so the app does not claim that.

The accompanying `_accessibility.html` is an individual report for the document owner. The prepared PDF is the course document. Keep original CAD/source files separately; the prepared PDF retains the original sheet layout and scale metadata. Viewer zoom or a print dialog's “fit” setting can still alter the displayed/printed size. For scale-dependent work, use the required print settings and verify a reference dimension.

No live Brightspace upload, course edit, student publication, browser-viewer interaction, or institutional accessibility audit was performed or requested for this update.
