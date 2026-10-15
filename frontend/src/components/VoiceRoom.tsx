/**
 * VoiceRoom: full-screen session UI with agent visualizer, transcript,
 * inline notes, and a physics reference panel.
 *
 * @author Pritam
 * @date 2026-10-12
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";
import AgentVisualizer from "./AgentVisualizer";
import TranscriptPanel from "./TranscriptPanel";
import SessionControls from "./SessionControls";
import { authFetch } from "@/lib/auth";
import { REFERENCES } from "@/data/references";

/** A single message record from the persistent conversation history. */
interface HistoryMessage {
  role: string;
  content: string;
  timestamp: string;
}

/** Props accepted by the VoiceRoom component. */
interface Props {
  /** Signed LiveKit JWT for room access. */
  token: string;
  /** WebSocket URL of the LiveKit server. */
  serverUrl: string;
  /** Human-readable room identifier. */
  roomName: string;
  /** Authenticated user's identity (username); owns the notes. */
  identity: string;
  /** Topic key chosen before joining, or "__open__" / "__assess__". */
  topic: string;
  /** Prior session messages to pre-populate the transcript panel. */
  history: HistoryMessage[];
  /** Callback invoked when the user ends the session or is disconnected. */
  onDisconnect: () => void;
}

/**
 * Format elapsed seconds as M:SS.
 *
 * @param secs - Total elapsed seconds.
 * @returns A formatted duration string.
 */
