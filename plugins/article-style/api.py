"""Научная статья: шаблон текста блока и публикации по выбранным требованиям.

Шаблоны собирает templates.py, их можно поправить и прямо в редакторе.
"""

from pathlib import Path

TEMPLATES = Path(__file__).with_name("templates")


def template(settings: dict[str, str]) -> Path:
    """Хук ядра: шаблон новых текстов и публикации — стили, поля, подписи."""
    return TEMPLATES / f"{settings['preset']}.docx"
