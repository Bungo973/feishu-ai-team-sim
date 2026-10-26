// 正片第 0–4 段：开场、自我介绍、引子、这家公司、三个痛点
import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import D1 from "../data/D1.json";
import { Avatar, emoji, TITLES } from "../feishu";
import { Badge, Glyph, IconName } from "./icons";
import { Appear, C, Card, clamp, GREEN, ORANGE, PURPLE, Scene, Sfx, Statement, Status, Tag, useIn } from "./kit";

export type SceneProps = { dur: number; talk?: number; text?: string }; // talk：这一幕口播的帧数（有配音时是真实时长）；text：这一幕的口播

// 鼠标指针：pts = [到达的帧, x, y]。每段先停在原地，到达前 move 帧才快速移过去（先加速后减速、走一点弧线）
// click 里的帧：指针按下缩一下，同时在指尖放一圈波纹
const ease = Easing.bezier(0.65, 0, 0.25, 1);
const posAt = (pts: [number, number, number][], move: number, f: number): [number, number] => {
  if (f <= pts[0][0]) return [pts[0][1], pts[0][2]];
  for (let k = 1; k < pts.length; k++) {
    const [f1, x1, y1] = pts[k];
    if (f > f1) continue;
    const [f0, x0, y0] = pts[k - 1];
    const start = Math.max(f0, f1 - move);
    const t = f1 === start ? 1 : ease(Math.min(1, Math.max(0, (f - start) / (f1 - start))));
    const bend = Math.sin(Math.PI * t) * 0.12; // 垂直方向偏一点，不走死直线
    return [x0 + (x1 - x0) * t - (y1 - y0) * bend, y0 + (y1 - y0) * t + (x1 - x0) * bend];
  }
  const last = pts[pts.length - 1];
  return [last[1], last[2]];
};

export const Cursor: React.FC<{ pts: [number, number, number][]; click?: number[]; move?: number }> = ({ pts, click = [], move = 12 }) => {
  const frame = useCurrentFrame();
  const [x, y] = posAt(pts, move, frame);
  const since = Math.min(...click.map((f) => (frame >= f ? frame - f : Infinity)));
  const press = since < 8 ? interpolate(since, [0, 3, 8], [1, 0.82, 1]) : 1;
  return (
    <>
      {click.map((f) => <Sfx key={`s${f}`} at={f} name="click" />)}
      {click.filter((f) => frame >= f && frame < f + 16).map((f) => {
        const [cx, cy] = posAt(pts, move, f);
        const r = interpolate(frame - f, [0, 16], [6, 42]);
        return <div key={f} style={{ position: "absolute", left: cx + 4 - r, top: cy + 4 - r, width: r * 2, height: r * 2, borderRadius: "50%", zIndex: 9,
          border: `4px solid ${C.blue}`, background: "rgba(51,112,255,0.18)", opacity: interpolate(frame - f, [0, 16], [1, 0]) }} />;
      })}
      <div style={{ position: "absolute", left: x, top: y, zIndex: 10, transform: `scale(${press})`, transformOrigin: "4px 4px",
        filter: "drop-shadow(0 2px 3px rgba(0,0,0,0.3))" }}>
        <Glyph name="cursor" size={44} color="#1F2329" />
      </div>
    </>
  );
};

// ---------- 0 开场 ----------
export const TitleCard: React.FC<SceneProps> = () => <Statement text="您好！这是一份求职视频" />;

// ---------- 1 自我介绍 ----------
export const ResumeCard: React.FC<SceneProps> = () => {
  const ROWS: [string, string, string][] = [["学历", "2025 届本科", C.text], ["工作经验", "7 个月", C.text], ["一直在学", "AI 应用", C.blue]];
  return (
    <Scene>
      <Appear at={4} dy={30}>
        <Card style={{ width: 900, padding: "50px 70px" }}>
          <div style={{ fontSize: 28, color: C.sub, marginBottom: 30 }}>关于我</div>
          {ROWS.map(([k, v, color], i) => (
            <div key={k} style={{ display: "flex", alignItems: "baseline", padding: "22px 0", borderTop: i ? `1px solid ${C.line}` : "none" }}>
              <div style={{ width: 240, fontSize: 34, color: C.sub }}>{k}</div>
              <div style={{ fontSize: 56, fontWeight: 700, color }}>{v}</div>
            </div>
          ))}
        </Card>
      </Appear>
    </Scene>
  );
};

