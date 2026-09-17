# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
import threading
import pytest
import pikepdf as q
import pymupdf as fitz
from pdfprep.engine import prepare, review, NeedsInput
from pdfprep.model import sha256, Queue
from pdfprep.saving import save_one, save_all
from pdfprep import validation
from pdfprep.batch import run_batch, isolated
from tests.fixtures import text_pdf, scan_pdf, accessible_pdf, corpus


def test_real_structure_and_review(tmp_path):
    source = text_pdf(tmp_path / 'original.pdf')
    digest = sha256(source)
    result = prepare(source, tmp_path / 'work')
    with q.open(result['output']) as pdf:
        assert '/StructTreeRoot' in pdf.Root
        assert len(pdf.Root.StructTreeRoot.ParentTree.Nums[1]) == 2
        ops = list(q.parse_content_stream(pdf.pages[0]))
        assert sum(str(o.operator) == 'BDC' for o in ops) == 2
        for index, element in enumerate(pdf.Root.StructTreeRoot.ParentTree.Nums[1]):
            assert element.K == index
            assert element.Pg.objgen == pdf.pages[0].obj.objgen
    edited = review(result, {'title': 'Reviewed title', 'language': 'en-US',
                            'elements': [dict(result['elements'][0], role='H1')],
                            'order': [e['object'] for e in reversed(result['elements'])],
                            'reviewed': [i['id'] for i in result['issues'] if i['reviewable']]})
    assert edited['sha256'] != result['sha256']
    assert edited['title'] == 'Reviewed title'
    assert sha256(source) == digest
    with q.open(edited['output']) as pdf:
        children = pdf.Root.StructTreeRoot.K[0].K[0].K
        assert str(children[1].S) == '/H1'
    assert all(p['source_render_sha256'] == p['prepared_render_sha256'] for p in result['pages'])


def test_existing_tree_preserved(tmp_path):
    source = accessible_pdf(tmp_path / 'tagged.pdf')
    result = prepare(source, tmp_path / 'work')
    assert len(result['elements']) == 2
    with q.open(source) as a, q.open(result['output']) as b:
        assert a.pages[0].Contents.read_bytes() == b.pages[0].Contents.read_bytes()
        assert str(a.Root.StructTreeRoot.K[0].S) == str(b.Root.StructTreeRoot.K[0].S)


def test_password_and_signature_collect_for_later(tmp_path):
    sources = corpus(tmp_path / 'inputs')
    with pytest.raises(NeedsInput) as e: prepare(tmp_path / 'inputs/encrypted.pdf', tmp_path / 'a')
    assert e.value.kind == 'password'
    r = prepare(tmp_path / 'inputs/encrypted.pdf', tmp_path / 'b', {'password': 'open-me'})
    with q.open(r['output']) as pdf: assert not pdf.is_encrypted
    with pytest.raises(NeedsInput) as e: prepare(tmp_path / 'inputs/signature-marker.pdf', tmp_path / 'c')
    assert e.value.kind == 'signature'


def test_ocr_without_replacing_visuals(tmp_path):
    source = scan_pdf(tmp_path / 'scan.pdf', mixed=True)
    r = prepare(source, tmp_path / 'work')
    assert r['page_count'] == 2
    if (validation.resources() / 'tessdata/eng.traineddata').exists():
        with fitz.open(r['output']) as doc:
            assert 'Scanned' in doc[0].get_text()
            assert 'Mixed document' in doc[1].get_text()
        assert any('invisible' in fix for fix in r['fixes'])
    assert r['status'] == 'Review needed — draft'


def test_save_no_clobber_reports_and_hashes(tmp_path):
    source = text_pdf(tmp_path / 'Résumé.pdf')
    r = prepare(source, tmp_path / 'work')
    dest = tmp_path / 'out'; dest.mkdir()
    collision = dest / 'Résumé_prepared_accessibility.html'; collision.write_text('keep')
    pdf, rep = save_one(r, dest)
    assert Path(pdf).name == 'Résumé_prepared_2.pdf'
    assert collision.read_text() == 'keep'
    assert sha256(pdf) == r['sha256'] and r['sha256'] in Path(rep).read_text()
    second, _ = save_one(r, dest); assert Path(second).name == 'Résumé_prepared_3.pdf'
    assert sha256(source) == r['source_sha256']


def test_missing_validator_never_passes(monkeypatch, tmp_path):
    monkeypatch.setattr(validation, 'command', lambda: None)
    assert validation.validate(tmp_path / 'x', tmp_path / 'report')['status'] == 'not performed'
    for raw in (b'<report/>', b'bad xml', b'<validationReport profileName="PDF/A-1b" isCompliant="true"/>'):
        assert validation.parse_report(raw)['status'] == 'not performed'


