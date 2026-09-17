Synthetic sample PDFs are generated from source instead of stored in Git.
After installing dependencies and resources, run from the repository root:

python -c "from pathlib import Path; from pdfprep.fixtures import corpus; corpus(Path('fixtures'))"

Automated tests generate their own inputs in temporary directories.
See pdfprep/fixtures.py for scan, tagging, table, encryption and drawing generators.
