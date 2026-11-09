"""Ручки окна выбора книги: папки библиотеки на диске и данные выбранной книги."""

from fastapi import APIRouter

from app.api.sources import SourceView, view
from app.service import library
from app.service.sources import recognize, store

router = APIRouter(tags=["library"])


@router.get("/library")
def browse_library(path: str | None = None) -> library.Folder:
    """Папка на диске для окна выбора книги; без path — корень библиотеки."""
    return library.browse(path)


@router.get("/library/source")
def read_library_source(path: str) -> SourceView:
    """Данные книги с диска для формы: подтверждённые раньше или найденные в ней."""
    file = library.find(path)
    source = store.saved(store.key(file)) or recognize.from_file(file)
    return view(source, file.suffix)
