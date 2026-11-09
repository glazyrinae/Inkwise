// Окна из полосы слева внизу: настройки книги и MCP-сервер проверки орфографии. Оба
// меняют настройки книги, а api сохраняет их целиком

import { query, request, send, showError } from "./http.js";
import { t } from "./i18n.js";

const settingsDialog = document.getElementById("settings");
const styleSelect = document.getElementById("style");
const spellingDialog = document.getElementById("spelling");
const spellingForm = document.getElementById("spelling-form");
const spellingStatus = document.getElementById("spelling-status");
let settings = null; // настройки книги, как их отдал api

export async function openSettings() {
  const styles = await loadSettings();
  styleSelect.replaceChildren(
    ...Object.entries(styles).map(
      ([key, title]) => new Option(title, key, false, key === settings.style),
    ),
  );
  settingsDialog.showModal();
}

export async function openSpelling() {
  await loadSettings();
  spellingForm.elements.namedItem("url").value = settings.mcp_url ?? "";
  showStatus("");
  spellingDialog.showModal();
}

async function loadSettings() {
  const { styles, ...current } = await request("/api/book/settings");
  settings = current;
  return styles;
}

async function save(change) {
  settings = { ...settings, ...change };
  await send("PUT", "/api/book/settings", settings);
}

// Адрес сохраняем, только когда сервер ответил: неработающий в настройки не попадёт.
// Пустой адрес отключает проверку
async function connect(url) {
  if (!url) {
    await save({ mcp_url: null });
    showStatus(t("Проверка орфографии отключена"));
    return;
  }
  showStatus(t("Подключаюсь…"));
  const tools = await request(`/api/spelling/tools${query({ url })}`);
  await save({ mcp_url: url });
  showStatus(
    t("Подключено. Инструменты сервера: {tools}", { tools: tools.join(", ") || t("нет") }),
  );
}

function showStatus(text, warning = false) {
  spellingStatus.textContent = text;
  spellingStatus.className = warning ? "warning" : "";
  spellingStatus.hidden = !text;
}

styleSelect.addEventListener("change", () =>
  save({ style: styleSelect.value }).catch(showError),
);
spellingForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const url = spellingForm.elements.namedItem("url").value.trim();
  connect(url).catch((error) => showStatus(error.message, true));
});
document
  .getElementById("spelling-close")
  .addEventListener("click", () => spellingDialog.close());
