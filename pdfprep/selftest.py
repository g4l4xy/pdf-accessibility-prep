# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Packaged integration test: no installed Java, OCR, or Python may be required."""
from pathlib import Path
import json
import sys
import tempfile
import threading
from .fixtures import accessible_pdf, scan_pdf, text_pdf, drawing_pdf
from .model import Queue, sha256
from .batch import run_batch
from .engine import review, prepare
from .saving import save_all
from .validation import validate, resources


def main():
    report_path = Path(sys.argv[sys.argv.index('--report') + 1]) if '--report' in sys.argv else Path(tempfile.gettempdir()) / 'pdf-prep-self-test.json'
    checks = {}; failure = None; outcomes = []
    try:
        with tempfile.TemporaryDirectory(prefix='pdf-prep-self-test-') as temp:
            root = Path(temp)
            accessible = accessible_pdf(root / 'tagged.pdf')
            checks['independent_ua1_fixture'] = validate(accessible, root / 'source.xml')['status'] == 'passed'
            scan = scan_pdf(root / 'scan.pdf', mixed=True)
            text = text_pdf(root / 'five.pdf', pages=5)
            bad = root / 'damaged.pdf'; bad.write_bytes(b'%PDF-1.7\ndamaged')
            queue = Queue(); queue.add([accessible, scan, bad, text, text])
            checks['selection_deduplication'] = len(queue.items) == 4
            run_batch(queue.items, root / 'work', threading.Event())
            checks['isolated_workers_and_failure_continuation'] = [bool(i.result) for i in queue.items] == [True, True, False, True]
            outcomes = [{'fixture': Path(i.source).name, 'status': i.status, 'error': i.error} for i in queue.items]
            first, scanned, _, five = queue.items
            checks['valid_existing_preserved'] = bool(first.result and first.result['validator']['status'] == 'passed')
            if first.result:
                reviewed = review(first.result, {'reviewed': [i['id'] for i in first.result['issues'] if i['reviewable']]})
                checks['review_revalidates_actual_final'] = reviewed['validator']['status'] == 'passed' and reviewed['status'] == 'Checks passed and review recorded'
            checks['bundled_english_ocr'] = bool(scanned.result and any('invisible English OCR' in f for f in scanned.result['fixes']))
            checks['page_preservation'] = bool(five.result and five.result['page_count'] == 5 and all(p['source_render_sha256'] == p['prepared_render_sha256'] for p in five.result['pages']))
            drawing = prepare(drawing_pdf(root / 'isometric.pdf'), root / 'drawing-work')
            figures = [e for e in drawing['elements'] if e['kind'] == 'figure']
            described = review(drawing, {'elements': [dict(e, alt='Synthetic isometric block: dimensions and features require instructor verification.') for e in figures]})
            checks['isometric_vector_preservation_and_description'] = len(figures) == 2 and all(p['vector_paths'] > 0 and p['vector_geometry_and_styles_preserved'] for p in described['pages']) and all(e['alt'] for e in described['elements'] if e['kind'] == 'figure')
            nested = prepare(drawing_pdf(root / 'nested-cad.pdf', nested=True), root / 'nested-work')
            checks['nested_cad_preserved_and_tagged'] = len([e for e in nested['elements'] if e['kind'] == 'figure']) == 2 and not any(i['kind'] == 'structure' for i in nested['issues']) and all(p['vector_geometry_and_styles_preserved'] for p in nested['pages'])
            checks['brightspace_documented_pdf_format'] = described['brightspace']['status'] == 'PDF format checks passed'
            output = root / 'output'; output.mkdir()
            saved, failed = save_all(queue.items, output)
            checks['save_all_pdf_and_report'] = len(saved) == 3 and not failed and all(Path(p).exists() for _, paths in saved for p in paths)
    except Exception as ex:
        failure = type(ex).__name__ + ': ' + str(ex)
    result = {'passed': bool(checks) and all(checks.values()) and failure is None, 'checks': checks,
              'failure': failure, 'fixture_outcomes': outcomes, 'platform': sys.platform, 'frozen': bool(getattr(sys, 'frozen', False)),
              'network_disabled_by_test': False,
              'executable_sha256': sha256(Path(sys.executable)) if getattr(sys, 'frozen', False) else None,
              'note': 'This self-test does not replace clean-Windows offline or screen-reader acceptance testing.'}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['passed'] else 1
