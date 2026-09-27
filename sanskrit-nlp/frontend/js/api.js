/**
 * Thin fetch wrapper shared by every page. Always talks to the same origin
 * that served the page (FastAPI serves both the API and these static files).
 */
const API_BASE = "/api";

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof body === "object" && body !== null ? body.detail : body;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

const Api = {
  generate: (words) => apiRequest("/generate", { method: "POST", body: JSON.stringify({ words }) }),
  lookup: (q) => apiRequest(`/lookup?q=${encodeURIComponent(q)}`),
  listWords: (category, page = 1) =>
    apiRequest(`/words?${category ? `category=${encodeURIComponent(category)}&` : ""}page=${page}`),
  addWord: (word) => apiRequest("/words", { method: "POST", body: JSON.stringify(word) }),
  pendingWords: () => apiRequest("/words/pending"),
  approveWord: (lemma) => apiRequest(`/words/${encodeURIComponent(lemma)}/approve`, { method: "POST" }),
  deleteWord: (lemma) => apiRequest(`/words/${encodeURIComponent(lemma)}`, { method: "DELETE" }),
  rules: () => apiRequest("/rules"),
  runTests: () => apiRequest("/run-tests", { method: "POST" }),
  explain: (trace) => apiRequest("/explain", { method: "POST", body: JSON.stringify({ trace }) }),
  suggestWord: (word) => apiRequest("/suggest-word", { method: "POST", body: JSON.stringify({ word }) }),
  health: () => apiRequest("/health"),
};