def test_duplicate_selection_aliases_and_same_names(tmp_path):
    a = text_pdf(tmp_path / 'a/same.pdf', label='A')
    b = text_pdf(tmp_path / 'b/same.pdf', label='B')
    alias = tmp_path / 'alias.pdf'
    try:
        alias.symlink_to(a)
    except OSError:
        # Windows standard users may not have symbolic-link privileges.
        # A same-volume hard link exercises the same identity deduplication.
        import os
        os.link(a, alias)
    queue = Queue(); added, duplicates, rejected = queue.add([a, a, b, alias])
    assert len(added) == 2 and len(duplicates) == 2 and not rejected


def local_runner(source, folder, options, cancel, emit):
    try: return 'result', prepare(source, folder, options, emit)
    except NeedsInput as e: return 'needs_input', {'kind': e.kind, 'message': e.message}
    except Exception: return 'error', {'message': 'Damaged document'}


@pytest.mark.parametrize('count', [1, 10, 50, 100])
def test_batches_every_page_and_order(tmp_path, count):
    inputs = []
    for i in range(count):
        p = tmp_path / f'input-{i}/same.pdf'
        if i == count // 2 and count > 1:
            p.parent.mkdir(); p.write_bytes(b'%PDF-1.7\nbroken')
        elif i % 10 == 3:
            p.parent.mkdir(); scan_pdf(p, mixed=True)
        else: text_pdf(p, pages=(i % 5) + 1, label=f'Document {i}', columns=(i % 4 == 0), graphics=(i % 7 == 0))
        inputs.append(p)
    queue = Queue(); queue.add(inputs + inputs)
    assert len(queue.items) == count
    run_batch(queue.items, tmp_path / 'work', threading.Event())
    good = [i for i in queue.items if i.result]
    assert len(good) == count - (count > 1)
    destination = tmp_path / 'out'; destination.mkdir()
    saved, failures = save_all(queue.items, destination)
    assert len(saved) == len(good) and not failures
    assert len({p[1][0] for p in saved}) == len(good)
    for item in good:
        with fitz.open(item.source) as source, fitz.open(item.result['output']) as prepared:
            assert len(source) == len(prepared) == item.result['page_count']
            for p, r in zip(source, prepared):
                assert tuple(p.mediabox) == tuple(r.mediabox) and p.rotation == r.rotation
                if p.get_text(): assert p.get_text() in r.get_text()
        assert all(p['source_render_sha256'] == p['prepared_render_sha256'] for p in item.result['pages'])


def test_cancellation_keeps_completed_outputs(tmp_path):
    queue = Queue(); queue.add([text_pdf(tmp_path / f'{n}.pdf', label=str(n)) for n in range(3)])
    cancel = threading.Event()
    def emit(kind, *args):
        if kind == 'done': cancel.set()
    run_batch(queue.items, tmp_path / 'work', cancel, emit, local_runner)
    assert queue.items[0].result and Path(queue.items[0].result['output']).exists()
    assert [i.status for i in queue.items[1:]] == ['Cancelled', 'Cancelled']
    cancel.clear(); run_batch(queue.items, tmp_path / 'work', cancel, runner=local_runner)
    assert all(i.result for i in queue.items)


def test_worker_process_and_corrupt_isolation(tmp_path):
    queue = Queue(); a = text_pdf(tmp_path / 'good.pdf'); bad = tmp_path / 'bad.pdf'; bad.write_bytes(b'broken')
    b = text_pdf(tmp_path / 'next.pdf', label='Next document')
    queue.add([a, bad, b]); run_batch(queue.items, tmp_path / 'work', threading.Event())
    assert queue.items[0].result and queue.items[1].status == 'Failed' and queue.items[2].result


def test_timeout_and_immediate_cancel(tmp_path):
    source = text_pdf(tmp_path / 'original.pdf')
    event = threading.Event(); event.set()
    assert isolated(source, tmp_path / 'cancel', {}, event)[0] == 'cancelled'
    result = isolated(source, tmp_path / 'timeout', {}, threading.Event(), timeout=0)
    assert result[0] == 'error' and 'limit' in result[1]['message']


def test_tampered_output_not_saved(tmp_path):
    source = text_pdf(tmp_path / 'original.pdf'); r = prepare(source, tmp_path / 'work')
    Path(r['output']).write_bytes(b'changed')
    with pytest.raises(ValueError): save_one(r, tmp_path)


def test_restricted_pdf_requires_owner_password(tmp_path):
    original = text_pdf(tmp_path / 'original.pdf')
    restricted = tmp_path / 'restricted.pdf'
    with q.open(original) as pdf:
        pdf.save(restricted, encryption=q.Encryption(owner='authorized-owner', user='', R=6,
                 allow=q.Permissions(extract=False, modify_other=False)))
    with pytest.raises(NeedsInput) as ex: prepare(restricted, tmp_path / 'blocked')
    assert ex.value.kind == 'password'
    assert prepare(restricted, tmp_path / 'allowed', {'password': 'authorized-owner'})['page_count'] == 1
