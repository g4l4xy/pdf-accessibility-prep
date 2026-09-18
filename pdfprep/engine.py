# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
import re
import shutil
import uuid
import pikepdf as q
import pymupdf as fitz
from .model import sha256
from . import structure, validation


class NeedsInput(Exception):
    def __init__(self, kind, message):
        self.kind, self.message = kind, message


def metadata(pdf, title, language, retain_claims=False):
    if not title.strip(): raise ValueError('A document title is required')
    if not re.fullmatch(r'[a-zA-Z]{2,8}(-[a-zA-Z0-9]{1,8})*', language):
        raise ValueError('Use a language code such as en, en-US, or es')
    pdf.docinfo['/Title'] = title.strip()
    pdf.Root.Lang = language
    if '/ViewerPreferences' not in pdf.Root:
        pdf.Root.ViewerPreferences = q.Dictionary()
    pdf.Root.ViewerPreferences.DisplayDocTitle = True
    with pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=False) as meta:
        meta['dc:title'] = title.strip()
        meta['dc:language'] = [language]
        # A derivative is not entitled to inherit a conformance assertion.
        for key in list(meta.keys()):
            if not retain_claims and ('pdfua' in key.lower() or 'pdfa/ns/id' in key.lower()):
                del meta[key]


def render_and_compare(source, output, directory, password='', emit=lambda *a: None, check_text=True):
    pages = []
    with fitz.open(source) as original, fitz.open(output) as prepared:
        if original.needs_pass and not original.authenticate(password):
            raise ValueError('Source password no longer works')
        if len(original) != len(prepared): raise ValueError('Page count changed; prepared copy rejected')
        for i, (a, b) in enumerate(zip(original, prepared)):
            emit('Checking the prepared file', i + 1, len(original))
            boxes_a = (tuple(a.mediabox), tuple(a.cropbox), tuple(a.trimbox), tuple(a.bleedbox), tuple(a.artbox), tuple(a.rect), a.rotation)
            boxes_b = (tuple(b.mediabox), tuple(b.cropbox), tuple(b.trimbox), tuple(b.bleedbox), tuple(b.artbox), tuple(b.rect), b.rotation)
            if boxes_a != boxes_b: raise ValueError(f'Page {i + 1} size or rotation changed')
            unit_a = original.xref_get_key(a.xref, 'UserUnit')
            unit_b = prepared.xref_get_key(b.xref, 'UserUnit')
            if unit_a != unit_b: raise ValueError(f'Page {i + 1} drawing scale (UserUnit) changed')
            # Compare the actual vector paths, line weights, colors, dashes and
            # opacity in addition to the rendered page. Exclude stream positions
            # because adding invisible OCR can shift sequence numbers.
            def paths(page):
                return [{k: v for k, v in d.items() if k not in ('seqno',)} for d in page.get_drawings()]
            vectors = paths(a)
            if vectors != paths(b): raise ValueError(f'Page {i + 1} vector geometry or line style changed')
            scale = min(1.5, 1800 / max(a.rect.width, a.rect.height))
            pa = a.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            pb = b.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            import hashlib
            ha, hb = hashlib.sha256(pa.samples).hexdigest(), hashlib.sha256(pb.samples).hexdigest()
            if ha != hb: raise ValueError(f'Page {i + 1} appearance changed; copy rejected')
            # Preserve source text and semantic navigation. OCR may add more text.
            source_text = a.get_text()
            output_text = b.get_text()
            if check_text and source_text and source_text not in output_text:
                raise ValueError(f'Page {i + 1} source text changed; copy rejected')
            pa.save(str(directory / f'page-{i + 1}.png'))
            pages.append({'page': i + 1, 'width': a.rect.width, 'height': a.rect.height,
                          'rotation': a.rotation, 'user_unit': unit_a[1], 'vector_paths': len(vectors),
                          'vector_geometry_and_styles_preserved': True, 'page_boxes_preserved': True, 'source_render_sha256': ha,
                          'prepared_render_sha256': hb, 'appearance': 'identical at comparison resolution'})
        if original.get_toc() != prepared.get_toc():
            raise ValueError('Bookmarks changed; copy rejected')
    return pages


