// Плагин «Цитата» в обоих редакторах оболочки. В книге (на просмотр) он даёт в меню
// «Цитировать». В тексте блока (на правку) вставляет цитату со сноской, считает и
// удаляет сноски, отправляет текст на проверку орфографии и ведёт заголовки раздела для
// дерева оболочки. Сами действия — в book.js, chapter.js, spelling.js и outline.js,
// здесь они связаны с меню и событиями редактора и с оболочкой.
//
// Напрямую через Docs API оболочка с плагином говорить не может: сообщения со страницы
// в плагин ONLYOFFICE пускает только в платной редакции. Поэтому плагин пишет оболочке
// в window.top, а она отвечает в окно плагина текста, которое запомнила по его первому
// сообщению.
(function () {
  const plugin = window.Asc.plugin;
  const selection = { Numbering: false, Math: false, ParaSeparator: "\n", TabSymbol: " " };
  let shown = ""; // заголовки, которые оболочка уже видела
  let pause = null; // заголовки читаем, когда курсор замер

  plugin.init = function () {
    if (!plugin.info.isViewMode) {
      window.top.postMessage({ writer: "chapter-ready" }, "*");
    }
  };

  // Пункт меню зависит от того, выделен ли текст: в книге — цитата или сноска на
  // страницу, в тексте — проверка выделенного или всего текста
  plugin.attachEvent("onContextMenuShow", function () {
    plugin.executeMethod("GetSelectedText", [selection], function (text) {
      const selected = Boolean(text && text.trim());
      const item = plugin.info.isViewMode
        ? quoteMenuItem(selected)
        : spellingMenuItem(selected);
      plugin.executeMethod("AddContextMenuItem", [{ guid: plugin.guid, items: [item] }]);
    });
  });

  plugin.attachContextMenuClickEvent("cite", function () {
    plugin.executeMethod("GetSelectedText", [selection], function (text) {
      sendQuote(text || "");
    });
  });

  plugin.attachContextMenuClickEvent("note", function () {
    sendQuote("");
  });

  plugin.attachContextMenuClickEvent("spelling", function () {
    plugin.executeMethod("GetSelectedText", [selection], function (text) {
      sendForSpelling(text || "");
    });
  });

  plugin.attachContextMenuClickEvent("spelling-chapter", sendChapterForSpelling);

  // Курсор двигается и при наборе текста: заголовки могли поменяться. Читаем их, когда
  // курсор замер, и сообщаем оболочке, только если они другие
  plugin.attachEvent("onTargetPositionChanged", function () {
    if (plugin.info.isViewMode) return;
    clearTimeout(pause);
    pause = setTimeout(function () {
      outline({ action: "read" }, function (headings) {
        if (JSON.stringify(headings) !== shown) sendHeadings(headings);
      });
    }, 1000);
  });

  function sendHeadings(headings) {
    shown = JSON.stringify(headings);
    window.top.postMessage({ writer: "headings", headings: headings }, "*");
  }

  // Команды тексту — только от самой оболочки
  window.addEventListener("message", function (event) {
    const message = event.data;
    if (event.source !== window.top || !message) return;
    if (message.writer === "insert") insertQuote(message);
    if (message.writer === "notes") notes(message);
    if (message.writer === "outline") {
      outline(message.request, function (headings) {
        sendHeadings(headings);
        if (message.request.action !== "read") plugin.executeMethod("FocusEditor");
      });
    }
  });
})();
