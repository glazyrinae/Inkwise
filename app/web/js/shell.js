// Оболочка: слева структура книги, справа редакторы ONLYOFFICE — текст блока на правку
// и рядом книга или веб-страница на просмотр. Здесь кнопки полосы слева (структура,
// расширения, орфография, настройки), области панели слева, меню «+» у заголовка
// «Структура», галка сборки публикации и первая загрузка; остальное — в модулях рядом

import { addBlock, KINDS, syncOpenText } from "./blocks.js";
import { onHeadings, onTextReady } from "./bridge.js";
import { buildDocument } from "./document.js";
import * as editors from "./editors.js";
import { showExtensions } from "./extensions.js";
import { showError } from "./http.js";
import { openSettings, openSpelling } from "./settings.js";
import { setupSplitters } from "./splitters.js";
import { saved } from "./storage.js";
import { blocksNow, markOpen, showBook, showHeadings } from "./tree.js";

const chapters = document.getElementById("chapters");
// Что показывает панель слева, как боковая панель VS Code: кнопка в полосе и её области
const activities = {
  explorer: {
    button: document.getElementById("toggle-chapters"),
    views: chapters.querySelectorAll(".view[data-view]"),
  },
  extensions: {
    button: document.getElementById("open-extensions"),
    views: [document.getElementById("extensions-view")],
  },
};

// Панель слева показывает структуру книги или расширения. Щелчок по кнопке того, что
// уже открыто, скрывает панель; name null — панель скрыта
function showActivity(name) {
  chapters.hidden = name === null;
  for (const [key, activity] of Object.entries(activities)) {
    activity.button.setAttribute("aria-pressed", String(key === name));
    for (const view of activity.views) view.hidden = key !== name;
  }
  saved.set("activity", name ?? "hidden");
  if (name === "extensions") showExtensions().catch(showError);
}

// Области панели слева сворачиваются, как в VS Code: щелчок по заголовку области
function setupViews() {
  for (const view of document.querySelectorAll(".view[data-view]")) {
    const title = view.querySelector(".view-title");
    const key = `view.${view.dataset.view}`;
    const show = (open) => {
      view.classList.toggle("collapsed", !open);
      title.setAttribute("aria-expanded", String(open));
      saved.set(key, open ? null : "collapsed");
    };
    title.addEventListener("click", () => show(view.classList.contains("collapsed")));
    show(saved.get(key) !== "collapsed");
  }
}

// Меню «+»: виды блоков. Введение, заключение и титульный лист — по одному на книгу:
// когда он уже есть, пункт неактивен. Меню встаёт под кнопкой «+»
function setupAddMenu() {
  const menu = document.getElementById("add-menu");
  const button = document.getElementById("add-block");
  const single = ["title_page", "introduction", "conclusion"];
  menu.addEventListener("beforetoggle", (event) => {
    if (event.newState !== "open") return;
    const box = button.getBoundingClientRect();
    menu.style.top = `${box.bottom + 2}px`;
    menu.style.left = `${box.left}px`;
    const taken = blocksNow().map((block) => block.kind);
    menu.replaceChildren(
      ...Object.entries(KINDS).map(([kind, name]) => {
        const item = document.createElement("button");
        item.type = "button";
        item.textContent = name;
        item.disabled = single.includes(kind) && taken.includes(kind);
        item.addEventListener("click", () => {
          menu.hidePopover();
          addBlock(kind).catch(showError);
        });
        return item;
      }),
    );
  });
}

function onClick(id, action) {
  document.getElementById(id).addEventListener("click", () => action().catch(showError));
}

onClick("build-document", buildDocument);
onClick("open-spelling", openSpelling);
onClick("open-settings", openSettings);
for (const [key, { button }] of Object.entries(activities)) {
  button.addEventListener("click", () =>
    showActivity(button.getAttribute("aria-pressed") === "true" ? null : key),
  );
}
// Файлы в папки блоков можно класть и снаружи: дерево обновляется при возврате на вкладку
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) showBook().catch(showError);
});
editors.onChange(markOpen);
onTextReady(syncOpenText);
onHeadings(showHeadings);
setupAddMenu();
setupSplitters();
setupViews();
const activity = saved.get("activity") ?? "explorer";
showActivity(activity in activities ? activity : null);
showBook().then(editors.restore).catch(showError);
