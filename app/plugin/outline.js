// Заголовки в тексте раздела (открыт на правку): список для дерева оболочки, заголовок
// и номер раздела, новый подраздел, пункт или подпункт, переход к заголовку.
//
// Раздел, подраздел, пункт, подпункт — абзацы со стилями «Heading 1»…«Heading 4».
// Номера им ставит сам редактор: стили связаны с многоуровневым списком (см.
// service/book/headings.py в api). Оболочка знает подраздел, пункт и подпункт по месту
// в их списке — том же, что api читает из файла.

// Действие с заголовками; в ответ — подразделы, пункты и подпункты по порядку: уровень
// и текст без номера.
//   read — только прочитать;
//   sync — заголовок блока: текст title, у раздела — номер number;
//   add — заголовок уровня level с текстом text в конце подраздела или пункта after
//         (место в списке; -1 — в конце раздела), под ним пустой абзац для текста;
//   go — курсор к заголовку index.
//
// Команды идут по очереди: запрос лежит в общем Asc.scope, и следующая команда,
// отправленная раньше ответа на эту, подменила бы его.
let outlineQueue = Promise.resolve();

function outline(request, callback) {
  outlineQueue = outlineQueue.then(function () {
    return new Promise(function (done) {
      runOutline(request, function (headings) {
        done();
        callback(headings);
      });
    });
  });
}

function runOutline(request, callback) {
  window.Asc.scope.request = request;
  window.Asc.plugin.callCommand(
    function () {
      const request = Asc.scope.request;
      const document = Api.GetDocument();
      // Все заголовки: уровень по стилю «Heading N»; без такого стиля — 0
      function headings() {
        return document.GetAllHeadingParagraphs().map(function (paragraph) {
          const style = paragraph.GetStyle();
          const match = style ? /^heading ([1-9])$/i.exec(style.GetName()) : null;
          return {
            paragraph: paragraph,
            level: match ? Number(match[1]) : 0,
            text: paragraph.GetText({ Numbering: false }).trim(),
          };
        });
      }
      // Подразделы, пункты и подпункты с названием — как в дереве оболочки
      function inTree(all) {
        return all.filter(function (heading) {
          return heading.level >= 2 && heading.level <= 4 && heading.text;
        });
      }
      const all = headings();
      const block = all.find(function (heading) {
        return heading.level === 1;
      });
      if (request.action === "sync" && block) {
        if (block.text !== request.title) {
          block.paragraph.RemoveAllElements();
          block.paragraph.AddText(request.title);
        }
        // Номер раздела — в начале текста заголовка вместе с номером списка. Без
        // списка заголовки без номеров: так велит шаблон, например APA
        const shown = /^(\d+)\s/.exec(block.paragraph.GetText());
        const numbering = block.paragraph.GetNumbering();
        if (numbering && request.number && (!shown || Number(shown[1]) !== request.number)) {
          numbering.SetStart(request.number);
        }
      }
      if (request.action === "add") {
        const parent = request.after >= 0 ? inTree(all)[request.after] : block;
        const level = parent ? parent.level : 1;
        const start = parent ? all.indexOf(parent) : -1;
        // Подраздел кончается там, где начинается следующий подраздел или раздел
        const next = all.find(function (heading, index) {
          return index > start && heading.level >= 1 && heading.level <= level;
        });
        const heading = Api.CreateParagraph();
        heading.AddText(request.text);
        heading.SetStyle(document.GetStyle("Heading " + request.level));
        const body = Api.CreateParagraph();
        if (next) {
          next.paragraph.InsertParagraph(heading, "before", true);
          next.paragraph.InsertParagraph(body, "before", true);
        } else {
          document.Push(heading);
          document.Push(body);
        }
        body.Select();
      }
      if (request.action === "go") {
        const found = inTree(all)[request.index];
        if (found) found.paragraph.GetRange().Select();
      }
      return inTree(request.action === "add" ? headings() : all).map(function (heading) {
        return { level: heading.level, text: heading.text };
      });
    },
    false,
    request.action !== "read",
    callback,
  );
}
