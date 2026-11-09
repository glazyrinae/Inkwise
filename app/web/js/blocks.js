// Блоки книги: добавить, переименовать, переставить, унести в корзину; подразделы,
// пункты и подпункты в тексте раздела. Заголовки в открытом тексте ставит плагин
// (outline.js), поэтому перед правкой текст раздела открывается слева

import { outline } from "./bridge.js";
import * as editors from "./editors.js";
import { query, send } from "./http.js";
import { blocksNow, showBook } from "./tree.js";

export const KINDS = {
  title_page: "Титульный лист",
  introduction: "Введение",
  section: "Раздел",
  conclusion: "Заключение",
  custom: "Свой блок",
};
export const LEVELS = { 2: "Подраздел", 3: "Пункт", 4: "Подпункт" };
const NAMES = { 2: "подраздела", 3: "пункта", 4: "подпункта" };
// Название спрашиваем у раздела и своего блока, остальные называются сами
const ASK = {
  section: "Название раздела",
  custom: "Название блока, например: Реферат, Приложение А",
};

// Новый блок встаёт на своё место по ГОСТ, его текст сразу открывается слева. Блоки
// за ним сдвигаются: номера в именах их папок растут на один
export async function addBlock(kind) {
  const title = ASK[kind] ? prompt(ASK[kind])?.trim() : null;
  if (ASK[kind] && !title) return;
  const before = blocksNow().map((found) => found.path);
  const block = await send("POST", "/api/book/blocks", { kind, title });
  await follow(before, block.path);
  await editors.openFile(block.text);
}

// Новое название — у папки блока и, когда текст откроется, у заголовка в нём. Открытый
// текст переезжает вместе с папкой: ключ документа в office прежний, и правки, ещё не
// сохранённые на диск, остаются в редакторе
export async function renameBlock(block) {
  const title = prompt("Новое название", block.title)?.trim();
  if (!title || title === block.title) return;
  const before = blocksNow().map((found) => found.path);
  await send("PATCH", `/api/book/blocks${query({ path: block.path })}`, { title });
  await follow(before);
  const renamed = blocksNow()[before.indexOf(block.path)];
  if (renamed.text && editors.openPath("text") !== renamed.text) {
    await editors.openFile(renamed.text);
  }
}

// Блок перетащили на место перед target или после него. Номера разделов меняются: в
// открытом тексте номер поправит плагин, в остальных — когда их откроют
export async function moveBlock(path, target, after) {
  const order = blocksNow()
    .map((block) => block.path)
    .filter((found) => found !== path);
  order.splice(order.indexOf(target) + (after ? 1 : 0), 0, path);
  await send("PUT", "/api/book/blocks/order", { order });
  await follow(order);
  await syncOpenText();
}

// Блок уходит в корзину целиком: с текстом, источниками и копиями веб-страниц. Книги по
// ссылкам остаются на диске
export async function removeBlock(block, label) {
  const lines = [
    `Удалить «${label}» в корзину?`,
    "Текст со всеми подразделами и источники лягут в папку .корзина в папке книги — " +
      "оттуда блок можно вернуть. Книги на диске останутся.",
  ];
  if (!confirm(lines.join("\n\n"))) return;
  // Открытый текст закрываем: последние правки office сохранит уже в корзину
  editors.closeWhere((path) => path.startsWith(`${block.path}/`));
  await send("DELETE", `/api/book/blocks${query({ path: block.path })}`);
  await showBook();
}

// Подраздел в конце раздела, пункт в конце подраздела, подпункт в конце пункта. parent —
// заголовок, куда добавить; null — сам раздел. Номер ставит редактор
export async function addHeading(block, parent) {
  const level = parent ? parent.level + 1 : 2;
  const text = prompt(`Название ${NAMES[level]}`)?.trim();
  if (!text) return;
  await openText(block);
  editors.focusText();
  await outline({ action: "add", after: parent?.index ?? -1, level, text });
}

// Заголовок в дереве: курсор встаёт к нему в тексте раздела
export async function goToHeading(block, heading) {
  await openText(block);
  editors.focusText();
  await outline({ action: "go", index: heading.index });
}

// Заголовок и номер в открытом тексте — как у блока в дереве. Зовётся, когда текст
// открылся и когда блоки переставили. У титульного листа заголовка нет
export async function syncOpenText() {
  const block = blocksNow().find((found) => found.text === editors.openPath("text"));
  if (!block || block.kind === "title_page") return;
  const title = block.kind === "section" ? block.title : block.title.toUpperCase();
  await outline({ action: "sync", title, number: block.number });
}

async function openText(block) {
  if (editors.openPath("text") !== block.text) await editors.openFile(block.text);
}

// После переименования, перестановки или нового блока в середине открытые файлы
// переехали вместе с папками. before — пути блоков до правки в новом порядке: блок на том
// же месте в дереве — тот же. added — путь нового блока: на его месте в before пусто
async function follow(before, added = null) {
  await showBook();
  const after = blocksNow().map((block) => block.path);
  if (added) before.splice(after.indexOf(added), 0, null);
  for (const name of ["text", "material"]) {
    const open = editors.openPath(name);
    const index = before.findIndex((path) => open?.startsWith(`${path}/`));
    const moved = index < 0 ? open : after[index] + open.slice(before[index].length);
    if (moved !== open) await editors.openFile(moved);
  }
}
