# Language support

Version 0.3.0 includes English plus Spanish, French, German, Portuguese, Italian, Dutch, Polish, Arabic, Hindi, Simplified Chinese, and Japanese interface catalogs. Portuguese uses Brazilian wording. Chinese uses Simplified characters. Arabic uses right-to-left layout. These initial translations have not received a complete native-speaker linguistic review.

## Using a language

Choose **App language** at the top of the window, then close and reopen the application. The active session is not discarded or rebuilt when a preference changes. Unsaved copies still receive the normal close confirmation. The preference applies to the next launch. A supported system language is used on first launch; unsupported languages fall back to English.

The separate document-language menu uses stable language codes and never inherits the interface setting. Choose **Other language** in manual review to enter a language code that is not listed. This sets metadata, not translation or OCR recognition language. OCR is English-only. PDF content, filenames, user-written descriptions and diagnostic data are never automatically translated. Saved reports remain English. Native file dialogs may use the operating system language.

## Maintaining translations

UTF-8 JSON catalogs live in `pdfprep/locales`. `en.json` defines message keys and `aliases.json` maps longer English wording and equivalent accessibility labels to shared phrases. Every supported catalog must have every key. Preserve `{count}`, `{page}`, `{v0}`, `{v1}`, and `{v2}` placeholders exactly; their positions can change. Do not translate internal result codes, PDF structure role names, file paths, document text, or user input. RTL direction is explicit for Arabic; additional RTL languages must opt in when added.

The application loads catalogs locally. No translation API is called at runtime. `PDFPREP_UI_LANGUAGE` is a testing override. Unsupported or missing catalogs fall back to English. Source-level localization tests verify coverage and placeholders, all-language window construction and status formatting, separate document metadata, persistence, unchanged failure states, narrow-window layout, and non-Latin glyph coverage. Packaged tests check catalogs, display strings, and glyphs inside the executable. These tests do not certify translation quality or screen-reader usability in every language.

For improvements, open a pull request identifying the language, current phrase, proposed phrase, and reason. Prefer short, plain language suitable for people without technical training. Keep warnings about unresolved issues and accessibility certification intact.
