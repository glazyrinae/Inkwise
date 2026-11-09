// Текст блока (открыт на правку): вставка цитаты со сноской, подсчёт и удаление сносок.
//
// Текст сноски — addin-поле Word, как у плагина Zotero. В поле невидимо лежат ключ
// источника (путь книги или адрес страницы) и страницы: по ключу сноски на источник
// находят, даже если его данные потом поправили
const CITATION_FIELD = "WRITER_CITATION ";

// Цитата встаёт туда, где курсор, сноска — сразу за ней; без цитаты — только сноска.
// Потом курсор возвращается в текст за знак сноски, и текст получает клавиатуру:
// можно сразу писать дальше
function insertQuote(message) {
  const plugin = window.Asc.plugin;
  window.Asc.scope.quote = message.quote;
  plugin.callCommand(
    function () {
      const document = Api.GetDocument();
      if (Asc.scope.quote) {
        const paragraph = Api.CreateParagraph();
        paragraph.AddText(Asc.scope.quote);
        document.InsertContent([paragraph], true);
      }
      // Курсор переходит в новую сноску: туда и встанет поле
      document.AddFootnote();
    },
    false,
    true,
    function () {
      const citation = { source: message.source, pages: message.pages };
      const field = {
        FieldId: "",
        Value: "ADDIN " + CITATION_FIELD + JSON.stringify(citation),
        Content: message.footnote,
      };
      plugin.executeMethod("AddAddinField", [field], function () {
        plugin.callCommand(
          function () {
            Api.GetDocument().GetCurrentFootEndnote().MoveCursorToNoteReference();
          },
          false,
          true,
          function () {
            plugin.executeMethod("FocusEditor");
          },
        );
      });
    },
  );
}

// Сноски текста на источник: сосчитать или, если message.remove, удалить вместе со
// знаком сноски в тексте; текст цитат остаётся. Сноску узнаём по ключу в её поле, а
// вставленную ещё без поля — по началу текста: заголовку и заглавию источника
function notes(message) {
  const plugin = window.Asc.plugin;
  plugin.executeMethod("GetAllAddinFields", [], function (fields) {
    window.Asc.scope.texts = (fields || [])
      .filter(function (field) {
        return citedSource(field) === message.source;
      })
      .map(function (field) {
        return field.Content.trim();
      })
      .filter(Boolean);
    window.Asc.scope.head = message.head || "";
    window.Asc.scope.remove = message.remove;
    plugin.callCommand(
      function () {
        const document = Api.GetDocument();
        const found = document.GetFootnotesFirstParagraphs().filter(function (paragraph) {
          const text = paragraph.GetText().trim();
          const marked = Asc.scope.texts.some(function (field) {
            return text.includes(field);
          });
          return marked || (Asc.scope.head !== "" && text.startsWith(Asc.scope.head));
        });
        if (Asc.scope.remove) {
          // Сноску удаляет её знак в тексте: выделяем его и удаляем
          found.forEach(function (paragraph) {
            paragraph.Select();
            document.GetCurrentFootEndnote().SelectNoteReference();
            document.GetRangeBySelect().Delete();
          });
        }
        return found.length;
      },
      false,
      message.remove,
      function (count) {
        window.top.postMessage({ writer: "notes", count: count }, "*");
      },
    );
  });
}

// Ключ источника из поля сноски; null — поле не наше или испорчено
function citedSource(field) {
  const start = field.Value.indexOf(CITATION_FIELD);
  if (start === -1) return null;
  try {
    return JSON.parse(field.Value.slice(start + CITATION_FIELD.length)).source;
  } catch (error) {
    return null;
  }
}
