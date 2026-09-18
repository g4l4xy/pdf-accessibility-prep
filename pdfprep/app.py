# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations
from pathlib import Path
import copy
import json
import os
import shutil
import tempfile
import threading
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap, QKeySequence, QShortcut, QFontDatabase
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QProgressBar, QGroupBox, QLineEdit, QFormLayout, QComboBox, QCheckBox, QPlainTextEdit,
    QScrollArea, QMessageBox, QSpinBox, QSplitter)
from .model import Queue
from . import __version__
from .validation import resources
from .batch import run_batch, isolated
from .saving import save_all
from .workflow import needs_attention, explanation, reasons


class Task(QThread):
    event = Signal(object)
    outcome = Signal(object)
    def __init__(self, fn):
        super().__init__(); self.fn = fn
    def run(self):
        try: self.outcome.emit(('ok', self.fn(self.event.emit)))
        except Exception as ex: self.outcome.emit(('error', str(ex)))


def button(text, fn, name=None):
    b = QPushButton(text); b.clicked.connect(fn)
    b.setAccessibleName(name or text.replace('&', ''))
    return b


def configure_application(app):
    """Use the bundled, licensed font instead of a platform-dependent fallback."""
    if app.property('pdfprepFontConfigured'): return
    font = app.font()
    path = resources() / 'NotoSans-Regular.ttf'
    if path.exists():
        font_id = QFontDatabase.addApplicationFont(str(path))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families: font.setFamily(families[0])
    font.setPointSize(11); app.setFont(font)
    app.setProperty('pdfprepFontConfigured', True)


