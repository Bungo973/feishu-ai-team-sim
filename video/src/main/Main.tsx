// 正片：口播稿（src/data/narration.json）里每个自然段对应一个画面，按顺序接起来，底部配字幕
// 有配音时每个画面放自己那一段配音（全片.mp3 按停顿切开），没有时按每秒 4.2 字加停顿估算
// 改了口播稿或配音后跑 python3 scripts/narration.py
import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { ChatReplay, DayData } from "../ChatReplay";
import D1 from "../data/D1.json";
import NARRATION from "../data/narration.json";
import { BG, clamp, FONT, RoleTag, Tag } from "./kit";
import { Collect, Disclaimer, Manual, PainSteps, Personas, Team, ProjectCards, Question, ResumeCard, SceneProps, TitleCard, TwoColumns } from "./scenes-intro";
import { AskChat, Capability, EditByHand, EditChat, Proof, ToolReport, ToolSet } from "./scenes-tools";
import { DepChain, DepFlow } from "./scenes-dep";
import { CheckGrid, Credits, Division, EndCard, JobAssistant } from "./scenes-end";

export const FPS = 30;
const CPS = 4.2; // 没配音时的语速（字/秒）
const PAD = 0.6; // 每个画面说完后多停的秒数（换画面前喘口气）

// 第一周全靠手动：飞书群消息还在往下刷（第 1 天真实记录）；5-2 接着用同一个界面去搜、去私聊
const Chat: React.FC<{ from?: number }> = ({ from = 0 }) => (
  <Sequence from={-from}>
    <ChatReplay data={D1 as DayData} group="品牌项目组" count={14} every={32} statsAt={1e9} />
  </Sequence>
);
type Clip = { start: number; end: number };
type Section = { id: number; title: string; paragraphs: string[]; pauses: number[]; clips: Clip[] | null };
const DATA = NARRATION as { audio: string | null; sections: Section[] };
type Shot = { el: React.FC<SceneProps>; min?: number; clip?: boolean }; // min：画面至少几秒；clip：飞书界面全屏（不盖角标）

// 顺序和口播稿的自然段一一对应（共 24 个）
const SHOTS: Shot[][] = [
  [{ el: TitleCard, min: 3 }],
  [{ el: ResumeCard }],
  [{ el: Question, min: 12 }],
  [{ el: ToolSet }, { el: Proof, min: 10 }],
  [
    { el: Team },
    { el: ProjectCards },
    { el: Personas, min: 6 },
    { el: TwoColumns, min: 14 },
    { el: Disclaimer, min: 6 },
  ],
  [
    { el: () => <><Manual><Chat from={230} /></Manual><Tag text="按真实聊天记录重建（第 1 天）" style={{ bottom: 150, right: 60 }} /></>, min: 5, clip: true },
    { el: (p) => <Collect {...p} bg={<Chat from={520} />} />, min: 14, clip: true },
    { el: (p) => <><ToolReport {...p} /><RoleTag text="表单和提醒：我在飞书里配置" /></>, min: 16, clip: true },
    { el: (p) => <><Capability {...p} /><RoleTag text="代码：AI 写 · 我提需求和验收" at={Math.round((p.talk ?? p.dur) * 0.3)} /></>, min: 21, clip: true },
    { el: AskChat, min: 13, clip: true },
    { el: EditByHand, min: 12, clip: true },
    { el: EditChat, min: 24, clip: true },
    { el: DepChain, clip: true },
    { el: (p) => <><DepFlow {...p} /><RoleTag text="工作流：我在飞书里配置，没写代码" style={{ top: "auto", right: "auto", bottom: 150, left: 520 }} /></>, clip: true },
  ],
  [{ el: CheckGrid, min: 29 }, { el: Division }],
  [{ el: JobAssistant, min: 12 }],
  [{ el: EndCard }],
  [{ el: Credits, min: 10 }],
];

const len = (s: string) => s.replace(/\s/g, "").length;

