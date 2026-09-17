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
from PySide6.QtGui import QDesktopServices, QPixmap, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QProgressBar, QGroupBox, QLineEdit, QFormLayout, QComboBox, QCheckBox, QPlainTextEdit,
    QScrollArea, QMessageBox, QSpinBox, QSplitter)
from .model import Queue
from .batch import run_batch, isolated
from .saving import save_all


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


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.queue = Queue(); self.cancel_event = threading.Event(); self.task = None
        self.session = tempfile.TemporaryDirectory(prefix='PDF-Accessibility-Prep-')
        try: os.chmod(self.session.name, 0o700)
        except OSError: pass
        self.output_folder = ''; self.active = None; self.reviewed = set(); self.tables = []; self.lists = []
        self.review_drafts = {}; self.loaded_review = None
        self.setWindowTitle('PDF Accessibility Prep'); self.resize(1050, 790); self.setMinimumSize(720, 520)
        self.setAcceptDrops(True)
        outer = QVBoxLayout(self)
        self.instructions = QLabel('1. Add your PDFs.  2. Select Prepare PDFs.  3. Review flagged items.  4. Save All.\nFiles stay on this computer. Drop multiple PDFs anywhere in this window.')
        self.instructions.setWordWrap(True); outer.addWidget(self.instructions)
        row = QHBoxLayout()
        self.add_button = button('&Add PDFs', self.choose)
        self.clear_button = button('C&lear All', self.clear)
        self.prepare_button = button('&Prepare PDFs', self.prepare)
        self.cancel_button = button('&Cancel batch', self.cancel); self.cancel_button.setEnabled(False)
        for b in (self.add_button, self.clear_button, self.prepare_button, self.cancel_button): row.addWidget(b)
        row.addStretch(); outer.addLayout(row)
        split = QSplitter(Qt.Vertical); self.main_split = split; outer.addWidget(split, 1)
        self.files = QTableWidget(0, 3); self.files.setHorizontalHeaderLabels(['PDF', 'Status', 'Remove'])
        self.files.setAccessibleName('PDF queue'); self.files.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.files.setSelectionMode(QAbstractItemView.SingleSelection); self.files.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.files.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.files.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.files.itemSelectionChanged.connect(self.selection)
        split.addWidget(self.files)
        self.review_box = QGroupBox('Review needed'); self.review_box.setVisible(False)
        review_layout = QVBoxLayout(self.review_box)
        self.review_scroll = QScrollArea(); self.review_scroll.setWidgetResizable(True)
        content = QWidget(); self.review_layout = QVBoxLayout(content)
        self.review_scroll.setWidget(content); review_layout.addWidget(self.review_scroll)
        split.addWidget(self.review_box); split.setSizes([160, 480])
        self.detail = QLabel(); self.detail.setWordWrap(True); self.detail.setTextFormat(Qt.PlainText)
        self.review_layout.addWidget(self.detail)
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password); self.password.setAccessibleName('PDF password')
        self.signature = QCheckBox('I authorize creating a derivative that may invalidate this digital signature.')
        self.retry = button('Use this password / consent and retry with Prepare PDFs', self.retry_item)
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
        self.back_button = button('← Back', lambda: self.review_step(-1))
        self.skip_button = button('Not sure — leave for later', self.skip_review_step)
        self.next_button = button('Next →', lambda: self.review_step(1))
        for widget in (self.back_button, self.skip_button, self.next_button): navigation.addWidget(widget)
        navigation_layout.addLayout(navigation)
        self.apply_button = button('Finish review for this PDF', self.apply_review); navigation_layout.addWidget(self.apply_button)
        self.next_file_button = button('Review next PDF →', self.next_review_file); navigation_layout.addWidget(self.next_file_button)
        review_layout.addWidget(self.navigation_box)
        self.review_layout.addWidget(self.edit_box)
        self.progress = QProgressBar(); self.progress.setAccessibleName('Batch progress'); outer.addWidget(self.progress)
        self.status = QLabel('Add one or more PDFs to begin.'); self.status.setWordWrap(True); self.status.setTextFormat(Qt.PlainText); self.status.setAccessibleName('Batch status'); outer.addWidget(self.status)
        bottom = QHBoxLayout()
        self.save_button = button('&Save All', self.save)
        self.folder_button = button('&Open Output Folder', self.open_folder); self.folder_button.setEnabled(False)
        bottom.addWidget(self.save_button); bottom.addWidget(self.folder_button); bottom.addStretch()
        bottom.addWidget(button('&Help', self.help)); outer.addLayout(bottom)
        QShortcut(QKeySequence('Delete'), self.files, activated=self.remove_selected)
        self.refresh()

    def busy(self): return self.task is not None and self.task.isRunning()
    def controls(self, busy):
        for w in (self.add_button, self.clear_button, self.prepare_button, self.save_button, self.apply_button, self.retry): w.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
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
        self.queue.items.clear(); self.active = None; self.review_drafts.clear(); self.loaded_review = None; self.session.cleanup()
        self.session = tempfile.TemporaryDirectory(prefix='PDF-Accessibility-Prep-'); self.refresh(); self.review_box.hide()
    def remove(self, item_id):
        if self.busy(): return
        item = next(i for i in self.queue.items if i.id == item_id)
        if item.result and (item.saved_hash != item.result['sha256'] or self.review_changed(item)):
            if QMessageBox.question(self, 'Remove unsaved copy?', 'Remove this unsaved prepared copy from the queue?') != QMessageBox.Yes: return
        self.review_drafts.pop(item.id, None)
        if self.active == item: self.active = None; self.loaded_review = None
        self.queue.items.remove(item); shutil.rmtree(Path(self.session.name) / item.id, ignore_errors=True)
        self.refresh(); self.selection()
    def remove_selected(self):
        r = self.files.currentRow()
        if r >= 0: self.remove(self.queue.items[r].id)
    def refresh(self):
        selected = self.active.id if self.active else None
        self.files.blockSignals(True); self.files.setRowCount(len(self.queue.items))
        for r, item in enumerate(self.queue.items):
            name = QTableWidgetItem(Path(item.source).name); name.setToolTip(item.source)
            state = item.status + (' · saved' if item.result and item.saved_hash == item.result['sha256'] else '')
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
            self.save_button.setEnabled(any(i.result and (i.saved_hash != i.result['sha256'] or self.review_changed(i)) for i in self.queue.items))
    def prepare(self):
        self.cancel_event.clear()
        self.launch(lambda emit: run_batch(self.queue.items, self.session.name, self.cancel_event, lambda *x: emit(x)), self.batch_done)
    def cancel(self):
        self.cancel_event.set(); self.status.setText('Cancelling the current document. Completed copies remain available to Save All.')
    def batch_done(self, _):
        ready = sum(i.result is not None for i in self.queue.items)
        failed = sum(i.status == 'Failed' for i in self.queue.items)
        self.status.setText(f'Batch stopped. {ready} prepared copies available; {failed} failures. Select flagged files to review, then Save All.' if self.cancel_event.is_set() else f'Batch finished. {ready} prepared copies available; {failed} failures. Select flagged files to review, then Save All.')
        self.selection()
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
        r = self.files.currentRow()
        if r < 0 or r >= len(self.queue.items): self.review_box.hide(); self.active = None; return
        self.remember_review()
        self.active = item = self.queue.items[r]
        self.review_box.setVisible(bool(item.result or item.error))
        self.detail.setText(Path(item.source).name + '\n' + (item.error or item.status))
        need_password = item.status == 'Password needed'; need_signature = item.status == 'Signature consent needed'
        self.password.setVisible(need_password); self.password.clear()
        self.signature.setVisible(need_signature); self.signature.setChecked(False)
        self.retry.setVisible(need_password or need_signature or item.status == 'Failed')
        self.edit_box.setVisible(item.result is not None)
        self.navigation_box.setVisible(item.result is not None)
        if not item.result: return
        result = item.result
        validation_message = {'passed': 'Automated PDF checks passed. Complete the requested human checks.', 'failed': 'Some automated accessibility checks failed. The saved report identifies remaining issues.', 'not performed': 'Automated validation could not be completed. This copy remains a draft.'}.get(result['validator']['status'], 'Checks incomplete.')
        self.detail.setText(Path(item.source).name + '\n' + validation_message)
        self.main_split.setSizes([100, 600])
        self.title_field.setText(result['title']); self.language.setText(result['language'])
        self.reviewed = {i['id'] for i in result['issues'] if i['reviewed']}
        self.tables = []; self.lists = []
        self.questions.blockSignals(True); self.questions.clear()
        grouped = []
        for original in result['issues']:
            issue = copy.deepcopy(original); issue['ids'] = [issue['id']]
            if issue['kind'] in ('graphics', 'figures', 'nested_drawing'):
                existing = next((v for v in grouped if v['kind'] == 'pictures' and v['page'] == issue['page']), None)
                if existing: existing['ids'].append(issue['id']); continue
                issue['kind'] = 'pictures'
                issue['message'] = 'Describe the pictures or drawings on this page. Explain what each shows and what someone who cannot see it needs to know. Include all important labels, dimensions and units. Select each picture below to add its description.'
            grouped.append(issue)
        for issue in grouped:
            self.questions.addItem(('Page ' + str(issue['page']) if issue['page'] else 'Document') + ' — ' + issue['kind'].replace('_', ' '), issue)
        self.questions.blockSignals(False)
        draft = self.review_drafts.get(item.id)
        self.load_elements(draft['elements'] if draft else result['elements'])
        if draft:
            self.title_field.setText(draft['title']); self.language.setText(draft['language']); self.reviewed = set(draft['reviewed']); self.tables = draft['tables']; self.lists = draft['lists']
            self.questions.setCurrentIndex(draft['step'])
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
        if self.active and self.active.result and self.loaded_review == self.active.id:
            self.review_drafts[self.active.id] = {'title': self.title_field.text(), 'language': self.language.text(), 'elements': self.current_elements(), 'reviewed': list(self.reviewed), 'tables': copy.deepcopy(self.tables), 'lists': copy.deepcopy(self.lists), 'step': self.questions.currentIndex()}
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
            if self.queue.items[row].result:
                self.files.selectRow(row); return
        self.status.setText('There are no other prepared PDFs. Finish this review, then choose Save All.')
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
                item.result = result; item.status = result['status']; self.review_drafts.pop(item.id, None); self.loaded_review = None
                self.status.setText('Review saved. Choose Review next PDF, or Save All when you are done. Items left for later remain in the report.')
            else: self.status.setText('Review cancelled; previous copy retained.' if kind == 'cancelled' else result.get('message', 'Review failed; previous copy retained.'))
            self.selection()
            if kind == 'result':
                self.questions.setCurrentIndex(self.questions.count() - 1)
                self.step_label.setText('Your answers have been saved')
                self.question.setText('Choose Review next PDF to continue, or Save All when you are done. Anything left for later stays in the report. Use Back if you want to change an answer.')
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
        self.status.setText('Ready to retry. Prepare PDFs will process all queued and retry files.')
    def save(self):
        self.remember_review()
        for row, item in enumerate(self.queue.items):
            if self.review_changed(item):
                self.files.selectRow(row)
                self.questions.setCurrentIndex(self.questions.count() - 1)
                self.question_changed()
                self.status.setText('One review has answers to keep. Choose Finish review for this PDF, then Save All.')
                self.review_scroll.verticalScrollBar().setValue(0)
                return
        folder = QFileDialog.getExistingDirectory(self, 'Save all prepared PDFs and reports', self.output_folder)
        if not folder: return
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
            'Add several PDFs at once, or drop them into the window. Prepare PDFs processes each separately. Select a flagged file to review it, then Save All chooses one output folder.\n\n'
            'Drafts are allowed. A missing check or unresolved issue never means a pass. English OCR is included in a complete portable build. Complex forms, graphics, equations, and layouts may require a specialist.\n\n'
            'Brightspace: open course Content, choose a module, then Upload/Create → Upload Files, or Add Existing / browse. Upload the saved PDF and test the published view and download with a keyboard and screen reader. Menus vary by institution. Brightspace upload and the HTML checker do not repair or validate an attached PDF.\n\n'
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
    window = Window(); window.show()
    return app.exec()
