/**
 * TopicGrid: 3-column grid of branch cards, each listing topic pills for the
 * currently selected expertise level.
 *
 * @author Pritam
 * @date 2026-10-12
 */

"use client";

import { BRANCHES, type Level } from "@/data/topics";

interface Props {
  level: Level;
  /** Whether a connection is currently being established (disables pill clicks). */
  loading?: boolean;
  onTopicClick: (topic: string) => void;
}

/**
 * Renders a responsive grid of physics branch cards.
 *
 * Each card shows the branch icon + name in a header, then a list of clickable
 * topic pills filtered to the active level. The selected topic pill glows
 * aurora and the card border brightens.
 *
 * @param props - active level, loading flag, and topic-click callback.
 * @returns The topic grid UI.
 */
export default function TopicGrid({ level, loading = false, onTopicClick }: Props) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full">
      {BRANCHES.map((branch) => {
        const topics = branch.topics[level];

        return (
          <div
            key={branch.id}
            className="flex flex-col gap-3 p-5 rounded-2xl border bg-nebula transition-all duration-200 border-white/5 hover:border-white/15 hover:-translate-y-0.5"
          >
            {/* Card header */}
            <div className="flex items-center gap-2">
              <span className="text-2xl leading-none">{branch.icon}</span>
              <h3 className="text-sm font-semibold text-white/90 leading-tight">
                {branch.name}
              </h3>
            </div>

            {/* Topic pills */}
            <div className="flex flex-wrap gap-2">
              {topics.map((topic) => (
                <button
                  key={topic}
                  onClick={() => onTopicClick(topic)}
                  disabled={loading}
                  className={[
                    "px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150",
                    "focus:outline-none focus-visible:ring-2 focus-visible:ring-aurora",
                    loading
                      ? "bg-white/5 text-white/30 border border-white/5 cursor-not-allowed"
                      : "bg-white/5 text-white/60 hover:bg-aurora/20 hover:text-white hover:border-aurora/40 border border-white/10 cursor-pointer",
                  ].join(" ")}
                >
                  {topic}
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
