"""Ручки панели «Расширения»: плагины, их включение и настройки в книге, файлы
настроек, импорт .zip и удаление."""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.service import fonts, plugins
from app.service.language import t

router = APIRouter(tags=["plugins"])


@router.get("/plugins")
def list_plugins() -> list[plugins.Plugin]:
    """Установленные плагины: манифест, включён ли в книге, настройки, ошибка."""
    return plugins.installed()


@router.put("/plugins/{plugin_id}", status_code=204)
def change_plugin(plugin_id: str, state: plugins.State) -> None:
    """Включает или выключает плагин в книге и сохраняет его настройки."""
    try:
        plugins.change(plugin_id, state)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.post("/plugins", status_code=201)
async def import_plugin(
    request: Request, content_type: Annotated[str | None, Header()] = None
) -> str:
    """Ставит плагин из архива .zip в теле запроса; в ответе — id плагина.

    Тело — сам архив с типом application/zip. Другой тип не принимаем: запрос с ним
    браузер не отправит с чужого сайта без разрешения CORS, а плагин — это код, который
    выполнит api.
    """
    if content_type != "application/zip":
        raise HTTPException(status_code=415, detail=t("Нужен архив .zip"))
    try:
        return plugins.install(await request.body())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.put("/plugins/{plugin_id}/files/{key}")
async def upload_file(
    plugin_id: str, key: str, name: str, request: Request
) -> plugins.Uploaded:
    """Файл настройки key в теле запроса, name — его имя. Плагин сразу разбирает его.

    Запрос PUT браузер не отправит с чужого сайта без разрешения CORS, а файл меняет
    оформление книги.
    """
    data = await request.body()
    try:
        # Разбор файла — секунды: пусть идёт в потоке, а api отвечает office
        return await run_in_threadpool(plugins.upload, plugin_id, key, name, data)
    except (ValueError, fonts.FontError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.delete("/plugins/{plugin_id}/files/{key}", status_code=204)
def remove_file(plugin_id: str, key: str) -> None:
    """Убирает файл настройки key: плагин работает без него."""
    plugins.forget(plugin_id, key)


@router.delete("/plugins/{plugin_id}", status_code=204)
def remove_plugin(plugin_id: str) -> None:
    """Уносит плагин в корзину плагинов."""
    plugins.remove(plugin_id)
