// 扁平矢量图标（自绘，24×24 网格）：Glyph 是单色图形，Badge 是彩色圆角底 + 白色图形
import React from "react";

type Shape = (c: string, d: string) => React.ReactNode; // c：主色，d：镂空细节的颜色（一般是底色）
const S = (c: string, w = 2) => ({ fill: "none", stroke: c, strokeWidth: w, strokeLinecap: "round" as const, strokeLinejoin: "round" as const });

const SHAPES: Record<string, Shape> = {
  group: (c, d) => <><path d="M3 5h13v9H8l-4 3.5V14H3z" fill={c} /><path d="M18 9h3v8h-1.5v2.5L16 17h-5v-1" {...S(c, 1.8)} /></>,
  dm: (c, d) => <><path d="M4 5h16v11H10l-5 4v-4H4z" fill={c} /><circle cx="9" cy="10.5" r="1.2" fill={d} opacity={0.9} /><circle cx="15" cy="10.5" r="1.2" fill={d} opacity={0.9} /></>,
  report: (c, d) => <><path d="M6 3h9l4 4v14H6z" fill={c} /><path d="M9 11h7M9 14.5h7M9 18h4" {...S(d, 1.6)} opacity={0.85} /></>,
  table: (c, d) => <><rect x="3" y="4" width="18" height="16" rx="2.5" fill={c} /><path d="M3.5 9.5h17M3.5 14.5h17M9.5 9.5v10" {...S(d, 1.5)} opacity={0.8} /></>,
  link: (c, d) => <><rect x="2.5" y="8" width="9" height="8" rx="4" {...S(c, 2.4)} /><rect x="12.5" y="8" width="9" height="8" rx="4" {...S(c, 2.4)} /><path d="M8.5 12h7" {...S(c, 2.4)} /></>,
  robot: (c, d) => <><path d="M12 2.5v3" {...S(c, 1.8)} /><circle cx="12" cy="2.5" r="1.5" fill={c} /><rect x="4" y="6" width="16" height="13" rx="4" fill={c} /><circle cx="9" cy="12" r="1.8" fill={d} /><circle cx="15" cy="12" r="1.8" fill={d} /><path d="M9.5 16h5" {...S(d, 1.5)} /><path d="M2 11v4M22 11v4" {...S(c, 2)} /></>,
  search: (c, d) => <><circle cx="10.5" cy="10.5" r="6.5" {...S(c, 2.6)} /><path d="M15.5 15.5L21 21" {...S(c, 3)} /></>,
  check: (c, d) => <path d="M4.5 12.5l5 5 10-11" {...S(c, 3)} />,
  cross: (c, d) => <path d="M6 6l12 12M18 6L6 18" {...S(c, 3)} />,
  warn: (c, d) => <><path d="M12 3l10 18H2z" fill={c} /><path d="M12 9.5v5" {...S(d, 2.2)} /><circle cx="12" cy="17.6" r="1.2" fill={d} /></>,
  undo: (c, d) => <><path d="M8 5L3.5 9.5 8 14" {...S(c, 2.6)} /><path d="M4 9.5h10a6 6 0 0 1 0 12H9" {...S(c, 2.6)} /></>,
  ask: (c, d) => <><path d="M4 4h16v12h-7l-5 4v-4H4z" fill={c} /><path d="M9.6 8.4a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.4" {...S(d, 1.8)} /><circle cx="12" cy="14.2" r="1" fill={d} /></>,
  mail: (c, d) => <><rect x="2.5" y="5" width="19" height="14" rx="2.5" fill={c} /><path d="M4 7l8 6 8-6" {...S(d, 1.8)} /></>,
  code: (c, d) => <><rect x="2.5" y="4" width="19" height="16" rx="3" fill={c} /><path d="M9 9l-3 3 3 3M15 9l3 3-3 3" {...S(d, 1.8)} /></>,
  gear: (c, d) => <><path d="M12 2.5l1.6 2.3 2.7-.7.7 2.7 2.6 1-.8 2.7 1.7 2.2-2.1 1.8.4 2.8-2.8.3-1.3 2.5-2.5-1.3-2.5 1.3-1.3-2.5-2.8-.3.4-2.8L3 12.5l1.7-2.2-.8-2.7 2.6-1 .7-2.7 2.7.7z" fill={c} /><circle cx="12" cy="12" r="3.3" fill={d} /></>,
  bubble: (c, d) => <><path d="M12 4c5 0 9 3.1 9 7s-4 7-9 7c-1 0-2-.1-2.9-.4L4.5 20l1.2-4C4 14.7 3 12.9 3 11c0-3.9 4-7 9-7z" fill={c} /><circle cx="8" cy="11" r="1.2" fill={d} /><circle cx="12" cy="11" r="1.2" fill={d} /><circle cx="16" cy="11" r="1.2" fill={d} /></>,
  person: (c, d) => <><circle cx="12" cy="8" r="4" fill={c} /><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7z" fill={c} /></>,
  bolt: (c, d) => <path d="M13.5 2L4.5 13.5h6L9.5 22l9-11.5h-6z" fill={c} />,
  funnel: (c, d) => <path d="M3 4h18l-7 8.5V19l-4 2v-8.5z" fill={c} />,
  resume: (c, d) => <><rect x="4" y="2.5" width="16" height="19" rx="2.5" fill={c} /><circle cx="9" cy="8" r="2" fill={d} opacity={0.9} /><path d="M13 7h4M13 9.5h3M7.5 13.5h9M7.5 17h6" {...S(d, 1.5)} opacity={0.85} /></>,
  wall: (c, d) => <><rect x="3" y="3" width="18" height="18" rx="2" fill={c} /><path d="M3 9h18M3 15h18M10 3v6M15 9v6M8 15v6M16 15v6" {...S(d, 1.4)} opacity={0.6} /></>,
  branch: (c, d) => <path d="M12 2.5l9.5 9.5-9.5 9.5L2.5 12z" fill={c} />,
  edit: (c, d) => <><path d="M15 4l5 5L9 20H4v-5z" fill={c} /><path d="M13 6l5 5" {...S(d, 1.6)} /></>,
  bell: (c, d) => <><path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z" fill={c} /><path d="M10 20.5a2 2 0 0 0 4 0" {...S(c, 2)} /></>,
  cursor: (c, d) => <path d="M5 3l14 7.5-6 1.5-2.5 6.5z" fill={c} stroke={d} strokeWidth={1.4} strokeLinejoin="round" />,
  lock: (c, d) => <><rect x="4.5" y="10" width="15" height="11" rx="2.5" fill={c} /><path d="M8 10V7.5a4 4 0 0 1 8 0V10" {...S(c, 2.2)} /><circle cx="12" cy="15.5" r="1.6" fill={d} /></>,
  clock: (c, d) => <><circle cx="12" cy="12" r="9" fill={c} /><path d="M12 7v5.5l3.5 2" {...S(d, 2)} /></>,
  handshake: (c, d) => <><path d="M2 9l4-2.5 4 1.5 3-1.5 5 2 4-1v6l-3 1-5 4-2-1.5-2.5 1L5 16l-3-1z" fill={c} /><path d="M10 8l-2.5 3 1.5 1.5 3-2 3 3" {...S(d, 1.4)} /></>,
};
export type IconName = keyof typeof SHAPES;

export const Glyph: React.FC<{ name: IconName; size?: number; color?: string; detail?: string; style?: React.CSSProperties }> = ({ name, size = 32, color = "#1F2329", detail = "#fff", style }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{ flexShrink: 0, display: "inline-block", verticalAlign: "middle", ...style }}>{SHAPES[name](color, detail)}</svg>
);

export const Badge: React.FC<{ name: IconName; size?: number; bg: string; round?: boolean; style?: React.CSSProperties }> = ({ name, size = 96, bg, round, style }) => (
  <div style={{ width: size, height: size, borderRadius: round ? "50%" : size * 0.28, background: bg, display: "flex", alignItems: "center",
    justifyContent: "center", flexShrink: 0, ...style }}>
    <Glyph name={name} size={size * 0.58} color="#fff" detail={bg} />
  </div>
);
