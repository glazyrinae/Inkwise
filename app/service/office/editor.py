"""Конфиг редактора ONLYOFFICE для файла книги: с ним оболочка открывает редактор.

Файл office скачивает у api по document.url, сохранённый присылает на callbackUrl —
см. callback.py.
"""

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import jwt

from app.service.book import blocks, paths, trash
from app.service.language import t
from app.service.office import formats
from app.settings.config import config

# Плагин «Цитата» из app/plugin. Compose монтирует его в office, в sdkjs-plugins/writer:
# редактор загружает конфиг плагина через fetch, и со своего адреса — без CORS
PLUGIN_DIR = Path(__file__).parents[2] / "plugin"
PLUGIN_GUID = json.loads((PLUGIN_DIR / "config.json").read_text())["guid"]


def api_js() -> str:
    """Адрес скрипта редактора на office: его грузит оболочка в браузере."""
    return f"{config.office.public_url}/web-apps/apps/api/documents/api.js"


def config_for(path: str) -> dict[str, Any]:
    """Конфиг DocsAPI.DocEditor для файла книги, подписанный общим с office секретом.

    Править можно только текст блока. Книги и прочие материалы открываем на просмотр,
    чтобы не испортить источник.

    Raises:
        FileNotFoundError: файла нет в книге.
        formats.UnsupportedFileError: редактор не открывает файлы такого типа.
    """
    file = paths.find(path)
    if not formats.can_open(path):
        raise formats.UnsupportedFileError(file.name)
    extension = formats.extension(path)
    editable = blocks.is_text(path)
    # Новый ключ после каждой записи файла: иначе office откроет свою копию из кеша,
    # а не файл, изменённый на диске. Путь в ключ не входит: переименованный блок
    # office откроет в той же сессии, со всеми правками
    stat = file.stat()
    version = f"{stat.st_dev}:{stat.st_ino}:{stat.st_mtime_ns}"
    editor: dict[str, Any] = {
        "document": {
            "fileType": extension,
            "key": hashlib.sha256(version.encode()).hexdigest(),
            "title": file.name,
            "url": f"{config.office.api_url}/api/files/{quote(path)}",
            "permissions": {"edit": editable},
        },
        "documentType": formats.EDITOR_TYPES[extension],
        "editorConfig": {
            "mode": "edit" if editable else "view",
            "lang": config.app.language,
            # Время открытия: если блок унесут в корзину, правки лягут в его копию
            # там, даже когда на его месте уже другой блок — см. callback.py
            "callbackUrl": f"{config.office.api_url}/api/office/callback?"
            + urlencode({"path": path, "opened": trash.stamp()}),
            "user": {"id": "author", "name": t(config.office.author)},
            "customization": {
                "forcesave": True,
                # Книгу рядом с текстом закрывают крестиком в заголовке редактора,
                # оболочка ловит его как onRequestClose
                "close": {"visible": not editable, "text": t("Закрыть")},
            },
            # В книге плагин даёт «Цитировать», в тексте вставляет цитату со сноской
            "plugins": {"pluginsData": [_plugin_url()], "autostart": [PLUGIN_GUID]},
        },
        "width": "100%",
        "height": "100%",
    }
    secret = config.office.jwt_secret.get_secret_value()
    editor["token"] = jwt.encode(editor, secret, algorithm="HS256")
    return editor


def _plugin_url() -> str:
    """Адрес конфига плагина в office с версией из его содержимого.

    Файлы плагинов office отдаёт с Cache-Control: immutable — браузер не спросит их
    снова целый год. Свои файлы office обновляет версией в начале пути
    (/10.0.0-…/sdkjs-plugins/…), так же делаем и мы: правка плагина меняет адрес.
    """
    digest = hashlib.sha256()
    for file in sorted(PLUGIN_DIR.iterdir()):
        digest.update(file.read_bytes())
    version = f"1.0.0-{digest.hexdigest()[:12]}"
    return f"{config.office.public_url}/{version}/sdkjs-plugins/writer/config.json"
