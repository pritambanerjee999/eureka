/**
 * SiteFooter: full-width footer with the brand, a short how-to-use guide
 * split into columns, reference links, and a copyright bar.
 *
 * @author Pritam
 * @date 2026-10-14
 */

import { REFERENCES } from "@/data/references";

/** How-to-use guide, grouped into footer columns. */
const GUIDE = [
  {
    heading: "Get started",
    items: [
      "Pick your level, or take the three-question level check",
      "Tap a topic card, or start an open session from the sidebar",
      "Allow microphone access when your browser asks",
    ],
  },
  {
    heading: "During a session",
    items: [
      "Eureka speaks first; answer out loud and interrupt anytime",
      "Mute or pause from the top bar while you think",
      "Explain ideas back in your own words to earn checkpoints",
      "Use headphones so background voices don't cut in",
    ],
  },
  {
    heading: "Your history",
    items: [
      "Past sessions live in the sidebar, grouped by day",
      "Open one to reread the transcript and your notes",
      "Pick a topic back up with one click",
      "Hide the sidebar for more room",
    ],
  },
];

/**
 * Render the site footer.
 *
 * @returns The footer element.
 */
export default function SiteFooter() {
  return (
    <footer aria-label="How to use Eureka" className="mt-8 border-t border-white/10 bg-black/40">
      <div className="max-w-6xl mx-auto px-6 py-12 grid gap-10 grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr_1fr]">
        {/* Brand */}
        <div className="col-span-2 lg:col-span-1">
          <div className="flex items-center gap-2">
            <span className="text-2xl">⚛</span>
            <span className="text-xl font-bold tracking-tight">Eureka</span>
          </div>
          <p className="mt-4 text-sm text-white/50 leading-relaxed max-w-xs">
            A voice physics tutor that teaches the Feynman way: intuition first, then questions
            that check you really understood.
          </p>
          <p className="mt-4 text-xs uppercase tracking-widest text-aurora/80 font-semibold">
            How to use Eureka
          </p>
        </div>

        {GUIDE.map((col) => (
          <div key={col.heading}>
            <h3 className="text-sm font-semibold text-white mb-4">{col.heading}</h3>
            <ul className="space-y-3">
              {col.items.map((item) => (
                <li key={item} className="text-sm text-white/55 leading-snug">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}

        <div>
          <h3 className="text-sm font-semibold text-white mb-4">Learn more</h3>
          <ul className="space-y-3">
            {REFERENCES.map((ref) => (
              <li key={ref.url}>
                <a
                  href={ref.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-white/55 hover:text-glow transition-colors"
                >
                  {ref.label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="border-t border-white/5">
        <div className="max-w-6xl mx-auto px-6 py-4 flex flex-wrap items-center justify-between gap-2 text-xs text-white/35">
          <p>© {new Date().getFullYear()} Eureka. Built for curious minds.</p>
          <p>Voice by OpenAI · Real-time audio by LiveKit</p>
        </div>
      </div>
    </footer>
  );
}
