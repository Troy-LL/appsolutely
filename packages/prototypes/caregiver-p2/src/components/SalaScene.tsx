// The sala, drawn flat: picture rail, family frames, wall clock, sofa (green),
// the Sino box on a side table, and the lamp (amber). Decoration only.
const INK = '#2b2420', PAPER = '#f4ede0', GREEN = '#2f5e4e', AMBER = '#e9a83a'

export function SalaScene({ initials }: { initials: string[] }) {
  const [a = '', b = '', c = ''] = initials
  return (
    <svg viewBox="0 0 340 150" aria-hidden="true">
      <rect width="340" height="150" fill={PAPER} />
      <line x1="0" y1="20" x2="340" y2="20" stroke={INK} strokeWidth="2" />
      <path d="M45 20 L38 30 M45 20 L52 30 M98 20 L90 28 M98 20 L106 28 M218 20 L212 30 M218 20 L224 30" stroke={INK} strokeWidth="2" />
      <rect x="28" y="30" width="34" height="42" rx="3" fill={PAPER} stroke={GREEN} strokeWidth="5" />
      <rect x="76" y="28" width="44" height="54" rx="3" fill={PAPER} stroke={INK} strokeWidth="6" />
      <rect x="202" y="30" width="32" height="40" rx="3" fill={PAPER} stroke={INK} strokeWidth="5" />
      <g fontFamily="Fredoka, sans-serif" fontWeight="600" fill={INK} textAnchor="middle">
        <text x="45" y="57" fontSize="15">{a}</text>
        <text x="98" y="61" fontSize="18">{b}</text>
        <text x="218" y="56" fontSize="14">{c}</text>
      </g>
      <circle cx="160" cy="50" r="20" fill={PAPER} stroke={INK} strokeWidth="5" />
      <path d="M160 50 V38 M160 50 L168 55" stroke={INK} strokeWidth="3" strokeLinecap="round" />
      <g fill={GREEN} stroke={INK} strokeWidth="2.5">
        <rect x="44" y="88" width="180" height="30" rx="10" />
        <rect x="36" y="108" width="196" height="24" rx="8" />
        <rect x="24" y="98" width="26" height="36" rx="8" />
        <rect x="218" y="98" width="26" height="36" rx="8" />
      </g>
      <path d="M134 110 V130" stroke={INK} strokeWidth="2" />
      <rect x="32" y="134" width="6" height="8" fill={INK} /><rect x="230" y="134" width="6" height="8" fill={INK} />
      <rect x="256" y="112" width="38" height="5" rx="2" fill={INK} />
      <path d="M262 117 V142 M288 117 V142" stroke={INK} strokeWidth="3" />
      <rect x="263" y="94" width="24" height="18" rx="5" fill={INK} />
      <circle cx="275" cy="103" r="4" fill={GREEN} stroke={PAPER} strokeWidth="1.5" />
      <path d="M316 62 V140" stroke={INK} strokeWidth="3" />
      <polygon points="298,40 334,40 340,64 292,64" fill={AMBER} stroke={INK} strokeWidth="2.5" strokeLinejoin="round" />
      <rect x="304" y="138" width="24" height="5" rx="2" fill={INK} />
      <line x1="0" y1="143" x2="340" y2="143" stroke={INK} strokeWidth="3" />
    </svg>
  )
}

// The bottom of the family wall: sofa, lamp and floor.
export function WallFloor() {
  return (
    <svg className="sn-house__scene" viewBox="0 0 390 70" aria-hidden="true">
      <rect width="390" height="70" fill={PAPER} />
      <g fill={GREEN} stroke={INK} strokeWidth="2.5">
        <rect x="60" y="14" width="210" height="26" rx="10" />
        <rect x="50" y="32" width="230" height="22" rx="8" />
        <rect x="38" y="22" width="26" height="34" rx="8" />
        <rect x="266" y="22" width="26" height="34" rx="8" />
      </g>
      <path d="M340 18 V60" stroke={INK} strokeWidth="3" />
      <polygon points="322,0 358,0 364,20 316,20" fill={AMBER} stroke={INK} strokeWidth="2.5" strokeLinejoin="round" />
      <rect x="328" y="58" width="24" height="5" rx="2" fill={INK} />
      <rect y="62" width="390" height="8" fill={INK} />
    </svg>
  )
}
