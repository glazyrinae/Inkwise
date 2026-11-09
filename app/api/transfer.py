"""Импорт книги из публикации, собранной в writer. Экспорт — сама публикация: в её
скрытой части вся книга, см. service/book/transfer.py."""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request

from app.service.book import transfer
from app.service.language import t

router = APIRouter(tags=["book"])

# Документ Word. Запрос с таким типом браузер не отправит с чужого сайта без разрешения
# CORS, а импорт заменяет всю книгу
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.post("/book/import", status_code=204)
async def import_book(
    request: Request, content_type: Annotated[str | None, Header()] = None
) -> None:
    """Заменяет книгу книгой из публикации в теле запроса; прежняя уходит в корзину."""
    if content_type != DOCX:
        raise HTTPException(status_code=415, detail=t("Нужен документ Word .docx"))
    try:
        transfer.restore(await request.body())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
