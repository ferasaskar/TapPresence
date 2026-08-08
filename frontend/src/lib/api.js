import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("ariadni_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Turn a stored image reference into a fully-qualified URL.
export const resolveImg = (url) => {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  if (url.startsWith("/api/")) return `${BACKEND_URL}${url}`;
  return url;
};

export const vcardUrl = (slug) => `${API_BASE}/cards/${slug}/vcard`;
export const qrUrl = (slug) => `${API_BASE}/cards/${slug}/qr`;
export const posterUrl = (slug) => `${API_BASE}/cards/${slug}/poster`;
