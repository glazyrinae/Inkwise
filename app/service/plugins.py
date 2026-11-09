"""Плагины writer — папки в папке плагинов, как расширения VS Code, см. PLUGINS.md.

В папке плагина его манифест plugin.json и, если плагину есть что делать в api, модуль
api.py с хуками — функциями, которые зовёт ядро. Плагин ставят папкой или импортом
.zip, а включают и настраивают в каждой книге: это лежит в файле плагинов книги.

Модуль api.py ядро выполняет заново при каждом вызове хука. Поэтому импортированный
плагин работает сразу, без перезапуска api, а у плагина нет состояния между вызовами.

Настройка плагина — выбор из списка или файл. Файл загружают в панели «Расширения», он
лежит в папке плагина в книге, а хук получает его путь.
"""

import importlib.util
import io
import re
import shutil
import sys
import threading
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Literal

from pydantic import BaseModel, Field, TypeAdapter

from app.service import fonts
from app.service.book import paths
from app.settings.config import config

# Имя папки плагина — его id: латиница, цифры и «-»
ID = re.compile(r"[a-z0-9][a-z0-9-]*")
# Самый большой плагин при импорте, байт: и архив, и распакованный. В плагине код и
# шаблоны, а не книги
LIMIT = 20 * 2**20
# Модули плагина выполняются заново на каждый вызов хука: два вызова сразу не должны
# убирать модули друг у друга из-под ног
LOADING = threading.Lock()


class PluginError(Exception):
    """Плагин упал в хуке: в сообщении его название и ошибка."""


class Choice(BaseModel):
    """Настройка плагина из его манифеста: выбор из списка."""

    title: str = Field(description="Подпись", examples=["Требования к оформлению"])
    choices: dict[str, str] = Field(
        description="Из чего выбирать: ключ → название",
        examples=[{"article": "Научная статья"}],
    )
    default: str = Field(description="Ключ по умолчанию", examples=["article"])


class File(BaseModel):
    """Настройка плагина из его манифеста: файл, его загружают в панели."""

    kind: Literal["file"] = Field(description="Вид настройки")
    title: str = Field(description="Подпись", examples=["Образец оформления"])
    accept: list[str] = Field(
        description="Расширения файла, строчными", examples=[[".pdf", ".docx"]]
    )


class Manifest(BaseModel):
    """plugin.json: что за плагин и какие у него настройки."""

    name: str = Field(description="Название", examples=["Научная статья"])
    version: str = Field(description="Версия", examples=["0.1.0"])
    description: str = Field(default="", description="Что делает плагин")
    settings: dict[str, Choice | File] = Field(
        default_factory=dict, description="Настройки: ключ → поле"
    )


class State(BaseModel):
    """Плагин в книге: включён ли и как настроен. Пока не трогали — включён."""

    enabled: bool = Field(default=True, description="Включён в этой книге")
    values: dict[str, str] = Field(
        default_factory=dict,
        description="Настройки в этой книге: ключ → выбранное или имя файла",
        examples=[{"preset": "article"}],
    )


class Plugin(Manifest, State):
    """Плагин для панели «Расширения»: манифест и состояние в этой книге."""

    id: str = Field(description="Папка плагина", examples=["article-style"])
    details: str | None = Field(
        description="Что плагин сообщает о себе в этой книге, хук describe",
        examples=["Текст: Times New Roman 14 пт, интервал 1,5"],
    )
    error: str | None = Field(
        description="Почему плагин не работает; null — работает",
        examples=["No module named 'pandas'"],
    )


class Uploaded(BaseModel):
    """Файл настройки принят, плагин его разобрал."""

    fonts: list[str] = Field(
        description="Шрифты, которые api скачал для office", examples=[["PT Serif"]]
    )
    shadowed_by: str | None = Field(
        description="Плагин, чей шаблон книга берёт раньше шаблона этого; null — нет",
        examples=["Научная статья"],
    )