// 每个画面：起点、时长、对应的口播、自己那一段配音
type Item = { from: number; dur: number; text: string; el: React.FC<SceneProps>; section: number; talk: number; clip?: boolean; voice?: Clip };
const build = () => {
  const items: Item[] = [];
  let at = 0;
  DATA.sections.forEach((sec, si) => {
    const shots = SHOTS[si];
    if (!shots || shots.length !== sec.paragraphs.length) throw new Error(`第 ${sec.id} 段：口播 ${sec.paragraphs.length} 个自然段，画面 ${shots?.length ?? 0} 个`);
    sec.paragraphs.forEach((text, k) => {
      const voice = sec.clips?.[k];
      const talk = voice ? voice.end - voice.start : len(text) / CPS + sec.pauses[k];
      // 每个画面只放自己那段配音，所以画面可以比配音长（后面留白），不会和声音错开
      const dur = Math.round(Math.max(talk + PAD, shots[k].min ?? 0) * FPS);
      items.push({ from: at, dur, text, el: shots[k].el, section: sec.id, talk: Math.round(talk * FPS), clip: shots[k].clip, voice });
      at += dur;
    });
  });
  return { items, total: at };
};
export const TIMELINE = build();

// 字幕：按标点切成短句，按字数分配时间
const chunks = (text: string) => {
  const out: string[] = [];
  for (const part of text.match(/[^。！？；：]+(?:[。！？；：][”"」]?)?/g) ?? [text]) {
    if (len(part) <= 24) { out.push(part); continue; }
    let cur = "";
    for (const piece of part.match(/[^，、]+[，、]?/g) ?? [part]) {
      if (cur && len(cur + piece) > 24) { out.push(cur); cur = ""; }
      cur += piece;
    }
    if (cur) out.push(cur);
  }
  return out.map((s) => s.replace(/[，。；：、]$/, "").replace(/^[”"」]/, "").trim()).filter(Boolean);
};

const Subtitle: React.FC<{ text: string; talk: number }> = ({ text, talk }) => {
  const frame = useCurrentFrame();
  const parts = chunks(text);
  const total = parts.reduce((s, p) => s + len(p), 0);
  let acc = 0;
  const idx = parts.findIndex((p) => { acc += len(p); return frame < (talk * acc) / total; });
  const line = parts[idx === -1 ? parts.length - 1 : idx];
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 54, pointerEvents: "none" }}>
      <div style={{ fontFamily: FONT, fontSize: 44, fontWeight: 600, color: "#fff", background: "rgba(20,22,26,0.72)", borderRadius: 12,
        padding: "10px 28px", maxWidth: 1600, textAlign: "center" }}>{line}</div>
    </AbsoluteFill>
  );
};

const Corner: React.FC = () => (
  <div style={{ position: "absolute", top: 28, left: 34, fontFamily: FONT, fontSize: 22, color: "rgba(31,35,41,0.55)",
    background: "rgba(255,255,255,0.6)", borderRadius: 999, padding: "6px 18px" }}>仿真项目 · 公司和同事均为虚构，由 AI 扮演</div>
);

// 底部章节进度条：每段一格，宽度按时长（太短的段保底 96px，放得下四个字）；当前段逐渐填满，名字点亮。从自我介绍到联系方式
const CHAPTERS: Record<number, string> = { 1: "自我介绍", 2: "问题由来", 3: "做了什么", 4: "怎么验证", 5: "怎么解决", 6: "效果如何", 7: "视频缘由", 8: "怎么联系" };
const Progress: React.FC = () => {
  const frame = useCurrentFrame();
  const segs = Object.keys(CHAPTERS).map(Number).map((id) => {
    const its = TIMELINE.items.filter((i) => i.section === id);
    return { id, from: its[0].from, to: its[its.length - 1].from + its[its.length - 1].dur };
  });
  const span = segs[segs.length - 1].to - segs[0].from;
  return (
    <div style={{ position: "absolute", left: 34, right: 34, bottom: 10, display: "flex", gap: 6, fontFamily: FONT }}>
      {segs.map((s) => {
        const p = interpolate(frame, [s.from, s.to], [0, 1], clamp);
        const cur = p > 0 && p < 1;
        return (
          <div key={s.id} style={{ flex: (s.to - s.from) / span, minWidth: 96 }}>
            <div style={{ fontSize: 18, color: cur ? "#3370FF" : "rgba(31,35,41,0.4)", fontWeight: cur ? 700 : 400, marginBottom: 4, whiteSpace: "nowrap" }}>{CHAPTERS[s.id]}</div>
            <div style={{ height: 6, borderRadius: 3, background: "rgba(31,35,41,0.12)", overflow: "hidden" }}>
              <div style={{ width: `${p * 100}%`, height: "100%", background: "#3370FF" }} />
            </div>
          </div>
        );
      })}
    </div>
  );
};

// 痛点段每一幕：讲到第几个痛点、是不是在讲解决办法（顺序同 SHOTS 第 5 段）
const PAIN: [number, boolean][] = [[-1, false], [0, false], [0, true], [0, true], [0, true], [1, false], [1, true], [2, false], [2, true]];
const PainOverlay: React.FC = () => {
  const frame = useCurrentFrame();
  const its = TIMELINE.items.filter((i) => i.section === 5);
  const k = its.findIndex((i) => frame >= i.from && frame < i.from + i.dur);
  if (k === -1) return null;
  const end = its[its.length - 1].from + its[its.length - 1].dur;
  const opacity = interpolate(frame, [its[0].from + 10, its[0].from + 25, end - 10, end], [0, 1, 1, 0], clamp);
  return <PainSteps step={PAIN[k][0]} fix={PAIN[k][1]} t={frame - its[k].from} opacity={opacity} />;
};

// 飞书界面的画面整体缩小一点、靠上放，底下留出进度条的位置
const CLIP: React.CSSProperties = { transform: "scale(0.94)", transformOrigin: "50% 20%", borderRadius: 14, overflow: "hidden", boxShadow: "0 12px 40px rgba(31,35,41,0.14)" };

// 背景音乐（scripts/bgm_warm.py 合成「温暖和弦」，旧的钢琴加木琴版用 bgm_long.py）：压在口播下面，说话时更低，停顿和没有口播的地方稍微回升，开头渐入、结尾渐出
const BGM = "music/bgm.mp3";
const BGM_TALK = 0.13, BGM_REST = 0.28;
const bgmVolume = (f: number) => {
  const { items, total } = TIMELINE;
  // 离最近一段口播有多远（帧）：说话时为 0，口播前后 12 帧内渐变
  const near = Math.min(...items.filter((i) => i.voice).map((i) => (f < i.from ? i.from - f : f > i.from + i.talk ? f - i.from - i.talk : 0)));
  const duck = interpolate(near, [0, 12], [BGM_TALK, BGM_REST], clamp);
  return duck * interpolate(f, [0, 45, total - 90, total], [0, 1, 1, 0], clamp);
};

export const Main: React.FC = () => {
  const frame = useCurrentFrame();
  const { items } = TIMELINE;
  const credits = items[items.length - 1];
  // 角标：从第 3 段（讲做了什么）到致谢之前
  const cornerFrom = items.find((i) => i.section === 3)!.from;
  const now = items.find((i) => frame >= i.from && frame < i.from + i.dur);
  const barFrom = items.find((i) => i.section === 1)!.from;
  const barTo = items.find((i) => i.section === 9)!.from;
  const barOpacity = interpolate(frame, [barFrom, barFrom + 15, barTo - 10, barTo], [0, 1, 1, 0], clamp);
  const cornerOpacity = now?.clip ? 0 : interpolate(frame, [cornerFrom, cornerFrom + 15, credits.from - 10, credits.from], [0, 1, 1, 0], clamp);
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      {items.map((it, i) => (
        <Sequence key={i} from={it.from} durationInFrames={it.dur}>
          {it.clip ? <AbsoluteFill style={CLIP}><it.el dur={it.dur} talk={it.talk} text={it.text} /></AbsoluteFill> : <it.el dur={it.dur} talk={it.talk} text={it.text} />}
          {it !== credits && <Subtitle text={it.text} talk={it.talk} />}
          {DATA.audio && it.voice && <Audio src={staticFile(DATA.audio)} startFrom={Math.round(it.voice.start * FPS)} endAt={Math.round(it.voice.end * FPS)} />}
        </Sequence>
      ))}
      {DATA.audio && <Audio src={staticFile(BGM)} volume={bgmVolume} />}
      <PainOverlay />
      <div style={{ opacity: cornerOpacity }}><Corner /></div>
      <div style={{ opacity: barOpacity }}><Progress /></div>
    </AbsoluteFill>
  );
};
