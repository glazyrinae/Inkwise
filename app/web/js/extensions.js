// Расширения — плагины writer, как в VS Code: что установлено, включено ли в этой книге,
// настройки плагина, импорт архива .zip и удаление. Поля настроек оболочка рисует по
// манифесту плагина — выбор из списка или файл, — а что они значат, знает сам плагин
// в api. Что плагин сообщает о себе в книге, видно под его настройками

import { query, request, send, showError } from "./http.js";

const list = document.getElementById("extensions");
const fileInput = document.getElementById("plugin-file");

export async function showExtensions() {
  const plugins = await request("/api/plugins");
  list.replaceChildren(...plugins.map(card));
  if (!plugins.length) {
    list.append(element("p", "Плагинов нет: импортируй архив .zip кнопкой «+»", "empty"));
  }
}

// Карточка плагина: название, версия и папка, что делает, включён ли в книге, настройки
function card(plugin) {
  const item = element("article", "", "plugin");
  const head = element("header");
  const version = [plugin.version, plugin.id].filter(Boolean).join(" · ");
  head.append(element("strong", plugin.name), element("span", version, "version"));
  item.append(head, element("p", plugin.description));
  if (plugin.error) item.append(element("p", plugin.error, "warning"));
  item.append(toggle(plugin));
  if (plugin.enabled) {
    for (const [key, setting] of Object.entries(plugin.settings)) {
      const field = setting.kind === "file" ? file : choice;
      item.append(field(plugin, key, setting));
    }
    if (plugin.details) item.append(element("p", plugin.details, "details"));
  }
  item.append(removeButton(plugin));
  return item;
}

// Файл настройки: загрузить или убрать. Плагин разбирает файл сразу, это бывает долго
function file(plugin, key, setting) {
  const label = element("div", setting.title, "file-setting");
  const row = element("div", "", "file-row");
  const name = element("span", plugin.values[key] || "не загружен", "file-name");
  const input = document.createElement("input");
  input.type = "file";
  input.accept = setting.accept.join(",");
  input.hidden = true;
  const choose = element("button", plugin.values[key] ? "Заменить…" : "Загрузить…");
  choose.type = "button";
  choose.addEventListener("click", () => input.click());
  input.addEventListener("change", () => {
    const [chosen] = input.files;
    input.value = "";
    if (!chosen) return;
    name.textContent = `${chosen.name}: разбираю…`;
    choose.disabled = true;
    upload(plugin, key, chosen).catch((error) => {
      showError(error);
      showExtensions().catch(showError);
    });
  });
  row.append(name, choose, input);
  if (plugin.values[key]) {
    const forget = element("button", "Убрать");
    forget.type = "button";
    forget.addEventListener("click", () => removeFile(plugin, key).catch(showError));
    row.append(forget);
  }
  label.append(row);
  return label;
}

async function upload(plugin, key, chosen) {
  const url =
    `/api/plugins/${encodeURIComponent(plugin.id)}/files/${encodeURIComponent(key)}` +
    query({ name: chosen.name });
  const { fonts, shadowed_by: shadowedBy } = await request(url, {
    method: "PUT",
    headers: { "Content-Type": "application/octet-stream" },
    body: chosen,
  });
  await showExtensions();
  const notes = [];
  if (fonts.length) {
    notes.push(
      `Скачаны шрифты для office: ${fonts.join(", ")}. Office поставит их сам ` +
        "примерно за минуту, открытые тексты при этом переподключатся. Чтобы новые " +
        "шрифты появились в редакторе, обнови страницу.",
    );
  }
  if (shadowedBy) {
    notes.push(
      `Шаблон книги сейчас даёт «${shadowedBy}»: выключи этот плагин в книге, ` +
        `чтобы работал «${plugin.name}».`,
    );
  }
  if (notes.length) alert(notes.join("\n\n"));
}

async function removeFile(plugin, key) {
  const url = `/api/plugins/${encodeURIComponent(plugin.id)}/files/${encodeURIComponent(key)}`;
  await request(url, { method: "DELETE" });
  await showExtensions();
}

function toggle(plugin) {
  const label = element("label", "", "switch");
  const box = document.createElement("input");
  box.type = "checkbox";
  box.checked = plugin.enabled;
  box.addEventListener("change", () =>
    save(plugin, { enabled: box.checked }).catch(showError),
  );
  label.append(box, "Включён в этой книге");
  return label;
}

function choice(plugin, key, setting) {
  const label = element("label", setting.title);
  const select = document.createElement("select");
  select.append(
    ...Object.entries(setting.choices).map(
      ([value, title]) => new Option(title, value, false, value === plugin.values[key]),
    ),
  );
  select.addEventListener("change", () =>
    save(plugin, { values: { ...plugin.values, [key]: select.value } }).catch(showError),
  );
  label.append(select);
  return label;
}

function removeButton(plugin) {
  const button = element("button", "Удалить", "remove");
  button.type = "button";
  button.addEventListener("click", () => remove(plugin).catch(showError));
  return button;
}

async function save(plugin, change) {
  const state = { enabled: plugin.enabled, values: plugin.values, ...change };
  await send("PUT", `/api/plugins/${encodeURIComponent(plugin.id)}`, state);
  await showExtensions();
}

async function remove(plugin) {
  const question =
    `Удалить плагин «${plugin.name}»?\n\n` +
    "Папка плагина уйдёт в корзину плагинов — .корзина в папке плагинов, " +
    "оттуда его можно вернуть.";
  if (!confirm(question)) return;
  await request(`/api/plugins/${encodeURIComponent(plugin.id)}`, { method: "DELETE" });
  await showExtensions();
}

// Архив уходит в api как есть: api проверит, что в нём папка плагина с plugin.json
async function importPlugin(file) {
  await request("/api/plugins", {
    method: "POST",
    headers: { "Content-Type": "application/zip" },
    body: file,
  });
  await showExtensions();
}

function element(tag, text = "", className = "") {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

document.getElementById("import-plugin").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  const [file] = fileInput.files;
  fileInput.value = ""; // тот же архив можно выбрать снова, например после правки
  if (file) importPlugin(file).catch(showError);
});
