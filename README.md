[![GOSTwriter: привидение-гострайтер пишет пером работу по ГОСТ](docs/logo.svg)](docs/logo.svg)

GOSTwriter
==========

**Пишешь ты — по ГОСТ оформляет GOSTwriter.** Курсовая, диплом, отчёт или книга прямо в браузере: цитаты со сносками в один клик, оформление по образцу и сборка всей работы в один DOCX.

[![ГОСТ](https://img.shields.io/badge/%D0%93%D0%9E%D0%A1%D0%A2-7.32%E2%80%932017%20%C2%B7%20%D0%A0%207.0.5%E2%80%932008-E5484D)](#что-умеет)
[![ONLYOFFICE Docs](https://img.shields.io/badge/ONLYOFFICE_Docs-10.0-FF6F3D?logo=onlyoffice&logoColor=white)](https://www.onlyoffice.com/docs)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![python-docx](https://img.shields.io/badge/python--docx-1.2-2B579A)](https://python-docx.readthedocs.io/)
[![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.28-1F6FEB)](https://pymupdf.readthedocs.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Last commit](https://img.shields.io/github/last-commit/glazyrinae/GOSTwriter)](https://github.com/glazyrinae/GOSTwriter/commits/main)
[![Repo size](https://img.shields.io/github/repo-size/glazyrinae/GOSTwriter)](https://github.com/glazyrinae/GOSTwriter)

## Что умеет

- 🧱 **Структура по ГОСТ 7.32** — титульный лист, введение, разделы, заключение. Разделы и подразделы нумеруются сами, порядок меняют перетаскиванием.
- ✍️ **Редактор как Word** — ONLYOFFICE в браузере: таблицы, формулы, сноски, проверка орфографии.
- 📚 **Цитата со сноской в один клик** — выделил фразу в книге или на веб-странице, и в тексте цитата со сноской по ГОСТ Р 7.0.5 с номером страницы.
- 🎨 **Оформление по образцу** — загрузи PDF или Word, оформленный как надо: поля, шрифт, интервалы и заголовки перейдут в работу, недостающий шрифт скачается из Google Fonts.
- 📦 **Сборка в один DOCX** — титульный лист, содержание с номерами страниц, все разделы и список использованных источников.
- 🔄 **Экспорт и импорт** — тексты, данные источников и настройки едут внутри собранного DOCX: отправил файл, на другом компьютере импортировал. Книги из библиотеки остаются ссылками.

## Как это выглядит

### Цитата со сноской

Книга открыта рядом с текстом. Выделяешь фразу, правый клик, «Цитировать» — цитата встаёт в текст, а сноска внизу страницы: автор, заглавие, издательство, год и страница.

![Цитата из книги со сноской по ГОСТ](docs/demo-quote.gif)

### Оформление по образцу

В «Расширениях» загружаешь образец, например статью из журнала в PDF. GOSTwriter читает в нём лист, поля, шрифт, кегль, интервалы, заголовки и номер страницы и собирает работу так же.

![Образец в PDF — и работа пересобрана в его оформлении](docs/demo-sample.gif)

### Сборка работы

Галка в заголовке «Публикация» — и вся работа в одном DOCX: титульный лист, содержание с отточием и номерами страниц, разделы, таблицы, сноски, список источников.

![Сборка работы в один DOCX по ГОСТ](docs/demo-build.gif)

## Как запустить

Нужны Docker с Compose и `make`. Проверено на Linux (Ubuntu). На macOS и Windows нужен Docker Desktop, там не проверяли.

```bash
git clone https://github.com/glazyrinae/GOSTwriter.git
cd GOSTwriter
make init
```

`make init` создаст файл настроек `.env` (секрет и права впишет сам), соберёт приложение, скачает редактор ONLYOFFICE и запустит всё. Первый раз это занимает несколько минут: образы весят около 3,5 ГБ.

Открой **http://localhost:8020**. При первом запуске редактор готовится ещё минуту-две, пока ONLYOFFICE собирает шрифты: если текст не открылся, обнови страницу чуть позже.

## Первые шаги

1. **«+»** в заголовке «Структура» — добавь титульный лист, введение, разделы и заключение. Текст блока сразу откроется в редакторе.
2. **Скрепка** у блока — подключи книгу из своей папки (PDF, DJVU, EPUB…) или веб-страницу по адресу. Данные для сноски GOSTwriter ищет в самой книге — проверь и поправь их в форме.
3. **Щелчок по книге** в структуре откроет её справа. Выдели фразу → правый клик → **«Цитировать»**.
4. **Галка** в заголовке «Публикация» соберёт работу, **стрелка** у строки скачает DOCX.

## Полезно знать

- Работа лежит в папке `deploy/book`: блок — папка, текст — обычный `.docx`. Другую папку задаёт `BOOK_DIR` в `.env`.
- Книги для цитат GOSTwriter берёт из домашней папки и только читает их. Другую папку задаёт `LIBRARY_DIR` в `.env`.
- Остановить — `make compose-down`, запустить снова — `make compose-up`, обновить — `git pull && make init`.
- Всё работает на твоём компьютере: порты 8020 (GOSTwriter) и 8021 (редактор) открыты только для него.
- Редактор — [ONLYOFFICE Docs](https://github.com/ONLYOFFICE/DocumentServer) Community Edition (AGPL v3), его образ скачивается с Docker Hub.

## Для разработчиков

Как всё устроено — в [CLAUDE.md](CLAUDE.md), как писать плагины — в [PLUGINS.md](PLUGINS.md).
