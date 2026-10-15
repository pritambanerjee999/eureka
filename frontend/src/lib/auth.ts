/**
 * Client-side auth helpers: access-token storage and authenticated fetch.
 *
 * @author Pritam
 * @date 2026-10-12
 */

/** Base URL of the Eureka API. */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

const TOKEN_KEY = "eureka_auth_token";

/** @returns The stored access token, or null if signed out. */
export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

/** @param token - Access token returned by /auth/login or /auth/register. */
export function setAuthToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

/** Remove the stored access token (log out). */
export function clearAuthToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * `fetch` against the API with the Bearer token attached.
 *
 * @param path - API path beginning with "/", e.g. "/history/alice".
 * @param init - Standard fetch options.
 * @returns The fetch response promise.
 */
export function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getAuthToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${API_URL}${path}`, { ...init, headers });
}