STATES = TypeAdapter(dict[str, State])


def installed() -> list[Plugin]:
    """Плагины из папки плагинов по имени папки, с их состоянием в этой книге."""
    found = []
    states = _states()
    for folder in _folders():
        state = states.get(folder.name, State())
        manifest = Manifest(name=folder.name, version="")
        details = error = None
        # Плагин — чужой код: показываем, почему он не работает, а не роняем панель
        try:
            manifest = _manifest(folder)
            describe = getattr(_module(folder), "describe", None)
            if describe and state.enabled:
                details = describe(_hook_values(folder.name, manifest, state))
        except Exception as failure:  # noqa: BLE001
            error = f"{type(failure).__name__}: {failure}"
        found.append(
            Plugin(
                id=folder.name,
                **manifest.model_dump(),
                enabled=state.enabled,
                values=_values(manifest, state),
                details=details,
                error=error,
            )
        )
    return found


def change(plugin_id: str, state: State) -> None:
    """Включает или выключает плагин в книге и сохраняет его настройки.

    Raises:
        FileNotFoundError: такого плагина нет.
        ValueError: у плагина нет такой настройки или такого значения в ней.
    """
    manifest = _manifest(_folder(plugin_id))
    for key, value in state.values.items():
        setting = manifest.settings.get(key)
        if isinstance(setting, File):
            continue
        if setting is None or value not in setting.choices:
            raise ValueError(f"У плагина нет настройки {key} = {value}")
    states = _states()
    # Файл настройки меняет только загрузка, см. upload
    files = {
        key: value
        for key, value in states.get(plugin_id, State()).values.items()
        if isinstance(manifest.settings.get(key), File)
    }
    states[plugin_id] = State(enabled=state.enabled, values={**state.values, **files})
    _save(states)


def upload(plugin_id: str, key: str, name: str, data: bytes) -> Uploaded:
    """Кладёт файл настройки key в папку плагина в книге и сразу готовит по нему
    шаблон: плагин разбирает файл, ядро ставит в office шрифты шаблона. В ответе —
    скачанные для office шрифты и плагин, чей шаблон книга берёт раньше этого.

    Прежний файл удаляется, только когда новый подошёл. Иначе плагин падал бы на каждом
    новом блоке, а так остаётся прежнее оформление.

    Raises:
        FileNotFoundError: такого плагина нет.
        ValueError: у плагина нет такой настройки-файла или файл не того вида.
        PluginError: плагин не разобрал файл.
        fonts.FontError: шрифта из шаблона нет ни в office, ни в Google Fonts.
    """
    folder = _folder(plugin_id)
    manifest = _manifest(folder)
    setting = manifest.settings.get(key)
    if not isinstance(setting, File):
        raise ValueError(f"У плагина нет настройки-файла {key}")
    # Скрытые имена — для файлов самого плагина рядом, например кеша
    named = name == Path(name).name and not paths.hidden(name)
    if not named or Path(name).suffix.lower() not in setting.accept:
        raise ValueError(f"Нужен файл {', '.join(setting.accept)}")
    states = _states()
    state = states.get(plugin_id, State())
    old = state.values.get(key)
    files = _book_files(plugin_id)
    files.mkdir(parents=True, exist_ok=True)
    paths.replace(files / name, data)
    state = State(enabled=state.enabled, values={**state.values, key: name})
    try:
        chosen = _template(folder, manifest, state)
        downloaded = fonts.install(chosen) if chosen else []
    except Exception:
        if name != old:
            (files / name).unlink()
        raise
    if old and old != name:
        (files / old).unlink(missing_ok=True)
    states[plugin_id] = state
    _save(states)
    return Uploaded(fonts=downloaded, shadowed_by=_shadowing(plugin_id))


