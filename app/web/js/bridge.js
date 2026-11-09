// Плагин «Цитата» (app/plugin) в обоих редакторах. Из книги он присылает выделенный текст
// и страницу: оболочка собирает у api цитату со сноской и отдаёт её плагину текста блока.
// Плагин текста ещё считает и удаляет сноски на источник, присылает текст на проверку
// орфографии и заголовки раздела для дерева, ставит заголовки по просьбе оболочки.
// Напрямую через Docs API с плагином не поговорить: это есть только в платной редакции
// ONLYOFFICE, поэтому плагин пишет оболочке в window.top

import * as editors from "./editors.js";
import { send, showError } from "./http.js";
import { t } from "./i18n.js";

let chapterPlugin = null; // окно плагина в редакторе текста: плагин сообщает о себе сам
const waiting = {}; // кто ждёт сообщения плагина текста: его тип → список resolve
let textReady = async () => {}; // текст открылся: оболочка ставит в нём заголовок и номер
let headingsChanged = () => {}; // заголовки открытого текста: дерево их показывает

export function onTextReady(listener) {
  textReady = listener;
}

export function onHeadings(listener) {
  headingsChanged = listener;
}

window.addEventListener("message", (event) => {
  const message = event.data;
  // api.js переписывается с редактором строками, плагин присылает объекты
  if (event.origin !== editors.officeOrigin || !message || typeof message !== "object") {
    return;
  }
  if (message.writer === "chapter-ready") {
    chapterPlugin = event.source;
    textReady().catch(showError);
  }
  if (message.writer === "headings") headingsChanged(message.headings);
  if (message.writer === "quote") cite(message).catch(showError);
  if (message.writer === "spelling") checkSpelling(message).catch(showError);
  const resolves = waiting[message.writer] ?? [];
  delete waiting[message.writer];
  for (const resolve of resolves) resolve(message);
});

// Действие с заголовками открытого текста раздела, см. outline.js в плагине. Заголовки
// после него плагин пришлёт сам, их покажет дерево
export async function outline(request) {
  if (!pluginReady()) await chapterMessage("chapter-ready");
  chapterPlugin.postMessage({ writer: "outline", request }, editors.officeOrigin);
}

// Сколько в тексте блока сносок на источник; remove — заодно удалить их. Текст должен
// быть открыт: файл на диске отстаёт от правок
export async function countNotes(material, remove) {
  if (!pluginReady()) await chapterMessage("chapter-ready");
  const answer = chapterMessage("notes");
  chapterPlugin.postMessage(
    { writer: "notes", source: material.source, head: material.head, remove },
    editors.officeOrigin,
  );
  return (await answer).count;
}

// Окно плагина закрыто, когда в редакторе открыли другой текст: плагин нового текста
// сообщит о себе сам
function pluginReady() {
  return chapterPlugin !== null && !chapterPlugin.closed;
}

async function cite({ text, page }) {
  if (!editors.openPath("text") || !pluginReady()) {
    throw new Error(t("Открой текст блока слева: цитата встанет туда, где курсор"));
  }
  editors.focusText();
  const quote = await send("POST", "/api/book/quote", {
    path: editors.openPath("material"),
    // GetCurrentPage считает страницы с 0, а у копии веб-страницы и EPUB их не знает
    page: Number.isInteger(page) ? page + 1 : null,
    text,
  });
  chapterPlugin.postMessage({ writer: "insert", ...quote }, editors.officeOrigin);
}

// Проверка орфографии — пока заглушка: api отвечает, что её ещё нет, и сообщает, дошёл ли
// текст и отвечает ли MCP-сервер
async function checkSpelling({ text }) {
  await send("POST", "/api/spelling", { text });
}

// Ждём сообщение плагина текста; не дождались — скорее всего, в редакторе ещё старая
// версия плагина
function chapterMessage(writer) {
  return new Promise((resolve, reject) => {
    const done = (message) => {
      clearTimeout(timer);
      resolve(message);
    };
    const timer = setTimeout(() => {
      waiting[writer] = waiting[writer]?.filter((other) => other !== done);
      reject(new Error(t("Текст блока не отвечает: обнови страницу и попробуй ещё раз")));
    }, 60000);
    (waiting[writer] ??= []).push(done);
  });
}
