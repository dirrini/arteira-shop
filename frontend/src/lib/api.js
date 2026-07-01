const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data.message || data.error || "Request failed";
    const error = new Error(message);
    error.payload = data;
    throw error;
  }
  return data;
}

export const api = {
  me: () => request("/api/auth/me"),
  loginGoogle: (credential) => request("/api/auth/google", { method: "POST", body: JSON.stringify({ credential }) }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  products: (params = {}) => request(`/api/products?${new URLSearchParams(params)}`),
  myProducts: () => request("/api/products/mine"),
  createProduct: (payload) => request("/api/products", { method: "POST", body: JSON.stringify(payload) }),
  upsertSeller: (payload) => request("/api/sellers/me", { method: "POST", body: JSON.stringify(payload) }),
  checkout: (payload) => request("/api/orders/checkout", { method: "POST", body: JSON.stringify(payload) }),
  orders: (role = "buyer") => request(`/api/orders?role=${role}`),
};
