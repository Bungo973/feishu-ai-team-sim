// 正片共用的零件：入场动画、背景、标题、卡片、角标
import React from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../feishu";

export { C, FONT };
export const BG = "linear-gradient(135deg, #EEF0F6, #E6EAF3)";
export const PURPLE = "#6425D0";
export const GREEN = "#2EA121";
export const ORANGE = "#E37318";

export const useIn = (at: number, damping = 16) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - at, fps, config: { damping } });
};

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// 音效（public/sfx/，由 scripts/sfx.py 生成）：在第 at 帧响一下。音量整体压低，别盖过口播
export type SfxName = "click" | "key" | "pop" | "whoosh" | "tick" | "chime" | "notify" | "ding";
const VOL: Record<SfxName, number> = { click: 0.35, key: 0.25, pop: 0.3, whoosh: 0.25, tick: 0.18, chime: 0.3, notify: 0.3, ding: 0.4 };
// 目前只保留消息提示音；其他音效的位置都还在，想加回来就往 ON 里加名字
const ON = new Set<SfxName>(["notify", "ding"]);
export const Sfx: React.FC<{ at: number; name: SfxName; volume?: number }> = ({ at, name, volume = 1 }) =>
  ON.has(name) ? (
    <Sequence from={Math.round(at)} durationInFrames={30} layout="none">
      <Audio src={staticFile(`sfx/${name}.wav`)} volume={VOL[name] * volume} />
    </Sequence>
  ) : null;

export const Appear: React.FC<{ at: number; children: React.ReactNode; style?: React.CSSProperties; dy?: number; dx?: number; sfx?: SfxName }> = ({ at, children, style, dy = 20, dx = 0, sfx }) => {
  const t = useIn(at);
  return (
    <div style={{ opacity: t, transform: `translate(${interpolate(t, [0, 1], [dx, 0])}px, ${interpolate(t, [0, 1], [dy, 0])}px)`, ...style }}>
      {sfx && <Sfx at={at} name={sfx} />}
      {children}
    </div>
  );
};

// 每个画面：背景一直在（不跟着淡入，免得切镜时露出黑底闪一下），只有内容在开头 10 帧淡入
export const Scene: React.FC<{ children: React.ReactNode; bg?: string; style?: React.CSSProperties }> = ({ children, bg = BG, style }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ fontFamily: FONT, background: bg }}>
      <AbsoluteFill style={{ opacity: interpolate(frame, [0, 10], [0, 1], clamp), alignItems: "center", justifyContent: "center", ...style }}>
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// 角上的分工标注：这一步是谁做的
export const RoleTag: React.FC<{ text: string; at?: number; style?: React.CSSProperties }> = ({ text, at = 20, style }) => {
  const t = useIn(at);
  return (
    <div style={{ position: "absolute", top: 40, right: 60, display: "flex", alignItems: "center", gap: 10, fontFamily: FONT, fontSize: 26, fontWeight: 600, color: "#fff",
      background: C.blue, borderRadius: 999, padding: "8px 22px 8px 14px", opacity: t, transform: `translateY(${(1 - t) * -16}px)`, ...style }}>
      <svg width={26} height={26} viewBox="0 0 24 24"><circle cx="12" cy="8" r="4" fill="#fff" /><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7z" fill="#fff" /></svg>
      {text}
    </div>
  );
};

export const Card: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div style={{ background: "#fff", borderRadius: 24, padding: "32px 40px", boxShadow: "0 10px 40px rgba(31,35,41,0.08)", ...style }}>{children}</div>
);

// 画面角落的说明小字（"真实截图""按记录重建"）
export const Tag: React.FC<{ text: string; style?: React.CSSProperties }> = ({ text, style }) => (
  <div style={{ position: "absolute", fontSize: 22, color: C.name, background: "rgba(255,255,255,0.85)", borderRadius: 999, padding: "8px 22px", ...style }}>{text}</div>
);

// 一行大字（整屏只有一句话的画面）
export const Statement: React.FC<{ text: React.ReactNode; sub?: React.ReactNode; kicker?: string }> = ({ text, sub, kicker }) => (
  <Scene>
    {kicker && <Appear at={2} style={{ fontSize: 30, color: C.blue, fontWeight: 600, marginBottom: 18 }}>{kicker}</Appear>}
    <Appear at={6} style={{ fontSize: 80, fontWeight: 700, color: C.text, textAlign: "center", lineHeight: 1.3 }}>{text}</Appear>
    {sub && <Appear at={20} style={{ fontSize: 34, color: C.name, marginTop: 30, textAlign: "center", lineHeight: 1.6 }}>{sub}</Appear>}
  </Scene>
);

// 状态标签，颜色和飞书任务表接近
export const STATUS: Record<string, [string, string]> = {
  已完成: ["#FDE2E2", "#D83931"],
  进行中: ["#D5F6F2", "#078372"],
  待审核: ["#FFF1CC", "#A35C00"],
  阻塞: ["#E8E8E8", "#4E5969"],
  "受影响-待确认": ["#ECE2FE", PURPLE],
};
export const Status: React.FC<{ s: string; size?: number }> = ({ s, size = 22 }) => {
  if (!s) return <span style={{ color: C.sub, fontSize: size }}>（空）</span>;
  const [bg, fg] = STATUS[s] ?? ["#EEE", C.text];
  return <span style={{ background: bg, color: fg, borderRadius: 6, padding: "3px 12px", fontSize: size, fontWeight: 500, whiteSpace: "nowrap" }}>{s}</span>;
};

// 口播说到某句话的帧数：按这句话在本段口播里的字数位置，乘上本段口播时长（语速基本均匀，误差半秒以内）
export const cue = (text: string | undefined, phrase: string, talk: number) => {
  const n = (s: string) => s.replace(/[\s“”"「」]/g, "");
  const all = n(text ?? ""), i = all.indexOf(n(phrase));
  if (i < 0) throw new Error(`口播里找不到「${phrase}」`);
  return Math.round((talk * i) / all.length);
};
