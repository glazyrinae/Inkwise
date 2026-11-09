// Форма данных источника для ссылок: перед подключением и по «✎» у него в дереве. Поля
// книги и веб-страницы — в своих fieldset, видна одна. Имя ссылки и пример сноски
// собирает api: правила оформления живут в одном месте

import { query, send, showError } from "./http.js";

const dialog = document.getElementById("source");
const form = document.getElementById("source-form");
const footnote = document.getElementById("source-footnote");
const kindFields = {
  book: document.getElementById("book-fields"),
  web: document.getElementById("web-fields"),
};
let sourcePath = null; // книга на диске, адрес страницы или ссылка в блоке
let sourceKind = null; // book или web
let sourceSave = null; // что сделать с данными по кнопке: подключить или сохранить

export function fileName(path) {
  return path.slice(path.lastIndexOf("/") + 1);
}

export function showSource(path, view, action, save) {
  const { source } = view;
  sourcePath = path;
  sourceKind = source.kind;
  sourceSave = save;
  document.getElementById("source-heading").textContent =
    source.kind === "web" ? "Веб-страница" : "Данные книги";
  document.getElementById("source-file").textContent =
    source.kind === "web" ? source.url : fileName(path);
  document.getElementById("source-submit").textContent = action;
  const warning = document.getElementById("source-warning");
  warning.textContent = view.warning;
  warning.hidden = !view.warning;
  // Поля чужого вида выключены: браузер не проверяет их и не ждёт их заполнения
  for (const [kind, fieldset] of Object.entries(kindFields)) {
    fieldset.hidden = fieldset.disabled = kind !== source.kind;
  }
  form.elements.namedItem("authors").value = source.authors.join(", ");
  form.elements.namedItem("title").value = source.title;
  for (const input of kindFields[source.kind].elements) input.value = source[input.name];
  showPreview(view);
  dialog.showModal();
}

export function closeSource() {
  dialog.close();
}

function readSource() {
  const source = {
    kind: sourceKind,
    authors: form.elements
      .namedItem("authors")
      .value.split(",")
      .map((author) => author.trim())
      .filter(Boolean),
    title: form.elements.namedItem("title").value.trim(),
  };
  for (const input of kindFields[sourceKind].elements) source[input.name] = input.value.trim();
  return source;
}

async function previewSource() {
  const view = await send("POST", `/api/sources/preview${query({ path: sourcePath })}`, readSource());
  showPreview(view);
}

function showPreview(view) {
  document.getElementById("source-link").textContent = view.link;
  document.getElementById("source-footnote-title").textContent = view.page
    ? `Сноска на ${view.page}-ю страницу файла`
    : "Сноска";
  footnote.textContent = view.footnote;
}

// Пустое заглавие и прочие ошибки проверки показываем на месте сноски, без окна
form.addEventListener("input", () =>
  previewSource().catch((error) => {
    footnote.textContent = error.message;
  }),
);
form.addEventListener("submit", (event) => {
  event.preventDefault();
  sourceSave(readSource()).catch(showError);
});
document.getElementById("source-cancel").addEventListener("click", () => dialog.close());
