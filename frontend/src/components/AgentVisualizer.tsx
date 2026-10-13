/**
 * AgentVisualizer: displays animated rings and a bar visualizer reflecting agent state.
 *
 * @author Pritam
 * @date 2026-10-12
 */

"use client";

import { useVoiceAssistant, BarVisualizer } from "@livekit/components-react";

/** Human-readable labels for each voice assistant state. */
const STATE_LABELS: Record<string, string> = {
  disconnected: "Disconnected",
  connecting: "Connecting…",
  initializing: "Waking up…",
  listening: "Listening",
  thinking: "Thinking…",
  speaking: "Speaking",
};

/** Tailwind colour classes applied to the status indicator per state. */
const STATE_COLORS: Record<string, string> = {
  disconnected: "text-white/30",
  connecting: "text-aurora/60",
  initializing: "text-aurora/60",
  listening: "text-green-400",
  thinking: "text-yellow-400",
  speaking: "text-glow",
};

/**
 * Renders an animated ring visualizer and a state label for the voice agent.
 *
 * Uses the LiveKit `useVoiceAssistant` hook to read the current agent state
 * and audio track, showing a `BarVisualizer` while the agent is speaking and
 * a static atom icon otherwise.
 *
 * @returns The agent visualizer UI.
 */
export default function AgentVisualizer() {
  const { state, audioTrack } = useVoiceAssistant();

  const label = STATE_LABELS[state] ?? state;
  const color = STATE_COLORS[state] ?? "text-white/50";
  const isSpeaking = state === "speaking";
  const isActive = !["disconnected", "connecting"].includes(state);

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Visualizer ring */}
      <div className="relative w-40 h-40 flex items-center justify-center">
        {/* Outer animated ring */}
        <div
          className={`absolute inset-0 rounded-full border-2 transition-all duration-500 ${
            isActive
              ? "border-aurora/50 animate-pulse_slow"
              : "border-white/10"
          }`}
        />
        {/* Second ring */}
        <div
          className={`absolute inset-4 rounded-full border transition-all duration-500 ${
            isSpeaking ? "border-glow/40 animate-spin_slow" : "border-white/5"
          }`}
        />

        {/* Bar visualizer or idle icon */}
        <div className="w-20 h-12 flex items-center justify-center">
          {isSpeaking && audioTrack ? (
            <BarVisualizer
              trackRef={audioTrack}
              barCount={5}
              style={{ width: "100%", height: "100%" }}
            />
          ) : (
            <span className="text-4xl opacity-60">⚛</span>
          )}
        </div>
      </div>

      {/* State label */}
      <div className="flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full ${
            isActive ? "bg-current animate-pulse" : "bg-white/20"
          } ${color}`}
        />
        <span className={`text-sm font-medium ${color}`}>{label}</span>
      </div>
    </div>
  );
}
