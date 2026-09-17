# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
import multiprocessing
import sys

if __name__ == '__main__':
    multiprocessing.freeze_support()
    if '--self-test' in sys.argv:
        from pdfprep.selftest import main
    else:
        from pdfprep.app import main
    raise SystemExit(main())
