# Contributing

Thanks for helping make PDF preparation easier to understand.

Start with a focused issue or pull request. Describe the problem, a small reproduction, and the behavior you expect. Synthetic PDFs are preferred; do not upload student records, proprietary drawings, credentials, or private documents.

Contributions intended for inclusion are submitted under AGPL-3.0-or-later, consistent with the repository license and GitHub's contribution terms. Submit only material you have the right to contribute. Third-party code must have a compatible license and retain its notices. No copyright assignment is required by this project.

Keep the main workflow simple: Add PDFs → Prepare PDFs → Review → Save All. Preserve originals, isolate failures, retain draft warnings, and never replace missing validation with a pass.

Install `requirements-dev.txt`, provide the resources described in `docs/DEVELOPER.md`, and run tests appropriate to the change with `python -m pytest tests -q`. For a Windows package, use `scripts/build.ps1`. Report exactly which tests ran and distinguish automated checks from native UI or screen-reader testing.
