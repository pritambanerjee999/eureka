/**
 * AuthForm: sign-in / create-account screen shown to signed-out users.
 *
 * @author Pritam
 * @date 2026-10-12
 */

"use client";

import { useState, type FormEvent } from "react";
import { API_URL } from "@/lib/auth";

interface Props {
  /** Called with the access token and username after a successful login/register. */
  onAuthenticated: (token: string, username: string) => void;
}

type Mode = "login" | "register";

/**
 * Turn a FastAPI error body into a readable message.
 *
 * @param body - Parsed JSON error body (``detail`` may be a string or a 422 list).
 * @param fallback - Message used when nothing better is available.
 * @returns A user-facing error string.
 */
function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) {
    return String(detail[0].msg).replace(/^Value error, /, "");
  }
  return fallback;
}

/**
 * Centered card with username/password fields and a login/register toggle.
 *
 * @param props - Component props.
 * @returns The auth screen.
 */
export default function AuthForm({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isRegister = mode === "register";

  /** Submit credentials to /auth/login or /auth/register. */
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const body = await res.json().catch(() => null);
      if (!res.ok) {
        setError(errorMessage(body, isRegister ? "Could not create account" : "Sign in failed"));
        return;
      }
      onAuthenticated(body.access_token, body.username);
    } catch {
      setError("Cannot reach the server. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  /** Flip between sign-in and create-account modes. */
  const toggleMode = () => {
    setMode(isRegister ? "login" : "register");
    setError(null);
  };

  const inputClass =
    "w-full bg-cosmos border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white " +
    "placeholder:text-white/20 outline-none focus:border-aurora/50 focus:bg-aurora/5 transition-colors";

  return (
    <main className="min-h-screen bg-cosmos text-white flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="relative w-14 h-14 mb-4">
            <div className="absolute inset-0 rounded-full border-2 border-aurora/30 animate-spin_slow" />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl">⚛</span>
            </div>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Eureka</h1>
          <p className="text-white/40 text-sm mt-1">Learn physics the Feynman way</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-nebula border border-white/5 rounded-2xl p-6 flex flex-col gap-4"
        >
          <h2 className="text-lg font-semibold">
            {isRegister ? "Create your account" : "Welcome back"}
          </h2>

          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-white/50">Username</span>
            <input
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className={inputClass}
              placeholder="feynman"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-white/50">Password</span>
            <input
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={isRegister ? 8 : undefined}
              className={inputClass}
              placeholder={isRegister ? "At least 8 characters" : "••••••••"}
            />
          </label>

          {error && (
            <p role="alert" className="text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="mt-1 w-full py-2.5 rounded-xl bg-aurora hover:bg-aurora/90 text-sm font-semibold
                       transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Please wait…" : isRegister ? "Create account" : "Sign in"}
          </button>
        </form>

        <p className="text-center text-sm text-white/40 mt-5">
          {isRegister ? "Already have an account?" : "New to Eureka?"}{" "}
          <button type="button" onClick={toggleMode} className="text-glow hover:underline">
            {isRegister ? "Sign in" : "Create an account"}
          </button>
        </p>
      </div>
    </main>
  );
}
