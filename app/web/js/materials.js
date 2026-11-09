// Источники блока: папка «Источники» в дереве, подключить книгу или веб-страницу,
// поправить данные источника, убрать из блока вместе со сносками на него

import { countNotes } from "./bridge.js";
import * as editors from "./editors.js";
import { query, request, send, showError } from "./http.js";
import { chooseSource } from "./library.js";
import { closeSource, fileName, showSource } from "./source-form.js";
import { action, folding, showBook } from "./tree.js";

// Скрепка у блока: книга с диска или веб-страница; подключённое сразу открывается справа
export async function attachSource(block) {
  await chooseSource(block.path, async (path) => {
    await showBook();
    await editors.openFile(path);
  });
}

// «✎» у материала: правка данных источника; ссылка получает имя по новым данным
export async function editSource(path) {
  const view = await request(`/api/book/source${query({ path })}`);
  showSource(path, view, "Сохранить", async (source) => {
    const renamed = await send("PUT", `/api/book/source${query({ path })}`, source);
    closeSource();
    await showBook();
    // Открытую книгу открываем заново под новым именем: старого пути уже нет
    if (editors.openPath("material") === path) await editors.openFile(renamed);
  });
}

// «✕» у материала: убрать его из блока. Сноски на него в тексте блока удаляются тоже —
// без источника в блоке они бы повисли, — а текст цитат остаётся
export async function removeMaterial(block, path) {
  const material = await request(`/api/book/material${query({ path })}`);
  let count = 0;
  if (block.text) {
    // Сноски ищет плагин в открытом тексте блока: файл на диске отстаёт от правок
    if (editors.openPath("text") !== block.text) await editors.openFile(block.text);
    count = await countNotes(material, false);
  }
  const lines = [
    `Убрать «${fileName(path)}» из блока?`,
    material.link ? "Сама книга останется на диске." : "Файл удалится из папки блока.",
  ];
  if (count) {
    lines.push(
      `Сносок на этот источник в тексте блока: ${count}. Они тоже удалятся, текст ` +
        "цитат останется.",
    );
  }
  if (!confirm(lines.join("\n\n"))) return;
  if (count) await countNotes(material, true);
  editors.closeWhere((open) => open === path);
  await send("DELETE", `/api/book/files${query({ path })}`);
  await showBook();
}

// Папка «Источники» в блоке, над заголовками раздела
export function sourcesItem(block) {
  const row = document.createElement("summary");
  row.className = "row";
  const title = document.createElement("span");
  title.className = "title";
  title.textContent = `Источники (${block.materials.length})`;
  row.append(title);
  const files = block.materials.map((path) => materialRow(block, path));
  return folding(`${block.path}/источники`, row, files);
}

function materialRow(block, path) {
  const open = document.createElement("button");
  open.type = "button";
  open.className = "file";
  open.dataset.path = path;
  open.textContent = path.split("/").pop();
  open.title = open.textContent;
  open.addEventListener("click", () => editors.openFile(path).catch(showError));
  const row = document.createElement("div");
  row.className = "row";
  row.append(
    open,
    action("edit", "✎", "Данные источника для ссылок", () => editSource(path)),
    action("remove", "✕", "Убрать из блока", () => removeMaterial(block, path)),
  );
  return row;
}
