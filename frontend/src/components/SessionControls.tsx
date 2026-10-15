/**
 * SessionControls: mute/unmute the microphone and pause/resume the session.
 *
 * Pausing mutes the mic and sets the participant attribute `paused` to "1";
 * the agent stops talking and waits (its idle timeout is suspended) until the
 * attribute goes back to "0".
 *
 * @author Pritam
 * @date 2026-10-14
 */

"use client";

import { useState } from "react";
import { useLocalParticipant } from "@livekit/components-react";

interface Props {
  /** Whether the session is currently paused. */
  paused: boolean;
  /** Called after the paused state changes. */
  onPausedChange: (paused: boolean) => void;
}

/**
 * Render the mute and pause buttons for the live session.
 *
 * @param props - Component props.
 * @returns The control buttons.
 */
export default function SessionControls({ paused, onPausedChange }: Props) {
  const { localParticipant, isMicrophoneEnabled } = useLocalParticipant();
  const [busy, setBusy] = useState(false);

  /** Run a LiveKit call, ignoring failures (the UI just stays as it was). */
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
    } catch {
      /* connection hiccup: leave state unchanged */
    } finally {
      setBusy(false);
    }
  };

  const toggleMute = () =>
    run(() => localParticipant.setMicrophoneEnabled(!isMicrophoneEnabled));

  const togglePause = () =>
    run(async () => {
      if (paused) {
        await localParticipant.setAttributes({ paused: "0" });
        await localParticipant.setMicrophoneEnabled(true);
        onPausedChange(false);
      } else {
        await localParticipant.setMicrophoneEnabled(false);
        await localParticipant.setAttributes({ paused: "1" });
        onPausedChange(true);
      }
    });

  const base =
    "flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium " +
    "transition-colors duration-200 disabled:opacity-40 disabled:cursor-not-allowed";

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={toggleMute}
        disabled={busy || paused}
        aria-pressed={!isMicrophoneEnabled}
        title={isMicrophoneEnabled ? "Mute microphone" : "Unmute microphone"}
        className={`${base} ${
          isMicrophoneEnabled
            ? "border-white/10 text-white/70 hover:bg-white/5"
            : "border-amber-400/40 text-amber-300 bg-amber-400/10 hover:bg-amber-400/20"
        }`}
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
          <rect x="5.5" y="1.5" width="5" height="8" rx="2.5" />
          <path d="M3 7.5a5 5 0 0 0 10 0M8 12.5v2" />
          {!isMicrophoneEnabled && <path d="M2 2l12 12" />}
        </svg>
        {isMicrophoneEnabled ? "Mute" : "Unmute"}
      </button>

      <button
        onClick={togglePause}
        disabled={busy}
        aria-pressed={paused}
        title={paused ? "Resume the session" : "Pause the session"}
        className={`${base} ${
          paused
            ? "border-aurora/50 text-glow bg-aurora/10 hover:bg-aurora/20"
            : "border-white/10 text-white/70 hover:bg-white/5"
        }`}
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
          {paused ? <path d="M5 3l8 5-8 5z" /> : <path d="M4 3h3v10H4zM9 3h3v10H9z" />}
        </svg>
        {paused ? "Resume" : "Pause"}
      </button>
    </div>
  );
}
