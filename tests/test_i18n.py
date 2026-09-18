# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
import ast
import json
import string
from pathlib import Path
from types import SimpleNamespace
import pytest
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QTextLayout
from PySide6.QtWidgets import QApplication, QMessageBox, QBoxLayout
from pdfprep import i18n
from pdfprep.app import Window
from pdfprep.workflow import explanation

@pytest.fixture(scope='module')
def app(): return QApplication.instance() or QApplication([])

def fields(text):
    return sorted(field for _, field, _, _ in string.Formatter().parse(text) if field is not None)

@pytest.mark.parametrize('code', list(i18n.LANGUAGES))
def test_catalog_complete_and_placeholders_preserved(code):
    english = i18n.catalog('en'); translated = i18n.catalog(code)
    assert translated.keys() == english.keys()
    for key, value in translated.items():
        assert value.strip()
        assert fields(value) == fields(key), (code, key)
    # Every literal passed to tr in app/runtime is covered, including aliases.
    for name in ('app.py', 'i18n.py', 'workflow.py'):
        tree = ast.parse(Path(i18n.__file__).with_name(name).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'tr' and node.args and isinstance(node.args[0], ast.Constant):
                key = node.args[0].value
                assert i18n.catalog('aliases').get(key, key) in english, key

@pytest.mark.parametrize('code', list(i18n.LANGUAGES))
def test_translated_window_preserves_document_data(app, monkeypatch, tmp_path, code):
    monkeypatch.setenv('PDFPREP_UI_LANGUAGE', code)
    w = Window(); w.show(); app.processEvents()
    assert w.heading.text() == i18n.tr('Prepare your PDFs')
    assert w.ui_language.currentData() == code
    assert w.layoutDirection() == (Qt.RightToLeft if code == 'ar' else Qt.LeftToRight)
    assert w.default_language.currentData() == 'en'  # Not inferred from interface language.
    w.language_choice.setCurrentIndex(w.language_choice.findData('ja'))
    assert w.language.text() == 'ja'
    w.language_choice.setCurrentIndex(w.language_choice.findData('other'))
    w.language.setText('sw-KE'); assert w.language.text() == 'sw-KE'
    from pdfprep.fixtures import text_pdf
    source = text_pdf(tmp_path / 'Prepare your PDFs.pdf')
    w.add([source]); assert w.files.item(0, 0).text() == 'Prepare your PDFs.pdf'
    assert w.files.item(0, 1).text() == i18n.tr('Queued')
    w.on_event(('progress', w.queue.items[0].id, 2, 10, 'Reading your PDF'))
    assert i18n.tr('Processing {v0} of {v1}', v0=2, v1=10) in w.status.text()
    w.resize(720, 520); app.processEvents()
    assert w.primary_actions.direction() == QBoxLayout.TopToBottom
    w.close()

@pytest.mark.parametrize('code', list(i18n.LANGUAGES))
def test_failed_file_and_validation_remain_failures(monkeypatch, code):
    monkeypatch.setenv('PDFPREP_UI_LANGUAGE', code)
    item = SimpleNamespace(result=None, status='Failed', error='Native diagnostic 123')
    assert 'Native diagnostic 123' in explanation(item)
    result = {'issues':[{'kind':'fonts','message':'Font missing','required':True,'reviewed':False}], 'validator':{'status':'failed','failures':[]}}
    item.result = result
    message = explanation(item)
    assert message
    assert result['validator']['status'] == 'failed' and not result['issues'][0]['reviewed']
    if code != 'en': assert i18n.tr('A font still needs repair. Export a new PDF from the original file with fonts embedded, then add it here again. If you cannot, save the draft and report for your accessibility office.') in message

def test_language_switch_applies_immediately_and_persists(app, monkeypatch):
    monkeypatch.delenv('PDFPREP_UI_LANGUAGE', raising=False)
    i18n.set_language('en'); w = Window(); w.show()
    session = w.session
    w.ui_language.setCurrentIndex(w.ui_language.findData('ar')); app.processEvents()
    assert i18n.current_language() == 'ar'
    assert w.heading.text() == i18n.tr('Prepare your PDFs') and w.layoutDirection() == Qt.RightToLeft
    assert w.session is session
    i18n._active = None
    assert i18n.current_language() == 'ar'
    w.english_button.click(); app.processEvents()
    assert w.heading.text() == 'Prepare your PDFs' and w.layoutDirection() == Qt.LeftToRight
    assert i18n.settings().value('ui_language_v2') == 'en'
    w.close()

def test_fresh_download_ignores_system_and_legacy_arabic(monkeypatch):
    import sys
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setenv('PDFPREP_UI_LANGUAGE', 'ar')
    i18n.settings().setValue('ui_language', 'ar')
    i18n._active = None
    assert i18n.current_language() == 'en'
    i18n.settings().setValue('ui_language_v2', 'invalid')
    i18n._active = None
    assert i18n.current_language() == 'en'

@pytest.mark.parametrize('code,sample', [('ar','إمكانية الوصول'),('hi','सुलभता'),('zh','准备文件'),('ja','読み上げ確認')])
def test_bundled_fonts_have_no_missing_glyphs(app, monkeypatch, code, sample):
    monkeypatch.setenv('PDFPREP_UI_LANGUAGE', code)
    w = Window()
    layout = QTextLayout(sample, w.font()); layout.beginLayout(); layout.createLine(); layout.endLayout()
    runs = layout.glyphRuns(); assert runs
    assert all(0 not in run.glyphIndexes() for run in runs)
    w.close()


@pytest.fixture(scope='module')
def review_source(tmp_path_factory):
    from pdfprep.fixtures import accessible_pdf
    from pdfprep.engine import prepare
    root = tmp_path_factory.mktemp('localized_review')
    source = accessible_pdf(root / 'Review example.pdf')
    return source, prepare(source, root / 'prepared')

@pytest.mark.parametrize('code', list(i18n.LANGUAGES))
def test_review_now_selects_first_file_without_prior_click(app, monkeypatch, review_source, code):
    import copy
    monkeypatch.setenv('PDFPREP_UI_LANGUAGE', code)
    source, result = review_source
    w = Window(); w.show(); app.processEvents(); w.add([source])
    item = w.queue.items[0]; item.result = copy.deepcopy(result)
    item.result['validator']['status'] = 'failed'; item.status = 'Review needed — draft'
    w.refresh(); w.batch_done(None); app.processEvents()
    assert w.attention_box.isVisible() and not w.review_box.isVisible()
    w.review_now_button.click(); app.processEvents()
    assert w.active == item and w.files.currentRow() == 0 and w.review_box.isVisible()
    assert item.result['validator']['status'] == 'failed'
    w.leave_review(); assert not w.review_box.isVisible()
    w.loaded_review = None; w.review_drafts.clear(); item.saved_hash = item.result['sha256']; w.close()


@pytest.mark.parametrize('code', list(i18n.LANGUAGES))
def test_live_switch_keeps_review_and_queue(app, monkeypatch, review_source, code):
    import copy
    monkeypatch.delenv('PDFPREP_UI_LANGUAGE', raising=False)
    i18n.set_language('en')
    source, result = review_source
    w = Window(); w.show(); w.add([source])
    item = w.queue.items[0]; item.result = copy.deepcopy(result); item.status = result['status']
    w.refresh(); w.files.setCurrentCell(0, 0); w.open_manual_review()
    w.title_field.setText('My unsaved title — 私の文書')
    w.language.setText('es-MX')
    w.reviewed.add('metadata:0')
    w.default_language.setCurrentIndex(w.default_language.findData('fr'))
    w.output_folder = 'saved-output'; w.preview_zoom.setValue(150)
    session = w.session; original_hash = item.result['sha256']
    w.ui_language.setCurrentIndex(w.ui_language.findData(code)); app.processEvents()
    assert i18n.current_language() == code
    assert w.queue.items[0] is item and w.session is session
    assert w.active is item and w.review_open and w.review_box.isVisible()
    assert w.title_field.text() == 'My unsaved title — 私の文書'
    assert w.language.text() == 'es-MX' and 'metadata:0' in w.reviewed
    assert w.default_language.currentData() == 'fr' and w.preview_zoom.value() == 150
    assert item.result['sha256'] == original_hash and w.output_folder == 'saved-output'
    w.english_button.click(); app.processEvents()
    assert w.heading.text() == 'Review this PDF' and w.layoutDirection() == Qt.LeftToRight
    w.loaded_review = None; w.review_drafts.clear(); item.saved_hash = original_hash; w.close()
