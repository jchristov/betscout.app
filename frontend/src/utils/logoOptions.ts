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
    <linearGradient id="goldAmber" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fef08a"/>
      <stop offset="55%" stop-color="#fde047"/>
      <stop offset="100%" stop-color="#f59e0b"/>
    </linearGradient>
  </defs>
`;

const SQUIRCLE_FRAME = `
  ${COMMON_DEFS}
  <rect x="3" y="3" width="58" height="58" rx="16" fill="url(#bgGrad)" stroke="url(#rimGrad)" stroke-width="2.2"/>
`;

export const LOGO_OPTIONS: LogoOption[] = [
  {
    id: 1,
    name: 'Variation 7.1 · Classic 4-Point',
    subtitle: 'Original Option 7',
    description:
      'Clean 4-point cardinal compass star (North in emerald-gold, South in deep emerald, East/West in electric cyan) over a single azimuth ring.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <circle cx="32" cy="32" r="18" stroke="#38bdf8" stroke-opacity="0.3" stroke-width="1.5"/>
      <polygon points="32,9 36.5,27.5 32,32 27.5,27.5" fill="url(#emeraldGold)"/>
      <polygon points="32,55 36.5,36.5 32,32 27.5,36.5" fill="#10b981" opacity="0.75"/>
      <polygon points="55,32 36.5,36.5 32,32 36.5,27.5" fill="#38bdf8"/>
      <polygon points="9,32 27.5,36.5 32,32 27.5,27.5" fill="#0284c7" opacity="0.8"/>
      <circle cx="32" cy="32" r="3.5" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: 2,
    name: 'Variation 7.2 · 8-Point Imperial Rose',
    subtitle: 'Cardinal + Diagonal Star',
    description:
      '4-point cardinal star layered over a 45° secondary 4-point diagonal star (NE, NW, SE, SW) with a gold-rimmed emerald center.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <circle cx="32" cy="32" r="19" stroke="#38bdf8" stroke-opacity="0.25" stroke-width="1.3"/>
      <!-- 4 Diagonal Sub-Needles -->
      <polygon points="46.5,17.5 35.5,32 32,28.5" fill="#38bdf8" opacity="0.55"/>
      <polygon points="17.5,17.5 32,28.5 28.5,32" fill="#38bdf8" opacity="0.45"/>
      <polygon points="46.5,46.5 32,35.5 35.5,32" fill="#38bdf8" opacity="0.45"/>
      <polygon points="17.5,46.5 28.5,32 32,35.5" fill="#38bdf8" opacity="0.38"/>
      <!-- 4 Main Cardinal Needles -->
      <polygon points="32,8 36.5,27.5 32,32 27.5,27.5" fill="url(#emeraldGold)"/>
      <polygon points="32,56 36.5,36.5 32,32 27.5,36.5" fill="#10b981" opacity="0.8"/>
      <polygon points="56,32 36.5,36.5 32,32 36.5,27.5" fill="#38bdf8"/>
      <polygon points="8,32 27.5,36.5 32,32 27.5,27.5" fill="#0284c7" opacity="0.85"/>
      <circle cx="32" cy="32" r="4.2" fill="#050912" stroke="#fde047" stroke-width="1.6"/>
      <circle cx="32" cy="32" r="1.8" fill="#34d399"/>
    </svg>`,
  },
  {
    id: 3,
    name: 'Variation 7.3 · 3D Chiseled Bevel',
    subtitle: 'Sunlit & Shadowed Facets',
    description:
      'Every compass needle is split down its centerline into a bright sunlit facet and a deep shadowed facet like a Swiss chronometer.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <circle cx="32" cy="32" r="18.5" stroke="#38bdf8" stroke-opacity="0.28" stroke-width="1.4"/>
      <!-- North split bevel -->
      <polygon points="32,8 32,32 27,27" fill="#fde047"/>
      <polygon points="32,8 37,27 32,32" fill="#10b981"/>
      <!-- South split bevel -->
      <polygon points="32,56 32,32 37,37" fill="#34d399"/>
      <polygon points="32,56 27,37 32,32" fill="#047857"/>
      <!-- East split bevel -->
      <polygon points="56,32 32,32 37,27" fill="#7dd3fc"/>
      <polygon points="56,32 37,37 32,32" fill="#0284c7"/>
      <!-- West split bevel -->
      <polygon points="8,32 32,32 27,37" fill="#38bdf8"/>
      <polygon points="8,32 27,27 32,32" fill="#0369a1"/>
      <circle cx="32" cy="32" r="3.4" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: 4,
    name: 'Variation 7.4 · Tilted +22° Scout',
    subtitle: 'Dynamic North-East Heading',
    description:
      'Compass rose dynamically canted +22° toward the upper-right with a glowing emerald-gold heading and radar sweep arc.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <path d="M 18 18 A 20 20 0 0 1 48 20" stroke="#fde047" stroke-opacity="0.55" stroke-width="2" stroke-linecap="round"/>
      <circle cx="32" cy="32" r="17.5" stroke="#38bdf8" stroke-opacity="0.24" stroke-width="1.3" stroke-dasharray="3 3"/>
      <g transform="rotate(22 32 32)">
        <polygon points="32,8.5 36.5,27.5 32,32 27.5,27.5" fill="url(#emeraldGold)"/>
        <polygon points="32,55.5 36.5,36.5 32,32 27.5,36.5" fill="#10b981" opacity="0.78"/>
        <polygon points="55.5,32 36.5,36.5 32,32 36.5,27.5" fill="#38bdf8"/>
        <polygon points="8.5,32 27.5,36.5 32,32 27.5,27.5" fill="#0284c7" opacity="0.82"/>
        <circle cx="32" cy="32" r="3.5" fill="#ffffff"/>
      </g>
    </svg>`,
  },
  {
    id: 5,
    name: 'Variation 7.5 · Chronometer Bezel',
    subtitle: 'Precision Azimuth Ticks',
    description:
      'Cardinal compass rose framed by a precision 12-tick chronometer degree bezel and a gold North index marker at 12 o’clock.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <circle cx="32" cy="32" r="21.5" stroke="#38bdf8" stroke-opacity="0.32" stroke-width="1.3"/>
      <circle cx="32" cy="32" r="18.5" stroke="#34d399" stroke-opacity="0.25" stroke-width="2.2" stroke-dasharray="1.5 4.5"/>
      <polygon points="32,10.5 36.2,27.8 32,32 27.8,27.8" fill="url(#emeraldGold)"/>
      <polygon points="32,53.5 36.2,36.2 32,32 27.8,36.2" fill="#10b981" opacity="0.78"/>
      <polygon points="53.5,32 36.2,36.2 32,32 36.2,27.8" fill="#38bdf8"/>
      <polygon points="10.5,32 27.8,36.2 32,32 27.8,27.8" fill="#0284c7" opacity="0.82"/>
      <circle cx="32" cy="32" r="3.4" fill="#fde047"/>
    </svg>`,
  },
  {
    id: 6,
    name: 'Variation 7.6 · Open-Frame Gyro',
    subtitle: 'Hollow Core & Floating Orb',
    description:
      'Sleek open-frame geometric compass needles with a dark hollow core and a floating emerald-gold center orb.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <circle cx="32" cy="32" r="19" stroke="#38bdf8" stroke-opacity="0.28" stroke-width="1.4"/>
      <polygon points="32,9 37,27 32,24 27,27" fill="url(#emeraldGold)"/>
      <polygon points="32,55 37,37 32,40 27,37" fill="#10b981" opacity="0.82"/>
      <polygon points="55,32 37,37 40,32 37,27" fill="#38bdf8"/>
      <polygon points="9,32 27,37 24,32 27,27" fill="#0284c7" opacity="0.85"/>
      <circle cx="32" cy="32" r="6.5" stroke="#34d399" stroke-opacity="0.5" stroke-width="1.5"/>
      <circle cx="32" cy="32" r="3.2" fill="#fde047"/>
    </svg>`,
  },
  {
    id: 7,
    name: 'Variation 7.7 · Polaris North Beacon',
    subtitle: 'Elongated North Pointer + Halo',
    description:
      'Asymmetric scout compass where the North needle extends boldly to the top with a glowing gold-emerald beacon halo.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <circle cx="32" cy="34" r="16.5" stroke="#38bdf8" stroke-opacity="0.28" stroke-width="1.4"/>
      <polygon points="32,9 37,29.5 32,34 27,29.5" fill="url(#emeraldGold)"/>
      <polygon points="32,54 35.8,38 32,34 28.2,38" fill="#10b981" opacity="0.75"/>
      <polygon points="52,34 36,38 32,34 36,30" fill="#38bdf8"/>
      <polygon points="12,34 28,38 32,34 28,30" fill="#0284c7" opacity="0.8"/>
      <circle cx="32" cy="9" r="3.2" fill="#fde047"/>
      <circle cx="32" cy="34" r="3.2" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: 8,
    name: 'Variation 7.8 · Circular Medallion',
    subtitle: 'Round Twin-Ring Coin Bezel',
    description:
      'Housed inside a circular twin-ring coin medallion (no squircle corners) with cardinal notches and a 4-point compass star.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${COMMON_DEFS}
      <circle cx="32" cy="32" r="29" fill="url(#bgGrad)" stroke="url(#rimGrad)" stroke-width="2.4"/>
      <circle cx="32" cy="32" r="22" stroke="#38bdf8" stroke-opacity="0.28" stroke-width="1.3"/>
      <polygon points="32,8 36.8,27.2 32,32 27.2,27.2" fill="url(#emeraldGold)"/>
      <polygon points="32,56 36.8,36.8 32,32 27.2,36.8" fill="#10b981" opacity="0.78"/>
      <polygon points="56,32 36.8,36.8 32,32 36.8,27.2" fill="#38bdf8"/>
      <polygon points="8,32 27.2,36.8 32,32 27.2,27.2" fill="#0284c7" opacity="0.82"/>
      <circle cx="32" cy="32" r="3.6" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: 9,
    name: 'Variation 7.9 · Twin-Ring Astrolabe',
    subtitle: 'Compass + Quadrant Nodes',
    description:
      'Combines the 4-point compass rose with twin concentric radar rings and 4 glowing NE/NW/SE/SW quadrant nodes.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <circle cx="32" cy="32" r="20" stroke="#38bdf8" stroke-opacity="0.28" stroke-width="1.4"/>
      <circle cx="32" cy="32" r="11" stroke="#34d399" stroke-opacity="0.32" stroke-width="1.2"/>
      <circle cx="46" cy="18" r="2.3" fill="#fde047"/>
      <circle cx="18" cy="18" r="2.0" fill="#38bdf8" opacity="0.75"/>
      <circle cx="46" cy="46" r="2.0" fill="#38bdf8" opacity="0.75"/>
      <circle cx="18" cy="46" r="2.0" fill="#34d399" opacity="0.75"/>
      <polygon points="32,8.5 36.5,27.5 32,32 27.5,27.5" fill="url(#emeraldGold)"/>
      <polygon points="32,55.5 36.5,36.5 32,32 27.5,36.5" fill="#10b981" opacity="0.78"/>
      <polygon points="55.5,32 36.5,36.5 32,32 36.5,27.5" fill="#38bdf8"/>
      <polygon points="8.5,32 27.5,36.5 32,32 27.5,27.5" fill="#0284c7" opacity="0.82"/>
      <circle cx="32" cy="32" r="3.4" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: 10,
    name: 'Variation 7.10 · Sovereign Gold & Emerald',
    subtitle: 'Warm Gold + Electric Emerald',
    description:
      'High-contrast obsidian dial with warm champagne-gold East/West needles, electric emerald North/South needles, and a diamond core.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <circle cx="32" cy="32" r="18.5" stroke="#fde047" stroke-opacity="0.26" stroke-width="1.4"/>
      <polygon points="32,8.5 36.8,27.2 32,32 27.2,27.2" fill="url(#emeraldGold)"/>
      <polygon points="32,55.5 36.8,36.8 32,32 27.2,36.8" fill="#10b981" opacity="0.85"/>
      <polygon points="55.5,32 36.8,36.8 32,32 36.8,27.2" fill="url(#goldAmber)"/>
      <polygon points="8.5,32 27.2,36.8 32,32 27.2,27.2" fill="#f59e0b" opacity="0.85"/>
      <polygon points="32,27.5 36.5,32 32,36.5 27.5,32" fill="#ffffff"/>
    </svg>`,
  },
];
