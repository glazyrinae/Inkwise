// Текст блока (открыт на правку): проверка орфографии — пока заглушка. Текст уходит
// оболочке, та отдаёт его api, а api ответит, дошёл ли текст до MCP-сервера
function spellingMenuItem(selected) {
  return selected
    ? { id: "spelling", text: "Проверить орфографию" }
    : { id: "spelling-chapter", text: "Проверить орфографию всего текста" };
}

function sendForSpelling(text) {
  window.top.postMessage({ writer: "spelling", text: text }, "*");
}

// Весь текст блока: абзацы через перевод строки
function sendChapterForSpelling() {
  window.Asc.plugin.callCommand(
    function () {
      return Api.GetDocument()
        .GetAllParagraphs()
        .map(function (paragraph) {
          return paragraph.GetText();
        })
        .join("\n");
    },
    false,
    false,
    function (text) {
      sendForSpelling(text || "");
    },
  );
}
