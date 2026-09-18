# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
from PySide6.QtWidgets import QApplication
from pdfprep.app import Window
from pdfprep.engine import prepare
from pdfprep.fixtures import drawing_pdf


def test_guided_review_groups_pictures_and_keeps_answers(tmp_path):
    app=QApplication.instance() or QApplication([])
    source=drawing_pdf(tmp_path/'one.pdf')
    result=prepare(source,tmp_path/'work')
    window=Window();window.add([source])
    item=window.queue.items[0];item.result=result;item.status=result['status']
    window.refresh();window.files.selectRow(0);window.selection();window.open_manual_review();window.show();app.processEvents()
    assert not window.questions.isVisible()
    assert not window.advanced_box.isVisible()
    assert 'Step 1 of' in window.step_label.text()
    assert window.metadata_box.isVisible()
    window.check.setChecked(True)
    index=next(i for i in range(window.questions.count()) if window.questions.itemData(i)['kind']=='pictures')
    window.questions.setCurrentIndex(index)
    assert window.picture_choice.count()==1
    window.check.setChecked(True); assert not window.check.isChecked()
    window.simple_description.setPlainText('Block with a hole. Dimensions are in millimeters.')
    window.check.setChecked(True)
    ids=window.questions.currentData()['ids']
    assert len(ids)>=2 and all(k in window.reviewed for k in ids)
    window.review_step(1);window.review_step(-1)
    assert window.simple_description.toPlainText().startswith('Block with')
    window.remember_review();window.selection()
    assert window.simple_description.toPlainText().startswith('Block with')
    window.skip_review_step()
    assert not any(k in window.reviewed for k in ids)
    window.save() # Changed answers must be finished, without opening a folder dialog.
    assert 'Finish review' in window.status.text()
    assert window.apply_button.isVisible()
    window.review_drafts.clear();item.saved_hash=result['sha256'];window.loaded_review=None;window.review_drafts.clear();window.close()


def test_review_navigation_does_not_confirm_unchecked_items(tmp_path):
    app=QApplication.instance() or QApplication([])
    source=drawing_pdf(tmp_path/'two.pdf',nested=True)
    result=prepare(source,tmp_path/'work')
    window=Window();window.add([source]);item=window.queue.items[0];item.result=result
    window.refresh();window.files.selectRow(0);window.selection();window.open_manual_review()
    for _ in range(window.questions.count()):window.review_step(1)
    assert not window.reviewed
    assert not window.next_button.isEnabled()
    window.review_step(-1);assert window.next_button.isEnabled()
    window.language_choice.setCurrentIndex(1);assert window.language.text()=='es'
    item.saved_hash=result['sha256'];window.loaded_review=None;window.review_drafts.clear();window.close()


def test_switching_pdfs_keeps_answers_and_finish_writes_them(tmp_path):
    import copy,time
    app=QApplication.instance() or QApplication([])
    source=drawing_pdf(tmp_path/'first.pdf');other=drawing_pdf(tmp_path/'second.pdf')
    result=prepare(source,tmp_path/'work')
    window=Window();window.add([source,other])
    for item in window.queue.items:item.result=copy.deepcopy(result);item.status=result['status']
    window.refresh();window.files.selectRow(0);window.selection();window.open_manual_review()
    window.title_field.setText('Class drawing worksheet');window.check.setChecked(True)
    window.next_review_file();assert window.active==window.queue.items[1]
    window.next_review_file();assert window.title_field.text()=='Class drawing worksheet'
    assert 'metadata:0' in window.reviewed
    window.questions.setCurrentIndex(window.questions.count()-1)
    window.apply_button.click()
    deadline=time.monotonic()+60
    while window.busy() and time.monotonic()<deadline:
        app.processEvents();time.sleep(.02)
    app.processEvents()
    assert not window.busy()
    assert window.queue.items[0].result['title']=='Class drawing worksheet'
    assert any(i['id']=='metadata:0' and i['reviewed'] for i in window.queue.items[0].result['issues'])
    assert not window.review_changed(window.queue.items[0])
    assert window.step_label.text()=='Your answers have been saved'
    for item in window.queue.items:item.saved_hash=item.result['sha256']
    window.loaded_review=None;window.review_drafts.clear();window.close()
