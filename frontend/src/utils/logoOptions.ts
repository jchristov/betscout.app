export interface LogoOption {
  id: number | string;
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

const CHISELED_NEEDLES = `
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
`;

export const SPORTS_COMPASS_3_OPTIONS: LogoOption[] = [
  {
    id: '3.1',
    name: 'Option 3.1 · Stadium Pitch Compass',
    subtitle: 'Arena Pitch Lines + 3D Bevel',
    description:
      'Combines the #3 3D Chiseled Bevel Compass with a stadium turf circle, halfway line, and penalty-box arcs.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <!-- Stadium Pitch Boundary & Markings -->
      <circle cx="32" cy="32" r="20" fill="#06131f" stroke="#10b981" stroke-opacity="0.45" stroke-width="1.5"/>
      <line x1="12" y1="32" x2="52" y2="32" stroke="#34d399" stroke-opacity="0.3" stroke-width="1.2"/>
      <path d="M 22 14.8 A 9 9 0 0 0 42 14.8" stroke="#38bdf8" stroke-opacity="0.35" stroke-width="1.2"/>
      <path d="M 22 49.2 A 9 9 0 0 1 42 49.2" stroke="#38bdf8" stroke-opacity="0.35" stroke-width="1.2"/>
      <circle cx="32" cy="32" r="8.5" stroke="#34d399" stroke-opacity="0.35" stroke-width="1.2"/>
      ${CHISELED_NEEDLES}
      <circle cx="32" cy="32" r="3.4" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: '3.2',
    name: 'Option 3.2 · Sports Sphere Core',
    subtitle: 'Ball Seams + 3D Bevel Compass',
    description:
      'The #3 3D Chiseled Bevel Compass radiates out of a 3D sports ball sphere with curved basketball/tennis/football seams.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <!-- 3D Sports Ball Sphere & Curved Seams -->
      <circle cx="32" cy="32" r="19" fill="#071526" stroke="#38bdf8" stroke-opacity="0.5" stroke-width="1.6"/>
      <path d="M 18.5 18.5 Q 27 32 18.5 45.5" stroke="#34d399" stroke-opacity="0.55" stroke-width="1.6" stroke-linecap="round"/>
      <path d="M 45.5 18.5 Q 37 32 45.5 45.5" stroke="#34d399" stroke-opacity="0.55" stroke-width="1.6" stroke-linecap="round"/>
      <ellipse cx="32" cy="32" rx="19" ry="7.5" stroke="#38bdf8" stroke-opacity="0.32" stroke-width="1.2"/>
      ${CHISELED_NEEDLES}
      <circle cx="32" cy="32" r="3.6" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: '3.3',
    name: 'Option 3.3 · Champions Football Star',
    subtitle: 'Soccer Pentagon Core + 3D Bevel',
    description:
      'Pairs the #3 3D Chiseled Bevel Compass with a geometric football/soccer pentagon-hexagon sphere and gold center.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <circle cx="32" cy="32" r="19.5" fill="#071426" stroke="#34d399" stroke-opacity="0.45" stroke-width="1.5"/>
      <!-- Geometric Football Struts -->
      <polygon points="32,19 44,28 39,42 25,42 20,28" stroke="#38bdf8" stroke-opacity="0.38" stroke-width="1.3" fill="none"/>
      <line x1="20" y1="28" x2="13.5" y2="25" stroke="#38bdf8" stroke-opacity="0.38" stroke-width="1.3"/>
      <line x1="44" y1="28" x2="50.5" y2="25" stroke="#38bdf8" stroke-opacity="0.38" stroke-width="1.3"/>
      <line x1="25" y1="42" x2="20" y2="48" stroke="#38bdf8" stroke-opacity="0.38" stroke-width="1.3"/>
      <line x1="39" y1="42" x2="44" y2="48" stroke="#38bdf8" stroke-opacity="0.38" stroke-width="1.3"/>
      ${CHISELED_NEEDLES}
      <polygon points="32,27.2 36.4,30.4 34.7,35.6 29.3,35.6 27.6,30.4" fill="#050912" stroke="#fde047" stroke-width="1.4"/>
    </svg>`,
  },
  {
    id: '3.4',
    name: 'Option 3.4 · Victory Laurel Compass',
    subtitle: 'Championship Wreath + 3D Bevel',
    description:
      'Frames the #3 3D Chiseled Bevel Compass inside a golden-emerald sports championship laurel wreath.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <!-- Left & Right Victory Laurel Arcs -->
      <path d="M 26 51 C 14 46, 10 34, 15 20 C 17 15, 21 12, 25 11" stroke="url(#emeraldGold)" stroke-width="2.2" stroke-linecap="round" stroke-dasharray="4 2.5"/>
      <path d="M 38 51 C 50 46, 54 34, 49 20 C 47 15, 43 12, 39 11" stroke="url(#emeraldGold)" stroke-width="2.2" stroke-linecap="round" stroke-dasharray="4 2.5"/>
      <circle cx="32" cy="32" r="15.5" stroke="#38bdf8" stroke-opacity="0.28" stroke-width="1.2"/>
      ${CHISELED_NEEDLES}
      <circle cx="32" cy="32" r="3.4" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: '3.5',
    name: 'Option 3.5 · Ball-Flight Orbit Compass',
    subtitle: 'Dynamic Ball Trajectory + 3D Bevel',
    description:
      'A high-velocity sports ball flight swoosh orbits around the #3 3D Chiseled Bevel Compass with a glowing ball in motion.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <ellipse cx="32" cy="32" rx="22" ry="9" transform="rotate(-35 32 32)" stroke="url(#emeraldGold)" stroke-width="2.2"/>
      <circle cx="47.5" cy="18.5" r="3.8" fill="#fde047" stroke="#050912" stroke-width="1"/>
      <path d="M 45 17 Q 47.5 18.5 46 21" stroke="#050912" stroke-width="1"/>
      <circle cx="32" cy="32" r="16.5" stroke="#38bdf8" stroke-opacity="0.25" stroke-width="1.2"/>
      ${CHISELED_NEEDLES}
      <circle cx="32" cy="32" r="3.4" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: '3.6',
    name: 'Option 3.6 · League Shield + 3D Bevel',
    subtitle: 'Premier Crest + Chiseled Star',
    description:
      'Houses the #3 3D Chiseled Bevel Compass inside a curved sports league shield crest with stadium pitch stripes.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <path d="M32 7.5 L51 14 V30.5 C51 44.5, 42.5 53, 32 56.5 C21.5 53, 13 44.5, 13 30.5 V14 L32 7.5 Z" fill="#081526" stroke="url(#cyanEmerald)" stroke-width="2" stroke-linejoin="round"/>
      <circle cx="32" cy="31" r="13.5" stroke="#38bdf8" stroke-opacity="0.3" stroke-width="1.2"/>
      <g transform="translate(0, -1) scale(0.84)" style="transform-origin: 32px 32px;">
        ${CHISELED_NEEDLES}
      </g>
      <circle cx="32" cy="31" r="3.2" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: '3.7',
    name: 'Option 3.7 · Running Track & Turf',
    subtitle: 'Multi-Lane Stadium Oval + 3D Bevel',
    description:
      'Surrounds the #3 3D Chiseled Bevel Compass with concentric stadium arena bowl lanes and 4 floodlight corner nodes.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <circle cx="32" cy="32" r="21" stroke="#38bdf8" stroke-opacity="0.38" stroke-width="1.4"/>
      <circle cx="32" cy="32" r="17.5" stroke="#34d399" stroke-opacity="0.32" stroke-width="1.4" stroke-dasharray="6 3"/>
      <circle cx="17" cy="17" r="2.2" fill="#fde047"/>
      <circle cx="47" cy="17" r="2.2" fill="#fde047"/>
      <circle cx="17" cy="47" r="2.2" fill="#38bdf8"/>
      <circle cx="47" cy="47" r="2.2" fill="#38bdf8"/>
      ${CHISELED_NEEDLES}
      <circle cx="32" cy="32" r="3.4" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: '3.8',
    name: 'Option 3.8 · Golden Ball Centerpiece',
    subtitle: '3D Chiseled Needles + Sports Ball Hub',
    description:
      'Places a detailed golden-emerald sports ball emblem right at the central hub of the #3 3D Chiseled Bevel Compass.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <circle cx="32" cy="32" r="19" stroke="#38bdf8" stroke-opacity="0.3" stroke-width="1.4"/>
      ${CHISELED_NEEDLES}
      <!-- Central Sports Ball Medallion -->
      <circle cx="32" cy="32" r="7.5" fill="#061220" stroke="#fde047" stroke-width="1.8"/>
      <path d="M 27.5 27.5 Q 32 32 27.5 36.5" stroke="#34d399" stroke-width="1.5" stroke-linecap="round"/>
      <path d="M 36.5 27.5 Q 32 32 36.5 36.5" stroke="#34d399" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="24.5" y1="32" x2="39.5" y2="32" stroke="#fde047" stroke-opacity="0.6" stroke-width="1.2"/>
    </svg>`,
  },
  {
    id: '3.9',
    name: 'Option 3.9 · Arena Crown & Pitch',
    subtitle: 'Stadium Roof Arch + 3D Bevel',
    description:
      'Crowned by a sweeping stadium roof arch at the top and a curved turf line below the #3 3D Chiseled Bevel Compass.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <path d="M 11 22 C 20 9, 44 9, 53 22" stroke="url(#emeraldGold)" stroke-width="2.4" stroke-linecap="round"/>
      <path d="M 13 44 C 22 54, 42 54, 51 44" stroke="#38bdf8" stroke-opacity="0.5" stroke-width="2" stroke-linecap="round"/>
      <circle cx="32" cy="32" r="16" stroke="#38bdf8" stroke-opacity="0.24" stroke-width="1.2"/>
      ${CHISELED_NEEDLES}
      <circle cx="32" cy="32" r="3.4" fill="#ffffff"/>
    </svg>`,
  },
  {
    id: '3.10',
    name: 'Option 3.10 · 8-Point Chiseled + Ball Sphere',
    subtitle: '3D Bevel + 4 Sport Quadrant Seams',
    description:
      'Combines the #3 3D Chiseled Bevel Compass with 4 diagonal emerald/cyan ball-seam blades and a gold-emerald ball core.',
    svg: `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      ${SQUIRCLE_FRAME}
      <circle cx="32" cy="32" r="19.5" fill="#061222" stroke="#38bdf8" stroke-opacity="0.38" stroke-width="1.5"/>
      <!-- 4 Diagonal Chiseled Sub-Points -->
      <polygon points="45.5,18.5 32,32 32,26.5" fill="#fde047" opacity="0.75"/>
      <polygon points="45.5,18.5 37.5,32 32,32" fill="#10b981" opacity="0.75"/>
      <polygon points="18.5,18.5 32,26.5 32,32" fill="#7dd3fc" opacity="0.65"/>
      <polygon points="18.5,18.5 32,32 26.5,32" fill="#0284c7" opacity="0.65"/>
      <polygon points="45.5,45.5 37.5,32 32,32" fill="#7dd3fc" opacity="0.65"/>
      <polygon points="45.5,45.5 32,32 32,37.5" fill="#0284c7" opacity="0.65"/>
      <polygon points="18.5,45.5 32,37.5 32,32" fill="#34d399" opacity="0.65"/>
      <polygon points="18.5,45.5 32,32 26.5,32" fill="#047857" opacity="0.65"/>
      ${CHISELED_NEEDLES}
      <circle cx="32" cy="32" r="5" fill="#050912" stroke="#fde047" stroke-width="1.6"/>
      <circle cx="32" cy="32" r="2.2" fill="#34d399"/>
    </svg>`,
  },
];

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
