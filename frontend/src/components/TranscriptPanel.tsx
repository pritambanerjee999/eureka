/**
 * TranscriptPanel: streams live transcription segments and shows prior session history.
 *
 * @author Pritam
 * @date 2026-10-12
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useRoomContext } from "@livekit/components-react";
import { RoomEvent } from "livekit-client";

/** A single message record from the persistent conversation history. */
interface HistoryMessage {
  role: string;
  content: string;
  timestamp: string;
}

/** A live transcription segment received from the LiveKit room. */
interface LiveSegment {
  id: string;
  role: "user" | "agent";
  text: string;
  isFinal: boolean;
}

/** Props accepted by the TranscriptPanel component. */
interface Props {
  /** Optional prior-session messages to display above the live transcript. */
  preloadedHistory?: HistoryMessage[];
}

/**
 * Displays a scrollable transcript of both past and live conversation turns.
 *
 * Subscribes to `RoomEvent.TranscriptionReceived` to update live segments in
 * real time, merging interim and final results by segment ID. Automatically
 * scrolls to the bottom as new content arrives.
 *
 * @param props - Component props.
 * @returns The transcript panel UI, or an empty-state placeholder.
 */
export default function TranscriptPanel({ preloadedHistory: rawHistory = [] }: Props) {
  // Only spoken turns belong in the transcript — drop session_start / level / checkpoint records.
  const preloadedHistory = rawHistory.filter((m) => m.role === "user" || m.role === "assistant");
  const [liveSegments, setLiveSegments] = useState<LiveSegment[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const room = useRoomContext();

  useEffect(() => {
    /**
     * Merge incoming transcription segments into component state.
     *
     * @param segments - Array of segment updates from the LiveKit event.
     * @param participant - The participant who produced the transcript.
     */
    const handleTranscription = (
      segments: { id: string; text: string; final: boolean }[],
      participant: { isAgent?: boolean } | undefined,
    ) => {
      const isAgent = !!(participant as { isAgent?: boolean })?.isAgent;
      const role = isAgent ? "agent" : "user";

      setLiveSegments((prev) => {
        const updated = [...prev];
        for (const seg of segments) {
          const idx = updated.findIndex((s) => s.id === seg.id);
          if (idx >= 0) {
            updated[idx] = { ...updated[idx], text: seg.text, isFinal: seg.final };
          } else {
            updated.push({ id: seg.id, role, text: seg.text, isFinal: seg.final });
          }
        }
        return updated;
      });
    };

    room.on(RoomEvent.TranscriptionReceived, handleTranscription as never);
    return () => {
      room.off(RoomEvent.TranscriptionReceived, handleTranscription as never);
    };
  }, [room]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [liveSegments]);

  const hasContent = preloadedHistory.length > 0 || liveSegments.length > 0;

  if (!hasContent) {
    return (
      <div className="text-white/20 text-sm text-center py-8">
        Your conversation will appear here…
      </div>
    );
  }

  return (
    <div className="w-full max-h-72 overflow-y-auto flex flex-col gap-3 pr-1">
      {/* Past sessions */}
      {preloadedHistory.length > 0 && (
        <>
          <p className="text-white/20 text-xs text-center">— previous sessions —</p>
          {preloadedHistory.map((msg, i) => (
            <div
              key={`hist-${i}`}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm leading-relaxed opacity-50 ${
                  msg.role === "user"
                    ? "bg-aurora/20 text-glow rounded-br-sm"
                    : "bg-nebula border border-white/10 text-white/80 rounded-bl-sm"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {liveSegments.length > 0 && (
            <p className="text-white/20 text-xs text-center">— this session —</p>
          )}
        </>
      )}

      {/* Live transcript */}
      {liveSegments.map((seg) => (
        <div
          key={seg.id}
          className={`flex ${seg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm leading-relaxed transition-opacity duration-200 ${
              seg.isFinal ? "opacity-100" : "opacity-60"
            } ${
              seg.role === "user"
                ? "bg-aurora/20 text-glow rounded-br-sm"
                : "bg-nebula border border-white/10 text-white/80 rounded-bl-sm"
            }`}
          >
            {seg.text}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
