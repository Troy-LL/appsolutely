import type { ReactNode } from "react"
// Simple ink stroke icons. Always next to a text label or an aria-label.
type P = { size?: number }
const svg = (size: number, children: ReactNode, width = 2.4) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={width}
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
)
export const Globe = ({ size = 18 }: P) => svg(size, <><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18" /></>, 2.2)
export const Back = ({ size = 22 }: P) => svg(size, <path d="M15 5l-7 7 7 7" />, 2.6)
export const Close = ({ size = 18 }: P) => svg(size, <path d="M6 6l12 12M18 6L6 18" />, 3)
export const Mic = ({ size = 26 }: P) => svg(size, <><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></>)
export const Play = ({ size = 22 }: P) => svg(size, <path d="M8 5l11 7-11 7z" />)
export const Redo = ({ size = 22 }: P) => svg(size, <><path d="M4 12a8 8 0 1 0 2.3-5.6" /><path d="M4 4v4.5h4.5" /></>)
export const Home = ({ size = 24 }: P) => svg(size, <><path d="M3 11l9-7 9 7" /><path d="M5 10v10h14V10" /><path d="M10 20v-5h4v5" /></>, 2.2)
export const Frames = ({ size = 24 }: P) => svg(size, <><rect x="3" y="5" width="8" height="10" rx="1" /><rect x="13" y="5" width="8" height="10" rx="1" /><path d="M2 20h20" /></>, 2.2)
export const List = ({ size = 24 }: P) => svg(size, <><path d="M9 6h11M9 12h11M9 18h11" /><circle cx="4.5" cy="6" r="1.2" /><circle cx="4.5" cy="12" r="1.2" /><circle cx="4.5" cy="18" r="1.2" /></>, 2.2)
export const Caret = ({ open }: { open: boolean }) => (
  <svg className="sn-chip__caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3}
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={open ? 'M6 15l6-6 6 6' : 'M6 9l6 6 6-6'} /></svg>
)
export const Camera = ({ size = 30 }: P) => svg(size, <><rect x="3" y="6" width="18" height="14" rx="2" /><path d="M8 6l1.5-2h5L16 6" /><circle cx="12" cy="13" r="3.5" /></>, 2.2)
// Sino AI: a speech bubble with three dots. Activity log: a clock.
export const Chat = ({ size = 24 }: P) => svg(size, <><path d="M4 5h16v11H9l-5 4z" /><path d="M9 10.5h.01M12 10.5h.01M15 10.5h.01" strokeWidth={3} /></>, 2.2)
export const Clock = ({ size = 24 }: P) => svg(size, <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>, 2.2)
