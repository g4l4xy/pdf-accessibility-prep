# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import os
import uuid


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


@dataclass
class Item:
    source: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: str = 'Queued'
    result: dict | None = None
    options: dict = field(default_factory=dict)
    saved_hash: str = ''
    error: str = ''


class Queue:
    def __init__(self):
        self.items: list[Item] = []

    def add(self, paths):
        """No document parsing on the GUI thread; identity handles aliases/hard links."""
        added, duplicate, rejected = [], [], []
        keys = set()
        for item in self.items:
            try:
                s = os.stat(item.source)
                keys.add((s.st_dev, s.st_ino))
            except OSError:
                pass
        names = {os.path.normcase(os.path.realpath(i.source)) for i in self.items}
        for raw in paths:
            p = Path(raw).resolve()
            try:
                if not p.is_file() or p.suffix.lower() != '.pdf':
                    rejected.append(str(p)); continue
                s = p.stat()
                key = (s.st_dev, s.st_ino)
                name = os.path.normcase(str(p))
                if key in keys or name in names:
                    duplicate.append(str(p)); continue
                item = Item(str(p))
                self.items.append(item); added.append(item)
                keys.add(key); names.add(name)
            except OSError:
                rejected.append(str(p))
        return added, duplicate, rejected
