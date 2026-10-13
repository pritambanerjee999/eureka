export type Level = "spark" | "current" | "momentum" | "field" | "singularity";

export interface LevelInfo {
  id: Level;
  name: string;
  subtitle: string;
  tag: string;
  gradient: string;
  border: string;
  text: string;
}

export interface Branch {
  id: string;
  name: string;
  icon: string;
  topics: Record<Level, string[]>;
}

export const LEVELS: LevelInfo[] = [
  {
    id: "spark",
    name: "Spark",
    subtitle: "Pure curiosity, no prior physics",
    tag: "Beginner",
    gradient: "from-orange-500 to-yellow-400",
    border: "border-orange-400",
    text: "text-orange-300",
  },
  {
    id: "current",
    name: "Current",
    subtitle: "High school / introductory physics",
    tag: "Foundational",
    gradient: "from-blue-500 to-cyan-400",
    border: "border-blue-400",
    text: "text-blue-300",
  },
  {
    id: "momentum",
    name: "Momentum",
    subtitle: "Undergraduate physics",
    tag: "Intermediate",
    gradient: "from-violet-500 to-purple-400",
    border: "border-violet-400",
    text: "text-violet-300",
  },
  {
    id: "field",
    name: "Field",
    subtitle: "Advanced undergrad / early grad",
    tag: "Advanced",
    gradient: "from-indigo-500 to-indigo-400",
    border: "border-indigo-400",
    text: "text-indigo-300",
  },
  {
    id: "singularity",
    name: "Singularity",
    subtitle: "Graduate & research level",
    tag: "Expert",
    gradient: "from-pink-500 to-rose-400",
    border: "border-pink-400",
    text: "text-pink-300",
  },
];

export const BRANCHES: Branch[] = [
  {
    id: "classical-mechanics",
    name: "Classical Mechanics",
    icon: "⚙️",
    topics: {
      spark: [
        "Why do things fall?",
        "What makes things move?",
        "Bouncing & collisions",
        "Why do pendulums swing?",
      ],
      current: [
        "Newton's three laws",
        "Projectile motion",
        "Work & energy",
        "Circular motion",
      ],
      momentum: [
        "Lagrangian mechanics",
        "Rotational dynamics",
        "Simple harmonic motion",
        "Coupled oscillators",
      ],
      field: [
        "Hamiltonian mechanics",
        "Noether's theorem",
        "Chaos & nonlinear dynamics",
        "Rigid body motion",
      ],
      singularity: [
        "Classical field theory",
        "Symplectic geometry",
        "KAM theorem",
        "Integrable systems",
      ],
    },
  },
  {
    id: "waves-sound",
    name: "Waves & Sound",
    icon: "🌊",
    topics: {
      spark: [
        "What is a wave?",
        "Why does sound travel?",
        "Why do strings make music?",
        "What is an echo?",
      ],
      current: [
        "Wave equation basics",
        "Interference & diffraction",
        "Standing waves",
        "The Doppler effect",
      ],
      momentum: [
        "Fourier analysis",
        "Wave packets",
        "Dispersion relations",
        "Polarisation",
      ],
      field: [
        "Group vs phase velocity",
        "Nonlinear waves",
        "Phonons",
        "Solitons",
      ],
      singularity: [
        "Topological wave phenomena",
        "Quantum optics basics",
        "Polaritons",
        "Photonic crystals",
      ],
    },
  },
  {
    id: "electromagnetism",
    name: "Electromagnetism",
    icon: "⚡",
    topics: {
      spark: [
        "What is electricity?",
        "How do magnets work?",
        "Lightning explained",
        "How does a motor work?",
      ],
      current: [
        "Coulomb's law",
        "Electric fields & potential",
        "Ohm's law & circuits",
        "Magnetic force",
      ],
      momentum: [
        "Maxwell's equations",
        "Electromagnetic waves",
        "Inductance & capacitance",
        "Poynting vector",
      ],
      field: [
        "Gauge theory basics",
        "Radiation from accelerating charges",
        "Multipole expansion",
        "Green's functions",
      ],
      singularity: [
        "Quantum electrodynamics intro",
        "Topological insulators",
        "Casimir effect",
        "Metamaterials",
      ],
    },
  },
  {
    id: "thermodynamics",
    name: "Thermodynamics",
    icon: "🌡️",
    topics: {
      spark: [
        "Why does ice melt?",
        "What is temperature?",
        "How does a fridge work?",
        "What is entropy?",
      ],
      current: [
        "Laws of thermodynamics",
        "Heat & work",
        "Ideal gas law",
        "Entropy basics",
      ],
      momentum: [
        "Carnot cycle",
        "Statistical mechanics intro",
        "Boltzmann distribution",
        "Phase transitions",
      ],
      field: [
        "Partition functions",
        "Ising model",
        "Critical phenomena",
        "Renormalisation group basics",
      ],
      singularity: [
        "Non-equilibrium thermodynamics",
        "Quantum thermodynamics",
        "Topological phases",
        "Field theory in stat mech",
      ],
    },
  },
  {
    id: "quantum-mechanics",
    name: "Quantum Mechanics",
    icon: "🔬",
    topics: {
      spark: [
        "Is light a wave or particle?",
        "Schrödinger's cat explained",
        "What is spin?",
        "What is a quantum?",
      ],
      current: [
        "Wave-particle duality",
        "The double-slit experiment",
        "Quantum tunnelling",
        "Atomic orbitals",
      ],
      momentum: [
        "Schrödinger equation",
        "Spin & angular momentum",
        "Perturbation theory",
        "Identical particles",
      ],
      field: [
        "Path integrals",
        "Second quantisation",
        "Entanglement & Bell's theorem",
        "Relativistic QM intro",
      ],
      singularity: [
        "Quantum field theory",
        "Renormalisation",
        "Spontaneous symmetry breaking",
        "Topological quantum computing",
      ],
    },
  },
  {
    id: "relativity",
    name: "Relativity",
    icon: "🌌",
    topics: {
      spark: [
        "Why does time slow near black holes?",
        "What is spacetime?",
        "E = mc² explained",
        "What is a black hole?",
      ],
      current: [
        "Special relativity basics",
        "Time dilation",
        "Length contraction",
        "The twin paradox",
      ],
      momentum: [
        "4-vectors & tensors",
        "Spacetime diagrams",
        "Relativistic mechanics",
        "Lorentz transformations",
      ],
      field: [
        "General relativity intro",
        "Geodesics",
        "Schwarzschild metric",
        "Gravitational waves",
      ],
      singularity: [
        "Einstein field equations",
        "Cosmological models",
        "Hawking radiation",
        "Quantum gravity approaches",
      ],
    },
  },
];
