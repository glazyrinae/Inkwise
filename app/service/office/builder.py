"""Содержание собранной книги: номера страниц в нём проставляет office.

Номер страницы знает только тот, кто раскладывает текст по страницам. Поэтому строки
содержания с номерами страниц заполняет ONLYOFFICE — его сервис Document Builder
(POST /docbuilder). Скрипт для него office скачивает у api по ссылке. Адрес файла
в скрипте записан прямо: по адресу из переменной office файл не скачивает.
"""

from urllib.parse import quote, urlencode

import httpx
import jwt

from app.service.language import t
from app.settings.config import config

# Под этим именем office отдаёт файл, сохранённый скриптом
RESULT = "book.docx"
# Скрипт Document Builder: открыть файл, заполнить содержание, сохранить
SCRIPT = f"""builder.OpenFile("{{url}}");
Api.GetDocument().UpdateAllTOC();
builder.SaveFile("docx", "{RESULT}");
builder.CloseFile();
"""


class BuilderError(Exception):
    """Office не заполнил содержание."""


def script(path: str) -> str:
    """Скрипт для office: заполнить содержание в файле книги path."""
    # quote оставляет в адресе только латиницу, цифры и «/_.-~»: кавычка или «\» из
    # имени файла скрипт не сломает
    return SCRIPT.format(url=f"{config.office.api_url}/api/files/{quote(path)}")


def fill_contents(path: str) -> bytes:
    """Файл книги path с заполненным содержанием: его собирает office.

    Raises:
        BuilderError: office не ответил за [office] timeout секунд или ответил ошибкой.
    """
    query = urlencode({"path": path})
    task: dict[str, object] = {
        "async": False,
        # Ссылка на скрипт: его отдаёт api, см. script()
        "url": f"{config.office.api_url}/api/office/builder?{query}",
    }
    secret = config.office.jwt_secret.get_secret_value()
    task["token"] = jwt.encode(task, secret, algorithm="HS256")
    try:
        with httpx.Client(
            base_url=config.office.internal_url, timeout=config.office.timeout
        ) as client:
            answer = client.post("/docbuilder", json=task).raise_for_status().json()
            if RESULT not in answer.get("urls", {}):
                # Что значит код ошибки — в документации Document Builder API
                raise BuilderError(
                    t("office ответил ошибкой {code}", code=answer.get("error"))
                )
            return client.get(answer["urls"][RESULT]).raise_for_status().content
    except httpx.HTTPError as error:
        raise BuilderError(
            t("office не ответил ({reason})", reason=type(error).__name__)
        ) from error