def add_ocr(source, destination, issue, fixes, emit):
    data = validation.resources() / 'tessdata'
    font = validation.resources() / 'NotoSans-Regular.ttf'
    changed = False
    with fitz.open(source) as doc:
        for i, page in enumerate(doc):
            if not page.get_images() and page.get_text().strip(): continue
            if not page.get_images():
                if not page.get_text().strip() and not page.get_drawings():
                    issue('empty', i + 1, 'This page has no extractable text or raster images. Check whether it is blank or contains outlined text or vector artwork.', False)
                continue
            # Partial OCR does not recreate an existing text layer. It covers images
            # on mixed pages as well as full scanned pages.
            if not (data / 'eng.traineddata').exists() or not font.exists():
                issue('ocr_missing', i + 1, 'Local English recognition data or its font is missing. Obtain a complete application build or add text in the source document.', False)
                continue
            # A pre-existing text layer over an image could already represent a scan.
            # Skip to avoid duplicating announcements; human review remains required.
            if len(page.get_text().strip()) >= 20 and any(
                    fitz.Rect(img['bbox']).get_area() > page.rect.get_area() * .7
                    for img in page.get_image_info()):
                issue('ocr_existing', i + 1, 'A large image already has a text layer. It was preserved to avoid duplicate text; check its accuracy and completeness.', True)
                continue
            emit('Recognizing scanned text', i + 1, len(doc))
            tp = page.get_textpage_ocr(language='eng', dpi=200, full=False, tessdata=str(data))
            content = page.get_text('dict', textpage=tp)
            inserted = 0
            for block in content['blocks']:
                for line in block.get('lines', []):
                    if tuple(line.get('dir', (1, 0))) != (1.0, 0.0):
                        issue('rotated_ocr', i + 1, 'Rotated recognized text needs correction in a specialist editor; it was not inserted.', False)
                        continue
                    for span in line.get('spans', []):
                        if 'GlyphLessFont' not in span.get('font', ''): continue
                        text = span.get('text', '').strip()
                        if not text: continue
                        page.insert_text(span['origin'], text, fontsize=max(3, span['size']),
                                         fontname='PrepOCR', fontfile=str(font), render_mode=3,
                                         overlay=True)
                        inserted += 1
            if inserted:
                issue('ocr', i + 1, 'Text was recognized from an image. Check the words, numbers and symbols against the original; OCR cannot guarantee their accuracy.', True)
                changed = True
                fixes.append(f'Page {i + 1}: added {inserted} invisible English OCR text spans without replacing the page image.')
            elif not page.get_text().strip() and any(fitz.Rect(img['bbox']).get_area() > page.rect.get_area() * .7 for img in page.get_image_info()):
                issue('ocr_empty', i + 1, 'No reliable additional text was recognized. Check the image or obtain a clearer original.', False)
        if changed:
            doc.save(destination, garbage=0, deflate=False)
    return changed


