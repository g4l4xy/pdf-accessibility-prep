# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
import copy
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from pdfprep.app import Window
from pdfprep.engine import prepare, refresh_status, simple_text_layout
from pdfprep.fixtures import accessible_pdf, drawing_pdf, text_pdf
from pdfprep.saving import report
from pdfprep.workflow import explanation, needs_attention
from pdfprep import validation

@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])

@pytest.fixture
def clean(tmp_path):
    if not validation.command(): pytest.skip('Bundled independent validator required')
    source=accessible_pdf(tmp_path/'ready.pdf')
    return source, prepare(source, tmp_path/'ready-work')

def window_for(app, source, result):
    w=Window();w.add([source]);i=w.queue.items[0];i.result=result;i.status=result['status']
    w.refresh();w.files.selectRow(0);w.show();app.processEvents()
    return w,i

def cleanup(w):
    w.loaded_review=None;w.review_drafts.clear()
    for item in w.queue.items:
        if item.result:item.saved_hash=item.result['sha256']
    w.close()

def test_valid_tagged_pdf_needs_no_manual_review(clean):
    _,r=clean
    assert r['validator']['status']=='passed'
    assert r['status']=='Automatic checks passed'
    assert not needs_attention(r) and not r['needs_attention']
    assert not r['publication_ready']
    assert not any(i['reviewed'] for i in r['issues']) # no invented human confirmations
    assert 'Optional check' in report(r)
    assert 'Human review required' not in report(r)

def test_clean_batch_no_offer_selection_never_opens_review(app,clean):
    source,r=clean;w,_=window_for(app,source,r)
    w.batch_done(None);app.processEvents()
    assert not w.review_box.isVisible() and not w.attention_box.isVisible()
    assert w.save_button.isEnabled()
    w.manual_button.click();app.processEvents()
    assert w.review_box.isVisible() and w.questions.count()>=3
    assert 'Optional review' in w.detail.text()
    w.leave_review();assert not w.review_box.isVisible()
    cleanup(w)

def test_failed_validation_explained_once_and_user_can_decline(app,clean):
    source,r=clean;r=copy.deepcopy(r)
    r['validator']={'status':'failed','failures':[{'description':'All fonts shall be embedded.'}]};refresh_status(r)
    w,_=window_for(app,source,r);w.batch_done(None);app.processEvents()
    assert w.attention_box.isVisible() and not w.review_box.isVisible()
    assert 'font' in w.attention_text.text().lower()
    w.not_now_button.click()
    for _ in range(3):w.refresh();w.selection();app.processEvents()
    assert not w.attention_box.isVisible() and not w.review_box.isVisible()
    assert w.save_button.isEnabled() and r['status']=='Review needed — draft'
    w.manual_button.click();assert w.review_box.isVisible()
    cleanup(w)

def test_missing_validator_remains_draft_even_if_optional_checks_recorded(app,clean):
    source,r=clean;r=copy.deepcopy(r)
    r['validator']={'status':'not performed','reason':'Bundled validator or Java runtime is unavailable.'}
    for issue in r['issues']:issue['reviewed']=True
    refresh_status(r);w,i=window_for(app,source,r);w.batch_done(None)
    assert 'could not finish' in w.attention_text.text() and 'unavailable' in w.attention_text.text()
    w.review_now_button.click();app.processEvents()
    assert w.review_box.isVisible() and w.questions.count()==1
    assert not w.check.isVisible() # failed validation cannot be checked away
    assert r['status']=='Review needed — draft'
    cleanup(w)

def test_review_now_only_shows_actual_required_items(app,tmp_path):
    source=drawing_pdf(tmp_path/'drawing.pdf');r=prepare(source,tmp_path/'work')
    w,_=window_for(app,source,r);w.batch_done(None);w.review_now_button.click();app.processEvents()
    assert w.review_box.isVisible()
    kinds=[w.questions.itemData(n)['kind'] for n in range(w.questions.count())]
    assert 'pictures' in kinds and 'metadata' not in kinds and 'visual_accessibility' not in kinds
    assert 'required' in next(i for i in r['issues'] if i['kind']=='figures')
    assert not w.metadata_box.isVisible()
    cleanup(w)

def test_leaving_review_keeps_edits_and_save_returns_to_them(app,clean):
    source,r=clean;w,i=window_for(app,source,r)
    w.open_manual_review();w.title_field.setText('My corrected title');w.leave_review()
    assert w.review_changed(i) and not w.review_box.isVisible()
    w.save();app.processEvents() # must not open a directory picker or discard answers
    assert w.review_box.isVisible() and w.title_field.text()=='My corrected title'
    assert 'Finish review' in w.status.text()
    cleanup(w)

def test_failed_file_explanation_does_not_offer_false_manual_fix(app,tmp_path):
    src=tmp_path/'damaged.pdf';src.write_bytes(b'broken')
    w=Window();w.add([src]);i=w.queue.items[0];i.status='Failed';i.error='The PDF structure is damaged.'
    w.refresh();w.files.selectRow(0);w.show();w.batch_done(None);app.processEvents()
    assert 'No prepared copy' in explanation(i)
    assert not w.review_box.isVisible() and not w.manual_button.isEnabled()
    w.review_now_button.click();app.processEvents()
    assert w.retry.isVisible() and not w.edit_box.isVisible()
    cleanup(w)

def test_simple_layout_check_does_not_accept_columns_or_headings(tmp_path):
    import pymupdf as fitz
    with fitz.open() as doc:
        p=doc.new_page();p.insert_text((50,70),'First line');p.insert_text((50,100),'Second line')
        assert simple_text_layout(p)
        p.insert_text((300,70),'Another column')
        assert not simple_text_layout(p)
    with fitz.open() as doc:
        p=doc.new_page();p.insert_text((50,70),'Heading',fontsize=20);p.insert_text((50,100),'Body',fontsize=11)
        assert not simple_text_layout(p)


def test_recording_review_after_saving_still_offers_updated_report(app,clean):
    import time
    source,r=clean;w,item=window_for(app,source,r)
    item.saved_hash=r['sha256'];w.refresh();assert not w.save_button.isEnabled()
    w.open_manual_review();w.check.setChecked(True);w.apply_review()
    deadline=time.monotonic()+60
    while w.task is not None and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert w.task is None and item.result['reviews']
    assert item.result['sha256']==r['sha256'] # answers can update the report without changing PDF bytes
    assert w.save_button.isEnabled() and not item.saved_hash
    cleanup(w)


def test_switching_optional_to_required_review_keeps_a_valid_step(app,tmp_path):
    source=drawing_pdf(tmp_path/'drawing.pdf');r=prepare(source,tmp_path/'work')
    w,_=window_for(app,source,r)
    w.open_manual_review();w.questions.setCurrentIndex(w.questions.count()-1)
    w.leave_review();w.review_flagged()
    assert w.questions.currentIndex()>=0 and w.questions.currentData()
    assert 'Step ' in w.step_label.text()
    assert w.picture_panel.isVisible() or w.question.text()
    cleanup(w)


def test_interface_font_has_readable_glyphs(app):
    from PySide6.QtGui import QRawFont
    w=Window()
    assert 'Noto' in app.font().family()
    assert QRawFont.fromFont(app.font()).supportsCharacter(ord('A'))
    cleanup(w)
