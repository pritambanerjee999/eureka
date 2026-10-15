/**
 * HistorySidebar: chat-app style left rail listing the user's past sessions,
 * grouped by date, with a new-session button and account footer.
 *
 * @author Pritam
 * @date 2026-10-12
 */

"use client";

import { fmtTime, groupSessionsByDate, type Session } from "@/lib/sessions";

interface Props {
  sessions: Session[];
  /** Key of the session currently open in the main panel, if any. */
  selectedKey: string | null;
  username: string;
  /** Whether the drawer is open on small screens. */
  open: boolean;
  /** Whether the sidebar is hidden on md+ screens to give the main panel full width. */
  collapsed?: boolean;
  /** Hide the sidebar on md+ screens. */
  onCollapse?: () => void;
  onSelect: (session: Session) => void;
  /** Start a new open-ended voice session. */
  onNewSession: () => void;
  /** Return to the topic picker. */
  onHome: () => void;
  /** Disables New session while a token request is in flight. */
  loading?: boolean;
  onLogout: () => void;
  onClose: () => void;
}

/**
 * Render the session history sidebar.
 *
 * @param props - Component props.
 * @returns The sidebar element (plus a mobile backdrop when open).
 */
export default function HistorySidebar({
  sessions,
  selectedKey,
  username,
  open,
  collapsed = false,
  onCollapse,
  onSelect,
  onNewSession,
  onHome,
  loading = false,
  onLogout,
  onClose,
}: Props) {
  const groups = groupSessionsByDate(sessions);

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-black/60 md:hidden" onClick={onClose} aria-hidden />
      )}
      <aside
        aria-label="Session history"
        className={[
          "fixed md:static inset-y-0 left-0 z-50 w-72 shrink-0 flex flex-col",
          "bg-nebula border-r border-white/5 transition-transform duration-200",
          open ? "translate-x-0" : "-translate-x-full md:translate-x-0",
          collapsed ? "md:hidden" : "",
        ].join(" ")}
      >
        {/* Brand + new session */}
        <div className="p-3 border-b border-white/5">
          <div className="flex items-center justify-between">
            <button
              onClick={onHome}
              aria-label="Home: pick a topic"
              className="flex items-center gap-2 px-2 h-10 rounded-lg hover:bg-white/5 transition-colors"
            >
              <span className="text-xl">⚛</span>
              <span className="font-bold text-lg tracking-tight">Eureka</span>
            </button>
            {onCollapse && (
              <button
                onClick={onCollapse}
                aria-label="Hide history"
                title="Hide history"
                className="hidden md:block p-2 rounded-lg text-white/50 hover:text-white hover:bg-white/5"
              >
                <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="2.5" width="12" height="11" rx="2" />
                  <path d="M6 2.5v11M11 6.5 9.5 8l1.5 1.5" />
                </svg>
              </button>
            )}
          </div>
          <button
            onClick={onNewSession}
            disabled={loading}
            className="mt-2 w-full flex items-center gap-2 px-3 py-2 rounded-xl border border-white/10
                       text-sm text-white/80 hover:bg-white/5 hover:border-white/20 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M8 3v10M3 8h10" />
            </svg>
            {loading ? "Connecting…" : "New session"}
          </button>
        </div>

        {/* Session list */}
        <nav className="flex-1 overflow-y-auto px-2 py-3">
          {groups.length === 0 ? (
            <p className="px-3 py-6 text-xs text-white/30 text-center">
              Your past sessions will show up here.
            </p>
          ) : (
            groups.map((group) => (
              <div key={group.label} className="mb-4">
                <p className="px-3 mb-1 text-[10px] uppercase tracking-widest text-white/25 font-semibold">
                  {group.label}
                </p>
                <ul className="flex flex-col gap-0.5">
                  {group.sessions.map((s) => {
                    const active = s.key === selectedKey;
                    const exchanges = s.messages.filter((m) => m.role === "user").length;
                    return (
                      <li key={s.key}>
                        <button
                          onClick={() => onSelect(s)}
                          aria-current={active ? "true" : undefined}
                          className={[
                            "w-full text-left px-3 py-2 rounded-lg transition-colors",
                            active ? "bg-aurora/15 text-white" : "text-white/70 hover:bg-white/5",
                          ].join(" ")}
                        >
                          <p className="text-sm truncate">{s.topic}</p>
                          <p className="text-[11px] text-white/30 mt-0.5 flex items-center gap-1.5">
                            <span>{fmtTime(s.startedAt)}</span>
                            {exchanges > 0 && <span>· {exchanges} msg{exchanges !== 1 ? "s" : ""}</span>}
                            {s.checkpoints.length > 0 && (
                              <span className="text-green-400/70">· ✓ {s.checkpoints.length}</span>
                            )}
                          </p>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))
          )}
        </nav>

        {/* Account footer */}
        <div className="p-3 border-t border-white/5 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-aurora/20 border border-aurora/30 flex items-center justify-center text-sm font-semibold text-glow uppercase">
            {username.charAt(0)}
          </div>
          <span className="flex-1 text-sm text-white/80 truncate">{username}</span>
          <button
            onClick={onLogout}
            className="text-xs text-white/40 hover:text-white px-2 py-1 rounded-lg hover:bg-white/5 transition-colors"
          >
            Log out
          </button>
        </div>
      </aside>
    </>
  );
}
