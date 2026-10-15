/**
 * Home page: gates on authentication, then orchestrates the history sidebar,
 * landing view, past-session view, and live voice session.
 *
 * @author Pritam
 * @date 2026-10-12
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import VoiceRoom from "@/components/VoiceRoom";
import LevelPicker from "@/components/LevelPicker";
import TopicGrid from "@/components/TopicGrid";
import AuthForm from "@/components/AuthForm";
import HistorySidebar from "@/components/HistorySidebar";
import SessionDetail from "@/components/SessionDetail";
import { type Level } from "@/data/topics";
import { authFetch, clearAuthToken, getAuthToken, setAuthToken } from "@/lib/auth";
import {
  buildSessions,
  type HistoryMessage,
  type NotesEntry,
  type Session,
} from "@/lib/sessions";

/** localStorage key for the desktop sidebar collapsed preference. */
const SIDEBAR_KEY = "eureka_sidebar_collapsed";

/** Steps shown in the "How to use Eureka" guide on the landing page. */
const HOW_TO_STEPS = [
  {
    title: "Pick your level",
    body: "Choose a level, or use the level check at the top: answer three spoken questions and Eureka sets it for you.",
  },
  {
    title: "Choose a topic",
    body: "Tap any topic card, or New session in the sidebar to ask about anything. Allow microphone access when asked.",
  },
  {
    title: "Just talk",
    body: "Eureka speaks first. Answer out loud and interrupt whenever you like. Use headphones or a quiet room so background voices don't cut in.",
  },
  {
    title: "Explain it back",
    body: "Put ideas in your own words. When you've understood something, Eureka saves a checkpoint to your history.",
  },
  {
    title: "Take notes",
    body: "Jot notes during a session; they save automatically and stay with that session.",
  },
  {
    title: "Pick up later",
    body: "Past sessions live in the sidebar. Open one to reread it, then Continue this topic. Hide the sidebar for more room.",
  },
];

/** Shape of the LiveKit session credentials returned by the token endpoint. */
interface SessionInfo {
  token: string;
  roomName: string;
  identity: string;
  livekitUrl: string;
  topic: string;
}

/** The valid Level values in ascending order. */
const VALID_LEVELS = new Set<Level>([
  "spark",
  "current",
  "momentum",
  "field",
  "singularity",
]);

/**
 * Derive the user's level from their history.
 *
 * Scans messages in reverse order looking for a persisted `[Level] <value>`
 * record saved by the agent after an assessment. Falls back to message-count
 * heuristics if none is found.
 *
 * @param messages - Array of prior history messages.
 * @returns A Level value.
 */
function defaultLevelFromHistory(messages: HistoryMessage[]): Level {
  // Walk backwards — most recent assessment wins
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m.role === "level") {
      const v = m.content.trim() as Level;
      if (VALID_LEVELS.has(v)) return v;
    }
  }
  if (messages.length > 20) return "momentum";
  return "spark";
}


/**
 * Root page component for the Eureka physics tutor.
 *
 * Signed-out users see the auth screen. Signed-in users get a chat-style
 * layout: a session-history sidebar on the left and, on the right, either
 * the topic picker or a past session's transcript. Transitions to the
 * full-screen voice room once a LiveKit session is established.
 *
 * @returns The rendered Home page.
 */
