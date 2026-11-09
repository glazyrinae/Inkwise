// Что было открыто, что свёрнуто и какой ширины панели: после обновления страницы вернём
// как было. Хранилище браузера бывает недоступно (например, в приватном окне) — тогда
// просто не запоминаем
export const saved = {
  get(key) {
    try {
      return localStorage.getItem(`writer.${key}`);
    } catch {
      return null;
    }
  },
  set(key, value) {
    try {
      if (value === null) localStorage.removeItem(`writer.${key}`);
      else localStorage.setItem(`writer.${key}`, value);
    } catch {
      // не запомнили — не страшно
    }
  },
};
