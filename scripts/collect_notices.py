# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
from importlib.metadata import distributions
from pathlib import Path
import json
import shutil
import sys

root = Path(__file__).resolve().parents[1]
out = root / 'resources' / 'licenses'; out.mkdir(parents=True, exist_ok=True)
versions = {}
for dist in distributions():
    name = dist.metadata['Name']; versions[name] = dist.version
    for p in dist.files or []:
        if any(t in str(p).lower() for t in ('license', 'copying', 'notice')):
            src = Path(dist.locate_file(p))
            if src.is_file():
                target = out / name / str(p).replace('..', '_')
                target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, target)
python_license = Path(sys.base_prefix) / 'LICENSE.txt'
if python_license.exists(): shutil.copyfile(python_license, out / 'Python-LICENSE.txt')
(root / 'resources' / 'python-dependencies.json').write_text(json.dumps(versions, indent=2))
