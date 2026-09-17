# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations
from pathlib import Path
import multiprocessing as mp
import shutil
import threading
import time
import psutil
from .model import sha256


def worker(pipe, source, directory, options, result=None, edits=None):
    # Parser diagnostics must not leak document content into routine logs.
    import pymupdf
    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    from .engine import prepare, review, NeedsInput
    try:
        emit = lambda *args: pipe.send(('progress', args))
        value = review(result, edits, emit) if result else prepare(source, directory, options, emit)
        pipe.send(('result', value))
    except NeedsInput as ex:
        pipe.send(('needs_input', {'kind': ex.kind, 'message': ex.message}))
    except BaseException as ex:
        # Avoid parser exception text containing extracted content.
        safe = str(ex) if type(ex) in (ValueError, OSError) else 'This PDF could not be processed safely. Try exporting it again from the source.'
        pipe.send(('error', {'type': type(ex).__name__, 'message': safe}))
    finally:
        pipe.close()


def stop_tree(process):
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in children:
            try: child.kill()
            except psutil.Error: pass
        parent.kill()
    except psutil.Error: pass
    process.join(timeout=3)


def isolated(source, directory, options, cancel, emit=lambda *a: None, result=None,
             edits=None, timeout=600, memory_limit=1536 * 1024 ** 2):
    context = mp.get_context('spawn')
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(send, source, str(directory), options, result, edits))
    process.start(); send.close()
    started = time.monotonic(); terminal = None
    try:
        monitor = psutil.Process(process.pid)
        while True:
            if cancel.is_set():
                terminal = ('cancelled', None); break
            if time.monotonic() - started > timeout:
                terminal = ('error', {'message': 'Processing exceeded the ten-minute safety limit.'}); break
            try:
                total = monitor.memory_info().rss + sum(c.memory_info().rss for c in monitor.children(recursive=True))
                if total > memory_limit:
                    terminal = ('error', {'message': 'Processing exceeded the memory safety limit. Use a smaller source export.'}); break
            except psutil.Error: pass
            if receive.poll(.05):
                try: kind, value = receive.recv()
                except EOFError: break
                if kind == 'progress': emit(*value)
                else:
                    terminal = (kind, value); break
            elif not process.is_alive(): break
    finally:
        stop_tree(process)
        receive.close()
    return terminal or ('error', {'message': 'The document worker stopped unexpectedly.'})


def run_batch(items, root, cancel, emit=lambda *a: None, runner=isolated):
    pending = [i for i in items if i.status in ('Queued', 'Cancelled', 'Retry')]
    known_hashes = {i.result['source_sha256']: i.id for i in items if i.result}
    for n, item in enumerate(pending, 1):
        if cancel.is_set(): break
        directory = Path(root) / item.id
        emit('start', item.id, n, len(pending))
        item.status = 'Processing'
        try:
            if Path(item.source).stat().st_size > 512 * 1024 ** 2:
                raise ValueError('This file exceeds the 512 MB safety limit. Use a smaller source export.')
            digest = sha256(item.source)
            if digest in known_hashes and known_hashes[digest] != item.id:
                item.status = 'Duplicate — skipped'
                item.error = 'Identical file content is already in this batch.'
                emit('done', item.id, n, len(pending)); continue
            # Reserve identity even if it fails; copied damaged PDFs should not be processed repeatedly.
            known_hashes[digest] = item.id
            kind, value = runner(item.source, directory, item.options, cancel,
                                 lambda *v: emit('progress', item.id, n, len(pending), *v))
            if kind == 'result':
                item.result = value; item.status = value['status']; item.error = ''
            elif kind == 'needs_input':
                item.status = 'Password needed' if value['kind'] == 'password' else 'Signature consent needed'
                item.error = value['message']
            elif kind == 'cancelled': item.status = 'Cancelled'
            else:
                item.status = 'Failed'; item.error = value['message']
        except (OSError, ValueError) as ex:
            item.status = 'Failed'; item.error = str(ex)
        finally:
            item.options.pop('password', None)
        if not item.result:
            shutil.rmtree(directory, ignore_errors=True)
        emit('done', item.id, n, len(pending))
    if cancel.is_set():
        for item in pending:
            if item.status == 'Queued' or item.status == 'Retry': item.status = 'Cancelled'
    emit('finished', '', 0, len(pending))
