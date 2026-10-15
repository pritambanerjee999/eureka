/**
 * Curated physics references shown in the live session and the site footer.
 *
 * @author Pritam
 * @date 2026-10-14
 */

export interface Reference {
  label: string;
  subtitle: string;
  url: string;
  icon: string;
}

export const REFERENCES: Reference[] = [
  {
    label: "The Feynman Lectures",
    subtitle: "Full text, free online",
    url: "https://www.feynmanlectures.caltech.edu",
    icon: "📖",
  },
  {
    label: "HyperPhysics",
    subtitle: "Concept maps + formulas",
    url: "http://hyperphysics.phy-astr.gsu.edu",
    icon: "🔗",
  },
  {
    label: "PhET Simulations",
    subtitle: "Interactive physics sims",
    url: "https://phet.colorado.edu",
    icon: "⚗️",
  },
  {
    label: "Khan Academy Physics",
    subtitle: "Video walkthroughs",
    url: "https://www.khanacademy.org/science/physics",
    icon: "🎥",
  },
  {
    label: "MIT OpenCourseWare",
    subtitle: "Full lecture notes + exams",
    url: "https://ocw.mit.edu/courses/physics/",
    icon: "🎓",
  },
];
