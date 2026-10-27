export interface LogoOption {
  id: number;
  name: string;
  subtitle: string;
  description: string;
  svg: string;
}

const COMMON_DEFS = `
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#132038"/>
      <stop offset="55%" stop-color="#0b1324"/>
      <stop offset="100%" stop-color="#050912"/>
    </linearGradient>
    <linearGradient id="rimGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="50%" stop-color="#2dd4bf"/>
      <stop offset="100%" stop-color="#10b981"/>
    </linearGradient>
    <linearGradient id="cyanEmerald" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="55%" stop-color="#34d399"/>
      <stop offset="100%" stop-color="#10b981"/>
    </linearGradient>
    <linearGradient id="emeraldGold" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#10b981"/>
      <stop offset="60%" stop-color="#34d399"/>
      <stop offset="100%" stop-color="#fde047"/>
    </linearGradient>
    <linearGradient id="cyanViolet" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#7dd3fc"/>
      <stop offset="50%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#818cf8"/>
    </linearGradient>
  </defs>
  <rect x="3" y="3" width="58" height="58" rx="16" fill="url(#bgGrad)" stroke="url(#rimGrad)" stroke-width="2.2"/>
`;

export const LOGO_OPTIONS: LogoOption[] = [
  {
    id: 1,
    name: 'Option 1 · The Falcon Eye',
    subtitle: 'Predator Scout Optics',
    description:
      'Sleek geometric falcon crest formed by overlapping cyan and emerald wing-blades with a glowing gold-emerald scout pupil.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${COMMON_DEFS}
      <path d="M12 36 C18 20, 34 14, 52 16 C43 24, 38 30, 34 44 C26 40, 19 38, 12 36 Z" fill="url(#cyanEmerald)" opacity="0.92"/>
      <path d="M16 44 C24 32, 36 26, 50 26 C42 36, 34 46, 22 50 C19 48, 17 46, 16 44 Z" fill="url(#emeraldGold)" opacity="0.88"/>
      <circle cx="35" cy="27" r="4.2" fill="#050912"/>
      <circle cx="35" cy="27" r="2.3" fill="#fde047"/>
    </svg>`,
  },
  {
    id: 2,
    name: 'Option 2 · The Prism Star',
    subtitle: '4-Point Alpha Facet',
    description:
      'Luxury 4-point faceted diamond star (✦) with cyan, emerald, and gold glass planes refracting from a central core.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${COMMON_DEFS}
      <circle cx="32" cy="32" r="19" stroke="#38bdf8" stroke-opacity="0.22" stroke-width="1.2"/>
      <path d="M32 10 L38.5 25.5 L54 32 L38.5 38.5 L32 54 L25.5 38.5 L10 32 L25.5 25.5 Z" fill="url(#cyanEmerald)" stroke="#a7f3d0" stroke-width="1"/>
      <path d="M32 10 L38.5 25.5 L32 32 L25.5 25.5 Z" fill="url(#emeraldGold)"/>
      <path d="M32 32 L54 32 L38.5 38.5 Z" fill="#38bdf8" opacity="0.85"/>
      <circle cx="32" cy="32" r="3.4" fill="#fde047"/>
    </svg>`,
  },
  {
    id: 3,
    name: 'Option 3 · The Neural Orbit',
    subtitle: 'Fine-Tuned AI Decision Core',
    description:
      'Intersecting gyroscopic orbital rings around a glowing emerald AI nucleus with calibrated satellite nodes.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${COMMON_DEFS}
      <ellipse cx="32" cy="32" rx="21" ry="9.5" transform="rotate(-30 32 32)" stroke="url(#cyanEmerald)" stroke-width="2.4"/>
      <ellipse cx="32" cy="32" rx="21" ry="9.5" transform="rotate(30 32 32)" stroke="url(#emeraldGold)" stroke-width="2.4"/>
      <circle cx="32" cy="32" r="6.2" fill="url(#emeraldGold)"/>
      <circle cx="32" cy="32" r="2.6" fill="#ffffff"/>
      <circle cx="16" cy="23" r="2.6" fill="#38bdf8"/>
      <circle cx="48" cy="23" r="2.6" fill="#fde047"/>
      <circle cx="32" cy="49" r="2.6" fill="#34d399"/>
    </svg>`,
  },
  {
    id: 4,
    name: 'Option 4 · The BS Monogram',
    subtitle: 'Geometric Interlocking Ribbon',
    description:
      'Architectural B and S letterforms sculpted from a continuous neon cyan-to-emerald ribbon.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${COMMON_DEFS}
      <path d="M17 17 H29 C34 17, 37 20, 37 24.5 C37 28, 34.5 30.5, 31 31.5 C35.5 32.5, 38 35.5, 38 40 C38 44.5, 34.5 47, 29 47 H17 V17 Z" stroke="url(#cyanEmerald)" stroke-width="4.2" stroke-linejoin="round"/>
      <path d="M48 21 C44 17.5, 36 18, 35 23.5 C34 29, 49 30, 48 39 C47 46, 38 47.5, 33 44" stroke="url(#emeraldGold)" stroke-width="4.2" stroke-linecap="round"/>
    </svg>`,
  },
  {
    id: 5,
    name: 'Option 5 · The Sonar Pulse',
    subtitle: 'Acoustic Signal Intelligence',
    description:
      'Asymmetric sonar wave arcs radiating outward from a high-conviction emerald-gold signal origin.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${COMMON_DEFS}
      <circle cx="22" cy="42" r="4.8" fill="url(#emeraldGold)"/>
      <path d="M 22 30 A 12 12 0 0 1 34 42" stroke="#34d399" stroke-width="3.4" stroke-linecap="round"/>
      <path d="M 22 21 A 21 21 0 0 1 43 42" stroke="#38bdf8" stroke-width="3.4" stroke-linecap="round"/>
      <path d="M 22 12 A 30 30 0 0 1 52 42" stroke="url(#cyanEmerald)" stroke-width="3.4" stroke-linecap="round"/>
      <circle cx="45" cy="19" r="3.2" fill="#fde047"/>
    </svg>`,
  },
  {
    id: 6,
    name: 'Option 6 · The Royal Crest',
    subtitle: 'Crowned Tournament Shield',
    description:
      'Smooth curved championship shield split in two-tone obsidian with a 3-point emerald & gold crown inside.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${COMMON_DEFS}
      <path d="M32 10 L50 16 V31 C50 43.5, 42 51.5, 32 55 C22 51.5, 14 43.5, 14 31 V16 L32 10 Z" fill="#0d182c" stroke="url(#cyanEmerald)" stroke-width="2.6" stroke-linejoin="round"/>
      <path d="M21 38 L23 25 L29 31 L32 22 L35 31 L41 25 L43 38 Z" fill="url(#emeraldGold)" stroke="#fde047" stroke-width="1.2" stroke-linejoin="round"/>
      <rect x="21" y="40.5" width="22" height="3" rx="1.5" fill="#38bdf8"/>
    </svg>`,
  },
  {
    id: 7,
    name: 'Option 7 · The Compass Rose',
    subtitle: 'True North Scout Navigator',
    description:
      'Precision 8-point navigator compass rose with emerald North-South and electric-cyan East-West needles.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${COMMON_DEFS}
      <circle cx="32" cy="32" r="18" stroke="#38bdf8" stroke-opacity="0.3" stroke-width="1.5"/>
      <polygon points="32,9 36.5,27.5 32,32 27.5,27.5" fill="url(#emeraldGold)"/>
      <polygon points="32,55 36.5,36.5 32,32 27.5,36.5" fill="#10b981" opacity="0.75"/>
      <polygon points="55,32 36.5,36.5 32,32 36.5,27.5" fill="#38bdf8"/>
      <polygon points="9,32 27.5,36.5 32,32 27.5,27.5" fill="#0284c7" opacity="0.8"/>
      <circle cx="32" cy="32" r="3.5" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: 8,
    name: 'Option 8 · The Infinity Wave',
    subtitle: 'Continuous Calibration Loop',
    description:
      '3D Möbius infinity loop (∞) in a continuous sky-to-emerald-to-gold gradient symbolizing compounding edge.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${COMMON_DEFS}
      <path d="M21 24 C14 24, 11 32, 16 38 C21 43, 28 36, 32 32 C36 28, 43 21, 48 26 C53 32, 50 40, 43 40 C37 40, 35 35, 32 32 C29 29, 26 24, 21 24 Z" stroke="url(#emeraldGold)" stroke-width="4.8" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="20" cy="32" r="2.8" fill="#38bdf8"/>
      <circle cx="44" cy="32" r="2.8" fill="#fde047"/>
    </svg>`,
  },
  {
    id: 9,
    name: 'Option 9 · The Quantum Matrix',
    subtitle: '9-Node Decision Grid',
    description:
      '3×3 neural decision matrix where the winning diagonal path lights up in emerald & gold.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${COMMON_DEFS}
      <line x1="18" y1="46" x2="32" y2="32" stroke="#34d399" stroke-width="3.2"/>
      <line x1="32" y1="32" x2="46" y2="18" stroke="#fde047" stroke-width="3.2"/>
      <line x1="18" y1="32" x2="32" y2="18" stroke="#38bdf8" stroke-opacity="0.45" stroke-width="2"/>
      <line x1="32" y1="46" x2="46" y2="32" stroke="#38bdf8" stroke-opacity="0.45" stroke-width="2"/>
      <circle cx="18" cy="18" r="3.6" fill="#38bdf8" opacity="0.55"/>
      <circle cx="32" cy="18" r="3.6" fill="#38bdf8"/>
      <circle cx="46" cy="18" r="4.8" fill="#fde047"/>
      <circle cx="18" cy="32" r="3.6" fill="#38bdf8"/>
      <circle cx="32" cy="32" r="4.8" fill="#34d399"/>
      <circle cx="46" cy="32" r="3.6" fill="#38bdf8"/>
      <circle cx="18" cy="46" r="4.6" fill="#10b981"/>
      <circle cx="32" cy="46" r="3.6" fill="#38bdf8"/>
      <circle cx="46" cy="46" r="3.6" fill="#38bdf8" opacity="0.55"/>
    </svg>`,
  },
  {
    id: 10,
    name: 'Option 10 · The Arena Star',
    subtitle: 'Stadium Arch & Victory Star',
    description:
      'Sweeping double stadium roof arch crowning a faceted 5-point championship star in emerald and gold.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${COMMON_DEFS}
      <path d="M12 28 C20 14, 44 14, 52 28" stroke="url(#cyanEmerald)" stroke-width="3.2" stroke-linecap="round"/>
      <path d="M17 33 C23 22, 41 22, 47 33" stroke="#38bdf8" stroke-opacity="0.5" stroke-width="2" stroke-linecap="round"/>
      <polygon points="32,24 35.3,31 43,32 37.3,37.2 38.8,44.8 32,41 25.2,44.8 26.7,37.2 21,32 28.7,31" fill="url(#emeraldGold)" stroke="#fde047" stroke-width="1"/>
    </svg>`,
  },
];