class Window(QWidget):
    def __init__(self):
        super().__init__()
        configure_application(QApplication.instance())
        self.queue = Queue(); self.cancel_event = threading.Event(); self.task = None
        self.session = tempfile.TemporaryDirectory(prefix='PDF-Accessibility-Prep-')
        try: os.chmod(self.session.name, 0o700)
        except OSError: pass
        self.output_folder = ''; self.active = None; self.reviewed = set(); self.tables = []; self.lists = []
        self.review_drafts = {}; self.loaded_review = None
        self.review_open = False; self.review_all = False
        self.setWindowTitle(f'PDF Accessibility Prep {__version__} — Eathan Huber'); self.resize(1000, 740); self.setMinimumSize(720, 520)
        self.setAcceptDrops(True)
        outer = QVBoxLayout(self)
        heading = QLabel('Prepare your PDFs'); self.heading = heading; heading.setStyleSheet('font-size: 24px; font-weight: 600;'); outer.addWidget(heading)
        self.instructions = QLabel('Everything runs on this computer. Manual review opens only when you choose it.')
        self.instructions.setWordWrap(True); outer.addWidget(self.instructions)
        self.main_tools = QWidget(); self.main_tools_layout = QVBoxLayout(self.main_tools); self.main_tools_layout.setContentsMargins(0, 0, 0, 0); outer.addWidget(self.main_tools)
        row = QHBoxLayout()
        self.add_button = button('&Add PDFs', self.choose)
        self.clear_button = button('C&lear All', self.clear)
        self.prepare_button = button('&Prepare PDFs', self.prepare)
        self.cancel_button = button('&Cancel batch', self.cancel); self.cancel_button.setEnabled(False)
        self.save_button = button('3. &Save prepared PDFs…', self.save)
        self.add_button.setText('1. &Add PDFs'); self.prepare_button.setText('2. &Prepare PDFs')
        for b in (self.add_button, self.prepare_button, self.save_button):
            b.setMinimumHeight(38); row.addWidget(b)
        self.main_tools_layout.addLayout(row)
        save_hint = QLabel('Saving opens one folder picker and writes each prepared PDF plus its report. Unresolved files are saved as drafts.'); save_hint.setWordWrap(True); self.main_tools_layout.addWidget(save_hint)
        settings = QHBoxLayout(); settings.addWidget(QLabel('Language when a PDF has none:'))
        self.default_language = QComboBox(); self.default_language.addItems(['English', 'Spanish', 'French', 'German']); self.default_language.setAccessibleName('Default language for PDFs with no language set')
        settings.addWidget(self.default_language); settings.addStretch(); settings.addWidget(self.clear_button); self.main_tools_layout.addLayout(settings)
        self.attention_box = QGroupBox('Automatic preparation finished — some items need help')
        notice = QVBoxLayout(self.attention_box); self.attention_text = QLabel(); self.attention_text.setWordWrap(True); self.attention_text.setTextFormat(Qt.PlainText); notice.addWidget(self.attention_text)
        choices = QHBoxLayout(); self.review_now_button = button('Review now', self.review_flagged); self.not_now_button = button('Not now — keep drafts', self.dismiss_attention)
        choices.addWidget(self.review_now_button); choices.addWidget(self.not_now_button); choices.addStretch(); notice.addLayout(choices); outer.addWidget(self.attention_box); self.attention_box.hide()
        self.queue_label = QLabel('No PDFs added yet'); outer.addWidget(self.queue_label)
        split = QSplitter(Qt.Vertical); self.main_split = split; outer.addWidget(split, 1)
        self.files = QTableWidget(0, 3); self.files.setHorizontalHeaderLabels(['PDF', 'Status', 'Remove'])
        self.files.verticalHeader().hide(); self.files.verticalHeader().setDefaultSectionSize(38); self.files.setAlternatingRowColors(True)
        self.files.setAccessibleName('PDF queue'); self.files.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.files.setSelectionMode(QAbstractItemView.SingleSelection); self.files.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.files.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.files.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.files.itemSelectionChanged.connect(self.selection)
        split.addWidget(self.files)
        self.review_box = QGroupBox('Review needed'); self.review_box.setVisible(False)
        review_layout = QVBoxLayout(self.review_box)
        self.close_review_button = button('Back to files', self.leave_review); review_layout.addWidget(self.close_review_button)
        self.review_scroll = QScrollArea(); self.review_scroll.setWidgetResizable(True)
        content = QWidget(); self.review_layout = QVBoxLayout(content)
        self.review_scroll.setWidget(content); review_layout.addWidget(self.review_scroll)
        split.addWidget(self.review_box); split.setSizes([160, 480])
        self.detail = QLabel(); self.detail.setWordWrap(True); self.detail.setTextFormat(Qt.PlainText)
        self.review_layout.addWidget(self.detail)
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password); self.password.setAccessibleName('PDF password')
        self.signature = QCheckBox('I authorize creating a derivative that may invalidate this digital signature.')
        self.retry = button('Continue preparation', self.retry_item)
        self.review_layout.addWidget(self.password); self.review_layout.addWidget(self.signature); self.review_layout.addWidget(self.retry)
        self.edit_box = QWidget(); form = QVBoxLayout(self.edit_box)
        self.metadata_box = QWidget(); metadata = QFormLayout(self.metadata_box); self.title_field = QLineEdit(); self.language = QLineEdit()
        metadata.addRow('Document &title:', self.title_field); metadata.addRow('Language code:', self.language)
        self.language_choice = QComboBox(); self.language_choice.addItems(['English', 'Spanish', 'French', 'German', 'Other language'])
        self.language_choice.setAccessibleName('Document language')
        self.language_choice.currentIndexChanged.connect(self.language_chosen)
        metadata.insertRow(1, 'Written in:', self.language_choice)
        self.title_field.setAccessibleName('Document title'); self.language.setAccessibleName('Document language code')
        form.addWidget(self.metadata_box)
        self.questions = QComboBox(); self.questions.setAccessibleName('Review question')
        self.questions.currentIndexChanged.connect(self.question_changed); self.questions.hide()
        self.step_label = QLabel(); self.step_label.setWordWrap(True); form.addWidget(self.step_label)
        self.question = QLabel(); self.question.setTextFormat(Qt.PlainText); self.question.setWordWrap(True); form.addWidget(self.question)
        self.check = QCheckBox('I checked this and it looks correct'); self.check.toggled.connect(self.record_check); form.addWidget(self.check)
        self.zoom_box = QWidget(); zoom_row = QHBoxLayout(self.zoom_box)
        zoom_row.addWidget(QLabel('Page preview zoom (%):'))
        self.preview_zoom = QSpinBox(); self.preview_zoom.setRange(50, 250); self.preview_zoom.setValue(100)
        self.preview_zoom.setSingleStep(25); self.preview_zoom.setAccessibleName('Page preview zoom percent')
        self.preview_zoom.valueChanged.connect(self.question_changed); zoom_row.addWidget(self.preview_zoom); zoom_row.addStretch(); form.addWidget(self.zoom_box)
        self.preview = QLabel(); self.preview.setAlignment(Qt.AlignCenter); self.preview.setAccessibleName('Page preview; use the adjacent content list for keyboard review')
        self.page_scroll = QScrollArea(); self.page_scroll.setWidget(self.preview); self.page_scroll.setWidgetResizable(True); self.page_scroll.setFixedHeight(200)
        form.addWidget(self.page_scroll)
        self.picture_choice = QComboBox(); self.picture_choice.setAccessibleName('Picture or drawing to describe'); self.picture_choice.currentIndexChanged.connect(self.picture_chosen); form.addWidget(self.picture_choice)
        self.simple_description = QPlainTextEdit(); self.simple_description.setAccessibleName('Describe this picture or drawing'); self.simple_description.setPlaceholderText('Explain what this shows and what the reader needs to know. For drawings, include the view, dimensions, units, and important features.'); self.simple_description.setFixedHeight(170); self.simple_description.textChanged.connect(self.simple_description_changed); form.addWidget(self.simple_description)
        self.picture_panel = QWidget(); picture_layout = QHBoxLayout(self.picture_panel)
        self.preview_side = QWidget(); preview_layout = QVBoxLayout(self.preview_side)
        self.picture_text_box = QWidget(); text_layout = QVBoxLayout(self.picture_text_box)
        for widget in (self.zoom_box, self.page_scroll, self.picture_choice, self.simple_description): form.removeWidget(widget)
        preview_layout.addWidget(self.zoom_box); preview_layout.addWidget(self.page_scroll)
        text_layout.addWidget(self.picture_choice); text_layout.addWidget(self.simple_description); text_layout.addStretch()
        picture_layout.addWidget(self.preview_side, 1); picture_layout.addWidget(self.picture_text_box, 1)
        form.addWidget(self.picture_panel)
        self.advanced_toggle = QCheckBox('More editing tools (optional)'); form.addWidget(self.advanced_toggle)
        self.advanced_box = QWidget(); advanced_form = QVBoxLayout(self.advanced_box); form.addWidget(self.advanced_box); self.advanced_box.hide(); self.advanced_toggle.toggled.connect(self.advanced_box.setVisible)
        self.elements = QTableWidget(0, 5)
        self.elements.setHorizontalHeaderLabels(['Page / item', 'Role', 'Text correction', 'Image / drawing description', 'Decorative'])
        self.elements.setAccessibleName('Content reading order and corrections')
        self.elements.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.elements.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.elements.setMinimumHeight(180)
        self.elements.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for c in (2, 3): self.elements.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        advanced_form.addWidget(self.elements)
        self.description_editor = QPlainTextEdit()
        self.description_editor.setAccessibleName('Full description for the selected image or drawing')
        self.description_editor.setPlaceholderText('Select a Figure row, then describe the drawing here. Multiple paragraphs are allowed.')
        self.description_editor.setMinimumHeight(100)
        self.description_editor.setEnabled(False)
        self.description_editor.textChanged.connect(self.description_changed)
        self.elements.currentCellChanged.connect(self.description_selected)
        self.elements.itemChanged.connect(self.description_table_changed)
        advanced_form.addWidget(self.description_editor)
        drawing_note = QLabel('Drawing or isometric view? Enter its full explanation in the Figure description: object, view direction, dimensions and units, features, hidden lines, and what the student must learn. Visible linework and page scale stay unchanged. Separate diagrams on a page need an explanation of each.')
        drawing_note.setWordWrap(True); advanced_form.addWidget(drawing_note)
        order = QHBoxLayout()
        order.addWidget(button('Move item &up', lambda: self.move(-1)))
        order.addWidget(button('Move item &down', lambda: self.move(1)))
        self.columns = QSpinBox(); self.columns.setRange(1, 20); self.columns.setValue(2); self.columns.setAccessibleName('Simple table column count')
        order.addWidget(QLabel('Table columns:')); order.addWidget(self.columns)
        order.addWidget(button('Make selected rows a table', self.make_table))
        order.addWidget(button('Make selected rows a list', self.make_list)); advanced_form.addLayout(order)
        note = QLabel('Select simple table cells in reading order; the first row becomes column headings. Complex or merged cells need specialist review. Text corrections change accessible replacement text, not the visible source.')
        note.setWordWrap(True); advanced_form.addWidget(note)
        self.navigation_box = QWidget(); navigation_layout = QVBoxLayout(self.navigation_box)
        navigation = QHBoxLayout()
        self.back_button = button('Back', lambda: self.review_step(-1))
        self.skip_button = button('Not sure — leave for later', self.skip_review_step)
        self.next_button = button('Next', lambda: self.review_step(1))
        for widget in (self.back_button, self.skip_button, self.next_button): navigation.addWidget(widget)
        navigation_layout.addLayout(navigation)
        self.apply_button = button('Finish review for this PDF', self.apply_review); navigation_layout.addWidget(self.apply_button)
        self.next_file_button = button('Review next PDF', self.next_review_file); navigation_layout.addWidget(self.next_file_button)
        review_layout.addWidget(self.navigation_box)
        self.review_layout.addWidget(self.edit_box)
        self.file_summary = QLabel('Drop PDFs here, or choose Add PDFs.'); self.file_summary.setWordWrap(True); self.file_summary.setTextFormat(Qt.PlainText); outer.addWidget(self.file_summary)
        actions = QHBoxLayout(); self.manual_button = button('Manual review…', self.open_manual_review); self.manual_button.setEnabled(False)
        self.input_button = button('Help with this file…', self.open_input); self.input_button.hide()
        actions.addWidget(self.manual_button); actions.addWidget(self.input_button); actions.addStretch(); outer.addLayout(actions)
        self.progress = QProgressBar(); self.progress.setAccessibleName('Batch progress'); outer.addWidget(self.progress)
        self.status = QLabel('Add one or more PDFs to begin.'); self.status.setWordWrap(True); self.status.setTextFormat(Qt.PlainText); self.status.setAccessibleName('Batch status'); outer.addWidget(self.status)
        bottom = QHBoxLayout()
        self.folder_button = button('&Open Output Folder', self.open_folder); self.folder_button.setEnabled(False)
        bottom.addWidget(self.cancel_button); bottom.addWidget(self.folder_button); bottom.addStretch(); bottom.addWidget(QLabel('Created by Eathan Huber'))
        bottom.addWidget(button('&Help', self.help)); outer.addLayout(bottom)
        QShortcut(QKeySequence('Delete'), self.files, activated=self.remove_selected)
        self.refresh(); self.cancel_button.hide(); self.progress.hide()

    def busy(self): return self.task is not None and self.task.isRunning()
    def controls(self, busy):
        for w in (self.add_button, self.clear_button, self.prepare_button, self.save_button, self.apply_button, self.retry): w.setEnabled(not busy)
        self.cancel_button.setEnabled(busy); self.cancel_button.setVisible(busy); self.progress.setVisible(busy)
        self.cancel_button.setText('Cancel review' if self.review_open else 'Cancel batch')
        self.default_language.setEnabled(not busy); self.manual_button.setEnabled(not busy and bool(self.active and self.active.result))
        self.input_button.setEnabled(not busy); self.review_now_button.setEnabled(not busy); self.close_review_button.setEnabled(not busy)
        for r in range(self.files.rowCount()): self.files.cellWidget(r, 2).setEnabled(not busy)
        self.edit_box.setEnabled(not busy)
        self.navigation_box.setEnabled(not busy)
        self.password.setEnabled(not busy); self.signature.setEnabled(not busy)

    def launch(self, fn, finished):
        self.controls(True)
        task = Task(fn); self.task = task
        task.event.connect(self.on_event)
        def outcome(value):
            self.last_outcome = value
        task.outcome.connect(outcome)
        def done():
            self.controls(False)
            value = getattr(self, 'last_outcome', ('error', 'The operation stopped unexpectedly.'))
            self.task = None
            if value[0] == 'error': self.status.setText(value[1])
            else: finished(value[1])
            self.refresh()
            task.deleteLater()
        task.finished.connect(done); task.start()

    def choose(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Add PDFs', '', 'PDF documents (*.pdf *.PDF)')
        self.add(paths)
    def add(self, paths):
        if self.busy(): return
        added, dup, rejected = self.queue.add(paths)
        self.status.setText(f'Added {len(added)} PDF(s). {len(dup)} duplicate selection(s) skipped. {len(rejected)} unsupported or unavailable file(s).')
        self.refresh()
    def dragEnterEvent(self, event):
        if not self.busy() and event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls()): event.acceptProposedAction()
    def dropEvent(self, event):
        self.add([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]); event.acceptProposedAction()
    def clear(self):
        if self.busy(): return
        if any(i.result and (i.saved_hash != i.result['sha256'] or self.review_changed(i)) for i in self.queue.items):
            if QMessageBox.question(self, 'Clear unsaved copies?', 'Clearing removes unsaved prepared copies from this session. Originals stay unchanged. Clear All?') != QMessageBox.Yes: return
        self.queue.items.clear(); self.active = None; self.review_drafts.clear(); self.loaded_review = None; self.review_open = False; self.attention_box.hide(); self.session.cleanup()
        self.session = tempfile.TemporaryDirectory(prefix='PDF-Accessibility-Prep-'); self.refresh(); self.leave_review()
    def remove(self, item_id):
        if self.busy(): return
        item = next(i for i in self.queue.items if i.id == item_id)
        if item.result and (item.saved_hash != item.result['sha256'] or self.review_changed(item)):
            if QMessageBox.question(self, 'Remove unsaved copy?', 'Remove this unsaved prepared copy from the queue?') != QMessageBox.Yes: return
        self.review_drafts.pop(item.id, None)
        if self.active == item: self.active = None; self.loaded_review = None
        self.attention_box.hide()
        self.queue.items.remove(item); shutil.rmtree(Path(self.session.name) / item.id, ignore_errors=True)
        self.refresh(); self.selection()
    def remove_selected(self):
        r = self.files.currentRow()
        if r >= 0: self.remove(self.queue.items[r].id)
    def refresh(self):
        selected = self.active.id if self.active else None
        count = len(self.queue.items); self.queue_label.setText(f'{count} PDF' + ('s' if count != 1 else '') + (' in this batch' if count else ' added yet'))
        self.files.blockSignals(True); self.files.setRowCount(count)
        for r, item in enumerate(self.queue.items):
            name = QTableWidgetItem(Path(item.source).name); name.setToolTip(item.source)
            state = {'Review needed — draft':'Prepared · draft', 'Automatic checks passed':'Prepared · checks passed', 'Checks passed and review recorded':'Prepared · reviewed', 'Failed':'Could not prepare'}.get(item.status, item.status) + (' · saved' if item.result and item.saved_hash == item.result['sha256'] else '')
            self.files.setItem(r, 0, name); self.files.setItem(r, 1, QTableWidgetItem(state))
            b = self.files.cellWidget(r, 2)
            if b is None or b.property('itemId') != item.id:
                if b is not None: b.hide()
                b = button('Remove', lambda checked=False, k=item.id: self.remove(k), 'Remove ' + Path(item.source).name)
                b.setProperty('itemId', item.id)
                self.files.setCellWidget(r, 2, b)
            b.setEnabled(not self.busy())
            if item.id == selected: self.files.selectRow(r)
        self.files.blockSignals(False)
        if not self.busy():
            self.prepare_button.setEnabled(any(i.status in ('Queued', 'Cancelled', 'Retry') for i in self.queue.items))
            available = sum(bool(i.result and (i.saved_hash != i.result['sha256'] or self.review_changed(i))) for i in self.queue.items)
            self.save_button.setEnabled(bool(available))
            self.save_button.setText(f'3. Save {available} prepared PDF' + ('s…' if available != 1 else '…') if available else '3. Save prepared PDFs…')
            self.save_button.setAccessibleName(self.save_button.text().replace('3. ', '') + ' and accessibility reports')
    def prepare(self):
        if self.busy(): return
        self.leave_review(); self.attention_box.hide()
        default = ['en', 'es', 'fr', 'de'][self.default_language.currentIndex()]
        self.batch_ids = {i.id for i in self.queue.items if i.status in ('Queued', 'Retry', 'Cancelled')}
        for item in self.queue.items:
            if item.status in ('Queued', 'Retry', 'Cancelled'): item.options['default_language'] = default
        self.cancel_event.clear()
        self.launch(lambda emit: run_batch(self.queue.items, self.session.name, self.cancel_event, lambda *x: emit(x)), self.batch_done)
    def cancel(self):
        self.cancel_event.set(); self.status.setText('Cancelling the current document. Completed copies remain available to Save prepared PDFs.')
    def batch_done(self, _):
        prepared = sum(i.result is not None for i in self.queue.items)
        drafts = sum(needs_attention(i.result) for i in self.queue.items)
        failed = sum(i.status == 'Failed' for i in self.queue.items)
        self.status.setText(('Batch cancelled. ' if self.cancel_event.is_set() else 'Preparation finished. ') +
            f'{prepared} prepared • {drafts} draft(s) • {failed} could not be prepared. Choose Save prepared PDFs to save available copies.')
        flagged = [i for i in self.queue.items if i.id in getattr(self, 'batch_ids', {v.id for v in self.queue.items}) and (needs_attention(i.result) or i.status in ('Failed', 'Password needed', 'Signature consent needed'))]
        if flagged:
            summaries = []
            for item in flagged:
                why = reasons(item.result) if item.result else [explanation(item).split('\n')[0]]
                for reason in why:
                    if reason not in summaries: summaries.append(reason)
            summary = '\n'.join('• ' + reason for reason in summaries[:3])
            if len(summaries) > 3: summary += '\n• Select a file below to see its other details.'
            self.attention_text.setText(f'{len(flagged)} file(s) need attention. ' +
                'The other files have continued normally.\n' + summary +
                '\n\nWould you like to review these items now? You can also save the available results as drafts.')
            self.attention_box.show()
        self.selection()

    def dismiss_attention(self):
        self.attention_box.hide()
        self.status.setText('Manual review skipped. Choose Save prepared PDFs to keep the prepared PDFs and their reports. Unresolved copies remain drafts.')

    def set_review_view(self):
        self.main_tools.setVisible(not self.review_open); self.instructions.setVisible(not self.review_open)
        self.queue_label.setVisible(not self.review_open); self.files.setVisible(not self.review_open)
        self.heading.setText('Review this PDF' if self.review_open else 'Prepare your PDFs')

    def leave_review(self):
        self.remember_review(); self.review_open = False; self.loaded_review = None
        self.review_box.hide(); self.file_summary.show(); self.manual_button.show(); self.set_review_view()
        self.selection()

    def open_manual_review(self, checked=False):
        if self.busy() or not self.active or not self.active.result: return
        self.review_all = True; self.review_open = True; self.attention_box.hide(); self.selection()

    def open_input(self, checked=False):
        if self.busy() or not self.active: return
        self.review_open = True; self.attention_box.hide(); self.selection()

    def review_flagged(self):
        if self.busy(): return
        self.attention_box.hide(); self.review_open = True; self.review_all = False
        for row, item in enumerate(self.queue.items):
            if needs_attention(item.result) or item.status in ('Password needed', 'Signature consent needed', 'Failed'):
                self.files.selectRow(row); self.selection(); return
        self.leave_review()

    def on_event(self, event):
        kind = event[0]
        if kind in ('start', 'progress', 'done'):
            _, item_id, n, total, *detail = event
            self.progress.setMaximum(max(1, total)); self.progress.setValue(n - 1 if kind != 'done' else n)
            self.status.setText(f'Processing {n} of {total}' + (f' — {detail[0]}' if detail else ''))
            if kind != 'progress': self.refresh()
        elif kind == 'save': self.status.setText(f'Saving {event[1]} of {event[2]}')
        elif kind == 'review': self.status.setText(str(event[1]))
    def selection(self):
        self.set_review_view()
        r = self.files.currentRow()
        if r < 0 or r >= len(self.queue.items):
            self.remember_review(); self.review_box.hide(); self.active = None; self.loaded_review = None; self.review_open = False; self.set_review_view()
            self.manual_button.setEnabled(False); self.input_button.hide(); self.file_summary.setText('Select a PDF to see its result.'); return
        self.remember_review()
        self.active = item = self.queue.items[r]
        self.file_summary.setText(Path(item.source).name + '\n' + explanation(item))
        self.manual_button.setEnabled(bool(item.result) and not self.busy())
        self.input_button.setVisible(item.status in ('Password needed', 'Signature consent needed', 'Failed') and not self.review_open)
        self.file_summary.setVisible(not self.review_open); self.manual_button.setVisible(not self.review_open)
        if not self.review_open:
            self.review_box.hide(); self.loaded_review = None; return
        self.review_box.setTitle(('Manual review — ' if item.result else 'Help with this PDF — ') + Path(item.source).name)
        self.review_box.setVisible(bool(item.result or item.error))
        self.detail.setText(explanation(item))
        need_password = item.status == 'Password needed'; need_signature = item.status == 'Signature consent needed'
        self.password.setVisible(need_password); self.password.clear()
        self.signature.setVisible(need_signature); self.signature.setChecked(False)
        self.retry.setVisible(need_password or need_signature or item.status == 'Failed')
        self.edit_box.setVisible(item.result is not None)
        self.navigation_box.setVisible(item.result is not None)
        if not item.result: return
        self.next_file_button.setVisible(sum(bool(i.result) for i in self.queue.items) > 1)
        result = item.result
        validation_message = 'Optional review. Automatic checks passed; no manual review is required.' if not needs_attention(result) else 'Review only what needs attention. You can leave anything for later and save a draft.'
        self.detail.setText(Path(item.source).name + '\n' + validation_message)
        self.main_split.setSizes([100, 600])
        self.title_field.setText(result['title']); self.language.setText(result['language'])
        self.reviewed = {i['id'] for i in result['issues'] if i['reviewed']}
        self.tables = []; self.lists = []
        self.questions.blockSignals(True); self.questions.clear()
        grouped = []
        for original in result['issues']:
            if not self.review_all and (not original.get('required', True) or original['reviewed']): continue
            issue = copy.deepcopy(original); issue['ids'] = [issue['id']]
            if issue['kind'] in ('graphics', 'figures', 'nested_drawing'):
                existing = next((v for v in grouped if v['kind'] == 'pictures' and v['page'] == issue['page']), None)
                if existing: existing['ids'].append(issue['id']); continue
                issue['kind'] = 'pictures'
                issue['message'] = 'Describe the pictures or drawings on this page. Explain what each shows and what someone who cannot see it needs to know. Include all important labels, dimensions and units. Select each picture below to add its description.'
            grouped.append(issue)
        if result['validator']['status'] != 'passed' or not grouped:
            grouped.append({'id':'validation-summary', 'ids':[], 'kind':'validation_summary', 'page':None, 'reviewable':False, 'reviewed':False, 'message':explanation(item)})
        for issue in grouped:
            self.questions.addItem(('Page ' + str(issue['page']) if issue['page'] else 'Document') + ' — ' + issue['kind'].replace('_', ' '), issue)
        self.questions.blockSignals(False)
        draft = self.review_drafts.get(item.id)
        self.load_elements(draft['elements'] if draft else result['elements'])
        if draft:
            self.title_field.setText(draft['title']); self.language.setText(draft['language']); self.reviewed = set(draft['reviewed']); self.tables = draft['tables']; self.lists = draft['lists']
            self.questions.setCurrentIndex(next((n for n in range(self.questions.count()) if self.questions.itemData(n)['id'] == draft.get('question_id')), min(max(draft['step'], 0), self.questions.count() - 1)))
        self.loaded_review = item.id
        self.language_choice.blockSignals(True); self.language_choice.setCurrentIndex({'en':0,'en-US':0,'en-GB':0,'es':1,'fr':2,'de':3}.get(self.language.text(),4)); self.language_choice.blockSignals(False)
        self.language.setVisible(self.language_choice.currentIndex() == 4); self.metadata_box.layout().labelForField(self.language).setVisible(self.language_choice.currentIndex() == 4)
        self.advanced_toggle.setChecked(False)
        self.question_changed()
    def load_elements(self, entries):
        self.elements.blockSignals(True)
        self.elements.setCurrentCell(-1, -1)
        self.elements.setRowCount(len(entries))
        for r, entry in enumerate(entries):
            label = QTableWidgetItem(f'{entry["page"]} / {r + 1}: {entry["label"]}')
            label.setData(Qt.UserRole, copy.deepcopy(entry)); label.setFlags(label.flags() & ~Qt.ItemIsEditable)
            self.elements.setItem(r, 0, label)
            roles = QComboBox(); roles.addItems(['P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'Figure', 'TH', 'TD', 'Span', 'LBody'])
            if entry['role'] not in [roles.itemText(n) for n in range(roles.count())]: roles.addItem(entry['role'])
            roles.setCurrentText(entry['role']); roles.setAccessibleName(f'Role for item {r + 1}'); self.elements.setCellWidget(r, 1, roles)
            self.elements.setItem(r, 2, QTableWidgetItem(entry.get('actual_text') or ''))
            self.elements.setItem(r, 3, QTableWidgetItem(entry.get('alt', '')))
            decorative = QCheckBox(); decorative.setChecked(entry.get('decorative', False)); decorative.setAccessibleName(f'Item {r + 1} is decorative')
            decorative.setEnabled(entry['kind'] == 'figure' and entry['mcid'] >= 0); self.elements.setCellWidget(r, 4, decorative)
        self.elements.blockSignals(False)
        self.description_selected()
    def description_selected(self, *args):
        row = self.elements.currentRow()
        item = self.elements.item(row, 0) if row >= 0 else None
        enabled = bool(item and item.data(Qt.UserRole)['kind'] == 'figure')
        self.description_editor.blockSignals(True)
        self.description_editor.setEnabled(enabled)
        self.description_editor.setPlainText(self.elements.item(row, 3).text() if enabled else '')
        self.description_editor.blockSignals(False)
    def description_changed(self):
        row = self.elements.currentRow()
        if row >= 0 and self.description_editor.isEnabled():
            self.elements.blockSignals(True)
            self.elements.item(row, 3).setText(self.description_editor.toPlainText())
            self.elements.blockSignals(False)
    def description_table_changed(self, item):
        if item.column() == 3:
            if item.row() == self.elements.currentRow(): self.description_selected()
            if item.row() == self.picture_choice.currentData(): self.picture_chosen()
    def current_elements(self):
        entries = []
        for r in range(self.elements.rowCount()):
            entry = copy.deepcopy(self.elements.item(r, 0).data(Qt.UserRole))
            entry.update(role=self.elements.cellWidget(r, 1).currentText(), alt=self.elements.item(r, 3).text(),
                         actual_text=self.elements.item(r, 2).text() or None,
                         decorative=self.elements.cellWidget(r, 4).isChecked())
            entries.append(entry)
        return entries
    def question_changed(self):
        issue = self.questions.currentData()
        if not issue or not self.active or not self.active.result: return
        n = self.questions.currentIndex(); total = self.questions.count()
        titles = {'metadata':'Check the document name and language', 'pictures':'Describe the pictures and drawings', 'reading':'Check the reading order', 'ocr':'Check the scanned text', 'visual_accessibility':'Check that the information is clear', 'layers':'Check the drawing layers'}
        title = titles.get(issue['kind'], 'Check this item' if issue['reviewable'] else 'This item needs extra help')
        self.step_label.setText(f'Step {n + 1} of {total}' + (f' • Page {issue["page"]}' if issue['page'] else '') + '\n' + title)
        messages = {'metadata':'Is the name below useful and easy to recognize? Check that the language matches the document.', 'reading':'Read the page from beginning to end. Does the content make sense in that order? If you are unsure, leave this for later. More editing tools are available below if changes are needed.', 'visual_accessibility':'Can the information be understood clearly? Check that text is readable, colors are not the only way to understand something, and pictures have useful explanations.'}
        self.question.setText(messages.get(issue['kind'], issue['message']) + ('' if issue['reviewable'] else '\nYou do not need to fix this here. Leave it for later; it will stay listed in the report.'))
        self.metadata_box.setVisible(issue['kind'] == 'metadata')
        self.back_button.setEnabled(n > 0); self.next_button.setEnabled(n < total - 1)
        self.apply_button.setVisible(n == total - 1)
        self.check.setVisible(issue['reviewable'])
        self.picture_choice.blockSignals(True); self.picture_choice.clear()
        if issue['kind'] == 'pictures':
            for row, entry in enumerate(self.current_elements()):
                if entry['kind'] == 'figure' and entry['page'] == issue['page']:
                    self.picture_choice.addItem(f'Picture or drawing {self.picture_choice.count() + 1}', row)
        self.picture_choice.blockSignals(False)
        visible = self.picture_choice.count() > 0
        self.picture_choice.setVisible(visible); self.simple_description.setVisible(visible)
        self.picture_text_box.setVisible(visible); self.picture_panel.setVisible(bool(issue['page']) or visible)
        self.picture_chosen()
        self.page_scroll.setVisible(bool(issue['page'])); self.zoom_box.setVisible(bool(issue['page']))
        self.check.blockSignals(True); self.check.setChecked(all(k in self.reviewed for k in issue.get('ids', [issue['id']])))
        self.check.setEnabled(issue['reviewable']); self.check.blockSignals(False)
        if issue['page']:
            pixmap = QPixmap(str(Path(self.active.result['directory']) / f'page-{issue["page"]}.png'))
            zoom = self.preview_zoom.value() / 100
            self.preview.setPixmap(pixmap.scaled(int(360 * zoom), int(190 * zoom), Qt.KeepAspectRatio, Qt.SmoothTransformation)); self.preview.show()
        else: self.preview.hide()
    def record_check(self, checked):
        issue = self.questions.currentData()
        if not issue: return
        if checked and issue['kind'] == 'pictures' and any(e['kind'] == 'figure' and e['page'] == issue['page'] and not e.get('decorative') and not e['alt'].strip() for e in self.current_elements()):
            self.check.blockSignals(True); self.check.setChecked(False); self.check.blockSignals(False)
            self.question.setText('Please add a description for each picture or drawing first. If you are unsure what to write, choose Not sure — leave for later.')
            return
        for key in issue.get('ids', [issue['id']]):
            if checked: self.reviewed.add(key)
            else: self.reviewed.discard(key)
    def language_chosen(self, index):
        if index < 4: self.language.setText(['en', 'es', 'fr', 'de'][index])
        self.language.setVisible(index == 4)
        self.metadata_box.layout().labelForField(self.language).setVisible(index == 4)
    def picture_chosen(self, *args):
        row = self.picture_choice.currentData()
        self.simple_description.blockSignals(True)
        self.simple_description.setPlainText(self.elements.item(row, 3).text() if row is not None else '')
        self.simple_description.blockSignals(False)
    def simple_description_changed(self):
        row = self.picture_choice.currentData()
        if row is not None: self.elements.item(row, 3).setText(self.simple_description.toPlainText())
    def review_step(self, offset):
        self.questions.setCurrentIndex(max(0, min(self.questions.count() - 1, self.questions.currentIndex() + offset)))
        self.review_scroll.verticalScrollBar().setValue(0)
    def skip_review_step(self):
        self.check.setChecked(False)
        if self.questions.currentIndex() < self.questions.count() - 1: self.review_step(1)
        else: self.status.setText('This item will remain in the report. Choose Finish review to keep your other answers.')
    def remember_review(self):
        if self.review_open and self.active and self.active.result and self.loaded_review == self.active.id:
            self.review_drafts[self.active.id] = {'title': self.title_field.text(), 'language': self.language.text(), 'elements': self.current_elements(), 'reviewed': list(self.reviewed), 'tables': copy.deepcopy(self.tables), 'lists': copy.deepcopy(self.lists), 'step': self.questions.currentIndex(), 'question_id': (self.questions.currentData() or {}).get('id')}
    def review_changed(self, item):
        self.remember_review()
        draft = self.review_drafts.get(item.id)
        if not draft or not item.result: return False
        def signature(entries):
            return [(e['object'], e['role'], e.get('alt', ''), e.get('actual_text') or None, bool(e.get('decorative'))) for e in entries]
        result = item.result
        return bool(draft['title'] != result['title'] or draft['language'] != result['language'] or
                    set(draft['reviewed']) != {i['id'] for i in result['issues'] if i['reviewed']} or
                    signature(draft['elements']) != signature(result['elements']) or draft['tables'] or draft['lists'])
    def next_review_file(self):
        if not self.queue.items: return
        start = self.files.currentRow()
        for offset in range(1, len(self.queue.items)):
            row = (start + offset) % len(self.queue.items)
            if self.queue.items[row].result and (self.review_all or needs_attention(self.queue.items[row].result)):
                self.files.selectRow(row); return
        self.status.setText('There are no other prepared PDFs. Finish this review, then choose Save prepared PDFs.')
    def move(self, direction):
        r = self.elements.currentRow(); target = r + direction
        if r < 0 or target < 0 or target >= self.elements.rowCount(): return
        entries = self.current_elements()
        if entries[r]['page'] != entries[target]['page']:
            self.status.setText('Move items within the same page. Cross-page restructuring needs a specialist.'); return
        entries[r], entries[target] = entries[target], entries[r]
        self.load_elements(entries); self.elements.selectRow(target); self.question_changed()
    def selected_entries(self):
        rows = sorted({i.row() for i in self.elements.selectedIndexes()})
        entries = self.current_elements()
        return [entries[r] for r in rows]
    def make_table(self):
        entries = self.selected_entries(); columns = self.columns.value()
        if not entries or len(entries) % columns or len(entries) < columns * 2:
            self.status.setText('Select a complete simple table, including a header row and at least one data row.'); return
        if len({e['page'] for e in entries}) != 1 or any(e['kind'] != 'text' for e in entries):
            self.status.setText('Select text cells on a single page.'); return
        self.tables.append({'rows': [[e['object'] for e in entries[i:i + columns]] for i in range(0, len(entries), columns)]})
        self.status.setText('Table correction recorded locally. Choose Finish review to keep these changes.')
    def make_list(self):
        entries = self.selected_entries()
        if len(entries) < 2 or len({e['page'] for e in entries}) != 1 or any(e['kind'] != 'text' for e in entries):
            self.status.setText('Select at least two text items on one page.'); return
        self.lists.append([e['object'] for e in entries]); self.status.setText('List correction recorded locally. Choose Finish review to keep these changes.')
    def apply_review(self):
        item = self.active
        if not item or not item.result: return
        entries = self.current_elements()
        edits = {'title': self.title_field.text(), 'language': self.language.text(), 'elements': entries,
                 'order': [e['object'] for e in entries], 'reviewed': list(self.reviewed), 'tables': self.tables, 'lists': self.lists}
        self.cancel_event.clear()
        def operation(emit):
            return isolated(item.source, item.result['directory'], {}, self.cancel_event,
                            lambda *x: emit(('review', x[0])), result=item.result, edits=edits)
        def done(value):
            kind, result = value
            if kind == 'result':
                item.result = result; item.status = result['status']; item.saved_hash = ''; self.review_drafts.pop(item.id, None); self.loaded_review = None
                self.status.setText('Review saved. Choose Review next PDF, or Save prepared PDFs when you are done. Items left for later remain in the report.')
            else: self.status.setText('Review cancelled; previous copy retained.' if kind == 'cancelled' else result.get('message', 'Review failed; previous copy retained.'))
            if self.active != item:
                self.refresh(); return
            self.selection()
            if kind == 'result':
                self.questions.setCurrentIndex(self.questions.count() - 1)
                self.step_label.setText('Your answers have been saved')
                self.question.setText('Choose Review next PDF to continue, or Back to files to save your prepared PDFs. Anything left for later stays in the report. Use Back if you want to change an answer.')
                self.check.hide(); self.apply_button.hide(); self.picture_panel.hide(); self.metadata_box.hide()
                self.advanced_toggle.setChecked(False)
                self.review_scroll.verticalScrollBar().setValue(0)
        self.launch(operation, done)
    def retry_item(self):
        if not self.active: return
        if self.active.status == 'Password needed': self.active.options['password'] = self.password.text(); self.password.clear()
        if self.active.status == 'Signature consent needed':
            if not self.signature.isChecked(): return
            self.active.options['signature_consent'] = True
        self.active.status = 'Retry'; self.active.error = ''; self.refresh()
        self.prepare()
    def save(self):
        self.remember_review()
        for row, item in enumerate(self.queue.items):
            if self.review_changed(item):
                self.review_open = True; self.review_all = True
                self.files.selectRow(row); self.selection()
                self.questions.setCurrentIndex(self.questions.count() - 1)
                self.question_changed()
                self.status.setText('One review has answers to keep. Choose Finish review for this PDF, then Save prepared PDFs.')
                self.review_scroll.verticalScrollBar().setValue(0)
                return
        folder = QFileDialog.getExistingDirectory(self, 'Save all prepared PDFs and reports', self.output_folder)
        if not folder: return
        self.attention_box.hide()
        self.output_folder = folder
        def done(value):
            saved, failed = value
            self.status.setText(f'Saved {len(saved)} PDFs and their reports. {len(failed)} save failures.' + (' ' + '; '.join(f'{next(Path(i.source).name for i in self.queue.items if i.id == k)}: {msg}' for k, msg in failed) if failed else ' Draft status is recorded in each report.'))
            self.folder_button.setEnabled(True)
        self.launch(lambda emit: save_all(self.queue.items, folder, lambda *x: emit(('save', *x))), done)
        # Saves are short transactions: finish each pair to avoid incomplete outputs.
        self.cancel_button.setEnabled(False)
    def open_folder(self):
        if self.output_folder: QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_folder))
    def help(self):
        QMessageBox.information(self, 'Using PDF Accessibility Prep',
            'Add several PDFs at once, or drop them into the window. Prepare PDFs processes each separately. Save prepared PDFs chooses one output folder. If an automatic check fails, read the explanation and choose Review now or Not now. Selecting a file never opens manual review by itself.\n\n'
            'Manual review is optional unless a specific problem needs human input. General checklists do not block saving. Drafts are allowed; a failed or missing automated check is never changed into a pass. English OCR is included in a complete portable build. Complex forms, graphics, equations, and layouts may require a specialist.\n\n'
            'Brightspace: open course Content, choose a module, then Upload/Create Upload Files, or Add Existing / browse. Upload the saved PDF and test the published view and download with a keyboard and screen reader. Menus vary by institution. Brightspace upload and the HTML checker do not repair or validate an attached PDF.\n\n'
            'No account, document upload, telemetry, or network access is used by processing. The full source and license notices are included in the source package.')
    def closeEvent(self, event):
        if self.busy():
            self.status.setText('Cancel the batch and wait for it to stop before closing. Completed copies remain available.'); event.ignore(); return
        if any(i.result and (i.saved_hash != i.result['sha256'] or self.review_changed(i)) for i in self.queue.items):
            if QMessageBox.question(self, 'Close with unsaved copies?', 'There are unsaved prepared copies. Close and discard these temporary copies?') != QMessageBox.Yes:
                event.ignore(); return
        self.session.cleanup(); event.accept()


def main():
    app = QApplication([])
    app.setApplicationName('PDF Accessibility Prep')
    configure_application(app)
    window = Window(); window.show()
    return app.exec()
