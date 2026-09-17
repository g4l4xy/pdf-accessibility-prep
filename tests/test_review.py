# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
import pytest
import pikepdf as q
from pdfprep.engine import prepare, review
from pdfprep.validation import command, validate
from pdfprep.fixtures import text_pdf, accessible_pdf, corpus


def test_independent_validation_preserves_true_pass(tmp_path):
    if not command(): pytest.skip('Independent validator requires bundled Java and veraPDF')
    src = accessible_pdf(tmp_path / 'accessible.pdf')
    assert validate(src, tmp_path / 'source.xml')['status'] == 'passed'
    r = prepare(src, tmp_path / 'work')
    assert r['validator']['status'] == 'passed'
    checked = review(r, {'reviewed': [i['id'] for i in r['issues'] if i['reviewable']]})
    assert checked['validator']['status'] == 'passed'
    assert checked['status'] == 'Checks passed and review recorded'


def test_simple_table_real_header_relationships(tmp_path):
    src = text_pdf(tmp_path / 'table.pdf', graphics=True)
    r = prepare(src, tmp_path / 'work')
    cells = r['elements'][-4:]
    edited = review(r, {'tables': [{'rows': [[e['object'] for e in cells[:2]], [e['object'] for e in cells[2:]]]}]})
    with q.open(edited['output']) as pdf:
        tables = [obj for obj in pdf.objects if isinstance(obj, q.Dictionary) and str(obj.get('/S', '')) == '/Table']
        assert len(tables) == 1
        assert str(tables[0].K[0].K[0].S) == '/TH'
        assert str(tables[0].K[0].K[0].A.Scope) == '/Column'
        assert str(tables[0].K[1].K[0].S) == '/TD'
    assert any(i['kind'] == 'graphics' and not i['reviewed'] for i in edited['issues'])


def test_list_hierarchy(tmp_path):
    r = prepare(text_pdf(tmp_path / 'list.pdf'), tmp_path / 'work')
    edited = review(r, {'lists': [[e['object'] for e in r['elements']]]})
    with q.open(edited['output']) as pdf:
        lists = [obj for obj in pdf.objects if isinstance(obj, q.Dictionary) and str(obj.get('/S', '')) == '/L']
        assert len(lists) == 1 and str(lists[0].K[0].S) == '/LI' and str(lists[0].K[0].K[0].S) == '/LBody'


def test_figure_description_and_artifact(tmp_path):
    corpus(tmp_path / 'in')
    r = prepare(tmp_path / 'in/figure.pdf', tmp_path / 'work')
    figure = next(e for e in r['elements'] if e['kind'] == 'figure')
    described = review(r, {'elements': [dict(figure, alt='A blue rectangle outlining the boundary.')],
                           'reviewed': ['figures:1']})
    assert next(e for e in described['elements'] if e['kind'] == 'figure')['alt'].startswith('A blue rectangle')
    figure = next(e for e in described['elements'] if e['kind'] == 'figure')
    decorative = review(described, {'elements': [dict(figure, decorative=True)]})
    assert not any(e['kind'] == 'figure' for e in decorative['elements'])
    with q.open(decorative['output']) as pdf:
        assert any(str(o.operator) == 'BMC' and str(o.operands[0]) == '/Artifact' for o in q.parse_content_stream(pdf.pages[0]))


def test_bad_review_retains_previous_copy(tmp_path):
    r = prepare(text_pdf(tmp_path / 'text.pdf'), tmp_path / 'work')
    old = Path(r['output']).read_bytes()
    with pytest.raises(ValueError): review(r, {'language': 'English (US)'})
    assert Path(r['output']).read_bytes() == old


def test_accessible_text_correction_does_not_repaint(tmp_path):
    r = prepare(text_pdf(tmp_path / 'text.pdf'), tmp_path / 'work')
    e = dict(r['elements'][0], actual_text='Human-corrected accessible text')
    changed = review(r, {'elements': [e]})
    with q.open(changed['output']) as pdf:
        assert any(isinstance(o, q.Dictionary) and str(o.get('/ActualText', '')) == 'Human-corrected accessible text' for o in pdf.objects)
