// Книга (открыта на просмотр): пункт меню для цитаты и выделенный текст — оболочке.
//
// Выделить текст можно не везде: у DJVU и сканов PDF без текстового слоя просмотрщик его
// не отдаёт. Тогда в меню — сноска на страницу, а цитату пишут руками
function quoteMenuItem(selected) {
  return selected
    ? { id: "cite", text: tr("Цитировать") }
    : { id: "note", text: tr("Сноска на эту страницу") };
}

// Цитату со сноской собирает api, оболочке нужны текст и номер страницы
function sendQuote(text) {
  window.Asc.plugin.executeMethod("GetCurrentPage", [], function (page) {
    window.top.postMessage({ writer: "quote", text: text, page: page }, "*");
  });
}
