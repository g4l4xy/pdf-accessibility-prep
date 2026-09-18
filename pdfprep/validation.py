# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations
from pathlib import Path
import os
import subprocess
import sys
import xml.etree.ElementTree as ET


def resources():
    if not getattr(sys, 'frozen', False) and os.environ.get('PDFPREP_RESOURCE_DIR'):
        return Path(os.environ['PDFPREP_RESOURCE_DIR'])
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1])) / 'resources'


def command():
    root = resources()
    java = root / 'jre' / 'bin' / ('java.exe' if os.name == 'nt' else 'java')
    # Use the windowless JVM when bundled; retain no-console flags for fallback.
    if os.name == 'nt' and java.with_name('javaw.exe').exists():
        java = java.with_name('javaw.exe')
    jars = list((root / 'verapdf' / 'bin').glob('*.jar'))
    if not java.exists() or not jars:
        return None
    return [str(java), '-Xmx512m', '-Djava.awt.headless=true', '-Dfile.encoding=UTF8',
            '--add-exports=java.base/sun.security.pkcs=ALL-UNNAMED', '-Duser.home=' + str(root.parent), '-Dapp.home=' + str(root / 'verapdf'),
            '-cp', str(root / 'verapdf' / 'bin' / '*'), 'org.verapdf.apps.GreenfieldCliWrapper']


def parse_report(raw):
    try:
        root = ET.fromstring(raw)
        for e in root.iter():
            e.tag = e.tag.rsplit('}', 1)[-1]
        versions = {e.get('id'): e.get('version') for e in root.iter('releaseDetails')}
        reports = list(root.iter('validationReport'))
        ua = [r for r in reports if 'PDF/UA-1' in r.get('profileName', '')]
        if len(ua) != 1:
            raise ValueError('Expected exactly one PDF/UA-1 report')
        r = ua[0]
        failures = []
        for rule in r.iter('rule'):
            if rule.get('status') == 'failed':
                failures.append({'clause': rule.get('clause'), 'specification': rule.get('specification'),
                                 'description': rule.findtext('description', ''),
                                 'contexts': [c.text or '' for c in rule.iter('context')]})
        summary = root.find('.//batchSummary')
        if summary is None or any(int(summary.get(k, '0')) for k in
                                  ('failedToParse', 'encrypted', 'outOfMemory', 'veraExceptions')):
            raise ValueError('Validator did not finish successfully')
        vr = summary.find('validationReports')
        if vr is None or int(vr.get('failedJobs', '0')):
            raise ValueError('Validator job failed')
        state = r.get('isCompliant')
        if state not in ('true', 'false'):
            raise ValueError('Missing compliance result')
        return {'status': 'passed' if state == 'true' and not failures else 'failed',
                'version': versions, 'profile': r.get('profileName'), 'failures': failures}
    except (ET.ParseError, ValueError, TypeError):
        return {'status': 'not performed', 'profile': 'PDF/UA-1',
                'reason': 'The validator returned an incomplete or unexpected report.'}


def validate(path, raw_path):
    cmd = command()
    if not cmd:
        return {'status': 'not performed', 'profile': 'PDF/UA-1',
                'reason': 'Bundled validator or Java runtime is unavailable.'}
    try:
        # No shell, URI loading, document scripts, or default PDF/A profile.
        with open(raw_path, 'wb') as out:
            p = subprocess.run(cmd + ['--flavour', 'ua1', '--format', 'xml',
                                      '--maxfailuresdisplayed', '20', str(path)],
                               stdout=out, stderr=subprocess.DEVNULL, timeout=120,
                               creationflags=0x08000000 if os.name == 'nt' else 0)
        raw = Path(raw_path).read_bytes()
        result = parse_report(raw)
        result['exit_code'] = p.returncode
        if p.returncode not in (0, 1) or (p.returncode != 0 and result['status'] == 'passed'):
            result['status'] = 'not performed'
            result['reason'] = 'Validator process did not complete normally.'
        return result
    except subprocess.TimeoutExpired:
        return {'status': 'not performed', 'profile': 'PDF/UA-1', 'reason': 'Validator timed out.'}
    except OSError:
        return {'status': 'not performed', 'profile': 'PDF/UA-1', 'reason': 'Validator could not start.'}
