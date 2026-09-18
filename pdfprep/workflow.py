# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plain-language explanations shared by the automatic-first desktop workflow."""

from .i18n import current_language, tr, issue_text

def needs_attention(result):
    return bool(result and (result['validator']['status'] != 'passed' or
        result.get('brightspace', {}).get('status', 'PDF format checks passed') != 'PDF format checks passed' or
        any(i.get('required', True) and not i['reviewed'] for i in result['issues'])))


def reasons(result):
    if current_language() != 'en':
        messages = list(dict.fromkeys(issue_text(i) for i in result['issues'] if i.get('required', True) and not i['reviewed']))
        if result['validator']['status'] != 'passed':
            messages.append(tr('The validation tool could not finish. See technical details.' if result['validator']['status'] == 'not performed' else 'The independent accessibility check did not pass. See the report.'))
        if result.get('brightspace', {}).get('status', 'PDF format checks passed') != 'PDF format checks passed':
            messages.append(tr('The independent accessibility check did not pass. See the report.'))
        return list(dict.fromkeys(messages))
    messages = []
    def add(message):
        if message not in messages: messages.append(message)
    labels = {
        'figures': 'A picture or drawing needs a written description.',
        'graphics': 'A drawing needs a description of its meaning, labels and dimensions.',
        'nested_drawing': 'A drawing needs a description of its meaning, labels and dimensions.',
        'reading': 'The page layout is too complex to safely decide the reading order or headings.',
        'ocr': 'Text was recognized from a scan; a person needs to check the words and numbers.',
        'ocr_existing': 'The scan already has a text layer. Its accuracy cannot be checked automatically.',
        'ocr_empty': 'The scan did not provide readable text. A clearer original may be needed.',
        'fonts': 'A font is missing from the PDF. Re-export it with embedded fonts; a checkbox cannot fix this.',
        'unicode': 'Some characters cannot be read reliably. The source text or fonts need repair.',
        'forms': 'Interactive form fields need specialist checking.',
        'links': 'Links need their accessible text and keyboard behavior checked.',
        'structure': 'Part of the PDF structure needs repair in the original document or a specialist editor.',
        'ocr_missing': 'The local text-recognition files are missing. A complete app build is needed.',
        'rotated_ocr': 'Rotated scanned text could not be added safely.',
        'existing_scan': 'A tagged page has no readable text. It may need OCR or a description.',
    }
    for issue in result['issues']:
        if issue.get('required', True) and not issue['reviewed']:
            kind = issue['kind']
            # One explanation for related drawing checks, not three copies.
            if kind in ('figures', 'graphics', 'nested_drawing'):
                add('A picture or drawing needs a written description, including important labels and dimensions.')
            else: add(labels.get(kind, issue['message']))
    validator = result['validator']
    if validator['status'] == 'not performed':
        add('The independent PDF check could not finish. ' + validator.get('reason', 'The validation tool did not return a usable result.'))
    elif validator['status'] != 'passed':
        failures = validator.get('failures', [])
        descriptions = ' '.join(f.get('description', '') for f in failures).lower()
        if 'pdfuaid' in descriptions or ('pdf/ua' in descriptions and ('identifier' in descriptions or 'identification' in descriptions)):
            add('The PDF is missing or has an invalid PDF/UA identification entry. The app does not add a certification claim automatically.')
        if 'font' in descriptions: add('The independent check found a font problem; it may need a new export from the original document.')
        if any(word in descriptions for word in ('structure', 'marked', 'tagged', 'structelem', 'parenttree')):
            add('The independent check found a tagging or document-structure problem.')
        if 'alt' in descriptions and not any('description' in m for m in messages):
            add('The independent check found missing or invalid alternative text.')
        if not failures: add('The independent accessibility check did not pass. Its report did not provide individual rule details.')
        elif not any(word in descriptions for word in ('pdfuaid', 'identifier', 'identification', 'font', 'structure', 'marked', 'tagged', 'structelem', 'parenttree', 'alt')):
            add('The independent accessibility check found a problem: ' + failures[0].get('description', 'See the saved report for details.'))
    if result.get('brightspace', {}).get('status', 'PDF format checks passed') != 'PDF format checks passed':
        add('The PDF format check found a problem. The saved report lists the details.')
    return messages


def explanation(item):
    if current_language() != 'en':
        if not item.result:
            message = {'Password needed':'This PDF is locked. Provide an authorized password.', 'Signature consent needed':'This PDF is signed. Permission is needed to create a changed copy.', 'Failed':'This PDF could not be prepared. Try a fresh export. Other PDFs can still be saved.'}.get(item.status, 'This PDF is waiting to be prepared.')
            return tr(message) + ('\n' + tr('Technical details (original language):') + '\n' + item.error if item.error else '')
        if not needs_attention(item.result): return tr('Automatic checks passed. You can save this PDF. This is not an accessibility certification.')
        return '\n'.join('• ' + m for m in reasons(item.result)) + '\n' + tr('Unresolved issues remain. You can save a draft; review cannot override failed validation.')
    if not item.result:
        if item.status == 'Password needed': return 'This PDF is locked. An authorized password is needed before it can be prepared.'
        if item.status == 'Signature consent needed': return 'This PDF is digitally signed. Your permission is needed before creating a changed copy.'
        if item.status == 'Failed':
            return 'This PDF could not be prepared. ' + item.error + '\nNo prepared copy was created. Try a fresh export or remove this file; the other PDFs can still be saved.'
        return 'This PDF is waiting to be prepared.' if item.status in ('Queued', 'Retry') else item.status
    if not needs_attention(item.result):
        return 'Automatic checks passed. You can save this PDF now. Manual review is optional; this is not an accessibility certification.'
    details = reasons(item.result)
    return '\n'.join('• ' + text for text in details) + '\nThe prepared copy can be saved as a draft. Manual review can add answers and corrections, but cannot override a failed check.'