function formatDuration(secs: number): string {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/**
 * Derive a human-readable session title from the topic key.
 *
 * @param topic - Raw topic key from the token request.
 * @returns Display title string.
 */
function topicTitle(topic: string): string {
  if (topic === "__open__") return "Open Session";
  if (topic === "__assess__") return "Level Assessment";
  return topic;
}

/**
 * Inner component rendered inside the LiveKitRoom context.
 *
 * Split into two panels:
 * - Left: agent visualizer + live transcript.
 * - Right: session notes (localStorage-backed) + reference links.
 */
function SessionLayout({
  roomName,
  identity,
  topic,
  history,
  onDisconnect,
}: Omit<Props, "token" | "serverUrl">) {
  const title = topicTitle(topic);
  const [elapsed, setElapsed] = useState(0);
  const [paused, setPaused] = useState(false);
  const [notes, setNotes] = useState<string>("");
  const [notesSaved, setNotesSaved] = useState(true);
  const notesTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Session timer (stops while paused)
  useEffect(() => {
    if (paused) return;
    const id = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [paused]);

  // Load notes for this session from the API on mount
  useEffect(() => {
    if (!identity || !roomName) return;
    authFetch(`/notes/${identity}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.notes) {
          const entry = (data.notes as { room_name: string; content: string }[]).find(
            (n) => n.room_name === roomName,
          );
          if (entry) setNotes(entry.content);
        }
      })
      .catch(() => {});
  }, [identity, roomName]);

  /** Persist notes to the API (debounced 800 ms after last keystroke). */
  const handleNotesChange = (value: string) => {
    setNotes(value);
    setNotesSaved(false);
    if (notesTimerRef.current) clearTimeout(notesTimerRef.current);
    notesTimerRef.current = setTimeout(() => {
      if (!identity) return;
      authFetch(`/notes/${identity}/${roomName}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: value }),
      })
        .then(() => setNotesSaved(true))
        .catch(() => {});
    }, 800);
  };

  return (
    <div className="flex flex-col h-screen text-white overflow-hidden">
      {/* ── Top bar ── */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-white/5 bg-cosmos/90 backdrop-blur shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-lg">⚛</span>
          <div>
            <p className="text-sm font-semibold text-white leading-none">{title}</p>
            <p className="text-[10px] text-white/30 font-mono mt-0.5">{roomName}</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <SessionControls paused={paused} onPausedChange={setPaused} />

          {/* Live session timer */}
          <div
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full border ${
              paused ? "bg-white/5 border-white/10" : "bg-green-500/10 border-green-500/20"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${paused ? "bg-white/40" : "bg-green-400 animate-pulse"}`}
            />
            <span className={`text-xs font-mono ${paused ? "text-white/50" : "text-green-400"}`}>
              {paused ? "Paused " : ""}
              {formatDuration(elapsed)}
            </span>
          </div>

          <button
            onClick={onDisconnect}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl border border-red-500/30
                       text-red-400 text-xs font-medium hover:bg-red-500/10 transition-colors duration-200"
          >
            <svg className="w-3 h-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M2 2l8 8M10 2l-8 8" />
            </svg>
            End Session
          </button>
        </div>
      </header>

      {/* ── Main content ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── Left panel: visualizer + transcript ── */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden border-r border-white/5">
          {/* Visualizer area */}
          <div className="flex flex-col items-center justify-center py-10 px-6 shrink-0 border-b border-white/5">
            <AgentVisualizer />
            <p className="mt-6 text-white/25 text-xs text-center">
              {paused
                ? "Paused: Eureka is waiting. Press Resume when you're ready."
                : "Just speak — Eureka is listening"}
            </p>
          </div>

          {/* Transcript */}
          <div className="flex-1 overflow-hidden p-4">
            <p className="text-[10px] uppercase tracking-widest text-white/20 font-semibold mb-3">
              Transcript
            </p>
            <div className="h-full overflow-y-auto">
              <TranscriptPanel preloadedHistory={history} />
            </div>
          </div>
        </div>

        {/* ── Right panel: notes + references ── */}
        <div className="flex flex-col w-80 xl:w-96 shrink-0 overflow-hidden">
          {/* Notes */}
          <div className="flex flex-col flex-1 overflow-hidden border-b border-white/5 p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[10px] uppercase tracking-widest text-white/20 font-semibold">
                My Notes
              </p>
              {notes.trim() && (
                <span className="text-[10px] text-white/20">
                  {notesSaved ? "saved" : "saving…"}
                </span>
              )}
            </div>

            <textarea
              value={notes}
              onChange={(e) => handleNotesChange(e.target.value)}
              placeholder="Jot down ideas, formulas, questions…"
              className="flex-1 w-full bg-transparent text-white/80 text-sm leading-relaxed
                         placeholder:text-white/15 resize-none outline-none
                         border border-white/5 rounded-xl p-3
                         focus:border-aurora/30 focus:bg-aurora/5 transition-colors duration-200"
              spellCheck={false}
            />
          </div>

          {/* References */}
          <div className="flex flex-col shrink-0 p-4 overflow-y-auto max-h-72">
            <p className="text-[10px] uppercase tracking-widest text-white/20 font-semibold mb-3">
              References
            </p>

            <div className="flex flex-col gap-2">
              {REFERENCES.map((ref) => (
                <a
                  key={ref.url}
                  href={ref.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start gap-3 px-3 py-2.5 rounded-xl border border-white/5
                             bg-nebula hover:border-aurora/30 hover:bg-aurora/5
                             transition-all duration-150 group"
                >
                  <span className="text-base leading-none mt-0.5 shrink-0">{ref.icon}</span>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-white/80 group-hover:text-white truncate transition-colors">
                      {ref.label}
                    </p>
                    <p className="text-[10px] text-white/30 truncate">{ref.subtitle}</p>
                  </div>
                  <svg
                    className="w-3 h-3 text-white/20 group-hover:text-aurora shrink-0 ml-auto mt-0.5 transition-colors"
                    viewBox="0 0 12 12"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path d="M2.5 9.5l7-7M5 2.5h4.5v4.5" />
                  </svg>
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Wraps the session layout in a LiveKitRoom context and mounts audio rendering.
 *
 * @param props - Component props.
 * @returns The full-screen voice room UI.
 */
export default function VoiceRoom({
  token,
  serverUrl,
  roomName,
  identity,
  topic,
  history,
  onDisconnect,
}: Props) {
  return (
    <LiveKitRoom
      token={token}
      serverUrl={serverUrl}
      connect={true}
      audio={true}
      video={false}
      onDisconnected={onDisconnect}
      className="h-screen"
    >
      <RoomAudioRenderer />
      <SessionLayout
        roomName={roomName}
        identity={identity}
        topic={topic}
        history={history}
        onDisconnect={onDisconnect}
      />
    </LiveKitRoom>
  );
}
