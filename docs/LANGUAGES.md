# Language support

Version 0.3.1 includes English plus Spanish, French, German, Portuguese, Italian, Dutch, Polish, Arabic, Hindi, Simplified Chinese, and Japanese interface catalogs. Portuguese uses Brazilian wording. Chinese uses Simplified characters. Arabic uses right-to-left layout. These initial translations have not received a complete native-speaker linguistic review.

## Using a language

A fresh installation starts in **English**, regardless of the Windows language. Choose **App language** to switch immediately, including between right-to-left and left-to-right layouts. Queued files, prepared outputs, unsaved review answers, document-language choices, and the current session are preserved. The always-visible **English** button switches back immediately. Language controls are disabled while processing or saving to avoid rebuilding active worker controls.

Explicit choices are saved using a new preference key. Version 0.3.1 deliberately ignores the old 0.3.0 language setting so an unintended Arabic preference cannot carry into the corrected version. Normal packaged launches ignore developer language overrides. Tests use an isolated preference store and cannot write the user's language setting.

The separate document-language menu uses stable language codes and never inherits the interface setting. Choose **Other language** in manual review to enter a language code that is not listed. This sets metadata, not translation or OCR recognition language. OCR is English-only. PDF content, filenames, user-written descriptions and diagnostic data are never automatically translated. Saved reports remain English. Native file dialogs may use the operating system language.

## Maintaining translations

UTF-8 JSON catalogs live in `pdfprep/locales`. `en.json` defines message keys and `aliases.json` maps longer English wording and equivalent accessibility labels to shared phrases. Every supported catalog must have every key. Preserve `{count}`, `{page}`, `{v0}`, `{v1}`, and `{v2}` placeholders exactly; their positions can change. Do not translate internal result codes, PDF structure role names, file paths, document text, or user input. RTL direction is explicit for Arabic; additional RTL languages must opt in when added.

The application loads catalogs locally. No translation API is called at runtime. `PDFPREP_UI_LANGUAGE` is a testing override honored only in source runs and packaged self-tests. `PDFPREP_SETTINGS_FILE` isolates packaged self-test preferences. Unsupported or missing catalogs fall back to English. Source-level localization tests verify coverage and placeholders, all-language window construction and status formatting, separate document metadata, persistence, unchanged failure states, narrow-window layout, and non-Latin glyph coverage. Packaged tests check catalogs, display strings, and glyphs inside the executable. These tests do not certify translation quality or screen-reader usability in every language.

For improvements, open a pull request identifying the language, current phrase, proposed phrase, and reason. Prefer short, plain language suitable for people without technical training. Keep warnings about unresolved issues and accessibility certification intact.
