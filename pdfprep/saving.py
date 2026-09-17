# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations
from pathlib import Path
import html
import json
import os
import re
import shutil
from .model import sha256


def report(result):
    e = lambda x: html.escape(str(x))
    lines = ['<!doctype html><html lang="en"><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             '<title>PDF accessibility preparation report</title>',
             '<style>body{font:1rem/1.6 system-ui,sans-serif;max-width:70em;margin:2em auto;padding:0 1em}code{overflow-wrap:anywhere}table{border-collapse:collapse}td,th{padding:.5em;border:1px solid}h1,h2{line-height:1.25}</style>',
             '<main><h1>PDF accessibility preparation report</h1>',
             f'<p><strong>{e(result["status"])}</strong></p>',
             '<p>This report is not a legal compliance certificate or publication approval. Unresolved checks mean this copy is a draft.</p>',
             f'<p>Source: {e(result["source_name"])}<br>Title: {e(result["title"])}<br>Language: {e(result["language"])}<br>Pages: {result["page_count"]}</p>',
             f'<p>Prepared PDF SHA-256: <code>{e(result["sha256"])}</code><br>Original SHA-256: <code>{e(result["source_sha256"])}</code></p>',
             '<h2>Changes performed</h2><ul>']
    lines += [f'<li>{e(f)}</li>' for f in result['fixes']]
    v = result['validator']
    lines += ['</ul><h2>Independent automated validation</h2>',
              f'<p>Result: <strong>{e(v["status"])}</strong><br>Profile: {e(v.get("profile"))}<br>Version: {e(v.get("version", "Unavailable"))}<br>{e(v.get("reason", ""))}</p><ul>']
    lines += [f'<li>{e(f.get("specification"))} {e(f.get("clause"))}: {e(f.get("description"))}<br>{e(f.get("contexts"))}</li>' for f in v.get('failures', [])]
    lines += ['</ul><h2>Review and remaining issues</h2><ul>']
    for i in result['issues']:
        state = 'Human review recorded' if i['reviewed'] else ('Human review required' if i['reviewable'] else 'Unsupported / unresolved')
        lines.append(f'<li><strong>{state}</strong> — {"Page " + str(i["page"]) if i["page"] else "Document"}: {e(i["message"])}</li>')
    lines += ['</ul><h2>Page preservation</h2><p>Every page was compared at its original position.</p><ol>']
    lines += [f'<li>Page {p["page"]}: {p["width"]} × {p["height"]} points; rotation {p["rotation"]}; {e(p["appearance"])}; {p.get("vector_paths", 0)} vector paths checked for unchanged geometry and line styles; page boxes and drawing scale checked.</li>' for p in result['pages']]
    lines += ['</ol><h2>Image and drawing descriptions</h2>']
    descriptions = [v for v in result['elements'] if v['kind'] == 'figure' and v.get('alt', '').strip()]
    if not descriptions: lines.append('<p>No image or drawing descriptions recorded.</p>')
    for n, figure in enumerate(descriptions, 1):
        lines.append(f'<h3>Page {figure["page"]}, figure {n}</h3><p style="white-space:pre-wrap">{e(figure["alt"])}</p>')
    lines += ['<h2>Recorded corrections</h2>']
    if not result['reviews']: lines.append('<p>No human reviews recorded.</p>')
    for r in result['reviews']:
        lines.append(f'<pre style="white-space:pre-wrap">{e(json.dumps(r, ensure_ascii=False, indent=2))}</pre>')
    lines += ['<h2>Coverage limits</h2><ul>'] + [f'<li>{e(v)}</li>' for v in result['limitations']]
    lines += [f'</ul><p>Brightspace file compatibility: <strong>{e(result.get("brightspace", {}).get("status", "Not checked"))}</strong>. File size: {e(result.get("brightspace", {}).get("bytes", "Unknown"))} bytes. Local format checks only; course restrictions and actual upload remain untested.</p>']
    lines += ['<h2>Brightspace check</h2><p>In your course Content area, choose a module and use Upload/Create → Upload Files, or Add Existing / browse in the newer Content experience. Select the prepared PDF. Menus vary by institution. Check the published view and the downloaded PDF using keyboard and assistive technology. Uploading does not fix accessibility; an HTML checker does not validate an attached PDF. No Brightspace instance was tested by this application.</p></main></html>']
    return '\n'.join(lines)


def safe_stem(name):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', Path(name).stem).strip(' .')[:100] or 'Document'
    if value.upper() in {'CON', 'PRN', 'AUX', 'NUL', *[f'COM{i}' for i in range(1, 10)], *[f'LPT{i}' for i in range(1, 10)]}:
        value = '_' + value
    return value


def save_one(result, folder):
    folder = Path(folder)
    if not folder.is_dir(): raise OSError('Choose an existing writable output folder')
    source = Path(result['output'])
    if sha256(source) != result['sha256']: raise ValueError('Prepared copy changed after validation; prepare it again')
    prefix = safe_stem(result['source_name']) + '_prepared'
    for number in range(1, 100000):
        stem = prefix if number == 1 else f'{prefix}_{number}'
        pdf = folder / (stem + '.pdf')
        rep = folder / (stem + '_accessibility.html')
        # Both names reserved exclusively. Matching report names also force a suffix.
        created = []
        try:
            fd = os.open(pdf, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600); created.append(pdf)
            try:
                report_fd = os.open(rep, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600); created.append(rep)
            except BaseException:
                os.close(fd); raise
        except FileExistsError:
            for p in created: p.unlink(missing_ok=True)
            continue
        except BaseException:
            for p in created: p.unlink(missing_ok=True)
            raise
        try:
            with os.fdopen(fd, 'wb') as out, source.open('rb') as inp:
                shutil.copyfileobj(inp, out, 1024 * 1024); out.flush(); os.fsync(out.fileno())
            with os.fdopen(report_fd, 'w', encoding='utf-8') as out:
                out.write(report(result)); out.flush(); os.fsync(out.fileno())
            if sha256(pdf) != result['sha256']: raise OSError('Saved copy failed integrity verification')
            return str(pdf), str(rep)
        except BaseException:
            try: os.close(report_fd)
            except OSError: pass
            for p in created: p.unlink(missing_ok=True)
            raise
    raise OSError('Too many matching output filenames')


def save_all(items, folder, emit=lambda *a: None):
    saved, failures = [], []
    candidates = [i for i in items if i.result and i.saved_hash != i.result['sha256']]
    for n, item in enumerate(candidates, 1):
        emit(n, len(candidates), item.id)
        try:
            paths = save_one(item.result, folder)
            item.saved_hash = item.result['sha256']; saved.append((item.id, paths))
        except (OSError, ValueError) as ex:
            failures.append((item.id, str(ex)))
    return saved, failures
