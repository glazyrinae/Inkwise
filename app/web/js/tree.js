// Структура книги в области «Структура» слева: блоки по порядку — титульный лист,
// введение, разделы, заключение, свои блоки. В блоке папка «Источники», в разделе —
// подразделы, пункты и подпункты из его текста. Название блока открывает текст,
// заголовок — место в тексте. Блоки переставляют, перетаскивая мышью. Публикация — в
// области «Публикация» под структурой

import {
  addHeading,
  goToHeading,
  KINDS,
  LEVELS,
  moveBlock,
  removeBlock,
  renameBlock,
} from "./blocks.js";
import { showDocument } from "./document.js";
import { draggable } from "./drag.js";
import * as editors from "./editors.js";
import { request, showError } from "./http.js";
import { attachSource, sourcesItem } from "./materials.js";
import { saved } from "./storage.js";

const sidebar = document.getElementById("chapters");
const tree = document.getElementById("tree");
const paperclip = document.getElementById("paperclip");
// Свёрнутые узлы: дерево перерисовывается целиком, а свёрнутое пусть таким и остаётся
const collapsed = new Set(JSON.parse(saved.get("collapsed") ?? "[]"));
let blocks = []; // блоки книги, как их последний раз прислал api
// Заголовки открытого текста от плагина: файл на диске отстаёт от правок
let live = { path: null, headings: [] };

export async function showBook() {
  const book = await request("/api/book");
  blocks = book.blocks;
  render();
  showDocument(book.document);
}

export function blocksNow() {
  return blocks;
}

// Плагин прислал заголовки открытого текста
export function showHeadings(headings) {
  live = { path: editors.openPath("text"), headings };
  render();
}

// Подсвечивает файлы, открытые в редакторах
export function markOpen() {
  for (const button of sidebar.querySelectorAll("[data-path]")) {
    button.classList.toggle("open", editors.isOpen(button.dataset.path));
  }
}

export function action(name, content, title, run) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `action ${name}`;
  button.title = title;
  button.append(content);
  button.addEventListener("click", (event) => {
    event.preventDefault(); // кнопка в строке не сворачивает блок
    run().catch(showError);
  });
  return button;
}

// Сворачиваемый узел дерева: блок, заголовок, папку источников; что свёрнуто, помним
export function folding(key, row, children) {
  const body = document.createElement("div");
  body.className = "body";
  body.append(...children);
  const item = document.createElement("details");
  item.className = children.length ? "chapter" : "chapter leaf";
  item.open = !collapsed.has(key);
  item.addEventListener("toggle", () => {
    if (item.open) collapsed.delete(key);
    else collapsed.add(key);
    saved.set("collapsed", JSON.stringify([...collapsed]));
  });
  item.append(row, body);
  return item;
}

function render() {
  tree.replaceChildren(...blocks.map(blockItem));
  markOpen();
}

// Раздел подписан номером без точки, как по ГОСТ: «1 Методы испытаний»
function blockItem(block) {
  const label = block.number === null ? block.title : `${block.number} ${block.title}`;
  const children = nest(headingsOf(block)).map((heading, index) =>
    headingItem(block, heading, `${block.number}.${index + 1}`),
  );
  if (block.materials.length) children.unshift(sourcesItem(block));
  const row = document.createElement("summary");
  row.className = "row";
  row.append(titleOf(block, label));
  if (block.kind === "section") {
    row.append(action("add", "+", "Добавить подраздел", () => addHeading(block, null)));
  }
  row.append(
    action("attach", paperclip.content.cloneNode(true), "Подключить книгу или веб-страницу", () =>
      attachSource(block),
    ),
  );
  if (block.kind === "section" || block.kind === "custom") {
    row.append(action("edit", "✎", "Переименовать", () => renameBlock(block)));
  }
  row.append(action("remove", "✕", "Удалить в корзину", () => removeBlock(block, label)));
  draggable(row, block.path, (target, after) =>
    moveBlock(block.path, target, after).catch(showError),
  );
  return folding(block.path, row, children);
}

// Подраздел, пункт, подпункт: «1.1 Стендовые испытания». Щелчок ставит курсор к нему в
// тексте, «+» добавляет заголовок уровнем ниже
function headingItem(block, heading, number) {
  const title = document.createElement("button");
  title.type = "button";
  title.className = "title";
  title.textContent = `${number} ${heading.text}`;
  title.title = `${LEVELS[heading.level]} ${title.textContent}`;
  title.addEventListener("click", (event) => {
    event.preventDefault(); // щелчок по названию ведёт в текст, а не сворачивает
    goToHeading(block, heading).catch(showError);
  });
  const row = document.createElement("summary");
  row.className = "row";
  row.append(title);
  const lower = LEVELS[heading.level + 1];
  if (lower) {
    const add = () => addHeading(block, heading);
    row.append(action("add", "+", `Добавить: ${lower.toLowerCase()}`, add));
  }
  const children = heading.children.map((child, index) =>
    headingItem(block, child, `${number}.${index + 1}`),
  );
  return folding(`${block.path}#${number}`, row, children);
}

// Заголовки открытого текста — от плагина, остальных — из файла
function headingsOf(block) {
  return live.path && live.path === block.text ? live.headings : block.headings;
}

// Заголовки по порядку → дерево: пункт под своим подразделом. index — место заголовка
// в списке: по нему плагин находит его в тексте
function nest(headings) {
  const root = { level: 1, children: [] };
  const stack = [root];
  headings.forEach((heading, index) => {
    while (stack.at(-1).level >= heading.level) stack.pop();
    const node = { ...heading, index, children: [] };
    stack.at(-1).children.push(node);
    stack.push(node);
  });
  return root.children;
}

// Название открывает текст блока; если текста в папке нет, это просто подпись
function titleOf(block, label) {
  const title = document.createElement(block.text ? "button" : "span");
  title.className = "title";
  title.textContent = label;
  title.title = `${KINDS[block.kind]}: ${label}`;
  if (block.text) {
    title.type = "button";
    title.dataset.path = block.text;
    title.addEventListener("click", (event) => {
      event.preventDefault(); // клик по названию открывает текст, а не сворачивает блок
      editors.openFile(block.text).catch(showError);
    });
  }
  return title;
}