def prepare(source, directory, options=None, emit=lambda *a: None):
    options = options or {}
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    source = Path(source)
    snapshot = directory / 'original.pdf'
    shutil.copyfile(source, snapshot)
    source_hash = sha256(snapshot)
    if source_hash != sha256(source): raise ValueError('The input changed while it was being read. Add it again.')
    password = options.get('password', '')
    issues, fixes = [], []
    def issue(kind, page, message, reviewable):
        key = f'{kind}:{page or 0}'
        if not any(v['id'] == key for v in issues):
            issues.append({'id': key, 'kind': kind, 'page': page, 'message': message,
                           'reviewable': reviewable, 'reviewed': False})
    emit('Reading your PDF', 0, 0)
    try:
        pdf = q.open(snapshot, password=password, attempt_recovery=False)
    except q.PasswordError:
        raise NeedsInput('password', 'This PDF needs its authorized password. The other files will continue.')
    with pdf:
        if pdf.is_encrypted and not pdf.owner_password_matched and (not pdf.allow.modify_other or not pdf.allow.extract):
            raise NeedsInput('password', 'This PDF restricts modification or extraction. Provide its authorized owner password or obtain an unrestricted copy from the owner.')
        if not len(pdf.pages): raise ValueError('This PDF has no pages')
        if len(pdf.pages) > 2000: raise ValueError('This PDF exceeds the 2,000-page safety limit. Split it at the source.')
        signed = any(isinstance(o, q.Dictionary) and
                     (str(o.get('/Type', '')) == '/Sig' or '/ByteRange' in o) for o in pdf.objects)
        if signed and not options.get('signature_consent'):
            raise NeedsInput('signature', 'This PDF contains a digital signature. Preparing a derivative can invalidate it. The original will remain unchanged.')
        if signed:
            issue('signature', None, 'This derivative is not an authenticated signed original. Retain the original and obtain a new signature if required.', False)
        for obj in pdf.objects:
            if isinstance(obj, q.Dictionary) and (str(obj.get('/S', '')) in ('/JavaScript', '/Launch', '/SubmitForm') or '/JS' in obj):
                issue('active_content', None, 'Embedded active content was not executed. Remove or assess it with the document owner before distribution.', False)
        existing = '/StructTreeRoot' in pdf.Root
        title = str(pdf.docinfo.get('/Title', '')).strip() or source.stem.replace('_', ' ')
        lang = str(pdf.Root.get('/Lang', '')).strip() or options.get('default_language', 'en')
        metadata(pdf, options.get('title', title), options.get('language', lang), retain_claims=existing)
        title, lang = str(pdf.docinfo.Title), str(pdf.Root.Lang)
        issue('metadata', None, 'Confirm the document title and language below.', True)
        if '/OCProperties' in pdf.Root:
            issue('layers', None, 'Drawing layers were preserved. Check the default view, hidden information, print visibility, and whether the description covers each meaningful layer. Layer settings can vary between PDF viewers.', True)
        if '/AcroForm' in pdf.Root:
            issue('forms', None, 'Form fields were preserved. Have an accessibility specialist check field names, instructions, focus order, and behavior.', False)
        base = directory / 'base.pdf'
        pdf.save(base, compress_streams=False, object_stream_mode=q.ObjectStreamMode.preserve)
    work = base
    ocr = directory / 'ocr.pdf'
    if not existing and add_ocr(base, ocr, issue, fixes, emit): work = ocr
    layout_uncertain = set()
    with fitz.open(work) as view:
        page_text = [[l for l in p.get_text().splitlines() if l.strip()] for p in view]
        for i, page in enumerate(view):
            if not simple_text_layout(page): layout_uncertain.add(i + 1)
            if page.get_drawings():
                issue('graphics', i + 1, 'Check drawing geometry and labels. Describe meaningful vector graphics in the Figure description: object, view, dimensions and units, holes, hidden lines, and relationships. Verify diameter, radius, angle, tolerance and scale symbols against the original. Tables need table structure; equations or pre-tagged or unsupported nested CAD artwork need source or specialist remediation.', True)
            if page.get_links():
                issue('links', i + 1, 'Links were preserved. Check link text, keyboard access, and link annotations with a specialist.', False)
            if '\ufffd' in page.get_text():
                issue('unicode', i + 1, 'Some characters cannot be mapped reliably. Repair fonts or text in the source document.', False)
            for font_info in page.get_fonts(full=True):
                try:
                    if not view.extract_font(font_info[0])[3]:
                        issue('fonts', i + 1, 'At least one source font is not embedded. Export with embedded fonts from the source when licensing permits.', False)
                except Exception:
                    issue('fonts', i + 1, 'Font embedding could not be confirmed. Check the source export.', False)
    emit('Organizing reading order', 0, 0)
    output = directory / 'prepared.pdf'
    with q.open(work) as pdf:
        if existing:
            model = structure.existing_model(pdf)
            fixes.append('Preserved the existing structure tree and page content associations.')
            for i in range(len(pdf.pages)):
                issue('reading', i + 1, 'Check the existing reading order and headings against the page. Complex tree corrections require a specialist.', True)
                if not page_text[i]:
                    issue('existing_scan', i + 1, 'This tagged page has no extractable text. Its existing structure was preserved; assess whether OCR or other remediation is needed.', False)
        else:
            model = structure.build(pdf, page_text, issue)
            fixes.append('Associated supported text, raster images, vector painting operators, and untagged nested artwork with MCIDs, structure elements, and a ParentTree. Complex reading roles may still need human review.')
        pdf.save(output, compress_streams=False, object_stream_mode=q.ObjectStreamMode.preserve)
    # Reopen to obtain final object numbers after writer renumbering.
    with q.open(output) as pdf:
        final_model = structure.existing_model(pdf)
    for m, old in zip(final_model, model): m['label'] = old['label']
    for page_num, lines in enumerate(page_text, 1):
        text_items = [m for m in final_model if m['page'] == page_num and m['kind'] == 'text']
        if len(text_items) == len(lines):
            for m, line in zip(text_items, lines): m['label'] = line[:200]
    for figure in final_model:
        if figure['kind'] == 'figure' and not figure.get('alt', '').strip():
            issue('figures', figure['page'], 'A picture or drawing is missing its description. Explain what it shows; the app cannot safely invent its meaning or dimensions.', True)
    pages = render_and_compare(snapshot, output, directory, password, emit)
    validator = validation.validate(output, directory / 'validator.xml')
    compatibility = brightspace_check(output)
    issue('visual_accessibility', None, 'Check contrast, information conveyed by color, meaningful diagrams, equations, and completeness of descriptions. Automated tags do not establish WCAG compliance.', True)
    fixes.append('Set document title, language, and display-title metadata. Preserved page dimensions and page order.')
    result = {'schema': 1, 'source_name': source.name, 'source_sha256': source_hash,
              'sha256': sha256(output), 'output': str(output), 'directory': str(directory),
              'title': title, 'language': lang, 'page_count': len(pages), 'pages': pages,
              'elements': final_model, 'issues': issues, 'fixes': fixes, 'validator': validator,
              'brightspace': compatibility,
              'reviews': [], 'created_utc': datetime.now(timezone.utc).isoformat(),
              'limitations': ['Pixel comparison is at up to 108 dpi and 1,800 pixels on the longest side, not a proof of all rendering behavior.',
                              'WCAG 2.1 AA human evaluation and Brightspace viewer testing are separate from PDF/UA machine checks.',
                              'Automatic structure is per supported text-show operator. Complex hierarchy and semantic interpretation require review.']}
    classify_checks(result, existing=existing, uncertain_pages=layout_uncertain)
    refresh_status(result)
    (directory / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    for transient in (base, ocr): transient.unlink(missing_ok=True)
    return result



def brightspace_check(path):
    path = Path(path)
    with q.open(path, attempt_recovery=False) as pdf:
        checks = {'pdf_extension': path.suffix.lower() == '.pdf',
                  'opens_without_password': not pdf.is_encrypted,
                  'has_pages': bool(len(pdf.pages)),
                  'syntax_warnings': list(pdf.check_pdf_syntax())}
    return {'status': 'PDF format checks passed' if all(checks[k] for k in
            ('pdf_extension', 'opens_without_password', 'has_pages')) and not checks['syntax_warnings']
            else 'Review required', 'checks': checks, 'bytes': path.stat().st_size,
            'live_upload_tested': False,
            'scope': 'D2L supports PDF in course Content and its embedded viewer. Course upload limits, assignment extension restrictions, and permissions must be checked in your institution. Format acceptance does not certify accessibility.',
            'source': 'https://community.d2l.com/brightspace/kb/articles/23030-what-types-of-files-can-i-use-for-course-content'}

def simple_text_layout(page):
    """Recognize only a uniform, single-column, top-to-bottom text layout.

    This is a geometry check, not a claim that semantics or WCAG were verified.
    Ambiguous columns, rotated lines, mixed type sizes and multi-span lines stay
    explicit review items when building a new structure tree.
    """
    lines = [line for block in page.get_text('dict')['blocks']
             for line in block.get('lines', []) if any(s.get('text', '').strip() for s in line.get('spans', []))]
    if not lines: return True
    spans = [line['spans'] for line in lines]
    if any(len(v) != 1 for v in spans): return False
    if any(tuple(line.get('dir', (1, 0))) != (1.0, 0.0) for line in lines): return False
    if max(v[0]['size'] for v in spans) - min(v[0]['size'] for v in spans) > .5: return False
    if len({(v[0].get('font'), v[0].get('flags')) for v in spans}) > 1: return False
    left = [line['bbox'][0] for line in lines]
    if max(left) - min(left) > 5: return False
    return all(b['bbox'][1] >= a['bbox'][3] - 2 for a, b in zip(lines, lines[1:]))


def classify_checks(result, existing=False, uncertain_pages=()):
    """Keep general advice separate from a specific unresolved problem."""
    passed = result['validator']['status'] == 'passed'
    for issue in result['issues']:
        kind, page = issue['kind'], issue['page']
        required = True
        if kind in ('metadata', 'visual_accessibility', 'layers', 'empty'):
            required = False
        elif kind == 'reading':
            required = not existing and page in uncertain_pages
            if required:
                issue['message'] = 'This page has columns, mixed text styles, rotated text or an uncertain reading order. Check the order and headings; the app has preserved the content rather than guessed.'
        elif kind in ('graphics', 'figures', 'nested_drawing'):
            figures = [e for e in result['elements'] if e['page'] == page and e['kind'] == 'figure']
            required = any(not e.get('alt', '').strip() for e in figures) or (not existing and not figures)
        elif kind in ('forms', 'links') and existing and passed:
            required = False
        elif kind == 'existing_scan':
            figures = [e for e in result['elements'] if e['page'] == page and e['kind'] == 'figure']
            required = not (figures and all(e.get('alt', '').strip() for e in figures))
        issue['required'] = required
    result['automatic_checks'] = {
        'existing_structure_preserved': existing,
        'simple_layout_pages': [p['page'] for p in result['pages'] if p['page'] not in uncertain_pages],
        'note': 'General human checks are optional advice, not automatic accessibility certification.'}


def refresh_status(result):
    unresolved = [i for i in result['issues'] if i.get('required', True) and not i['reviewed']]
    passed = result['validator']['status'] == 'passed'
    compatible = result.get('brightspace', {}).get('status', 'PDF format checks passed') == 'PDF format checks passed'
    result['needs_attention'] = bool(unresolved or not passed or not compatible)
    if result['needs_attention']:
        result['status'] = 'Review needed — draft'
    else:
        result['status'] = 'Checks passed and review recorded' if result['reviews'] else 'Automatic checks passed'
    result['publication_ready'] = False  # This utility never certifies publication or legal compliance.


def review(result, edits, emit=lambda *a: None):
    # Transaction: old prepared output stays usable if correction or validation fails.
    result = json.loads(json.dumps(result))
    directory = Path(result['directory'])
    current = Path(result['output'])
    candidate = directory / f'review-{uuid.uuid4().hex}.pdf'
    try:
        old_elements = {tuple(e['object']): e for e in result['elements']}
        content_changed = any(e.get('decorative') or e.get('actual_text') is not None or
                              e.get('role', old_elements.get(tuple(e['object']), {}).get('role')) != old_elements.get(tuple(e['object']), {}).get('role') or
                              e.get('alt', '') != old_elements.get(tuple(e['object']), {}).get('alt', '')
                              for e in edits.get('elements', []))
        changed = (content_changed or edits.get('tables') or edits.get('lists') or
                   (edits.get('order') and edits['order'] != [e['object'] for e in result['elements']]) or
                   edits.get('title', result['title']) != result['title'] or
                   edits.get('language', result['language']) != result['language'])
        if not changed:
            shutil.copyfile(current, candidate)
        else:
            with q.open(current) as pdf:
                metadata(pdf, edits.get('title', result['title']), edits.get('language', result['language']))
                structure.apply(pdf, edits)
                pdf.save(candidate, compress_streams=False, object_stream_mode=q.ObjectStreamMode.preserve)
        # Compare with the previous known-identical prepared copy, avoiding storing
        # a source password after the initial job.
        pages = render_and_compare(current, candidate, directory, emit=emit, check_text=False)
        validator = validation.validate(candidate, directory / 'validator-review.xml')
        with q.open(candidate) as pdf:
            elements = structure.existing_model(pdf)
        # Candidate has been validated; save it immutably and update the pointer.
        result['output'] = str(candidate)
        result['sha256'] = sha256(candidate)
        result['validator'] = validator
        result['brightspace'] = brightspace_check(candidate)
        result['elements'] = elements
        result['title'] = edits.get('title', result['title'])
        result['language'] = edits.get('language', result['language'])
        reviewed = set(edits.get('reviewed', []))
        # Figure checks cannot be dismissed while meaningful figures lack descriptions.
        for i in result['issues']:
            if i['reviewable']:
                i['reviewed'] = False
            if i['reviewable'] and i['id'] in reviewed:
                if i['kind'] in ('figures', 'graphics', 'nested_drawing') and any(e['page'] == i['page'] and e['kind'] == 'figure' and not e['alt'].strip() for e in elements):
                    continue
                i['reviewed'] = True
        result['pages'] = pages
        result['reviews'].append({'recorded_utc': datetime.now(timezone.utc).isoformat(),
                                  'reviewed_items': [i['id'] for i in result['issues'] if i['reviewed']],
                                  'corrections': edits})
        result['fixes'].append('Applied recorded title, language, structure, or text corrections and revalidated the resulting PDF.')
        refresh_status(result)
        (directory / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return result
    except BaseException:
        candidate.unlink(missing_ok=True)
        raise