// ---------- 2 引子：先多（四处消息刷屏）→ 再乱（同一件事四种说法）→ AI 挑出来要核对 → 再由人来判断 ----------
// 卡片里是虚构的示意内容（不是模拟里的真实对话）；时间点是这段口播里的字数位置
type Row = { text?: string; label?: string; chip?: string; me?: boolean; flag?: boolean };
const SOURCES: { k: string; icon: "group" | "dm" | "report" | "table"; color: string; x: number; y: number; count: string; rows: Row[] }[] = [
  { k: "群聊", icon: "group", color: C.blue, x: 330, y: 370, count: "未读 99+", rows: [
    { text: "早，今天同步一下" }, {}, { text: "物料清单更新了" }, { text: "下午三点开会" }, {}, { text: "收到" }, { text: "文案我晚点发" }, {},
    { text: "海报初稿发群里了", flag: true }, { text: "收到，下午看看" }, { text: "彩排改到周四" }] },
  { k: "私聊", icon: "dm", color: GREEN, x: 1590, y: 370, count: "6 个对话", rows: [
    { text: "文案看了吗？", me: true }, { text: "看了，有两处要改" }, { text: "预算表在哪？", me: true }, { text: "我找找" }, {}, {},
    { text: "海报到哪了？", me: true }, { text: "还差最后一版", flag: true }, {}] },
  { k: "简报", icon: "report", color: ORANGE, x: 330, y: 780, count: "8 份", rows: [
    { label: "今日", text: "整理需求" }, { label: "明日", text: "出草图" }, { label: "风险" }, { label: "今日", text: "改文案" }, { label: "明日" }, { label: "风险" },
    { label: "今日", text: "海报完成初稿", flag: true }, { label: "明日", text: "等反馈" }, { label: "风险" }] },
  { k: "表格", icon: "table", color: PURPLE, x: 1590, y: 780, count: "30 行", rows: [
    { chip: "已完成" }, { chip: "进行中" }, { chip: "待审核" }, { chip: "进行中" }, { chip: "已完成" }, { chip: "进行中" },
    { text: "海报", chip: "进行中", flag: true }, { chip: "已完成" }, { chip: "待审核" }] },
];
// AI 挑出来的同一件事：四处的说法放在一起，一眼看出对不上
const SAME: { k: string; icon: "group" | "dm" | "report" | "table"; color: string; say: string; note?: string }[] = [
  { k: "群聊", icon: "group", color: C.blue, say: "“海报初稿发群里了”" },
  { k: "私聊", icon: "dm", color: GREEN, say: "“还差最后一版”", note: "我私聊问的" },
  { k: "简报", icon: "report", color: ORANGE, say: "初稿完成，明天等反馈" },
  { k: "表格", icon: "table", color: PURPLE, say: "状态还是「进行中」" },
];
const ROW_H = 56;
// 前面的消息再刷两轮，显得多（最后停在带"海报"的那几行）
for (const src of SOURCES) { const lead = src.rows.slice(0, src.rows.length - 3); src.rows = [...lead, ...lead, ...src.rows]; }
const Bar: React.FC<{ w: number }> = ({ w }) => <div style={{ width: w, height: 16, borderRadius: 8, background: "#E3E6EB" }} />;
const SourceRow: React.FC<{ r: Row; color: string }> = ({ r, color }) => {
  if (r.chip) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
      {r.text ? <span style={{ fontSize: 26, color: C.text }}>{r.text}</span> : <Bar w={170} />}
      <span style={{ fontSize: 22, padding: "4px 14px", borderRadius: 8, background: `${color}1F`, color }}>{r.chip}</span>
    </div>
  );
  if (r.label) return (
    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
      <span style={{ fontSize: 22, color: C.sub, width: 50 }}>{r.label}</span>
      {r.text ? <span style={{ fontSize: 26, color: C.text }}>{r.text}</span> : <Bar w={150} />}
    </div>
  );
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, flexDirection: r.me ? "row-reverse" : "row", width: "100%" }}>
      <div style={{ width: 34, height: 34, borderRadius: "50%", background: r.me ? color : "#D5D9E0", flexShrink: 0 }} />
      {r.text
        ? <span style={{ fontSize: 26, padding: "6px 16px", borderRadius: 12, background: r.me ? `${color}1F` : "#F2F3F5", color: C.text }}>{r.text}</span>
        : <Bar w={190} />}
    </div>
  );
};
export const Question: React.FC<SceneProps> = ({ dur }) => {
  const frame = useCurrentFrame();
  const F = (x: number) => Math.round(dur * x);
  // 口播先说"我想用 AI 解决一个很常见的问题"，标题等说到问题时再出
  const head = useIn(F(0.2));
  const up = interpolate(frame, [dur * 0.24, dur * 0.3], [0, 1], clamp);
  const sub = useIn(F(0.5));
  // 又多又杂：消息往上刷，未读数往上跳
  const scroll = interpolate(frame, [dur * 0.4, dur * 0.64], [0, 1], { ...clamp, easing: Easing.inOut(Easing.quad) });
  const join = interpolate(frame, [dur * 0.62, dur * 0.7], [0, 1], clamp);
  const flag = interpolate(frame, [dur * 0.7, dur * 0.74], [0, 1], clamp);
  const panel = useIn(F(0.76));
  const panelOut = interpolate(frame, [dur * 0.74, dur * 0.78], [0, 1], clamp); // 聚好以后，四张卡退到后面
  const odd = useIn(F(0.86));
  const human = useIn(F(0.9));
  const CX = 960, CY = 520;
  return (
    <Scene>
      <div style={{ position: "absolute", top: 470, fontSize: 60, fontWeight: 700, color: C.text, opacity: useIn(4) * interpolate(frame, [dur * 0.15, dur * 0.19], [1, 0], clamp) }}>
        用 AI 解决一个<span style={{ color: C.blue }}>很常见的问题</span>
      </div>
      <div style={{ position: "absolute", top: interpolate(up, [0, 1], [400, 60]), display: "flex", flexDirection: "column", alignItems: "center", opacity: head }}>
        <div style={{ fontSize: interpolate(up, [0, 1], [76, 46]), fontWeight: 700, color: C.text }}>进度信息散在四个地方</div>
        <div style={{ fontSize: interpolate(up, [0, 1], [56, 36]), fontWeight: 700, color: ORANGE, marginTop: interpolate(up, [0, 1], [24, 10]),
          opacity: sub, transform: `translateY(${(1 - sub) * 16}px)` }}>又多又杂</div>
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0, opacity: 1 - panelOut }}>
        {SOURCES.filter(({ k }) => k !== "私聊").map(({ k, color, x, y }) => {
          const x0 = x + (x < CX ? 230 : -230);
          return <line key={k} x1={x0} y1={y} x2={x0 + (CX - x0) * join} y2={y + (CY - y) * join} stroke={color} strokeWidth={4} strokeDasharray="12 10" opacity={0.6 * join} />;
        })}
        {/* 私聊：灰线伸到一半就断了（助手不在两个人的私聊里，读不到） */}
        {SOURCES.filter(({ k }) => k === "私聊").map(({ k, x, y }) => {
          const x0 = x - 230;
          return <line key={k} x1={x0} y1={y} x2={x0 + (CX - x0) * 0.42 * join} y2={y + (CY - y) * 0.42 * join} stroke="#B8BEC8" strokeWidth={4} strokeDasharray="12 10" opacity={join} />;
        })}
      </svg>
      {SOURCES.map(({ k, icon, color, x, y, count, rows }, i) => {
        const t = useIn(F(0.33 + i * 0.04));
        const n = rows.length;
        return (
          <div key={k} style={{ position: "absolute", left: x - 230, top: y - 135, width: 460, opacity: t * (1 - 0.6 * panelOut), transform: `scale(${(0.9 + 0.1 * t) * (1 - 0.06 * join)})` }}>
            <Card style={{ width: 460, padding: "22px 28px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 14 }}>
                <Badge name={icon} bg={color} size={48} />
                <span style={{ fontSize: 30, fontWeight: 700, color: C.text }}>{k}</span>
                <span style={{ marginLeft: "auto", fontSize: 22, fontWeight: 600, color: "#fff", background: k === "群聊" ? C.red : C.sub, borderRadius: 999, padding: "3px 14px",
                  opacity: scroll > 0.05 ? 1 : 0 }}>{scroll < 0.98 && k === "群聊" ? `未读 ${Math.max(3, Math.round(99 * scroll))}` : count}</span>
              </div>
              <div style={{ height: ROW_H * 3, overflow: "hidden" }}>
                <div style={{ transform: `translateY(${-(n - 3) * ROW_H * scroll}px)` }}>
                  {rows.map((r, j) => {
                    const on = r.flag ? flag : 0;
                    return (
                      <div key={j} style={{ height: ROW_H, display: "flex", alignItems: "center", padding: "0 10px", borderRadius: 10,
                        opacity: 1 - 0.55 * flag * (r.flag ? 0 : 1),
                        boxShadow: `inset 0 0 0 ${3 * on}px ${ORANGE}`, background: on ? `rgba(227,115,24,${0.08 * on})` : "transparent" }}>
                        <SourceRow r={r} color={color} />
                      </div>
                    );
                  })}
                </div>
              </div>
            </Card>
          </div>
        );
      })}
      <div style={{ position: "absolute", left: CX - 75, top: CY - 75, opacity: join * (1 - panelOut), transform: `scale(${0.6 + 0.4 * join})` }}>
        <Badge name="robot" bg={PURPLE} size={150} round />
      </div>
      {/* 助手读不到私聊：连线断开处画一把锁，下面说明原因 */}
      {SOURCES.filter(({ k }) => k === "私聊").map(({ k, x, y }) => {
        const x0 = x - 230, lx = x0 + (CX - x0) * 0.47, ly = y + (CY - y) * 0.47;
        return (
          <div key={k} style={{ position: "absolute", left: lx - 26, top: ly - 26, width: 52, height: 52, borderRadius: "50%", background: "#fff", boxShadow: "0 4px 14px rgba(31,35,41,0.15)",
            display: "flex", alignItems: "center", justifyContent: "center", opacity: join * (1 - panelOut), transform: `scale(${0.6 + 0.4 * join})` }}>
            <Glyph name="lock" size={30} color="#8F959E" />
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 1330, top: 515, width: 520, textAlign: "center", fontSize: 24, color: C.name, lineHeight: 1.5, opacity: join * (1 - panelOut) }}>
        私聊只在两个人之间，助手不在里面，读不到<br />这部分由我补充
      </div>
      {/* AI 挑出同一件事：四种说法排在一起 */}
      <div style={{ position: "absolute", left: CX - 400, top: 210, width: 800, opacity: panel, transform: `scale(${0.85 + 0.15 * panel})` }}>
        <Card style={{ width: 800, padding: "26px 32px", boxShadow: "0 24px 70px rgba(31,35,41,0.18)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <Badge name="robot" bg={PURPLE} size={52} round />
            <span style={{ fontSize: 32, fontWeight: 700, color: C.text }}>AI 聚到一起：<span style={{ color: PURPLE }}>海报</span>做到哪了？</span>
          </div>
          {SAME.map(({ k, icon, color, say, note }, j) => {
            const m = useIn(F(0.78 + j * 0.02));
            return (
              <div key={k} style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 16, padding: "12px 16px", borderRadius: 12, background: "#F7F8FA",
                opacity: m, transform: `translateX(${(1 - m) * -30}px)` }}>
                <Badge name={icon} bg={color} size={40} />
                <span style={{ fontSize: 24, color: C.sub, width: 56 }}>{k}</span>
                <span style={{ fontSize: 30, fontWeight: 600, color: C.text }}>{say}</span>
                {note && <span style={{ marginLeft: "auto", fontSize: 21, color: C.name }}>{note}</span>}
              </div>
            );
          })}
          <div style={{ marginTop: 18, display: "flex", alignItems: "center", gap: 12, fontSize: 30, fontWeight: 700, color: ORANGE, opacity: odd, transform: `translateY(${(1 - odd) * 12}px)` }}>
            <Glyph name="warn" size={34} color={ORANGE} />四种说法对不上 → 要核对
          </div>
        </Card>
      </div>
      <div style={{ position: "absolute", top: 820, display: "flex", alignItems: "center", gap: 18, opacity: human, transform: `translateY(${(1 - human) * 20}px)` }}>
        <Badge name="person" bg={C.blue} size={64} round />
        <span style={{ fontSize: 44, fontWeight: 700, color: C.blue }}>再由人来判断？</span>
      </div>
    </Scene>
  );
};

// ---------- 4 这家公司 ----------
// 跟着口播走：右边是要验证的提效工具，左边我和 AI 搭出模拟团队，工具放进去验证
// → 一个结果能核对的模拟团队 → 小家电公司的市场部 → 8 个同事由 AI 扮演 → 每人都是一个飞书机器人
const TOOLS3: [IconName, string][] = [["report", "日报表单"], ["robot", "AI 进度助手"], ["bell", "自动提醒流程"]];
// 左卡（模拟公司）的位置，和它放大后变成的大面板；8 个头像从左卡飞到各自的同事卡上
const BOX0 = { x: 245, y: 250, w: 640, h: 420 }, BOX1 = { x: 250, y: 70, w: 1420, h: 690 };
const AV0 = (i: number) => ({ x: 280 + i * 72, y: 416, s: 60 });
const AV1 = (i: number) => ({ x: 335 + (i % 4) * 330, y: 358 + Math.floor(i / 4) * 142, s: 72 });
export const Team: React.FC<SceneProps> = ({ dur }) => {
  const frame = useCurrentFrame();
  const F = (x: number) => Math.round(dur * x);
  const tools = useIn(2);
  const builder = useIn(F(0.11));
  const sim = useIn(F(0.25));
  const ok = useIn(F(0.3));
  const arrow = interpolate(frame, [dur * 0.3, dur * 0.36], [0, 1], clamp);
  const fade = interpolate(frame, [dur * 0.37, dur * 0.41], [0, 1], clamp); // 右卡、箭头、左卡里的字褪去
  const grow = interpolate(frame, [dur * 0.38, dur * 0.46], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) }); // 左卡放大成面板
  const head = useIn(F(0.43));
  const dept = useIn(F(0.46));
  const staff = F(0.52);
  const bot = F(0.8);
  const box = Object.fromEntries((["x", "y", "w", "h"] as const).map((k) => [k, BOX0[k] + (BOX1[k] - BOX0[k]) * grow])) as typeof BOX0;
  return (
    <Scene>
      {/* 左：模拟公司（先是虚线空框 + "我 + AI"，说到"搭了"时填上；之后放大成团队面板） */}
      <div style={{ position: "absolute", left: box.x, top: box.y, width: box.w, height: box.h, borderRadius: 24, border: `3px dashed ${sim > 0.5 ? "transparent" : "#B8C0CC"}`, opacity: builder }}>
        {/* 等"搭了"之前：灰色骨架条一条条长出来，像在搭建中 */}
        <div style={{ position: "absolute", inset: 0, padding: "38px 36px", opacity: 1 - sim }}>
          {[[0.3, 26], [0.55, 44], [0.9, 22], [0.75, 22], [0.6, 22]].map(([w, h], i) => {
            const g = interpolate(frame, [F(0.11) + 6 + i * 9, F(0.11) + 20 + i * 9], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
            const pulse = 0.75 + 0.25 * Math.sin((frame - i * 6) / 7);
            return <div key={i} style={{ width: `${w * 100 * g}%`, height: h, borderRadius: 8, background: "#DDE2EA", opacity: pulse, marginTop: i === 0 ? 0 : i === 2 ? 52 : 18 }} />;
          })}
        </div>
        <Card style={{ position: "absolute", inset: 0, padding: "30px 34px", opacity: sim, borderTop: `8px solid ${C.blue}` }}>
          <div style={{ opacity: 1 - fade }}>
            <div style={{ fontSize: 24, color: C.sub }}>用于验证</div>
            <div style={{ fontSize: 42, fontWeight: 800, color: C.text, marginTop: 6 }}>模拟公司</div>
            <div style={{ height: 60, marginTop: 30 }} />
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 34, fontSize: 30, fontWeight: 700, color: GREEN, opacity: ok, transform: `translateY(${(1 - ok) * 12}px)` }}>
              <Glyph name="check" size={36} color={GREEN} />结果能核对
            </div>
            <div style={{ fontSize: 26, color: C.name, marginTop: 16, opacity: ok }}>3 个项目 · 15 个工作日 · 每一步都有记录</div>
          </div>
        </Card>
        <div style={{ position: "absolute", left: 0, right: 0, bottom: -70, display: "flex", justifyContent: "center", opacity: 1 - fade }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 26, color: C.name, background: "#fff", borderRadius: 999, padding: "8px 22px", boxShadow: "0 4px 16px rgba(31,35,41,0.08)" }}>
            <Glyph name="code" size={30} color={C.blue} />我 + AI 搭建
          </div>
        </div>
      </div>
      {/* 中间：工具放进模拟公司里跑 */}
      <div style={{ position: "absolute", left: 925, top: 412, width: 150, display: "flex", flexDirection: "column", alignItems: "center", opacity: arrow * (1 - fade) }}>
        <div style={{ fontSize: 24, color: C.blue, fontWeight: 600, whiteSpace: "nowrap" }}>放进去验证</div>
        <svg width={150} height={40} style={{ marginTop: 8 }}>
          <path d={`M${146 - 130 * arrow} 20 H146 M${146 - 130 * arrow} 20 l16 -12 M${146 - 130 * arrow} 20 l16 12`} stroke={C.blue} strokeWidth={5} fill="none" strokeLinecap="round" />
        </svg>
      </div>
      {/* 右：要验证的提效工具 */}
      <Card style={{ position: "absolute", left: 1115, top: 250, width: 560, height: 420, padding: "30px 34px", opacity: tools * (1 - fade), borderTop: `8px solid ${PURPLE}`,
        transform: `translate(${fade * 40}px, ${(1 - tools) * 20}px)` }}>
        <div style={{ fontSize: 24, color: C.sub }}>提效方式</div>
        <div style={{ fontSize: 42, fontWeight: 800, color: C.text, marginTop: 6 }}>提效工具</div>
        {TOOLS3.map(([icon, name]) => (
          <div key={name} style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 24 }}>
            <Badge name={icon} bg={PURPLE} size={56} />
            <span style={{ fontSize: 32, fontWeight: 600, color: C.text }}>{name}</span>
          </div>
        ))}
      </Card>
      <div style={{ position: "absolute", top: 110, display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ fontSize: 40, fontWeight: 700, color: C.text, opacity: head, transform: `translateY(${(1 - head) * 20}px)` }}>
          一个结果能核对的模拟团队
        </div>
        <div style={{ fontSize: 34, color: C.blue, fontWeight: 600, marginTop: 14, opacity: dept }}>小家电公司 · 市场部</div>
      </div>
      <div style={{ position: "absolute", top: 340, display: "grid", gridTemplateColumns: "repeat(4, 300px)", gap: "34px 30px" }}>
        {Object.entries(TITLES).map(([name, title], i) => {
          const t = useIn(staff + i * 4);
          const b = useIn(bot + i * 3);
          return (
            <div key={name} style={{ opacity: t, display: "flex", alignItems: "center", gap: 16, height: 108, boxSizing: "border-box",
              background: "#F5F6F8", borderRadius: 18, padding: "18px 20px" }}>
              <div style={{ width: 72, height: 72, flexShrink: 0 }} />
              <div style={{ transform: `translateX(${(1 - t) * -16}px)` }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 30, fontWeight: 700, color: C.text }}>{name}</span>
                  <span style={{ fontSize: 17, color: "#C17D00", background: "#FFF1CC", borderRadius: 4, padding: "2px 6px", opacity: b, transform: `scale(${0.6 + 0.4 * b})` }}>机器人</span>
                </div>
                <div style={{ fontSize: 21, color: C.sub, marginTop: 4, whiteSpace: "nowrap" }}>{title.replace("知暖电器", "").replace("（模拟同事）", "")}</div>
              </div>
            </div>
          );
        })}
      </div>
      {/* 头像：先在左卡里排成一排，放大时各自飞到同事卡上 */}
      {Object.keys(TITLES).map((name, i) => {
        const m = interpolate(frame, [dur * 0.4 + i * 2, dur * 0.5 + i * 2], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
        const [p0, p1] = [AV0(i), AV1(i)];
        const sz = p0.s + (p1.s - p0.s) * m;
        return (
          <div key={name} style={{ position: "absolute", left: p0.x + (p1.x - p0.x) * m, top: p0.y + (p1.y - p0.y) * m, opacity: sim * useIn(F(0.25) + 4 + i * 3) }}>
            <Avatar name={name} size={sz} />
          </div>
        );
      })}
      <Appear at={bot + 20} style={{ position: "absolute", top: 680, fontSize: 30, color: C.name }}>同事和合作方共 8 人，全部由 AI 扮演 · 每人都是一个飞书机器人</Appear>
    </Scene>
  );
};

