# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plain-language explanations shared by the automatic-first desktop workflow."""

from .i18n import current_language, tr, issue_text

def needs_attention(result):
    return bool(result and (result['validator']['status'] != 'passed' or
        result.get('brightspace', {}).get('status', 'PDF format checks passed') != 'PDF format checks passed' or
        any(i.get('required', True) and not i['reviewed'] for i in result['issues'])))


def reasons(result):
    """Actionable prompts; technical validator rules belong in the report."""
    messages = []
    kinds = {i['kind'] for i in result['issues'] if i.get('required', True) and not i['reviewed']}
    def add(message):
        value = tr(message)
        if value not in messages: messages.append(value)
    if kinds & {'figures', 'graphics', 'nested_drawing'}:
        add('Describe the drawing: open review, look at the page, and explain what a student needs to understand.')
    if 'reading' in kinds:
        add('Check the reading sequence: review shows the numbered items and lets you move them up or down.')
    if kinds & {'ocr', 'ocr_existing'}:
        add('Check the scanned words and numbers against the page preview.')
    other = kinds - {'figures', 'graphics', 'nested_drawing', 'reading', 'ocr', 'ocr_existing'}
    for issue in result['issues']:
        if issue['kind'] in other and issue.get('required', True) and not issue['reviewed']:
            if issue.get('reviewable', False): add(issue_text(issue))
    technical = technical_help(result)
    if technical: messages.append(technical)
    return messages


def technical_help(result):
    """Separate questions the teacher can answer from repairs outside this editor."""
    validator = result['validator']
    if validator['status'] == 'not performed':
        return tr('The independent PDF check could not finish. Download the complete app and prepare the PDF again.') + ' ' + validator.get('reason', '')
    failures = validator.get('failures', [])
    # Missing alternative text is addressed by the picture question, not a second
    # misleading "structure" warning. Identification is still a failed rule and
    # is retained in the report and draft status; it is never checked away.
    pending_picture = any(i.get('required', True) and not i['reviewed'] and i['kind'] in ('figures', 'graphics', 'nested_drawing') for i in result['issues'])
    remaining = [f for f in failures if not (pending_picture and f.get('clause') == '7.3')]
    substantive = [f for f in remaining if f.get('clause') != '5']
    blocked = any(i.get('required', True) and not i['reviewed'] and not i.get('reviewable', False) for i in result['issues'])
    if substantive or blocked or (validator['status'] != 'passed' and not failures):
        desc = ' '.join(f.get('description', '') for f in substantive).lower()
        if 'font' in desc or any(i['kind'] in ('fonts', 'unicode') and i.get('required', True) and not i['reviewed'] for i in result['issues']):
            return tr('A font still needs repair. Export a new PDF from the original file with fonts embedded, then add it here again. If you cannot, save the draft and report for your accessibility office.')
        return tr('This PDF needs help from your school’s accessibility office. Save the PDF and help report, then give both to the office. The report explains what needs fixing. Your copy will be marked as a draft.')
    if any(f.get('clause') == '5' for f in remaining):
        return tr('This PDF needs help from your school’s accessibility office. Save the PDF and help report, then give both to the office. The report explains what needs fixing. Your copy will be marked as a draft.')
    if result.get('brightspace', {}).get('status', 'PDF format checks passed') != 'PDF format checks passed':
        return tr('The PDF format check did not pass. Save the report for your accessibility office and try a fresh export from the original file.')
    return ''


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
    return '\n\n'.join(details) + '\n\nChoose Review now for step-by-step help, or save a draft to finish later.'
