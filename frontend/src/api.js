async function request(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error ?? `Request failed (${response.status})`);
  }
  return data;
}

export const api = {
  createUser: () => request("/users", { method: "POST" }),
  login: (userId) => request(`/users/${userId}`),
  getRatings: (userId) => request(`/users/${userId}/ratings`),
  addRating: (userId, isbn, rating) =>
    request("/ratings", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, isbn, rating }),
    }),
  searchBooks: (q) => request(`/books/search?q=${encodeURIComponent(q)}`),
  getBook: (isbn) => request(`/books/${encodeURIComponent(isbn)}`),
  getRecommenders: () => request("/recommenders"),
  reloadRecommenders: () => request("/recommenders/reload", { method: "POST" }),
  getRecommendations: (userId, model) =>
    request(`/users/${userId}/recommendations?model=${encodeURIComponent(model)}`),
};