// ---------- 3 这家公司 ----------
export const ProjectCards: React.FC<SceneProps> = ({ dur }) => {
  const frame = useCurrentFrame();
  const P: [string, string, string, string][] = [
    ["发布会", "小暖 S2 新品发布会", "第 13 天开场", C.blue],
    ["内容", "公众号和小红书", "一个月的内容更新", PURPLE],
    ["流程", "入职流程优化", "第 15 天前向人事汇报", GREEN],
  ];
  const progress = interpolate(frame, [30, dur - 10], [0, 1], clamp);
  const me = useIn(34); // 进度条一出来，"我"就跟着从第 1 天往前走
  return (
    <Scene>
      <div style={{ display: "flex", gap: 40 }}>
        {P.map(([k, name, note, color], i) => (
          <Appear key={k} at={4 + i * 16} dy={40} sfx="pop">
            <Card style={{ width: 470, borderTop: `8px solid ${color}` }}>
              <div style={{ fontSize: 26, color, fontWeight: 600 }}>项目 {i + 1} · {k}</div>
              <div style={{ fontSize: 40, fontWeight: 700, color: C.text, marginTop: 14 }}>{name}</div>
              <div style={{ fontSize: 26, color: C.name, marginTop: 14 }}>{note}</div>
            </Card>
          </Appear>
        ))}
      </div>
      <Sfx at={34} name="pop" />
      <Appear at={30} style={{ width: 1490, marginTop: 70, position: "relative" }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 22, color: C.sub, marginBottom: 12 }}>
          <span>第 1 天</span><span>第 5 天</span><span>第 10 天</span><span>第 15 天</span>
        </div>
        <div style={{ height: 18, borderRadius: 9, background: "#DDE1E8", overflow: "hidden" }}>
          <div style={{ width: `${progress * 100}%`, height: "100%", background: C.blue }} />
        </div>
        <div style={{ position: "absolute", left: Math.max(0, progress * 1490 - 90), top: 70, opacity: me, transform: `translateY(${(1 - me) * -30}px)`,
          display: "flex", alignItems: "center", gap: 10, background: C.blue, color: "#fff", borderRadius: 999, padding: "8px 22px", fontSize: 28, fontWeight: 600, whiteSpace: "nowrap" }}>
          <Glyph name="person" size={26} color="#fff" />我 · 项目助理
        </div>
      </Appear>
    </Scene>
  );
};

