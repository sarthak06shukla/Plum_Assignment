const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

let authToken: string | null = null;

export function setToken(token: string | null) {
  authToken = token;
}

export function getToken() {
  return authToken;
}

function getStoredToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("plum_token");
}

function clearStoredAuth() {
  authToken = null;
  if (typeof window === "undefined") return;
  localStorage.removeItem("plum_token");
  localStorage.removeItem("plum_role");
  localStorage.removeItem("plum_email");
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {};
  const token = authToken || getStoredToken();
  if (token) {
    authToken = token;
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (!(options?.body instanceof FormData))
    headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...headers,
      ...((options?.headers as Record<string, string>) ?? {}),
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    if (res.status === 401) {
      clearStoredAuth();
      throw new ApiError(
        res.status,
        "Your session expired. Please sign in again before uploading.",
      );
    }
    throw new ApiError(res.status, err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string; role: string }>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
    ),

  register: (
    email: string,
    name: string,
    password: string,
    role: string,
  ) =>
    request<{ access_token: string; token_type: string; role: string }>(
      "/auth/register",
      { method: "POST", body: JSON.stringify({ email, name, password, role }) },
    ),

  getClaims: () => request<any[]>("/claims"),

  getClaim: (id: string) => request<any>(`/claims/${id}`),

  getProcessing: (id: string) => request<any[]>(`/claims/${id}/processing`),

  submitClaim: (formData: FormData) =>
    request<any>("/claims", { method: "POST", body: formData }),

  getDashboard: () => request<any>("/admin/dashboard"),

  getAdminClaims: () => request<any[]>("/admin/claims"),

  getManualReviews: () => request<any[]>("/admin/manual-reviews"),

  overrideReview: (reviewId: string, decision: string, reason: string) =>
    request<any>(`/admin/manual-reviews/${reviewId}/override`, {
      method: "POST",
      body: JSON.stringify({ decision, reason }),
    }),
};
