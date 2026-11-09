// Язык интерфейса — из настроек api, его задают при сборке. Строки в коде и на странице
// по-русски, они же ключи перевода: на en оболочка берёт перевод из en.js, строку без
// перевода показывает как есть. Модули, которые берут t(), ждут языка: top-level await

import { EN } from "./en.js";

const { language } = await fetch("/api/interface")
  .then((response) => response.json())
  .catch(() => ({ language: "ru" }));
const words = language === "en" ? EN : {};

// Строка на языке интерфейса, со значениями на местах {имя}
export function t(text, values = {}) {
  const template = words[text] ?? text;
  return template.replace(/\{(\w+)\}/g, (match, key) => (key in values ? values[key] : match));
}

// Текст и подсказки самой страницы: index.html написан по-русски
export function translatePage() {
  if (language === "ru") return;
  document.documentElement.lang = language;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = node.nodeValue.trim();
    const found = words[text.replace(/\s+/g, " ")];
    if (found) node.nodeValue = node.nodeValue.replace(text, found);
  }
  for (const name of ["title", "placeholder", "aria-label"]) {
    for (const element of document.querySelectorAll(`[${name}]`)) {
      const found = words[element.getAttribute(name).replace(/\s+/g, " ").trim()];
      if (found) element.setAttribute(name, found);
    }
  }
}
