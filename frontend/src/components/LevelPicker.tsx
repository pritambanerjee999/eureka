/**
 * LevelPicker: horizontal tab bar for selecting a physics expertise level.
 *
 * @author Pritam
 * @date 2026-10-12
 */

"use client";

import { LEVELS, type Level } from "@/data/topics";

interface Props {
  selected: Level;
  onChange: (level: Level) => void;
}

/**
 * Renders a scrollable horizontal row of five level tabs.
 *
 * The active tab gets the level's gradient background and scales up slightly.
 * Inactive tabs are dark with a muted text colour that brightens on hover.
 *
 * @param props - selected level and change handler.
 * @returns The level picker tab bar.
 */
export default function LevelPicker({ selected, onChange }: Props) {
  return (
    <div className="w-full overflow-x-auto pb-2 scrollbar-hide">
      <div className="flex gap-3 min-w-max px-1">
        {LEVELS.map((level) => {
          const isActive = level.id === selected;
          return (
            <button
              key={level.id}
              onClick={() => onChange(level.id)}
              className={[
                "relative flex flex-col items-start gap-1 px-5 py-4 rounded-2xl border transition-all duration-200",
                "focus:outline-none focus-visible:ring-2 focus-visible:ring-aurora",
                isActive
                  ? `bg-gradient-to-br ${level.gradient} border-transparent text-white scale-105 shadow-lg`
                  : `bg-nebula ${level.border}/20 border hover:border-opacity-60 hover:bg-white/5 text-white/50 hover:text-white/80`,
              ].join(" ")}
            >
              {/* Tag pill */}
              <span
                className={[
                  "text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full",
                  isActive
                    ? "bg-white/20 text-white"
                    : `bg-white/5 ${level.text}`,
                ].join(" ")}
              >
                {level.tag}
              </span>

              {/* Level name */}
              <span className="text-lg font-bold leading-tight whitespace-nowrap">
                {level.name}
              </span>

              {/* Subtitle */}
              <span
                className={[
                  "text-xs leading-snug max-w-[160px] text-left",
                  isActive ? "text-white/80" : "text-white/30",
                ].join(" ")}
              >
                {level.subtitle}
              </span>

              {/* Active indicator dot */}
              {isActive && (
                <span className="absolute bottom-2 right-3 w-1.5 h-1.5 rounded-full bg-white/60" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