// 人设卡：说话风格 + 一句原话（D1 群聊、D1 私聊）
const PERSONAS: [string, string, string, React.ReactNode][] = [
  ["王丽", "组长", "像语音转文字", "不清楚的问老张小李 他们手上东西多 每周五给我一份周报 我周末看"],
  ["张伟", "资深市场专员", "回话极短", "推进中。"],
  ["李想", "内容运营", "热情、表情多", <>这个表比较全 你先照着看 欢迎一起干活！<Glyph name="handshake" size={34} color={ORANGE} style={{ marginLeft: 4 }} /></>],
];
export const Personas: React.FC<SceneProps> = () => {
  return (
    <Scene>
      <div style={{ display: "flex", gap: 40 }}>
        {PERSONAS.map(([name, title, style, quote], i) => (
          <Appear key={name} at={4 + i * 8} dy={40} sfx="pop">
            <Card style={{ width: 500, height: 420, display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
                <Avatar name={name} size={84} />
                <div>
                  <div style={{ fontSize: 36, fontWeight: 700, color: C.text }}>{name}</div>
                  <div style={{ fontSize: 24, color: C.sub, marginTop: 4 }}>{title}</div>
                </div>
              </div>
              <div style={{ alignSelf: "flex-start", marginTop: 26, fontSize: 28, fontWeight: 600, color: PURPLE, background: "#F1EAFE", borderRadius: 999, padding: "6px 20px" }}>{style}</div>
              <div style={{ marginTop: 24, background: C.bubble, borderRadius: 12, padding: "16px 20px", fontSize: 28, color: C.text, lineHeight: 1.6 }}>{quote}</div>
            </Card>
          </Appear>
        ))}
      </div>
      <Tag text="原话 · 第 1 天的群聊和私聊" style={{ top: 60, right: 60 }} />
    </Scene>
  );
};

export const TwoColumns: React.FC<SceneProps> = ({ dur, talk = dur }) => {
  const frame = useCurrentFrame();
  const T = (x: number) => Math.round(talk * x); // 跟着口播走的时间点
  const Col: React.FC<{ at: number; icon: "bubble" | "gear"; title: string; color: string; items: string[] }> = ({ at, icon, title, color, items }) => (
    <Appear at={at} dy={30} sfx="pop">
      <Card style={{ width: 620, minHeight: 300 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <Badge name={icon} bg={color} size={72} />
          <div style={{ fontSize: 44, fontWeight: 700, color }}>{title}</div>
        </div>
        {items.map((s) => <div key={s} style={{ fontSize: 30, color: C.text, marginTop: 22 }}>· {s}</div>)}
      </Card>
    </Appear>
  );
  const TRAITS: [string, boolean][] = [["会说错", false], ["会拖", false], ["不会凭空变出进度", true]];
  const t0 = T(0.55);
  // 说到"不会凭空变出进度"：上面整体缩小上移，下面演示一次虚报进度被对照拆穿（示意）
  const demo = T(0.86);
  const up = interpolate(frame, [demo, demo + 16], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const claim = useIn(demo + 10), table = useIn(demo + 34);
  const xAt = demo + 62;
  const x = interpolate(frame, [xAt, xAt + 8], [0, 1], { ...clamp, easing: Easing.out(Easing.back(2)) });
  const verdict = useIn(xAt + 14);
  const ROWS: [string, string, string][] = [["A12 新闻通稿", "进行中", "40%"], ["A14 直播方案", "未开始", "0%"]];
  return (
    <Scene>
      <Sfx at={demo + 10} name="notify" />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", transform: `translateY(${-250 * up}px) scale(${1 - 0.3 * up})` }}>
        <div style={{ display: "flex", gap: 50 }}>
          <Col at={4} icon="bubble" title="AI 演" color={PURPLE} items={["说什么、怎么说", "群聊、私聊、日报"]} />
          <Col at={T(0.22)} icon="gear" title="程序算" color={C.blue} items={["工时、进度", "活干到哪一步"]} />
        </div>
        <div style={{ display: "flex", gap: 28, marginTop: 56 }}>
          {TRAITS.map(([s, key], i) => (
            <Appear key={s} at={t0 + i * 14} sfx="tick" style={{ fontSize: 34, padding: "14px 32px", borderRadius: 999, fontWeight: key ? 700 : 400,
              background: key ? C.blue : "#fff", color: key ? "#fff" : C.text }}>{s}</Appear>
          ))}
        </div>
      </div>
      {frame >= demo && (
        <div style={{ position: "absolute", top: 500, display: "flex", alignItems: "center", gap: 60 }}>
          {/* 左：同事在群里说"都干完了"（AI 演的） */}
          <div style={{ position: "relative", opacity: claim, transform: `translateY(${(1 - claim) * 20}px)` }}>
            <div style={{ fontSize: 24, color: PURPLE, fontWeight: 600, marginBottom: 12 }}>同事说的（AI 演）</div>
            <div style={{ display: "flex", gap: 16, alignItems: "flex-start", background: "#fff", borderRadius: 18, padding: "24px 28px", boxShadow: "0 10px 40px rgba(31,35,41,0.1)" }}>
              <Avatar name="李想" size={60} />
              <div>
                <div style={{ fontSize: 22, color: C.sub }}>李想</div>
                <div style={{ fontSize: 34, color: C.text, background: "#F2F3F5", borderRadius: 10, padding: "10px 18px", marginTop: 6 }}>我后面的活都干完了！</div>
              </div>
            </div>
            {/* 大红叉 */}
            <svg width={220} height={220} viewBox="0 0 24 24" style={{ position: "absolute", left: "50%", top: "55%", marginLeft: -110, marginTop: -110,
              opacity: Math.min(1, x * 1.5), transform: `scale(${0.4 + 0.6 * x}) rotate(${(1 - x) * -20}deg)` }}>
              <path d="M5 5l14 14M19 5L5 19" stroke={C.red} strokeWidth={3.2} strokeLinecap="round" fill="none" />
            </svg>
          </div>
          <div style={{ fontSize: 40, color: C.sub, opacity: table }}>对照</div>
          {/* 右：程序按工时算出来的真实进度 */}
          <div style={{ opacity: table, transform: `translateY(${(1 - table) * 20}px)` }}>
            <div style={{ fontSize: 24, color: C.blue, fontWeight: 600, marginBottom: 12 }}>程序记录（按工时算）</div>
            <div style={{ background: "#fff", borderRadius: 18, padding: "14px 28px", boxShadow: "0 10px 40px rgba(31,35,41,0.1)" }}>
              {ROWS.map(([n, st, pct], i) => (
                <div key={n} style={{ display: "flex", alignItems: "center", gap: 24, padding: "12px 0", borderTop: i ? `1px solid ${C.line}` : "none", fontSize: 28, color: C.text }}>
                  <span style={{ width: 230 }}>{n}</span>
                  <span style={{ width: 120 }}>{st === "未开始" ? <span style={{ color: C.sub, fontSize: 24 }}>未开始</span> : <Status s={st} size={24} />}</span>
                  <span style={{ width: 70, textAlign: "right", fontWeight: 700 }}>{pct}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      {frame >= demo && (
        <div style={{ position: "absolute", top: 790, fontSize: 36, fontWeight: 700, color: C.red, opacity: verdict, transform: `translateY(${(1 - verdict) * 16}px)` }}>
          说了不算，进度按程序记录
        </div>
      )}
      <Tag text="示意" style={{ bottom: 150, right: 60, opacity: interpolate(frame, [demo, demo + 10], [0, 1], clamp) }} />
    </Scene>
  );
};

// 口播：真实工作更复杂 → 但在这里每一步都有记录 → 工具有没有用，可以逐条验证（引出下一段"先看第一周"）
export const Disclaimer: React.FC<SceneProps> = ({ dur }) => {
  const LOGS = ["群聊和私聊", "我的每个动作", "任务表的每次改动", "AI 助手的每次核对", "程序算出的真实进度"];
  return (
    <Scene>
      <Appear at={4} style={{ fontSize: 34, color: C.name }}>真实的工作只会更复杂</Appear>
      <Appear at={Math.round(dur * 0.3)} style={{ fontSize: 66, fontWeight: 700, color: C.text, marginTop: 20 }}>但在这里，每一步都有记录</Appear>
      <div style={{ display: "flex", gap: 22, marginTop: 60 }}>
        {LOGS.map((s, i) => (
          <Appear key={s} at={Math.round(dur * 0.38) + i * 8} dy={30} sfx="tick">
            <Card style={{ padding: "24px 28px", fontSize: 28, color: C.text, display: "flex", alignItems: "center", gap: 12 }}>
              <Glyph name="check" size={30} color={GREEN} />{s}
            </Card>
          </Appear>
        ))}
      </div>
      <Appear at={Math.round(dur * 0.62)} dy={20} style={{ marginTop: 60, fontSize: 46, fontWeight: 700, color: C.blue }}>
        → 工具到底有没有用，可以逐条验证
      </Appear>
    </Scene>
  );
};

// ---------- 4 三个痛点 ----------
const PAINS = ["逐条收集", "手动改表", "前置变更"];
// 三个痛点：独立一层，竖着挂在画面右侧空白处（不压在飞书界面上）
// 痛点卡：整个痛点段常驻在左下角（Main 里统一画，不跟着画面切换）
// step：当前讲第几个痛点（-1 = 还没开始）；fix：这一幕在讲解决办法；t：这一幕开始后的帧数（当前项弹一下）
export const PainSteps: React.FC<{ step: number; fix: boolean; t: number; opacity?: number }> = ({ step, fix, t, opacity = 1 }) => {
  const pop = 1 + 0.08 * interpolate(t, [0, 6, 14], [0, 1, 0], clamp);
  return (
    <div style={{ position: "absolute", left: 70, bottom: 64, display: "flex", flexDirection: "column", gap: 12, padding: 16, borderRadius: 18, opacity,
      background: "rgba(255,255,255,0.94)", boxShadow: "0 12px 40px rgba(31,35,41,0.16)", zIndex: 20 }}>
      {PAINS.map((s, i) => {
        const done = i < step, cur = i === step;
        return (
          <div key={s} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 26, fontWeight: 600, borderRadius: 999, padding: "8px 22px",
            transform: `scale(${cur ? pop : 1})`, background: cur ? (fix ? C.blue : C.red) : done ? "#E8F7EF" : "#F2F3F5", color: cur ? "#fff" : done ? GREEN : C.sub }}>
            <span>{"①②③"[i]}</span>{s}{done && <span style={{ marginLeft: "auto" }}>✓</span>}
          </div>
        );
      })}
    </div>
  );
};

const Panel: React.FC<{ title: string; children: React.ReactNode; style?: React.CSSProperties }> = ({ title, children, style }) => (
  <div style={{ position: "absolute", background: "#fff", borderRadius: 18, boxShadow: "0 10px 40px rgba(31,35,41,0.12)", overflow: "hidden", ...style }}>
    <div style={{ height: 64, display: "flex", alignItems: "center", padding: "0 26px", fontSize: 24, fontWeight: 600, color: C.text, borderBottom: `1px solid ${C.line}` }}>{title}</div>
    {children}
  </div>
);

// 痛点 ①：在群里搜"KV"翻记录（D1 群聊原话），再挨个点开私聊（真实问答）
const HITS = D1.messages.filter((m) => m.text.includes("KV") && m.sender !== "我").slice(0, 6);
const DMS: [string, string, string, string][] = [
  ["张伟", "老张 入职优化在进行中了吗？", "推进中。", "第 1 天"],
  ["王丽", "王姐邀约名单OK吗？", "还没过呢 我这才刚从一个会出来 名单晚点我自己看一遍", "第 2 天"],
  ["陈悦", "kv那边在进行了吗？", "版式框架上周就搭好了……还没正式开做。", "第 3 天"],
  ["李想", "邀请函的文案大概什么时候出啊？", "中午前后吧……下午一点前能给陈悦一版🙏", "第 3 天"],
];
const mark = (s: string) => s.split("KV").flatMap((p, i) => (i ? [<b key={i} style={{ background: "#FFE58F" }}>KV</b>, p] : [p]));

// 整段在同一个飞书界面里走：点顶栏的搜索 → 界面褪去，聚焦到搜索结果 → 界面回来 → 点开张伟的私聊 → 再聚焦到私聊
// 时间点是这段口播里的字数位置："想知道一件事做到哪了"开始搜，"再挨个私聊"时点私聊
const SEARCH_ICON: [number, number] = [1737, 36]; // 顶栏搜索图标（飞书界面 1440 宽，放大 4/3 后的位置）
const ZW_ROW: [number, number] = [307, 156]; // 会话列表里"张伟"那一行
export const Collect: React.FC<SceneProps & { bg?: React.ReactNode }> = ({ dur, talk = dur, bg }) => {
  const frame = useCurrentFrame();
  const F = (x: number) => Math.round(talk * x); // 跟着口播走，说完后画面停住
  const clickSearch = F(0.1), f1 = F(0.2), u1 = F(0.52), clickDm = F(0.6), f2 = F(0.63);
  const focus = Math.max(interpolate(frame, [f1, f1 + 10, u1, u1 + 10], [0, 1, 1, 0], clamp), interpolate(frame, [f2, f2 + 10], [0, 1], clamp));
  const one = interpolate(frame, [f1, f1 + 10, u1, u1 + 10], [0, 1, 1, 0], clamp);
  const two = interpolate(frame, [f2, f2 + 10], [0, 1], clamp);
  // 界面里的搜索侧栏：点了搜索图标滑出来，打"KV"；聚焦回来以后收起
  const side = interpolate(frame, [clickSearch, clickSearch + 8, u1 + 10, u1 + 18], [0, 1, 1, 0], clamp);
  const typedSide = "KV".slice(0, Math.max(0, Math.floor((frame - clickSearch - 10) / 8)));
  // 第一拍：出结果 → 鼠标一条条点
  const hitStart = f1 + 16;
  const hitStep = (u1 - hitStart - 10) / HITS.length;
  const hit = Math.floor((frame - hitStart) / hitStep);
  // 第二拍：鼠标依次点开 4 个私聊
  const dmStep = (dur - f2 - 20) / DMS.length;
  const dm = Math.min(DMS.length - 1, Math.max(0, Math.floor((frame - f2 - 10) / dmStep)));
  const LIST_X = 170;
  return (
    <Scene>
      {DMS.map((_, i) => <Sfx key={i} at={f2 + 10 + i * dmStep + dmStep * 0.15} name="notify" volume={0.7} />)}
      {/* 背景：飞书界面，聚焦时褪去 */}
      <AbsoluteFill style={{ opacity: 1 - 0.88 * focus, transform: `scale(${1 + 0.03 * focus})` }}>
        {bg}
        <div style={{ position: "absolute", top: 82, right: 6, bottom: 6, width: 440, background: "#fff", borderLeft: `1px solid ${C.line}`, opacity: side,
          transform: `translateX(${(1 - side) * 60}px)`, padding: "22px 24px", boxShadow: "-8px 0 24px rgba(31,35,41,0.06)" }}>
          <div style={{ fontSize: 22, fontWeight: 600, color: C.text }}>搜索会话内容</div>
          <div style={{ display: "flex", gap: 24, fontSize: 18, color: C.sub, marginTop: 18 }}>
            <span style={{ color: C.blue, fontWeight: 600, borderBottom: `3px solid ${C.blue}`, paddingBottom: 6 }}>消息</span><span>云文档</span><span>文件</span><span>链接</span>
          </div>
          <div style={{ marginTop: 18, height: 44, borderRadius: 8, border: `2px solid ${C.blue}`, display: "flex", alignItems: "center", gap: 10, padding: "0 12px", fontSize: 22, color: C.text }}>
            <Glyph name="search" size={22} color={C.sub} />{typedSide}<span style={{ opacity: frame % 30 < 15 ? 1 : 0, color: C.blue }}>|</span>
          </div>
        </div>
      </AbsoluteFill>
      <div style={{ position: "absolute", inset: 0, opacity: one, transform: `scale(${0.94 + 0.06 * one})` }}>
        <Panel title="品牌项目组 · 搜索聊天记录" style={{ left: 150, top: 150, width: 1440, height: 680 }}>
          <div style={{ margin: "22px 26px", height: 56, borderRadius: 10, border: `2px solid ${C.blue}`, display: "flex", alignItems: "center", gap: 12, padding: "0 18px", fontSize: 28, color: C.text }}>
            <Glyph name="search" size={28} color={C.sub} />KV<span style={{ opacity: frame % 30 < 15 ? 1 : 0, color: C.blue }}>|</span>
          </div>
          {HITS.map((m, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 16, padding: "14px 26px", opacity: interpolate(frame, [f1 + 6 + i * 4, f1 + 12 + i * 4], [0, 1], clamp),
              background: i === hit ? "#EAF1FF" : "transparent" }}>
              <Avatar name={m.sender} size={48} />
              <div style={{ width: 160, fontSize: 22, color: C.sub }}>{m.sender} · {m.time}</div>
              <div style={{ fontSize: 26, color: C.text }}>{mark(emoji(m.text))}</div>
            </div>
          ))}
        </Panel>
        <div style={{ position: "absolute", top: 170, right: 360, fontSize: 24, color: C.red, fontWeight: 600 }}>翻了 {Math.max(0, Math.min(HITS.length, hit + 1))} 条</div>
      </div>
      <div style={{ position: "absolute", inset: 0, opacity: two, transform: `scale(${0.94 + 0.06 * two})` }}>
        <Panel title="消息" style={{ left: LIST_X - 20, top: 150, width: 420, height: 680 }}>
          {DMS.map(([who], i) => (
            <div key={who} style={{ display: "flex", alignItems: "center", gap: 16, height: 96, padding: "0 24px", background: i === dm ? "#EAF1FF" : "transparent" }}>
              <Avatar name={who} size={56} /><span style={{ fontSize: 28, color: C.text }}>{who}</span>
            </div>
          ))}
        </Panel>
        <Panel title={`私聊 · ${DMS[dm][0]}`} style={{ left: 580, top: 150, width: 1010, height: 680 }}>
          <div style={{ padding: "30px 34px", display: "flex", flexDirection: "column", gap: 26 }}>
            <div style={{ fontSize: 20, color: C.sub, textAlign: "center" }}>{DMS[dm][3]}</div>
            <div style={{ display: "flex", gap: 14 }}>
              <Avatar name="我" size={52} />
              <div style={{ background: C.mine, borderRadius: 10, padding: "12px 18px", fontSize: 30, color: C.text }}>{DMS[dm][1]}</div>
            </div>
            <div style={{ display: "flex", gap: 14, opacity: interpolate(frame - f2 - 10 - dm * dmStep, [dmStep * 0.15, dmStep * 0.15 + 8], [0, 1], clamp) }}>
              <Avatar name={DMS[dm][0]} size={52} />
              <div style={{ background: C.bubble, borderRadius: 10, padding: "12px 18px", fontSize: 30, color: C.text, maxWidth: 820, lineHeight: 1.6 }}>{DMS[dm][2]}</div>
            </div>
          </div>
        </Panel>
        <div style={{ position: "absolute", top: 170, right: 360, fontSize: 24, color: C.red, fontWeight: 600 }}>问了 {dm + 1} 个人</div>
      </div>
      {/* 鼠标一直是同一个：界面里点搜索 → 结果里一条条点 → 界面里点张伟 → 私聊列表里一个个点 */}
      <Cursor
        pts={[[4, 1100, 600], [clickSearch, ...SEARCH_ICON], [f1 + 4, 1500, 700],
          ...HITS.map((_, i): [number, number, number] => [hitStart + i * hitStep, 840, 310 + i * 80 + 30]),
          [u1 + 14, 1000, 500], [clickDm, ...ZW_ROW],
          ...DMS.map((_, i): [number, number, number] => [f2 + 10 + i * dmStep, 320, 214 + i * 96 + 30])]}
        click={[clickSearch, ...HITS.map((_, i) => Math.round(hitStart + i * hitStep + 3)), clickDm, ...DMS.slice(1).map((_, i) => Math.round(f2 + 10 + (i + 1) * dmStep + 3))]} />
      <Tag text="消息是原话 · 操作是示意" style={{ bottom: 150, right: 60 }} />
    </Scene>
  );
};



export const PainSummary: React.FC<SceneProps> = () => (
  <Scene>
    <div style={{ display: "flex", gap: 36 }}>
      {([["group", "逐条收集", "翻记录、挨个私聊"], ["table", "手动改表", "一格一格点开改"], ["link", "前置变更", "后面最后才知道"]] as const).map(([icon, s, d], i) => (
        <Appear key={s} at={4 + i * 10} dy={30} sfx="pop">
          <Card style={{ width: 420, textAlign: "center", padding: "40px 30px" }}>
            <Badge name={icon} bg={C.red} size={84} style={{ margin: "0 auto" }} />
            <div style={{ fontSize: 40, fontWeight: 700, color: C.text, marginTop: 20 }}>{"①②③"[i]} {s}</div>
            <div style={{ fontSize: 26, color: C.name, marginTop: 10 }}>{d}</div>
          </Card>
        </Appear>
      ))}
    </div>
    <Appear at={40} style={{ fontSize: 46, fontWeight: 700, color: C.text, marginTop: 70 }}>
      时间花在<span style={{ color: C.red }}>搬运信息</span>上，真正用来判断的很少
    </Appear>
  </Scene>
);

export const Manual: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill>
    {children}
  </AbsoluteFill>
);
