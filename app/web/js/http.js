// Запросы к api: ответ — JSON, ошибка — исключение с текстом от api. Его и показываем

export async function request(url, options) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    // detail от FastAPI: строка или список ошибок проверки запроса
    const detail = Array.isArray(body.detail)
      ? body.detail.map((error) => error.msg).join("; ")
      : body.detail;
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return body;
}

export function send(method, url, body) {
  return request(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// Параметры запроса: query({ path }) → «?path=…»
export function query(params) {
  return `?${new URLSearchParams(params)}`;
}

export function showError(error) {
  alert(error.message);
}
