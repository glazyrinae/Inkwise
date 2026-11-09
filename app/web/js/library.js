// Окно выбора источника: адрес веб-страницы сверху, под ним папки библиотеки с книгами.
// Выбранное открывается в форме данных источника, а «Подключить» кладёт его в блок

import { query, request, send, showError } from "./http.js";
import { closeSource, showSource } from "./source-form.js";
import { saved } from "./storage.js";
import { t } from "./i18n.js";

const disk = document.getElementById("disk");
const diskPath = document.getElementById("disk-path");
const diskUp = document.getElementById("disk-up");
const diskList = document.getElementById("disk-list");
const webForm = document.getElementById("web-form");
let block = null; // блок, к которому подключаем источник
let connected = null; // что сделать с подключённым: ему передают путь ссылки или копии
let parent = null; // папка выше открытой

export async function chooseSource(blockPath, onConnected) {
  block = blockPath;
  connected = onConnected;
  webForm.reset();
  // Окно открываем там, где выбирали книгу в прошлый раз; той папки могло уже не
  // стать — тогда с корня библиотеки
  await showFolder(saved.get("diskFolder")).catch(() => showFolder(null));
  disk.showModal();
}

async function showFolder(path) {
  const folder = await request(`/api/library${path ? query({ path }) : ""}`);
  saved.set("diskFolder", folder.path);
  diskPath.textContent = folder.path;
  parent = folder.parent;
  diskUp.disabled = folder.parent === null;
  const items = [
    ...folder.folders.map((name) =>
      diskItem("📁", name, () => showFolder(`${folder.path}/${name}`)),
    ),
    ...folder.books.map((name) =>
      diskItem("📄", name, () => chooseBook(`${folder.path}/${name}`)),
    ),
  ];
  if (!items.length) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = t("Здесь нет папок и книг");
    items.push(empty);
  }
  diskList.replaceChildren(...items);
  diskList.scrollTop = 0;
}

function diskItem(icon, name, choose) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "file";
  button.textContent = `${icon} ${name}`;
  button.addEventListener("click", () => choose().catch(showError));
  const item = document.createElement("li");
  item.append(button);
  return item;
}

// Книгу выбрали на диске: сначала её данные — что распознал api, человек проверяет
async function chooseBook(path) {
  const view = await request(`/api/library/source${query({ path })}`);
  disk.close();
  showSource(path, view, t("Подключить"), async (source) => {
    const link = await send("POST", `/api/book/books${query({ block })}`, { path, source });
    closeSource();
    await connected(link);
  });
}

// Адрес веб-страницы: api скачивает её и находит данные, человек проверяет. После
// подтверждения в блок ложится копия текста страницы
async function chooseWebPage(url) {
  const button = webForm.querySelector("button");
  button.disabled = true;
  button.textContent = t("Скачиваю…");
  try {
    const view = await request(`/api/web/source${query({ url })}`);
    disk.close();
    showSource(view.source.url, view, t("Подключить"), async (source) => {
      const copy = await send("POST", `/api/book/web${query({ block })}`, source);
      closeSource();
      await connected(copy);
    });
  } finally {
    button.disabled = false;
    button.textContent = t("Подключить страницу");
  }
}

diskUp.addEventListener("click", () => showFolder(parent).catch(showError));
webForm.addEventListener("submit", (event) => {
  event.preventDefault();
  chooseWebPage(webForm.elements.namedItem("url").value.trim()).catch(showError);
});
