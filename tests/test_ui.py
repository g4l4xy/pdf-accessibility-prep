# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import time
import pytest
from PySide6.QtCore import Qt, QMimeData, QUrl, QPointF
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication, QFileDialog
from pdfprep.app import Window
from pdfprep.fixtures import text_pdf


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def finish(app, window, timeout=60):
    deadline = time.monotonic() + timeout
    ticks = 0
    while window.task is not None and time.monotonic() < deadline:
        app.processEvents(); time.sleep(.01); ticks += 1
    assert window.task is None
    assert ticks > 1  # Event loop continues while document work runs elsewhere.


def test_multi_picker_drop_remove_and_clear(app, tmp_path, monkeypatch):
    w = Window()
    a = text_pdf(tmp_path / 'a.pdf'); b = text_pdf(tmp_path / 'b.pdf', label='B')
    monkeypatch.setattr(QFileDialog, 'getOpenFileNames', lambda *args: ([str(a), str(b)], 'PDF'))
    w.choose(); assert len(w.queue.items) == 2
    mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(str(a)), QUrl.fromLocalFile(str(b))])
    event = QDropEvent(QPointF(20, 20), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    w.dropEvent(event); assert len(w.queue.items) == 2
    w.files.cellWidget(0, 2).click(); assert len(w.queue.items) == 1
    w.clear(); assert not w.queue.items
    w.close()


def test_one_click_batch_and_save_all(app, tmp_path, monkeypatch):
    w = Window(); w.show()
    a = text_pdf(tmp_path / 'a/same.pdf'); b = text_pdf(tmp_path / 'b/same.pdf', pages=5, label='B')
    bad = tmp_path / 'bad.pdf'; bad.write_bytes(b'bad PDF')
    w.add([a, bad, b]); w.prepare(); finish(app, w)
    assert w.queue.items[0].result and w.queue.items[1].status == 'Failed' and w.queue.items[2].result
    w.files.selectRow(0); app.processEvents()
    assert not w.review_box.isVisible()
    assert w.attention_box.isVisible()
    w.dismiss_attention(); assert not w.attention_box.isVisible()
    destination = tmp_path / 'out'; destination.mkdir(); calls = []
    def picker(*args): calls.append(1); return str(destination)
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory', picker)
    w.save(); finish(app, w)
    assert len(calls) == 1 and len(list(destination.glob('*.pdf'))) == 2
    assert len(list(destination.glob('*.html'))) == 2
    assert w.folder_button.isEnabled()
    w.close()
