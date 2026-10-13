/**
 * SessionDetail: read-only view of a past session — transcript as chat
 * bubbles, checkpoints reached, and saved notes.
 *
 * @author Pritam
 * @date 2026-10-12
 */

"use client";

import { fmtDate, fmtTime, levelLabel, type Session } from "@/lib/sessions";

interface Props {
  session: Session;
  /** Notes saved for this session's room, if any. */
  note: string | null;
  loading: boolean;
  /** Start a new live session on the same topic. */
  onContinue: (rawTopic: string) => void;
}

/**
 * Render a past session in the main panel.
 *
 * @param props - Component props.
 * @returns The session detail view.
 */
export default function SessionDetail({ session, note, loading, onContinue }: Props) {
  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{session.topic}</h1>
          <p className="text-xs text-white/40 mt-1">
            {fmtDate(session.startedAt)} · {fmtTime(session.startedAt)}
          </p>
          <div className="flex flex-wrap gap-1.5 mt-3">
            {session.level && (
              <span className="px-2 py-0.5 rounded-full bg-aurora/10 border border-aurora/20 text-[11px] font-medium text-glow">
                Level: {levelLabel(session.level)}
              </span>
            )}
            {session.checkpoints.map((cp, i) => (
              <span
                key={`${cp}-${i}`}
                className="px-2 py-0.5 rounded-full bg-green-500/10 border border-green-500/20 text-[11px] font-medium text-green-400"
              >
                ✓ {cp}
              </span>
            ))}
          </div>
        </div>
        <button
          onClick={() => onContinue(session.rawTopic)}
          disabled={loading}
          className="px-4 py-2 rounded-xl bg-aurora hover:bg-aurora/90 text-sm font-semibold
                     transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Continue this topic
        </button>
      </div>

      {/* Notes */}
      {note?.trim() && (
        <div className="mb-6 rounded-2xl border border-yellow-500/15 bg-yellow-500/5 p-4">
          <p className="text-[10px] uppercase tracking-widest text-yellow-400/60 font-semibold mb-2">
            Your notes
          </p>
          <p className="text-sm text-white/70 leading-relaxed whitespace-pre-wrap">{note}</p>
        </div>
      )}

      {/* Transcript */}
      {session.messages.length === 0 ? (
        <p className="text-sm text-white/30 italic">No transcript was recorded for this session.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {session.messages.map((m, i) => {
            const isUser = m.role === "user";
            return (
              <div key={i} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                <div
                  className={[
                    "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap",
                    isUser
                      ? "bg-aurora/20 border border-aurora/20 text-white rounded-br-md"
                      : "bg-nebula border border-white/5 text-white/80 rounded-bl-md",
                  ].join(" ")}
                >
                  {!isUser && <p className="text-[10px] text-glow/70 font-semibold mb-0.5">Eureka</p>}
                  {m.content}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
