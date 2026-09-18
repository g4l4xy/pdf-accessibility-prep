# 📚 PDF Accessibility Prep

### More accessible course materials. More opportunity to learn.

**Prepare existing PDFs for screen-reader access and accessible delivery through Blackboard and Brightspace.**

PDF Accessibility Prep helps teachers, faculty, instructional designers, disability-services staff, and campus accessibility teams improve the PDFs their students use every day. Process a whole batch of syllabi, readings, worksheets, assignments, and student-support documents in one simple Windows application.

Built to support **ADA Title II accessibility compliance work in schools and colleges**, with automatic preparation, independent PDF checks, and clear explanations when a document needs human attention.

**Created and maintained by Eathan Huber · [g4l4xy](https://github.com/g4l4xy)**

Copyright © 2026 Eathan Huber. [Authorship and attribution](AUTHORS.md).

**[Get started](#-three-steps-from-course-files-to-prepared-pdfs)** · **[Title II and compliance](#-supporting-federal-title-ii-compliance)** · **[Blackboard and Brightspace](#-for-blackboard-and-brightspace)** · **[License](LICENSE)**

## 🎓 Built for the people who support students

A student should be able to read course information, follow its structure, and understand its images using the tools they rely on. A PDF that looks clear on screen can still lack the text and structure that assistive technology needs.

This app helps education teams address those barriers without handling every file as a separate project:

- **Faculty and teachers:** prepare multiple course documents in one session.
- **Instructional designers:** make PDF preparation a repeatable part of course development.
- **Disability-services and accessibility teams:** identify unresolved issues and retain a report for each document.
- **Schools and colleges:** keep document processing local and preserve the original course files.

## ⚖️ Supporting federal Title II compliance

The U.S. Department of Justice's ADA Title II web-accessibility rule establishes **WCAG 2.1 Level AA** as the technical standard for covered state and local government web content. Public schools, community colleges, and public universities are among the entities covered, and the rule's definition of web content includes documents. Institutions should consult DOJ guidance for applicable dates, exceptions, and obligations. [DOJ Title II fact sheet](https://www.ada.gov/resources/2024-03-08-web-rule/).

PDF Accessibility Prep supports the **document-remediation part of that compliance process**: making text available to assistive technology, adding supported document structure, preserving existing accessibility information, checking the prepared file, and identifying work that remains.

**A machine-check pass is not a certification of federal or state compliance.** The app checks PDF/UA-1 requirements with veraPDF; PDF/UA machine checks do not establish complete WCAG 2.1 AA or ADA conformance. Meaningful descriptions, correct reading order, contrast, complex content, and actual assistive-technology use can require human evaluation. The app does not assess every state's accessibility law or replace an institution's accessibility review.

## 🔎 What the app does—and why it helps

| Document need | What PDF Accessibility Prep does | Why it matters for students |
|---|---|---|
| Text in scanned pages | Adds an invisible English OCR text layer to supported scans while preserving the visible page. Flags text that needs accuracy checking. | Makes recognized words available for reading, searching, and assistive technology. |
| Document structure | Preserves an existing tag tree or adds tags and content associations for supported untagged content. | Gives compatible PDF readers information about the document's structure. |
| Reading order and headings | Checks for a simple text layout and flags uncertain layouts. Provides review tools for order and heading corrections. | Helps students follow the intended sequence and navigate appropriately structured content. |
| Pictures and illustrations | Identifies missing descriptions and lets a reviewer add meaningful alternative text. | Gives students information that cannot be conveyed by the image alone. |
| Titles and language | Preserves existing metadata, supplies a filename-based title when needed, and uses the selected language when the PDF has none. | Helps identify the document and provides language information for assistive technology. |
| Tables and lists | Preserves existing structure and offers correction tools for supported simple tables and lists. | Makes relationships and organization available beyond their visual appearance. |
| Verification and records | Runs independent PDF/UA-1 checks, checks page preservation, and saves an individual accessibility report. | Gives staff a clear record of completed work and remaining barriers. |

These capabilities address PDF accessibility techniques described by W3C, including [text alternatives](https://www.w3.org/WAI/WCAG21/Techniques/pdf/PDF1), [reading order](https://www.w3.org/WAI/WCAG21/Techniques/pdf/PDF3), and [OCR for scanned documents](https://www.w3.org/WAI/WCAG21/Techniques/pdf/PDF7). Results still depend on the source PDF, the corrections made, and the student's PDF reader and assistive technology.

## 🚀 Three steps from course files to prepared PDFs

1. **Add PDFs.** Select several files at once or drag them into the window. Add more, remove individual files, or clear the list before starting.
2. **Prepare PDFs.** The app processes each document separately, performs supported automatic fixes, and runs its checks. A damaged file does not stop the rest of the batch.
3. **Save prepared PDFs…** Choose one output folder. Save each available PDF and its accessibility report. The button shows how many PDFs will be saved.

Files stay separate. Original documents are not overwritten. Duplicate selections are skipped, and matching output names receive a numbered suffix.

For example, `Week_1_Reading.pdf` becomes `Week_1_Reading_prepared.pdf`, with a separate report beside it.

### Human review only when you choose it

A PDF that passes the automatic checks does not require a generic manual checklist before saving. If something remains unresolved, one message explains the problem and offers **Review now** or **Not now — keep drafts**. The rest of the batch continues normally.

Choose **Manual review…** whenever you want a closer look. The review view focuses on one question at a time, keeps answers when you move between files, and has a clear **Back to files** button. Missing descriptions, uncertain recognized text, or complex structures remain flagged until appropriately addressed. Failed validation cannot be changed to a pass by checking a box.

## 🏫 For Blackboard and Brightspace

The app produces ordinary `.pdf` files for your institution's course-content workflow. It checks that a prepared file can be opened, contains pages, has a PDF extension, and is not password-encrypted; it also records syntax warnings and file size.

| Learning platform | How prepared PDFs fit into your course |
|---|---|
| **Blackboard** | Upload the prepared PDF as course content. Blackboard documents PDF as a supported content type and provides file-viewing and download controls. [Blackboard file guidance](https://help.anthology.com/blackboard/instructor/en/course-and-content-management/add-content.html). |
| **Brightspace** | Add the prepared PDF to course Content using your institution's file-upload workflow. D2L lists PDF as supported course content and recommends PDF for non-HTML documents to avoid conversion. [Brightspace supported files](https://community.d2l.com/brightspace/kb/articles/23412-what-types-of-files-can-i-use-for-course-content). |

**The goal is accessible course PDFs in either platform.** Upload compatibility and accessibility are separate checks: neither platform makes a document compliant merely by accepting it. Review unresolved findings, follow your institution's publishing requirements, and verify the student's experience in the course viewer and downloaded PDF with the relevant assistive technology. D2L also recommends OCR for scanned course documents used with screen readers. [D2L accessible learning-material guidance](https://community.d2l.com/brightspace/kb/articles/4968-providing-alternative-learning-materials).

Compatibility guidance is based on official platform documentation and local file checks. No live Blackboard or Brightspace course upload is claimed. Institutional upload limits, permissions, viewers, and course settings can vary. The project is independent and is not endorsed or certified by either platform.

## 🔒 Local processing, useful records

Documents are processed on the computer running the app. No document upload to a project server, account, or API key is required for processing.

Each saved report identifies the source document, the preparation performed, the actual validation result, recorded corrections, and unresolved items. Drafts remain clearly identified. Reports support follow-up and institutional recordkeeping; they do not constitute an accessibility certificate. Store PDFs and reports according to your institution's privacy and retention requirements.

## ✅ Verification you can inspect

The automatic-first update passed **48 Windows regression tests**, **16 focused Windows UI tests**, and **15 checks inside the packaged Windows executable**. These runs include overlapping coverage; they are not a single combined test count.

Batch verification includes **1, 10, 50, and 100 PDFs**, duplicate filenames, damaged input, and checks that each successful output retains its own original page count and page order. Read the [test record](docs/TESTING.md), [coverage limits](docs/COVERAGE.md), and [automatic-workflow notes](docs/AUTOMATIC-WORKFLOW.md).

## 💻 Getting the Windows application

The portable application runs on Windows and bundles its normal PDF, OCR, and validation runtime components. This public repository currently provides the source, build instructions, and verification records; a prebuilt executable is not attached to a GitHub release here.

<details>
<summary><strong>For school and college IT teams: build the portable application</strong></summary>

Use Python **3.13.15 x64** on Windows. From the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
```

The script installs pinned dependencies, verifies resource downloads, runs tests, packages the app, and checks the executable. Build-time internet access is required unless inputs are cached. The output is `dist/PDF-Accessibility-Prep.exe`.

See [developer instructions](docs/DEVELOPER.md), [third-party notices](THIRD-PARTY-NOTICES.md), and [corresponding-source considerations](THIRD-PARTY-SOURCES.md) before redistributing a build.

</details>

## 🤝 Open source, with credit where it belongs

PDF Accessibility Prep is licensed under **GNU AGPL-3.0-or-later**. Use, modification, commercial use, and redistribution are permitted under the license's conditions. Preserve the applicable copyright and license notices, including **Eathan Huber's** credit for the original project.

Third-party distributions may not claim Eathan Huber's sponsorship or endorsement without written permission. See [AUTHORS.md](AUTHORS.md), [LICENSE](LICENSE), and the professional warranty and liability provisions in [TERMS.md](TERMS.md).

Have a suggestion that would make course preparation easier? [Open an issue](https://github.com/g4l4xy/pdf-accessibility-prep/issues). Use synthetic or fully redacted examples; do not post student records or confidential institutional documents. [Contribution guidelines](CONTRIBUTING.md) · [Security reporting](SECURITY.md).

---

**Help every student get to the learning—not just the file.**
