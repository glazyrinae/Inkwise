// Пункты меню на языке редактора: язык в конфиге редактора задаёт api по языку
// интерфейса, плагин видит его в info.lang («en», «en-US»)
const ENGLISH = {
  Цитировать: "Quote",
  "Сноска на эту страницу": "Footnote to this page",
  "Проверить орфографию": "Check spelling",
  "Проверить орфографию всего текста": "Check spelling of the whole text",
};

function tr(text) {
  const lang = window.Asc.plugin.info.lang || "";
  return lang.startsWith("en") ? (ENGLISH[text] ?? text) : text;
}
