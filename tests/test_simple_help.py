# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
import copy
import pikepdf as q
import pytest
from PySide6.QtWidgets import QApplication
from pdfprep.engine import prepare, repair_export_defaults, review
from pdfprep.fixtures import export_defaults_pdf
from pdfprep.workflow import reasons, technical_help
from pdfprep.app import Window

@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
    root=tmp_path_factory.mktemp('export-defaults')
    source=export_defaults_pdf(root/'defaults.pdf')
    return source,prepare(source,root/'work')

def test_automatic_repairs_preserve_pages_geometry_and_content(prepared):
    source,result=prepared
    assert result['page_count']==2
    assert all(p['source_render_sha256']==p['prepared_render_sha256'] and p['vector_geometry_and_styles_preserved'] for p in result['pages'])
    assert any('identity glyph mapping' in f for f in result['fixes'])
    assert any('layer configurations' in f for f in result['fixes'])
    assert not any(f['clause'] in ('7.21.3.2','7.10') for f in result['validator']['failures'])
    with q.open(source) as original,q.open(result['output']) as output:
        assert '/Name' not in original.Root.OCProperties.D
        assert str(output.Root.OCProperties.D.Name)=='Default view'
        assert list(output.Root.OCProperties.D.OFF)==[]
        assert str(output.Root.OCProperties.OCGs[0].Name)=='Drawing'

@pytest.mark.parametrize('mapping,embedded,encoding',[(q.Name.Identity,True,'/Identity-H'),(None,False,'/Identity-H'),(None,True,'/Custom-Encoding')])
def test_repair_does_not_replace_existing_maps_or_guess_other_encodings(mapping,embedded,encoding):
    with q.new() as pdf:
        descriptor=q.Dictionary()
        if embedded: descriptor.FontFile2=pdf.make_stream(b'fixture-only')
        descendant=q.Dictionary(Subtype=q.Name.CIDFontType2,FontDescriptor=descriptor)
        if mapping is not None:descendant.CIDToGIDMap=mapping
        font=pdf.make_indirect(q.Dictionary(Subtype=q.Name.Type0,Encoding=q.Name(encoding),DescendantFonts=q.Array([descendant])))
        pdf.Root.TestFont=font
        fixes=[];repair_export_defaults(pdf,fixes)
        assert not fixes
        assert ('/CIDToGIDMap' in descendant)==(mapping is not None)

def test_drawing_alt_failure_is_not_misreported_as_broken_structure(prepared):
    _,r=prepared
    text=' '.join(reasons(r)).lower()
    assert 'describe the drawing' in text and 'reading sequence' in text
    assert 'structure problem' not in text and 'font still' not in text
    assert r['status']=='Review needed — draft' and r['validator']['status']=='failed'
    assert not r['publication_ready']

def test_outside_repairs_are_one_help_step_with_no_checkbox(prepared):
    source,result=prepared;r=copy.deepcopy(result)
    r['issues'].append(dict(id='fonts:1',kind='fonts',page=1,required=True,reviewable=False,reviewed=False,message='Font missing'))
    r['issues']=[i for i in r['issues'] if i['kind']=='fonts']
    r['validator']={'status':'failed','failures':[{'clause':'7.21','description':'Font missing'}]}
    app=QApplication.instance() or QApplication([]);w=Window();w.add([source]);item=w.queue.items[0];item.result=r;item.status=r['status']
    w.refresh();w.files.setCurrentCell(0,0);w.review_flagged();w.show();app.processEvents()
    assert not any(w.questions.itemData(i)['kind']=='fonts' for i in range(w.questions.count()))
    w.questions.setCurrentIndex(w.questions.count()-1)
    assert w.questions.currentData()['kind']=='validation_summary'
    assert 'fonts embedded' in w.question.text() and not w.check.isVisible()
    assert not w.step_label.isVisible() and not w.navigation_box.isVisible()
    assert not w.advanced_toggle.isVisible() and w.help_save_button.isVisible()
    assert 'no questions' in w.detail.text()
    item.saved_hash=r['sha256'];w.loaded_review=None;w.review_drafts.clear();w.close()

def test_simple_reading_buttons_write_real_pdf_order(prepared):
    source,result=prepared;r=copy.deepcopy(result)
    app=QApplication.instance() or QApplication([]);w=Window();w.add([source]);item=w.queue.items[0];item.result=r;item.status=r['status']
    w.refresh();w.files.setCurrentCell(0,0);w.review_flagged();w.show();app.processEvents()
    step=next(i for i in range(w.questions.count()) if w.questions.itemData(i)['kind']=='reading')
    w.questions.setCurrentIndex(step)
    assert w.reading_panel.isVisible() and not w.advanced_box.isVisible()
    original=w.current_elements();w.reading_items.setCurrentRow(0);w.reading_down.click()
    updated=w.current_elements();assert updated[0]['object']==original[1]['object']
    assert not w.check.isChecked()
    applied=review(r,dict(order=[e['object'] for e in updated]))
    assert [e['mcid'] for e in applied['elements']][:2]==[original[1]['mcid'],original[0]['mcid']]
    assert applied['elements'][0]['label']==original[1]['label']
    assert all(p['source_render_sha256']==p['prepared_render_sha256'] for p in applied['pages'])
    item.saved_hash=r['sha256'];w.loaded_review=None;w.review_drafts.clear();w.close()


def test_pdfua_identification_added_and_preserved_after_review(prepared):
    _,result=prepared
    with q.open(result['output']) as pdf:
        with pdf.open_metadata() as meta: assert str(meta['pdfuaid:part'])=='1'
    assert not any(f['clause']=='5' for f in result['validator']['failures'])
    assert result['validator']['status']=='failed'  # Missing descriptions still fail.
    edited=review(result,{'title':'Updated title'})
    with q.open(edited['output']) as pdf:
        with pdf.open_metadata() as meta: assert str(meta['pdfuaid:part'])=='1'
    assert edited['status']=='Review needed — draft' and not edited['publication_ready']


def test_actionable_review_has_no_technical_error_steps(prepared):
    source,r=prepared
    app=QApplication.instance() or QApplication([]);w=Window();w.add([source]);item=w.queue.items[0];item.result=r;item.status=r['status']
    w.refresh();w.files.setCurrentCell(0,0);w.review_flagged()
    assert all(w.questions.itemData(i)['reviewable'] for i in range(w.questions.count()))
    assert not any(w.questions.itemData(i)['kind']=='validation_summary' for i in range(w.questions.count()))
    item.saved_hash=r['sha256'];w.loaded_review=None;w.review_drafts.clear();w.close()
