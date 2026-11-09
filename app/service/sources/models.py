"""Данные источника: из них складываются имя ссылки в блоке и сноска."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Book(BaseModel):
    """Книга: из этих данных складываются имя ссылки в блоке и сноска."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # У записей, сохранённых до веб-страниц, поля kind нет: это книги
    kind: Literal["book"] = "book"
    authors: list[str] = Field(
        description="Авторы в форме заголовка по ГОСТ: «Фамилия И. О.»",
        examples=[["Харенслак Б.", "де Руйтер Дж."]],
    )
    title: str = Field(
        min_length=1,
        description="Заглавие",
        examples=["Apache Airflow и конвейеры обработки данных"],
    )
    edition: str = Field(
        description="Сведения об издании", examples=["2-е изд., испр."]
    )
    place: str = Field(description="Город издания", examples=["М."])
    publisher: str = Field(description="Издательство", examples=["ДМК Пресс"])
    year: str = Field(description="Год издания", examples=["2021"])
    page_offset: int = Field(
        description="На сколько номер страницы в файле больше печатного", examples=[1]
    )


class WebPage(BaseModel):
    """Веб-страница: её копия лежит в папке блока, из неё и цитируют."""

    model_config = ConfigDict(str_strip_whitespace=True)

    kind: Literal["web"]
    authors: list[str] = Field(
        description="Авторы в форме заголовка по ГОСТ: «Фамилия И. О.»",
        examples=[["Соколов А."]],
    )
    title: str = Field(
        min_length=1, description="Заглавие статьи", examples=["Все статьи подряд"]
    )
    site: str = Field(description="Название сайта", examples=["Хабр"])
    year: str = Field(description="Год публикации", examples=["2026"])
    url: str = Field(
        description="Адрес страницы, он же ключ её данных",
        examples=["https://habr.com/ru/articles/"],
    )
    accessed: str = Field(
        description="Дата обращения: когда сохранили копию", examples=["06.11.2026"]
    )


# Записи без kind — книги, поэтому union без дискриминатора: Pydantic сам выберет
# модель, с которой данные сходятся
Source = Book | WebPage