export default function Home() {
  const [user, setUser] = useState<string | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [level, setLevel] = useState<Level>("spark");
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [history, setHistory] = useState<HistoryMessage[]>([]);
  const [notes, setNotes] = useState<NotesEntry[]>([]);
  const [selected, setSelected] = useState<Session | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** Restore the remembered desktop sidebar preference. */
  useEffect(() => {
    try {
      setSidebarCollapsed(localStorage.getItem(SIDEBAR_KEY) === "1");
    } catch {
      /* storage unavailable: keep default */
    }
  }, []);

  /**
   * Show or hide the history sidebar on desktop and remember the choice.
   *
   * @param collapsed - True to hide the sidebar.
   */
  const setCollapsed = (collapsed: boolean) => {
    setSidebarCollapsed(collapsed);
    try {
      localStorage.setItem(SIDEBAR_KEY, collapsed ? "1" : "0");
    } catch {
      /* storage unavailable: preference lasts for this page only */
    }
  };

  /** Drop credentials and all per-user state. */
  const handleLogout = useCallback(() => {
    clearAuthToken();
    setUser(null);
    setSession(null);
    setSelected(null);
    setHistory([]);
    setNotes([]);
    setLevel("spark");
  }, []);

  /** Fetch history and notes for the signed-in user. */
  const refreshData = useCallback(
    (identity: string) => {
      authFetch(`/history/${identity}`)
        .then((res) => {
          if (res.status === 401) handleLogout();
          return res.ok ? res.json() : null;
        })
        .then((data) => {
          if (data?.messages) {
            const msgs: HistoryMessage[] = data.messages;
            setHistory(msgs);
            setLevel(defaultLevelFromHistory(msgs));
          }
        })
        .catch(() => {});
      authFetch(`/notes/${identity}`)
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data?.notes) setNotes(data.notes as NotesEntry[]);
        })
        .catch(() => {});
    },
    [handleLogout],
  );

  /** On mount: restore the signed-in user from a stored token, if still valid. */
  useEffect(() => {
    if (!getAuthToken()) {
      setAuthChecked(true);
      return;
    }
    authFetch("/auth/me")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.username) setUser(data.username);
        else clearAuthToken();
      })
      .catch(() => {})
      .finally(() => setAuthChecked(true));
  }, []);

  /** Load data whenever the signed-in user changes. */
  useEffect(() => {
    if (user) refreshData(user);
  }, [user, refreshData]);

  /**
   * Store the token from a successful login/register.
   *
   * @param token - Access token.
   * @param username - Authenticated username.
   */
  const handleAuthenticated = (token: string, username: string) => {
    setAuthToken(token);
    setUser(username);
  };

  /**
   * Request a LiveKit token and enter the voice session.
   *
   * @param topic - Topic key to pass to the agent, or "__open__" for free chat.
   */
  const handleConnect = async (topic?: string) => {
    if (loading) return;
    setLoading(true);
    setError(null);
    try {
      const tokenRes = await authFetch("/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic ?? "__open__" }),
      });
      if (tokenRes.status === 401) {
        handleLogout();
        return;
      }
      if (tokenRes.status === 429) {
        throw new Error("You're starting sessions too quickly. Please wait a minute and try again.");
      }
      if (!tokenRes.ok) throw new Error(`API error: ${tokenRes.status}`);
      const data = await tokenRes.json();
      setSession({
        token: data.token,
        roomName: data.room_name,
        identity: data.identity,
        livekitUrl: data.livekit_url,
        topic: topic ?? "__open__",
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to connect");
    } finally {
      setLoading(false);
    }
  };

  /** Trigger the level-assessment flow via a special topic key. */
  const handleAssess = () => handleConnect("__assess__");

  /** Clear the active session and refresh history + notes on return to landing. */
  const handleDisconnect = () => {
    setSession(null);
    setSelected(null);
    if (user) refreshData(user);
  };

  // ---- Auth gate ----------------------------------------------------------
  if (!authChecked) {
    return <main className="min-h-screen bg-cosmos" />;
  }
  if (!user) {
    return <AuthForm onAuthenticated={handleAuthenticated} />;
  }

  // ---- Active session view ------------------------------------------------
  if (session) {
    return (
      <main className="min-h-screen bg-cosmos">
        <VoiceRoom
          token={session.token}
          serverUrl={session.livekitUrl}
          roomName={session.roomName}
          identity={session.identity}
          topic={session.topic}
          history={history}
          onDisconnect={handleDisconnect}
        />
      </main>
    );
  }

  const sessions = buildSessions(history);
  const selectedNote = selected?.roomName
    ? notes.find((n) => n.room_name === selected.roomName)?.content ?? null
    : null;

  // ---- Signed-in layout: sidebar + main panel -----------------------------
  return (
    <div className="flex h-screen bg-cosmos text-white overflow-hidden">
      <HistorySidebar
        sessions={sessions}
        selectedKey={selected?.key ?? null}
        username={user}
        open={sidebarOpen}
        collapsed={sidebarCollapsed}
        onCollapse={() => setCollapsed(true)}
        onSelect={(s) => {
          setSelected(s);
          setSidebarOpen(false);
        }}
        onNewSession={() => {
          setSidebarOpen(false);
          handleConnect("__open__");
        }}
        onHome={() => {
          setSelected(null);
          setSidebarOpen(false);
        }}
        loading={loading}
        onLogout={handleLogout}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="flex-1 min-w-0 overflow-y-auto">
        {/* ── Top bar ── */}
        <div className="sticky top-0 z-30 bg-cosmos/80 backdrop-blur border-b border-white/5">
          <div className="px-6 h-14 flex items-center justify-between gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="md:hidden p-2 -ml-2 rounded-lg text-white/60 hover:bg-white/5"
              aria-label="Open history"
            >
              <svg className="w-5 h-5" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M3 5h14M3 10h14M3 15h14" />
              </svg>
            </button>
            {sidebarCollapsed && (
              <button
                onClick={() => setCollapsed(false)}
                className="hidden md:flex items-center gap-2 px-3 py-1.5 -ml-2 rounded-lg text-sm text-white/60 hover:text-white hover:bg-white/5"
                aria-label="Show history"
                title="Show history"
              >
                <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="2.5" width="12" height="11" rx="2" />
                  <path d="M6 2.5v11M9.5 6.5 11 8l-1.5 1.5" />
                </svg>
                History
              </button>
            )}
            <div className="flex-1" />
            <button
              onClick={handleAssess}
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium
                         border border-aurora/30 text-glow hover:bg-aurora/10 hover:border-aurora/60
                         transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Assess My Level
              <svg
                className="w-3.5 h-3.5"
                viewBox="0 0 14 14"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M2 7h10M8 3l4 4-4 4" />
              </svg>
            </button>
          </div>
        </div>

        {error && (
          <div className="px-6 pt-4 text-center">
            <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-2 inline-block">
              {error}
            </p>
          </div>
        )}

        {selected ? (
          <SessionDetail
            session={selected}
            note={selectedNote}
            loading={loading}
            onContinue={(rawTopic) => handleConnect(rawTopic)}
          />
        ) : (
          <>
            {/* ── Hero ── */}
            <section className="max-w-5xl mx-auto px-6 pt-12 pb-10 text-center">
              <div className="flex justify-center mb-6">
                <div className="relative w-16 h-16">
                  <div className="absolute inset-0 rounded-full border-2 border-aurora/30 animate-spin_slow" />
                  <div className="absolute inset-2 rounded-full border border-aurora/50 animate-spin_slow [animation-direction:reverse]" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-3xl">⚛</span>
                  </div>
                </div>
              </div>

              <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4 leading-tight">
                Learn Physics the{" "}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-aurora to-glow">
                  Feynman Way
                </span>
              </h1>
              <p className="text-white/50 text-lg max-w-xl mx-auto">
                Ask anything. Build real intuition. No textbooks.
              </p>
            </section>

            {/* ── Level picker ── */}
            <section className="max-w-5xl mx-auto px-6 mb-8">
              <p className="text-xs uppercase tracking-widest text-white/30 font-semibold mb-3 pl-1">
                Your level
              </p>
              <LevelPicker selected={level} onChange={setLevel} />
            </section>

            {/* ── Topic grid ── */}
            <section className="max-w-5xl mx-auto px-6 mb-16">
              <p className="text-xs uppercase tracking-widest text-white/30 font-semibold mb-3 pl-1">
                Pick a topic
              </p>
              <TopicGrid
                level={level}
                loading={loading}
                onTopicClick={(topic) => handleConnect(topic)}
              />
            </section>

            {/* ── How to use ── */}
            <section aria-labelledby="how-to-use" className="max-w-5xl mx-auto px-6 pb-16">
              <h2
                id="how-to-use"
                className="text-xs uppercase tracking-widest text-white/30 font-semibold mb-3 pl-1"
              >
                How to use Eureka
              </h2>
              <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {HOW_TO_STEPS.map((step, i) => (
                  <li
                    key={step.title}
                    className="rounded-2xl border border-white/5 bg-nebula/60 p-4"
                  >
                    <p className="text-sm font-semibold text-white/90 mb-1">
                      <span className="text-aurora mr-2">{i + 1}</span>
                      {step.title}
                    </p>
                    <p className="text-sm text-white/50 leading-relaxed">{step.body}</p>
                  </li>
                ))}
              </ol>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
