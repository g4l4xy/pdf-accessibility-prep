"""Keep every test's language preferences away from the user's settings."""
import pytest
from PySide6.QtCore import QSettings
from pdfprep import i18n

@pytest.fixture(autouse=True)
def isolated_language_settings(tmp_path, monkeypatch):
    store = QSettings(str(tmp_path / 'language-test.ini'), QSettings.IniFormat)
    monkeypatch.setattr(i18n, 'settings', lambda: store)
    monkeypatch.setattr(i18n, '_active', None)
