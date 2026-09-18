# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Offline interface catalogs. Document text and machine statuses are never translated."""
from functools import lru_cache
import json
import os
from pathlib import Path
from PySide6.QtCore import QLocale, QSettings

LANGUAGES = {'en':'English', 'es':'Español', 'fr':'Français', 'de':'Deutsch',
             'pt':'Português', 'it':'Italiano', 'nl':'Nederlands', 'pl':'Polski',
             'ar':'العربية', 'hi':'हिन्दी', 'zh':'简体中文', 'ja':'日本語'}
ROOT = Path(__file__).with_name('locales')
_active = None

@lru_cache(maxsize=16)
def catalog(code):
    try:
        return json.loads((ROOT / f'{code}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}

def current_language():
    global _active
    override = os.environ.get('PDFPREP_UI_LANGUAGE')
    if override is not None: return override if override in LANGUAGES else 'en'
    if _active is None:
        saved = QSettings('Eathan Huber', 'PDF Accessibility Prep').value('ui_language', '')
        code = saved or QLocale.system().name().split('_')[0]
        _active = code if code in LANGUAGES else 'en'
    return _active

def set_language(code, *, persist=False, activate=True):
    global _active
    if code not in LANGUAGES: code = 'en'
    if persist:
        settings = QSettings('Eathan Huber', 'PDF Accessibility Prep')
        settings.setValue('ui_language', code); settings.sync()
    if activate: _active = code

def tr(source, **values):
    code = current_language()
    key = catalog('aliases').get(source, source)
    translated = catalog(code).get(key, source) if code != 'en' else source
    # Keep intentional separators when equivalent labels share a catalog entry.
    if code != 'en':
        if source.startswith('\n\n'): translated = '\n\n' + translated
        elif source.startswith('\n'): translated = '\n' + translated
        elif source.startswith(' '): translated = ' ' + translated
        if source.endswith(' — '): translated += ' — '
        elif source.endswith('\n'): translated += '\n'
        elif source.endswith(' '): translated += ' '
        if source.startswith('1. '): translated = '1. ' + translated
        if source.startswith('2. '): translated = '2. ' + translated
        if source.startswith('3. '): translated = '3. ' + translated
    try: return translated.format(**values) if values else translated
    except (KeyError, ValueError): return source.format(**values) if values else source

def populate_languages(combo, other=False):
    for code, name in LANGUAGES.items(): combo.addItem(name, code)
    if other: combo.addItem(tr('Other language'), 'other')

ISSUES = {
    'metadata':'Check that the title is useful and the language matches the document.',
    'figures':'A picture or drawing needs a meaningful description.',
    'graphics':'A picture or drawing needs a meaningful description.',
    'nested_drawing':'A picture or drawing needs a meaningful description.',
    'pictures':'Describe what the image shows. Include important labels, dimensions and units.',
    'reading':'Check the reading order and headings. If unsure, leave this for later.',
    'ocr':'Check recognized text, including numbers, against the original.',
    'ocr_existing':'Check recognized text, including numbers, against the original.',
    'ocr_empty':'No readable text was found. A clearer source or specialist help is needed.',
    'existing_scan':'No readable text was found. A clearer source or specialist help is needed.',
    'fonts':'Fonts or characters need repair in the original document.',
    'unicode':'Fonts or characters need repair in the original document.',
    'forms':'Forms or links need specialist accessibility review.',
    'links':'Forms or links need specialist accessibility review.',
    'structure':'Document structure needs repair in the source or a specialist editor.',
    'layers':'Check that all meaningful layers are visible and described.',
    'visual_accessibility':'Check readability, contrast, image descriptions and information conveyed by color.',
    'ocr_missing':'The OCR files are missing or this scan could not be processed safely.',
    'rotated_ocr':'The OCR files are missing or this scan could not be processed safely.',
    'signature':'This signed copy or embedded active content needs specialist review.',
    'active_content':'This signed copy or embedded active content needs specialist review.',
}

def issue_text(issue):
    if current_language() == 'en' or issue['kind'] == 'validation_summary': return issue['message']
    return tr(ISSUES.get(issue['kind'], 'Check this page. Empty or unsupported content may need specialist review.'))

def localize_message(message):
    """Known worker messages only; external diagnostics retain their original text."""
    if current_language() == 'en': return message
    if message in catalog('en') or message in catalog('aliases'): return tr(message)
    return tr('Technical details (original language):') + '\n' + message
