// Перетаскивание блоков в дереве мышью. Блок встаёт перед строкой, на которую его
// отпустили, или после неё — смотря на какую половину строки

let dragged = null; // путь блока, который тащат

// row — строка блока path; drop(target, after) — блок path отпустили на строку target
export function draggable(row, path, drop) {
  row.draggable = true;
  row.addEventListener("dragstart", (event) => {
    dragged = { path, drop };
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", path);
  });
  row.addEventListener("dragend", () => {
    dragged = null;
  });
  row.addEventListener("dragover", (event) => {
    if (!dragged || dragged.path === path) return;
    event.preventDefault(); // без этого строка не примет блок
    const after = lowerHalf(row, event);
    row.classList.toggle("drop-before", !after);
    row.classList.toggle("drop-after", after);
  });
  row.addEventListener("dragleave", () => unmark(row));
  row.addEventListener("drop", (event) => {
    event.preventDefault();
    unmark(row);
    if (dragged && dragged.path !== path) dragged.drop(path, lowerHalf(row, event));
  });
}

function lowerHalf(row, event) {
  const box = row.getBoundingClientRect();
  return event.clientY > box.top + box.height / 2;
}

function unmark(row) {
  row.classList.remove("drop-before", "drop-after");
}