def forget(plugin_id: str, key: str) -> None:
    """Убирает файл настройки key из книги: плагин работает без него.

    Raises:
        FileNotFoundError: такого плагина нет.
    """
    _folder(plugin_id)
    states = _states()
    state = states.get(plugin_id, State())
    name = state.values.pop(key, None)
    if name:
        (_book_files(plugin_id) / name).unlink(missing_ok=True)
    states[plugin_id] = state
    _save(states)


def template() -> Path | None:
    """Хук template: шаблон текстов и публикации от первого включённого плагина, у
    которого он есть; None — шаблон решает ядро.

    Raises:
        PluginError: плагин упал.
    """
    states = _states()
    for folder in _folders():
        state = states.get(folder.name, State())
        if not state.enabled:
            continue
        try:
            manifest = _manifest(folder)
        except Exception as failure:
            raise PluginError(f"{folder.name}: {failure}") from failure
        chosen = _template(folder, manifest, state)
        if chosen:
            return chosen
    return None


def install(archive: bytes) -> str:
    """Ставит плагин из .zip; в ответе — его id. Прежняя версия плагина уходит в
    корзину плагинов.

    В архиве одна папка, названная как плагин, в ней plugin.json: так получается
    архив папки плагина, например zip -r article-style.zip article-style.

    Raises:
        ValueError: это не архив плагина или он больше LIMIT.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            plugin_id = _check(zipped, len(archive))
            # Распаковываем рядом в скрытую папку: её не видно в списке, а в папку
            # плагина она переезжает одним rename
            unpacked = _root() / f".{plugin_id}.new"
            shutil.rmtree(unpacked, ignore_errors=True)
            zipped.extractall(unpacked)
    except zipfile.BadZipFile:
        raise ValueError("Это не архив .zip") from None
    try:
        _manifest(unpacked / plugin_id)
    except ValueError:
        shutil.rmtree(unpacked)
        raise
    folder = _root() / plugin_id
    if folder.exists():
        _to_trash(folder)
    (unpacked / plugin_id).rename(folder)
    unpacked.rmdir()
    return plugin_id


def remove(plugin_id: str) -> None:
    """Уносит папку плагина в корзину плагинов: оттуда его можно вернуть руками.

    Raises:
        FileNotFoundError: такого плагина нет.
    """
    _to_trash(_folder(plugin_id))


def _check(zipped: zipfile.ZipFile, size: int) -> str:
    """id плагина в архиве.

    Raises:
        ValueError: в архиве не одна папка плагина, нет plugin.json или он слишком
            большой.
    """
    names = [PurePosixPath(info.filename) for info in zipped.infolist()]
    if size + sum(info.file_size for info in zipped.infolist()) > LIMIT:
        raise ValueError(f"Плагин больше {LIMIT // 2**20} МБ")
    # Имя папки — id плагина. Абсолютный путь или «..» в архиве его не пройдут
    tops = {name.parts[0] for name in names if name.parts}
    plugin_id = tops.pop() if len(tops) == 1 else ""
    if not ID.fullmatch(plugin_id):
        raise ValueError(
            "В архиве должна быть одна папка плагина: латиница, цифры и «-»"
        )
    if PurePosixPath(plugin_id, "plugin.json") not in names:
        raise ValueError(f"В папке {plugin_id} архива нет plugin.json")
    return plugin_id


def _shadowing(plugin_id: str) -> str | None:
    """Название плагина, чей шаблон книга берёт раньше шаблона plugin_id: шаблон даёт
    первый включённый плагин по имени папки."""
    states = _states()
    for folder in _folders():
        if folder.name == plugin_id:
            return None
        state = states.get(folder.name, State())
        try:
            manifest = _manifest(folder)
            chosen = _template(folder, manifest, state) if state.enabled else None
        except (ValueError, PluginError):
            continue
        if chosen:
            return manifest.name
    return None


def _template(folder: Path, manifest: Manifest, state: State) -> Path | None:
    """Хук template одного плагина.

    Raises:
        PluginError: плагин упал.
    """
    try:
        hook = getattr(_module(folder), "template", None)
        chosen = hook(_hook_values(folder.name, manifest, state)) if hook else None
    except Exception as failure:
        raise PluginError(f"{folder.name}: {failure}") from failure
    return Path(chosen) if chosen else None


def _values(manifest: Manifest, state: State) -> dict[str, str]:
    """Настройки плагина в книге: выбранное или по умолчанию, если выбора нет или
    плагин его больше не знает; у файла — его имя, пусто — файла нет."""
    values = {}
    for key, setting in manifest.settings.items():
        chosen = state.values.get(key, "")
        if isinstance(setting, File):
            values[key] = chosen
        else:
            values[key] = chosen if chosen in setting.choices else setting.default
    return values


def _hook_values(plugin_id: str, manifest: Manifest, state: State) -> dict[str, str]:
    """Настройки для хука: у файла — его путь в книге, пусто — файла нет."""
    values = _values(manifest, state)
    for key, setting in manifest.settings.items():
        if isinstance(setting, File) and values[key]:
            file = _book_files(plugin_id) / values[key]
            values[key] = str(file) if file.is_file() else ""
    return values


def _module(folder: Path) -> ModuleType | None:
    """Модуль api.py плагина, выполненный заново; None — у плагина его нет.

    Папка плагина — пакет: api.py берёт свои модули рядом, «from . import pdf». Прежние
    модули плагина забываем, иначе после его обновления работали бы старые.
    """
    file = folder / "api.py"
    if not file.is_file():
        return None
    name = f"writer_plugin_{folder.name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(
        name, file, submodule_search_locations=[str(folder)]
    )
    if spec is None or spec.loader is None:
        raise ImportError(file)
    with LOADING:
        for loaded in [key for key in sys.modules if key.split(".")[0] == name]:
            del sys.modules[loaded]
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


def _manifest(folder: Path) -> Manifest:
    """Манифест плагина.

    Raises:
        ValueError: манифеста нет или он не по стандарту.
    """
    file = folder / "plugin.json"
    if not file.is_file():
        raise ValueError(f"У плагина {folder.name} нет plugin.json")
    return Manifest.model_validate_json(file.read_bytes())


def _folder(plugin_id: str) -> Path:
    """Папка плагина.

    Raises:
        FileNotFoundError: такого плагина нет.
    """
    folder = _root() / plugin_id
    if not ID.fullmatch(plugin_id) or not folder.is_dir():
        raise FileNotFoundError(plugin_id)
    return folder


def _folders() -> list[Path]:
    """Папки плагинов по имени. Скрытые — корзина и недораспакованный архив."""
    root = _root()
    # Папку плагинов монтирует compose: без неё плагинов просто нет
    if not root.is_dir():
        return []
    return sorted(
        folder
        for folder in root.iterdir()
        if folder.is_dir() and not paths.hidden(folder.name)
    )


def _to_trash(folder: Path) -> None:
    trash = _root() / config.book.trash
    trash.mkdir(exist_ok=True)
    # С миллисекундами: обновление плагина и его удаление укладываются в одну секунду
    stamp = datetime.now().isoformat(" ", "milliseconds").replace(":", "-")
    folder.rename(trash / f"{stamp} {folder.name}")


def _states() -> dict[str, State]:
    file = _states_file()
    return STATES.validate_json(file.read_bytes()) if file.is_file() else {}


def _save(states: dict[str, State]) -> None:
    paths.replace(_states_file(), STATES.dump_json(states, indent=2))


def _states_file() -> Path:
    return paths.root() / config.book.plugins_file


def _book_files(plugin_id: str) -> Path:
    """Папка плагина в книге: файлы его настроек и что он хранит для этой книги."""
    return paths.root() / config.book.plugin_files / plugin_id


def _root() -> Path:
    return config.plugins.root
