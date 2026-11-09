// Разделители между панелями: их тянут левой кнопкой мыши, ширина запоминается

import { saved } from "./storage.js";

export function setupSplitters() {
  const chapters = document.getElementById("chapters");
  const material = document.getElementById("material");
  // Панель структуры: от её левого края до мыши. Книга: доля ширины от мыши до правого края
  splitter(document.getElementById("chapters-splitter"), chapters, "width", (x) => {
    const left = chapters.getBoundingClientRect().left;
    return `${clamp(x - left, 160, window.innerWidth / 2)}px`;
  });
  splitter(document.getElementById("material-splitter"), material, "flexBasis", (x) => {
    const box = document.getElementById("panes").getBoundingClientRect();
    return `${clamp(((box.right - x) / box.width) * 100, 15, 85)}%`;
  });
}

// size по положению мыши даёт новый размер панели в её свойстве style[property]
function splitter(handle, panel, property, size) {
  const key = `${panel.id}.${property}`;
  panel.style[property] = saved.get(key) ?? "";
  handle.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    event.preventDefault(); // не выделять текст, пока тянем
    handle.setPointerCapture(event.pointerId);
    document.body.classList.add("resizing");
  });
  handle.addEventListener("pointermove", (event) => {
    if (handle.hasPointerCapture(event.pointerId)) panel.style[property] = size(event.clientX);
  });
  // Кнопку отпустили или захват мыши сорвался: запоминаем ширину
  handle.addEventListener("lostpointercapture", () => {
    document.body.classList.remove("resizing");
    saved.set(key, panel.style[property] || null);
  });
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}
