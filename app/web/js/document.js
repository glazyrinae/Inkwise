// Публикация — собранная книга: галка «Собрать публикацию» в заголовке области
// «Публикация» под структурой. Публикация — единственный файл в корне книги, у остальных
// путь с папкой блока. Она же экспорт книги: в скрытой части — вся книга, стрелка у
// публикации её скачивает, стрелка в заголовке области импортирует

import * as editors from "./editors.js";
import { request, send, showError } from "./http.js";
import { action, showBook } from "./tree.js";
import { t } from "./i18n.js";

const DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
const area = document.getElementById("document");
const bookFile = document.getElementById("book-file");
const downloadIcon = document.getElementById("download-icon");
const isDocument = (path) => !path.includes("/");

// Повторная сборка заменяет прежнюю публикацию. Тексты берём сохранённые на диске
export async function buildDocument() {
  editors.closeWhere(isDocument);
  const path = await send("POST", "/api/book/document");
  await showBook();
  await editors.openFile(path);
}

// path — публикация; null — её ещё не собирали
export function showDocument(path) {
  if (path) {
    area.replaceChildren(documentRow(path));
    return;
  }
  const hint = document.createElement("p");
  hint.className = "empty";
  hint.textContent = t("Не собрана: галка справа в заголовке «Публикация»");
  area.replaceChildren(hint);
}

function documentRow(path) {
  const open = document.createElement("button");
  open.type = "button";
  open.className = "file";
  open.dataset.path = path;
  open.textContent = path;
  open.title = t("Публикация: открыть на просмотр");
  open.addEventListener("click", () => editors.openFile(path).catch(showError));
  const row = document.createElement("div");
  row.className = "row";
  row.append(
    open,
    action(
      "download",
      downloadIcon.content.cloneNode(true),
      t("Скачать: экспорт книги в Word. Внутри вся книга, её можно импортировать обратно"),
      async () => download(path),
    ),
    action("remove", "✕", t("Удалить публикацию"), removeDocument),
  );
  return row;
}

// Имя с датой и временем: файлы, скачанные в разное время, не перепутать
function download(path) {
  const link = document.createElement("a");
  link.href = `/api/files/${encodeURIComponent(path)}`;
  // Шведская запись даты — «2026-11-09 14:30:05», как ISO, но с пробелом
  const now = new Date().toLocaleString("sv-SE").slice(0, 16).replace(":", "-");
  link.download = `${t("Публикация")} ${now}.docx`;
  link.click();
}

// Импорт заменяет книгу целиком: дерево, открытые тексты и публикацию берём заново
async function importBook(file) {
  const question = [
    t("Импортировать книгу из «{file}»?", { file: file.name }),
    t(
      "Текущая книга целиком уйдёт в корзину — .корзина в папке книги, оттуда её можно " +
        "вернуть.",
    ),
  ].join("\n\n");
  if (!confirm(question)) return;
  await request("/api/book/import", {
    method: "POST",
    headers: { "Content-Type": DOCX },
    body: file,
  });
  location.reload();
}

async function removeDocument() {
  if (!confirm(t("Удалить публикацию? Её всегда можно собрать снова."))) return;
  editors.closeWhere(isDocument);
  await send("DELETE", "/api/book/document");
  await showBook();
}

document.getElementById("import-book").addEventListener("click", () => bookFile.click());
bookFile.addEventListener("change", () => {
  const [file] = bookFile.files;
  bookFile.value = ""; // тот же файл можно выбрать снова
  if (file) importBook(file).catch(showError);
});
