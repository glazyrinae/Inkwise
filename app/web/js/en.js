// Английский интерфейс: русская строка из кода или страницы → перевод. Пробелы в
// ключах схлопнуты, {имя} — значение, которое подставит t()

export const EN = {
  // Полоса слева и области панели
  "Скрыть или показать структуру книги": "Show or hide the book structure",
  "Расширения: плагины": "Extensions: plugins",
  "Проверка орфографии: MCP-сервер": "Spell checking: MCP server",
  "Настройки книги": "Book settings",
  Структура: "Structure",
  "Добавить блок": "Add a block",
  Публикация: "Publication",
  "Импортировать книгу из публикации, собранной в Inkwise. Текущая книга уйдёт в корзину":
    "Import a book from a publication compiled in Inkwise. The current book goes to the trash",
  "Собрать публикацию: титульный лист, содержание, блоки по порядку, список источников. Берутся тексты, сохранённые на диске (Ctrl+S)":
    "Compile the publication: title page, contents, blocks in order, references. Texts saved to disk are used (Ctrl+S)",
  Расширения: "Extensions",
  "Импортировать плагин из архива .zip": "Import a plugin from a .zip archive",
  "Потяни, чтобы изменить ширину": "Drag to change the width",
  "Открой блок в структуре слева или добавь его кнопкой «+»":
    "Open a block in the structure on the left or add one with «+»",

  // Блоки и заголовки
  "Титульный лист": "Title page",
  Введение: "Introduction",
  Раздел: "Chapter",
  Заключение: "Conclusion",
  "Свой блок": "Custom block",
  Подраздел: "Section",
  Пункт: "Subsection",
  Подпункт: "Paragraph",
  "Название подраздела": "Section title",
  "Название пункта": "Subsection title",
  "Название подпункта": "Paragraph title",
  "Название раздела": "Chapter title",
  "Название блока, например: Реферат, Приложение А":
    "Block title, for example: Abstract, Appendix A",
  "Новое название": "New title",
  "Удалить «{label}» в корзину?": "Move «{label}» to the trash?",
  "Текст со всеми подразделами и источники лягут в папку .корзина в папке книги — оттуда блок можно вернуть. Книги на диске останутся.":
    "The text with all its sections and sources goes to the .корзина folder in the book folder — the block can be restored from there. Books on disk stay.",
  "Добавить подраздел": "Add a section",
  "Подключить книгу или веб-страницу": "Attach a book or a web page",
  Переименовать: "Rename",
  "Удалить в корзину": "Move to the trash",
  "Добавить: {what}": "Add: {what}",

  // Публикация
  "Не собрана: галка справа в заголовке «Публикация»":
    "Not compiled yet: the check mark in the «Publication» header",
  "Публикация: открыть на просмотр": "Publication: open for viewing",
  "Скачать: экспорт книги в Word. Внутри вся книга, её можно импортировать обратно":
    "Download: export the book to Word. The whole book is inside, it can be imported back",
  "Удалить публикацию": "Delete the publication",
  "Импортировать книгу из «{file}»?": "Import the book from «{file}»?",
  "Текущая книга целиком уйдёт в корзину — .корзина в папке книги, оттуда её можно вернуть.":
    "The whole current book goes to the trash — the .корзина folder in the book folder, it can be restored from there.",
  "Удалить публикацию? Её всегда можно собрать снова.":
    "Delete the publication? It can always be compiled again.",

  // Редакторы и цитаты
  "Открой текст блока слева: цитата встанет туда, где курсор":
    "Open a block's text on the left: the quote goes where the cursor is",
  "Текст блока не отвечает: обнови страницу и попробуй ещё раз":
    "The block's text does not respond: reload the page and try again",
  "Редактор не загрузился: office ещё запускается или не запущен":
    "The editor did not load: office is still starting or is not running",

  // Расширения
  "Плагинов нет: импортируй архив .zip кнопкой «+»": "No plugins: import a .zip archive with «+»",
  "не загружен": "not uploaded",
  "Заменить…": "Replace…",
  "Загрузить…": "Upload…",
  "{file}: разбираю…": "{file}: reading…",
  Убрать: "Remove",
  "Скачаны шрифты для office: {fonts}. Office поставит их сам примерно за минуту, открытые тексты при этом переподключатся. Чтобы новые шрифты появились в редакторе, обнови страницу.":
    "Fonts downloaded for office: {fonts}. Office installs them by itself in about a minute, open texts reconnect meanwhile. Reload the page to see the new fonts in the editor.",
  "Шаблон книги сейчас даёт «{other}»: выключи этот плагин в книге, чтобы работал «{plugin}».":
    "The book template now comes from «{other}»: turn that plugin off in the book for «{plugin}» to work.",
  "Включён в этой книге": "On in this book",
  Удалить: "Delete",
  "Удалить плагин «{plugin}»?": "Delete the «{plugin}» plugin?",
  "Папка плагина уйдёт в корзину плагинов — .корзина в папке плагинов, оттуда его можно вернуть.":
    "The plugin folder goes to the plugins trash — the .корзина folder in the plugins folder, it can be restored from there.",

  // Источники
  "Здесь нет папок и книг": "No folders or books here",
  Подключить: "Attach",
  "Скачиваю…": "Downloading…",
  "Подключить страницу": "Attach the page",
  Сохранить: "Save",
  "Убрать «{file}» из блока?": "Remove «{file}» from the block?",
  "Сама книга останется на диске.": "The book itself stays on disk.",
  "Файл удалится из папки блока.": "The file is deleted from the block folder.",
  "Сносок на этот источник в тексте блока: {count}. Они тоже удалятся, текст цитат останется.":
    "Footnotes to this source in the block's text: {count}. They are deleted too, the quoted text stays.",
  "Источники ({count})": "Sources ({count})",
  "Данные источника для ссылок": "Source data for citations",
  "Убрать из блока": "Remove from the block",
  "Веб-страница": "Web page",
  "Данные книги": "Book data",
  "Сноска на {page}-ю страницу файла": "Footnote to page {page} of the file",
  Сноска: "Footnote",
  "Адрес веб-страницы: https://…": "Web page address: https://…",
  "Папка выше": "Parent folder",
  Отмена: "Cancel",
  Авторы: "Authors",
  "Фамилия И. О., Фамилия И. О.": "Surname N., Surname N.",
  Заглавие: "Title",
  Издание: "Edition",
  "2-е изд., испр.": "2nd ed., rev.",
  Город: "City",
  "М.": "London",
  Издательство: "Publisher",
  Год: "Year",
  "Сдвиг страниц": "Page offset",
  "Печатный номер страницы = номер страницы в файле − сдвиг":
    "Printed page number = page number in the file − offset",
  Сайт: "Site",
  Хабр: "Medium",
  Адрес: "Address",
  "Дата обращения": "Accessed",
  "ДД.ММ.ГГГГ": "DD.MM.YYYY",
  "Когда страницу открывали; копия в блоке сохранена в этот день":
    "When the page was opened; the copy in the block was saved on that day",
  "Ссылка в блоке": "Link in the block",

  // Настройки и проверка орфографии
  "Оформление ссылок": "Citation style",
  "По этому правилу встают новые сноски, уже вставленные не меняются":
    "New footnotes follow this rule, footnotes already inserted do not change",
  Готово: "Done",
  "Проверка орфографии": "Spell checking",
  "MCP-сервер": "MCP server",
  "http://сервер:порт/mcp": "http://server:port/mcp",
  "Адрес, как его видит api из контейнера: localhost там — сам контейнер, этот компьютер — host.docker.internal. Пусто — проверка отключена":
    "The address as the api sees it from its container: localhost there is the container itself, this computer is host.docker.internal. Empty — checking is off",
  "Проверка орфографии отключена": "Spell checking is off",
  "Подключаюсь…": "Connecting…",
  "Подключено. Инструменты сервера: {tools}": "Connected. Server tools: {tools}",
  нет: "none",
  Закрыть: "Close",
};
