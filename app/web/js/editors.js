// Два редактора ONLYOFFICE: слева текст блока на правку, справа книга или копия
// веб-страницы на просмотр. Сам редактор — готовый api.js с сервера office; здесь только
// открываем в нём файлы

import { query, request } from "./http.js";
import { saved } from "./storage.js";
import { t } from "./i18n.js";

const hint = document.querySelector("#text .hint");
const panes = {
  text: { name: "text", section: document.getElementById("text"), editor: null, path: null },
  material: {
    name: "material",
    section: document.getElementById("material"),
    editor: null,
    path: null,
  },
};
let editorScript = null; // загрузка api.js: одна на страницу
let changed = () => {}; // открытые файлы сменились: дерево подсвечивает их

// Адрес office: с него приходят сообщения плагина
export let officeOrigin = null;

export function onChange(listener) {
  changed = listener;
}

// Путь файла в редакторе: name — text или material
export function openPath(name) {
  return panes[name].path;
}

export function isOpen(path) {
  return path === panes.text.path || path === panes.material.path;
}

export async function openFile(path) {
  const { api_js, config } = await request(`/api/office/config${query({ path })}`);
  await loadEditorScript(api_js);
  // Текст блока office открывает на правку — он слева; книги и прочие материалы —
  // на просмотр, справа
  const pane = config.editorConfig.mode === "edit" ? panes.text : panes.material;
  // Закрытый документ office сохранит сам: пришлёт файл в callback со статусом 2
  pane.editor?.destroyEditor();
  pane.section.hidden = false;
  if (pane === panes.text) hint.hidden = true;
  // Крестик в заголовке редактора office показывает, только когда задан onRequestClose
  const events = pane === panes.material ? { onRequestClose: () => close(pane) } : {};
  pane.editor = new DocsAPI.DocEditor(`${pane.name}-editor`, { ...config, events });
  pane.path = path;
  saved.set(pane.name, path);
  changed();
}

// Закрывает редакторы, где открыт файл, подходящий под условие: например, файл из
// блока, который уносят в корзину
export function closeWhere(test) {
  for (const pane of Object.values(panes)) {
    if (pane.path && test(pane.path)) close(pane);
  }
}

// Клавиатуру тексту отдаёт оболочка: забрать фокус у редактора книги сам плагин текста
// не может, а у оболочки есть активация от клика по «Цитировать»
export function focusText() {
  panes.text.section.querySelector("iframe")?.focus();
}

export async function restore() {
  for (const pane of Object.values(panes)) {
    const path = saved.get(pane.name);
    // Файл могли удалить или переименовать — тогда просто забываем его
    if (path) await openFile(path).catch(() => saved.set(pane.name, null));
  }
}

function close(pane) {
  pane.editor?.destroyEditor();
  pane.editor = null;
  pane.path = null;
  // На месте текста блока — подсказка, а место книги справа отходит тексту
  if (pane === panes.text) hint.hidden = false;
  else pane.section.hidden = true;
  saved.set(pane.name, null);
  changed();
}

function loadEditorScript(src) {
  officeOrigin = new URL(src).origin;
  editorScript ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.onload = resolve;
    script.onerror = () => {
      editorScript = null; // следующая попытка загрузит заново
      script.remove();
      reject(new Error(t("Редактор не загрузился: office ещё запускается или не запущен")));
    };
    document.head.append(script);
  });
  return editorScript;
}
