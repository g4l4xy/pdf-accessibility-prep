# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
import errno
from pathlib import Path
from pdfprep import saving
from pdfprep.engine import prepare
from pdfprep.model import Queue, sha256
from pdfprep.fixtures import text_pdf


def test_disk_full_removes_partial_pair_and_continues(tmp_path, monkeypatch):
    sources = [text_pdf(tmp_path / f'{i}.pdf', label=str(i)) for i in range(2)]
    queue = Queue(); queue.add(sources)
    for n, item in enumerate(queue.items): item.result = prepare(item.source, tmp_path / f'work-{n}')
    original_copy = saving.shutil.copyfileobj; attempts = 0
    def fail_first(src, dst, length):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            dst.write(b'partial PDF')
            raise OSError(errno.ENOSPC, 'Injected disk-full condition')
        return original_copy(src, dst, length)
    monkeypatch.setattr(saving.shutil, 'copyfileobj', fail_first)
    dest = tmp_path / 'out'; dest.mkdir()
    saved, failures = saving.save_all(queue.items, dest)
    assert len(saved) == 1 and len(failures) == 1
    assert not (dest / '0_prepared.pdf').exists()
    assert not (dest / '0_prepared_accessibility.html').exists()
    assert (dest / '1_prepared.pdf').exists() and (dest / '1_prepared_accessibility.html').exists()
    assert queue.items[0].saved_hash == ''
    assert all(sha256(i.source) == i.result['source_sha256'] for i in queue.items)
    assert all(Path(i.result['output']).exists() for i in queue.items)


def test_unavailable_folder_does_not_discard_results(tmp_path):
    q = Queue(); q.add([text_pdf(tmp_path / 'original.pdf')])
    q.items[0].result = prepare(q.items[0].source, tmp_path / 'work')
    saved, failures = saving.save_all(q.items, tmp_path / 'unavailable')
    assert not saved and len(failures) == 1 and q.items[0].saved_hash == ''
    assert Path(q.items[0].result['output']).exists()
