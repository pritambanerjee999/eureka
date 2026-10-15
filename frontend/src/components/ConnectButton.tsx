/**
 * ConnectButton: landing screen with branding, feature pills, and the session CTA.
 *
 * @author Pritam
 * @date 2026-10-12
 */

"use client";

import { useState } from "react";

/** Props accepted by the ConnectButton component. */
interface Props {
  /** Async callback invoked when the user clicks "Start Session". */
  onConnect: () => Promise<void>;
  /** Error message to display beneath the button, or null when there is none. */
  error: string | null;
}

/**
 * Renders the pre-connection landing screen for the Eureka tutor app.
 *
 * Shows the animated logo, a tagline, feature pills, and a call-to-action
 * button that triggers the LiveKit token fetch. Displays a loading spinner
 * while the connection is being established and an inline error on failure.
 *
 * @param props - Component props.
 * @returns The connect screen UI.
 */
export default function ConnectButton({ onConnect, error }: Props) {
  const [loading, setLoading] = useState(false);

  /**
   * Set the loading state, await the parent's connect handler, then clear it.
   */
  const handleClick = async () => {
    setLoading(true);
    await onConnect();
    setLoading(false);
  };

  return (
    <div className="flex flex-col items-center gap-10 px-6 text-center">
      {/* Logo / title */}
      <div className="flex flex-col items-center gap-3">
        <div className="relative w-24 h-24">
          {/* Outer ring */}
          <div className="absolute inset-0 rounded-full border-2 border-aurora/30 animate-spin_slow" />
          {/* Inner ring */}
          <div className="absolute inset-3 rounded-full border border-aurora/50 animate-spin_slow [animation-direction:reverse]" />
          {/* Core */}
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-4xl">⚛</span>
          </div>
        </div>

        <h1 className="text-5xl font-bold tracking-tight text-white">Eureka</h1>
        <p className="text-glow/80 text-lg">Your Feynman-style physics tutor</p>
      </div>

      {/* Feature pills */}
      <div className="flex flex-wrap justify-center gap-2 max-w-sm">
        {["Voice-first", "Physics intuition", "Socratic method", "Saves progress"].map(
          (f) => (
            <span
              key={f}
              className="px-3 py-1 rounded-full bg-aurora/10 border border-aurora/20 text-glow text-sm"
            >
              {f}
            </span>
          ),
        )}
      </div>

      {/* CTA */}
      <button
        onClick={handleClick}
        disabled={loading}
        className="relative px-10 py-4 rounded-2xl bg-aurora hover:bg-aurora/90 disabled:opacity-50 disabled:cursor-not-allowed
                   text-white font-semibold text-lg transition-all duration-200
                   shadow-[0_0_30px_rgba(99,102,241,0.4)] hover:shadow-[0_0_50px_rgba(99,102,241,0.6)]"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8H4z"
              />
            </svg>
            Connecting…
          </span>
        ) : (
          "Start Session"
        )}
      </button>

      {error && <p className="text-red-400 text-sm max-w-xs">{error}</p>}

      <p className="text-white/20 text-xs max-w-xs">
        Make sure your microphone is allowed. Eureka will greet you once connected.
      </p>
    </div>
  );
}
