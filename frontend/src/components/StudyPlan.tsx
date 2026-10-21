/**
 * StudyPlan: list of suggested next topics, built from the learner's past
 * lessons. Picking one starts a session that teaches it straight away.
 *
 * @author Pritam
 * @date 2026-10-21
 */

"use client";

/** One suggested topic from GET /study-plan/{identity}. */
export interface PlanTopic {
  topic: string;
  reason: string;
}

interface Props {
  /** Suggestions, or null while they are being fetched. */
  topics: PlanTopic[] | null;
  /** Whether a session is being started (disables the rows). */
  loading: boolean;
  onPick: (topic: string) => void;
  onClose: () => void;
}

/**
 * Render the study plan as a list.
 *
 * @param props - Component props.
 * @returns The study plan section.
 */
export default function StudyPlan({ topics, loading, onPick, onClose }: Props) {
  return (
    <section className="max-w-5xl mx-auto px-6 mb-8" aria-label="Study plan">
      <div className="flex items-center justify-between mb-3 pl-1">
        <p className="text-xs uppercase tracking-widest text-white/30 font-semibold">
          Your next lesson
        </p>
        <button
          onClick={onClose}
          className="text-xs text-white/40 hover:text-white"
          aria-label="Close study plan"
        >
          Close
        </button>
      </div>

      {topics === null ? (
        <p className="text-sm text-white/40 pl-1">Planning your next topics…</p>
      ) : topics.length === 0 ? (
        <p className="text-sm text-white/40 pl-1">
          Finish a lesson first and we&apos;ll suggest what&apos;s next.
        </p>
      ) : (
        <ul className="divide-y divide-white/5 rounded-2xl border border-white/5 bg-nebula">
          {topics.map((t, i) => (
            <li key={t.topic}>
              <button
                onClick={() => onPick(t.topic)}
                disabled={loading}
                className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-aurora/10
                           transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed
                           focus:outline-none focus-visible:ring-2 focus-visible:ring-aurora"
              >
                <span className="text-sm font-semibold text-glow w-5">{i + 1}</span>
                <span className="flex-1 min-w-0">
                  <span className="block text-sm font-medium text-white/90">{t.topic}</span>
                  {t.reason && (
                    <span className="block text-xs text-white/40 mt-0.5">{t.reason}</span>
                  )}
                </span>
                <span className="text-xs text-white/40">Start →</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
