// 正片第 6–9 段：效果、为什么做这个视频、联系方式、致谢
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Badge, Glyph, IconName } from "./icons";
import { Appear, C, Card, clamp, cue, FONT, GREEN, ORANGE, PURPLE, Scene, Sfx, useIn } from "./kit";
import type { SceneProps } from "./scenes-intro";

// 前后对比：三行对应三个痛点，一次翻完
export const Contrast: React.FC<SceneProps> = () => {
  const ROWS: [IconName, string, string][] = [["group", "翻记录、挨个私聊", "问一句"], ["table", "一格一格改", "核实完说一句"], ["link", "返工了最后才知道", "返工马上提醒"]];
  return (
    <Scene>
      {[0, 1, 2].map((i) => <Sfx key={i} at={10 + i * 12} name="whoosh" />)}
      <div style={{ display: "flex", gap: 120, fontSize: 32, fontWeight: 600, marginBottom: 20, width: 1300 }}>
        <span style={{ width: 560, color: C.sub, paddingLeft: 140 }}>以前</span><span style={{ color: C.blue }}>现在</span>
      </div>
      {ROWS.map(([icon, a, b], i) => {
        const t = useIn(10 + i * 12);
        return (
          <div key={a} style={{ display: "flex", alignItems: "center", gap: 40, marginTop: 24, width: 1300 }}>
            <Badge name={icon} bg={C.sub} size={80} />
            <div style={{ width: 520, fontSize: 44, color: C.sub, textDecoration: t > 0.5 ? "line-through" : "none", opacity: 1 - 0.4 * t }}>{a}</div>
            <div style={{ fontSize: 50, color: C.blue, opacity: t }}>→</div>
            <div style={{ fontSize: 56, fontWeight: 800, color: C.text, opacity: t, transform: `translateX(${(1 - t) * 30}px)` }}>{b}</div>
          </div>
        );
      })}
    </Scene>
  );
};

// 10 次核对 × 每次 8 条，按时间排；判定见 video/AI核对-逐条评分.md
const CHECKS: [string, number][] = [
  ["11-13 下班后", 1], ["11-16 中午", 17], ["11-16 下班", 9], ["11-17 中午", 33], ["11-17 下班", 25],
  ["11-18 中午", 49], ["11-18 下班", 41], ["11-19 中午", 65], ["11-19 下班", 57], ["11-20 中午", 73],
];
const PART = new Set([1, 4, 13, 18, 22, 27, 33, 37, 53, 65, 73, 80]);
const WRONG = new Set([3]);
const COLOR = { ok: GREEN, part: "#F5B400", wrong: C.red };

// 跟着口播一步步讲（时间点都按口播里的位置算）：
// ① 核对了 10 次、80 条提醒 → 一行行摆出灰格子；② 助手看不到存档 → 另一个 AI 拿存档逐条对（扫一遍格子）；
// ③ 有出入的我逐条复核 → 13 个格子圈出来；④ 67 / 12 / 1 依次上色计数；⑤ 漏报、结论
export const CheckGrid: React.FC<SceneProps> = ({ dur, talk = dur, text }) => {
  const frame = useCurrentFrame();
  const Q = (p: string) => cue(text, p, talk);
  const cells = CHECKS.flatMap(([, first]) => Array.from({ length: 8 }, (_, k) => first + k));
  const kindOf = (n: number) => (WRONG.has(n) ? "wrong" : PART.has(n) ? "part" : "ok");
  const [gray0, gray1] = [Q("助手一共核对了"), Q("它看不到")];
  const rowAt = (r: number) => gray0 + ((gray1 - gray0 - 10) * r) / 10;
  const blind = Q("它看不到"), judge = Q("我就让另一个"), scan0 = Q("逐条去对"), scan1 = Q("有出入的再由我");
  const review = scan1;
  const at = { ok: Q("67 条正确"), part: Q("12 条细节"), wrong: Q("1 条误报") };
  const total = { ok: 67, part: 12, wrong: 1 };
  const shown = (k: keyof typeof at) => Math.round(total[k] * interpolate(frame, [at[k], at[k] + 15], [0, 1], clamp));
  const f = useIn(at.wrong);
  const miss = useIn(Q("另外也有漏报"));
  const sum = useIn(Q("总的效果"));
  // 右边三块轮流出现：A 数量 → B 谁来对 → C 计数
  const pA = interpolate(frame, [gray0, gray0 + 10, blind - 8, blind], [0, 1, 1, 0], clamp);
  const pB = interpolate(frame, [blind, blind + 10, at.ok - 8, at.ok], [0, 1, 1, 0], clamp);
  const pC = interpolate(frame, [at.ok, at.ok + 10], [0, 1], clamp);
  const scanRow = interpolate(frame, [scan0, scan1], [-1, 10], clamp); // 扫到第几行
  const ring = useIn(review);
  const reviewOff = interpolate(frame, [at.ok - 6, at.ok + 6], [1, 0], clamp);
  const Panel: React.FC<{ p: number; children: React.ReactNode }> = ({ p, children }) => (
    <div style={{ position: "absolute", inset: 0, opacity: p, transform: `translateY(${(1 - p) * 16}px)`, display: "flex", flexDirection: "column", justifyContent: "center" }}>{children}</div>
  );
  const Node: React.FC<{ icon: IconName; label: string; color: string }> = ({ icon, label, color }) => (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, width: 150 }}>
      <Badge name={icon} bg={color} size={88} />
      <span style={{ fontSize: 25, color: C.text, whiteSpace: "nowrap" }}>{label}</span>
    </div>
  );
  return (
    <Scene>
      {CHECKS.map((_, r) => <Sfx key={r} at={rowAt(r)} name="tick" />)}
      <Sfx at={at.ok} name="chime" />
      <Sfx at={at.part} name="pop" />
      <Sfx at={at.wrong} name="pop" volume={1.5} />
      <div style={{ fontSize: 44, fontWeight: 700, color: C.text, marginBottom: 18, marginTop: -30, opacity: useIn(0) }}>准确率怎么样？</div>
      <div style={{ display: "flex", gap: 60, alignItems: "center" }}>
        <Card style={{ padding: "26px 36px" }}>
          <div style={{ fontSize: 24, color: C.sub, marginBottom: 12 }}>本次仿真演练 · 助手的 10 次核对 · 每次最多列 8 条</div>
          {CHECKS.map(([label], r) => {
            const scan = Math.max(0, 1 - Math.abs(scanRow - r)); // 扫描光带
            return (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6, borderRadius: 8, background: `rgba(51,112,255,${0.14 * scan})`,
                opacity: interpolate(frame, [rowAt(r), rowAt(r) + 8], [0, 1], clamp) }}>
                <div style={{ width: 170, fontSize: 22, color: C.name }}>{label}</div>
                {cells.slice(r * 8, r * 8 + 8).map((n) => {
                  const kind = kindOf(n);
                  const on = interpolate(frame, [at[kind], at[kind] + 10], [0, 1], clamp);
                  const dim = kind !== "wrong" ? 1 - 0.5 * f * (1 - sum) : 1;
                  const flag = kind !== "ok" ? ring * reviewOff : 0; // 有出入的 13 条：圈出来，我复核
                  return <div key={n} style={{ width: 52, height: 38, borderRadius: 8, background: on > 0.5 ? COLOR[kind] : "#E5E6EB", opacity: dim,
                    transform: kind === "wrong" ? `scale(${1 + 0.25 * f})` : `scale(${1 + 0.12 * Math.sin(Math.PI * on)})`,
                    boxShadow: kind === "wrong" && f > 0.1 ? `0 0 0 ${4 * f}px rgba(245,74,69,0.3)` : flag ? `0 0 0 ${4 * flag}px ${ORANGE}` : undefined }} />;
                })}
              </div>
            );
          })}
        </Card>
        <div style={{ width: 620, height: 520, position: "relative" }}>
          <Panel p={pA}>
            {([["10", "次核对", gray0], ["80", "条提醒", Q("发出 80 条")]] as const).map(([v, k, t0]) => (
              <div key={k} style={{ display: "flex", alignItems: "baseline", gap: 18, marginTop: 20, opacity: useIn(t0) }}>
                <span style={{ fontSize: 96, fontWeight: 800, color: C.blue, width: 170, textAlign: "right" }}>{v}</span>
                <span style={{ fontSize: 36, color: C.text }}>{k}</span>
              </div>
            ))}
          </Panel>
          <Panel p={pB}>
            {/* 助手看不到存档 */}
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Node icon="robot" label="进度助手" color={PURPLE} />
              <div style={{ position: "relative", width: 150, height: 4, background: "#C9CDD4" }}>
                <div style={{ position: "absolute", left: 51, top: -24, width: 48, height: 48, borderRadius: "50%", background: C.red, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Glyph name="cross" size={30} color="#fff" />
                </div>
              </div>
              <Node icon="lock" label="模拟程序存档" color="#8F959E" />
            </div>
            <div style={{ fontSize: 26, color: C.sub, margin: "8px 0 0 10px" }}>助手看不到真实进度</div>
            {/* 另一个 AI 拿存档逐条对 */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 34, opacity: useIn(judge) }}>
              <Node icon="lock" label="存档里的真实进度" color="#8F959E" />
              <div style={{ fontSize: 40, color: C.sub, width: 60, textAlign: "center" }}>→</div>
              <Node icon="robot" label="另一个 AI" color={C.blue} />
              <div style={{ fontSize: 26, color: C.blue, fontWeight: 600, marginLeft: 6 }}>← 逐条对照</div>
            </div>
            {/* 有出入的我复核 */}
            <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 34, opacity: ring, transform: `translateY(${(1 - ring) * 12}px)`,
              background: "#FFF4E5", border: `2px solid ${ORANGE}`, borderRadius: 14, padding: "12px 20px", fontSize: 28, fontWeight: 600, color: C.text }}>
              <Glyph name="person" size={34} color={ORANGE} />有出入的 13 条，我逐条复核
            </div>
          </Panel>
          <Panel p={pC}>
            {([["正确", "ok", GREEN], ["问题存在，细节有出入", "part", "#D99A00"], ["误报", "wrong", C.red]] as const).map(([k, kind, color]) => (
              <div key={k} style={{ display: "flex", alignItems: "baseline", gap: 18, marginTop: 0, opacity: frame >= at[kind] ? 1 : 0.25 }}>
                <span style={{ fontSize: 68, fontWeight: 800, color, width: 120, textAlign: "right" }}>{shown(kind)}</span>
                <span style={{ fontSize: 30, color: C.text }}>{k}</span>
              </div>
            ))}
            <div style={{ opacity: f, marginTop: 14, fontSize: 25, color: C.text, background: "#FDECEC", borderRadius: 12, padding: "14px 18px", lineHeight: 1.6 }}>
              误报：它说印刷还没下单，其实已经下了——同事在会上的说法把它带偏了
            </div>
            <div style={{ opacity: miss, marginTop: 12, fontSize: 25, color: C.name, background: "#fff", borderRadius: 12, padding: "14px 18px", lineHeight: 1.6 }}>
              也会漏：比如群里没人提起的事，它就不知道
            </div>
          </Panel>
        </div>
      </div>
      <div style={{ opacity: sum, transform: `translateY(${(1 - sum) * 20}px)`, marginTop: 18, marginBottom: 90, display: "flex", alignItems: "center", gap: 22, fontSize: 28, color: C.text,
        background: "#fff", border: `3px solid ${GREEN}`, borderRadius: 16, padding: "12px 30px", boxShadow: "0 10px 40px rgba(31,35,41,0.08)" }}>
        <b style={{ color: GREEN }}>结论</b>
        <div style={{ lineHeight: 1.5 }}>
          <div>80 条里有 <b style={{ color: GREEN, fontSize: 40 }}>79</b> 条，指出的问题确实存在（<b style={{ color: GREEN }}>67</b> 条完全正确，<b style={{ color: "#D99A00" }}>12</b> 条细节有误）</div>
          <div>→ 效果还不错，适合先帮我筛一遍，拍板还得靠人</div>
        </div>
      </div>
    </Scene>
  );
};

export const Division: React.FC<SceneProps> = ({ dur }) => (
  <Scene>
    <div style={{ fontSize: 34, color: C.sub, marginBottom: 50 }}>我的分工原则</div>
    <div style={{ display: "flex", gap: 40 }}>
      {([["gear", "交给自动流程", "规则明确的", C.blue], ["robot", "让 AI 找出依据", "需要理解和核对的", PURPLE], ["person", "由我拍板", "要确认、会改动结果的", ORANGE]] as const).map(([icon, who, what, color], i) => (
        <Appear key={who} at={Math.round(dur * [0.18, 0.42, 0.68][i])} dy={40}>
          <Card style={{ width: 500, textAlign: "center", padding: "46px 30px", borderTop: `8px solid ${color}` }}>
            <Badge name={icon} bg={color} size={88} round style={{ margin: "0 auto" }} />
            <div style={{ fontSize: 32, color: C.name, marginTop: 26 }}>{what}</div>
            <div style={{ fontSize: 46, color, fontWeight: 800, marginTop: 12 }}>{who}</div>
          </Card>
        </Appear>
      ))}
    </div>
  </Scene>
);

// 求职助手：几个品牌色方块代表招聘平台（不写名字、不画标志）→ 筛选 → 高匹配的岗位才投
const PLATFORMS = ["#00BEBD", "#FF6A00", "#F7B500", "#1B5FE4"];
export const JobAssistant: React.FC<SceneProps> = ({ dur }) => {
  const frame = useCurrentFrame();
  const flow = Math.round(dur * 0.12);
  const statAt = Math.round(dur * 0.44); // 说到"简历投了很多"
  const needAt = Math.round(dur * 0.6); // 说到"很多岗位都要求经验丰富"
  const resumeAt = Math.round(dur * 0.71); // 说到"简历上的几句话"
  const stat = useIn(statAt);
  const need = useIn(needAt);
  const rest = Math.max(stat, useIn(resumeAt)); // 投递流程退到背景
  const resume = useIn(resumeAt + 8); // 数字卡先退掉，简历再出来，不叠在一起
  const statOut = interpolate(frame, [resumeAt - 4, resumeAt + 6], [1, 0], clamp);
  const CARDS = Array.from({ length: 16 }, (_, i) => i);
  return (
    <Scene>
      {CARDS.filter((i) => i % 5 === 2).map((i) => <Sfx key={i} at={flow + i * 9 + 45} name="tick" volume={2} />)}
      <Sfx at={resumeAt} name="whoosh" />
      {/* 投了很多 → 面试很少（不放具体数字），再加一句：很多岗位要经验丰富 */}
      <div style={{ position: "absolute", zIndex: 3, opacity: stat * statOut, transform: `scale(${0.9 + 0.1 * stat - 0.06 * (1 - statOut)})`, display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
          {([["投了很多", C.text], ["面试很少", C.red]] as const).map(([big, color], i) => (
            <React.Fragment key={big}>
              {i > 0 && <div style={{ fontSize: 70, color: C.sub }}>→</div>}
              <div style={{ background: "#fff", borderRadius: 24, padding: "26px 48px", boxShadow: "0 10px 40px rgba(31,35,41,0.1)", textAlign: "center" }}>
                <div style={{ fontSize: 84, fontWeight: 800, color, lineHeight: 1.2 }}>{big}</div>
              </div>
            </React.Fragment>
          ))}
        </div>
        <div style={{ opacity: need, transform: `translateY(${(1 - need) * 20}px)`, marginTop: 50, fontSize: 38, color: C.text, background: "#fff", borderRadius: 999, padding: "14px 40px",
          border: `3px solid ${ORANGE}` }}>很多岗位都要求：<b style={{ color: ORANGE }}>经验丰富</b></div>
      </div>
      <div style={{ position: "absolute", top: 220, left: 160, display: "flex", flexDirection: "column", gap: 26, opacity: 1 - 0.7 * rest }}>
        {PLATFORMS.map((c, i) => <Appear key={c} at={4 + i * 6} sfx="pop"><div style={{ width: 110, height: 110, borderRadius: 28, background: c }} /></Appear>)}
      </div>
      <Appear at={flow - 10} style={{ position: "absolute", left: 820, top: 330, zIndex: 2, opacity: 1 - rest }}>
        <Glyph name="funnel" size={220} color={PURPLE} />
      </Appear>
      {CARDS.map((i) => {
        const start = flow + i * 9;
        const p = interpolate(frame, [start, start + 50], [0, 1], clamp);
        const keep = i % 5 === 2; // 只留少数高匹配
        const y0 = 270 + (i % 4) * 136;
        const x = interpolate(p, [0, 0.45, 0.6, 1], [290, 860, 860, keep ? 1500 : 860]);
        const y = interpolate(p, [0, 0.45, 0.6, 1], [y0, 330, keep ? 560 : 330, keep ? 300 + (i % 3) * 130 : 330]);
        const o = keep ? 1 : interpolate(p, [0.4, 0.5], [1, 0], clamp);
        return p > 0 && (
          <div key={i} style={{ position: "absolute", left: x, top: y, width: 140, height: 84, borderRadius: 12, background: keep && p > 0.9 ? "#fff" : "#fff",
            outline: keep && p > 0.9 ? `4px solid ${GREEN}` : "none", boxShadow: "0 4px 16px rgba(31,35,41,0.12)", opacity: o * (1 - 0.7 * rest), padding: 14 }}>
            <div style={{ width: 80, height: 10, borderRadius: 5, background: "#D0D3D6" }} />
            <div style={{ width: 100, height: 10, borderRadius: 5, background: "#E5E6EB", marginTop: 10 }} />
            {keep && p > 0.9 && <div style={{ position: "absolute", right: 8, top: 8 }}><Glyph name="check" size={28} color={GREEN} /></div>}
          </div>
        );
      })}
      <div style={{ position: "absolute", top: 160, left: 1480, fontSize: 30, fontWeight: 600, color: GREEN, opacity: interpolate(frame, [flow + 60, flow + 80], [0, 1], clamp) * (1 - 0.7 * rest) }}>高匹配 · 自动投递</div>
      {/* 一张简历：只有几行灰色的线 */}
      <div style={{ position: "absolute", zIndex: 3, opacity: resume, transform: `scale(${0.8 + 0.2 * resume})`, display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ width: 420, height: 540, background: "#fff", borderRadius: 20, boxShadow: "0 20px 60px rgba(31,35,41,0.18)", padding: 44 }}>
          <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
            <div style={{ width: 90, height: 90, borderRadius: 16, background: "#E5E6EB" }} />
            <div><div style={{ width: 160, height: 18, borderRadius: 9, background: "#C9CDD4" }} /><div style={{ width: 110, height: 14, borderRadius: 7, background: "#E5E6EB", marginTop: 14 }} /></div>
          </div>
          {[300, 260, 320, 200, 280, 240].map((w, i) => <div key={i} style={{ width: w, height: 14, borderRadius: 7, background: "#E5E6EB", marginTop: i === 0 ? 50 : 26 }} />)}
        </div>
        <div style={{ fontSize: 36, fontWeight: 600, color: C.text, marginTop: 40 }}>简历上的几句话，很难看出我能做什么</div>
      </div>
    </Scene>
  );
};

// 能力随口播逐个落下，每个配一张前面片子里出现过的缩略图；说到"如果您在视频里看到了我的价值"时再出联系方式
const Thumb: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ height: 120, margin: "18px auto 0", width: 330, background: "#F5F6F8", borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 14 }}>{children}</div>
);
const bar = (w: number, c = "#D0D3D6") => <div style={{ width: w, height: 10, borderRadius: 5, background: c }} />;
// 三个痛点：翻记录、逐格改表、返工滞后
const ThumbPains = () => (
  <Thumb>{(["group", "table", "link"] as const).map((n) => <Badge key={n} name={n} bg="#8F959E" size={60} />)}</Thumb>
);
// 三个痛点 → 三样工具
const ThumbSplit = () => (
  <Thumb>
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{[0, 1, 2].map((i) => <div key={i} style={{ width: 22, height: 22, borderRadius: 11, background: "#8F959E" }} />)}</div>
    <Glyph name="branch" size={40} color={C.sub} />
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{[0, 1, 2].map((i) => <div key={i} style={{ width: 70, height: 22, borderRadius: 6, background: C.blue, opacity: 0.85 - i * 0.2 }} />)}</div>
  </Thumb>
);
// 日报表单的字段 + 改表前后
const ThumbTools = () => (
  <Thumb>
    <div style={{ display: "flex", flexDirection: "column", gap: 9, background: "#fff", borderRadius: 8, padding: "10px 12px" }}>
      {[50, 70, 40].map((w, i) => <div key={i} style={{ display: "flex", gap: 8 }}>{bar(30, "#C9CDD4")}{bar(w + 30, "#E5E6EB")}</div>)}
    </div>
    <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 18, fontWeight: 600 }}>
      {[0, 1].map((i) => <div key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ color: C.sub, textDecoration: "line-through" }}>进行中</span><span style={{ color: C.sub }}>→</span><span style={{ color: GREEN }}>已完成</span>
      </div>)}
    </div>
  </Thumb>
);
// 核对格子：67 绿、12 黄、1 红，缩成 16×5
const ThumbGrid = () => (
  <Thumb>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(16, 14px)", gap: 4 }}>
      {Array.from({ length: 80 }, (_, i) => <div key={i} style={{ width: 14, height: 14, borderRadius: 3, background: WRONG.has(i + 1) ? C.red : PART.has(i + 1) ? "#F5B400" : GREEN }} />)}
    </div>
  </Thumb>
);
const ABILITY: [IconName, string, string, React.FC, number][] = [
  ["search", "找出重复流程", "翻记录、逐格改表、返工滞后", ThumbPains, 0.06],
  ["branch", "拆成需求", "三个痛点 → 三样工具", ThumbSplit, 0.14],
  ["gear", "搭出工具", "表单流程我配 · 代码 AI 写", ThumbTools, 0.3],
  ["check", "检验效果", "AI 评分 · 我复核 13 条疑点", ThumbGrid, 0.45],
];
export const EndCard: React.FC<SceneProps> = ({ dur }) => (
  <Scene>
    <Appear at={0} style={{ fontSize: 52, fontWeight: 700, color: C.text }}>我能做的</Appear>
    <div style={{ display: "flex", gap: 26, marginTop: 40 }}>
      {ABILITY.map(([icon, name, proof, Pic], i) => (
        <Appear key={name} at={10 + i * 12} dy={30}>
          <Card style={{ width: 400, padding: "24px 22px", textAlign: "center", borderTop: `6px solid ${C.blue}` }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 14 }}>
              <Badge name={icon} bg={C.blue} size={52} round />
              <span style={{ fontSize: 36, fontWeight: 700, color: C.text }}>{name}</span>
            </div>
            <Pic />
            <div style={{ fontSize: 22, color: C.name, marginTop: 12, whiteSpace: "nowrap" }}>{proof}</div>
          </Card>
        </Appear>
      ))}
    </div>
    <Appear at={Math.round(dur * 0.58)} style={{ fontSize: 42, fontWeight: 700, color: C.text, marginTop: 56 }}>如果您在视频里看到了我的价值，欢迎联系我</Appear>
    <div style={{ display: "flex", gap: 40, marginTop: 30 }}>
      {([["mail", "联系邮箱", C.blue], ["code", "项目源码 · GitHub", "#24292F"]] as const).map(([icon, s, color], k) => (
        <Appear key={s} at={Math.round(dur * 0.58) + 10 + k * 14} dy={30} sfx="pop">
          <Card style={{ display: "flex", alignItems: "center", gap: 24, padding: "22px 40px" }}>
            <Badge name={icon} bg={color} size={64} />
            <div>
              <div style={{ fontSize: 34, fontWeight: 700, color: C.text }}>{s}</div>
              <div style={{ fontSize: 24, color: C.name, marginTop: 6 }}>见视频简介</div>
            </div>
          </Card>
        </Appear>
      ))}
    </div>
  </Scene>
);

// ---------- 9 致谢：黑底白字，整张名单一起由浅入深显示后停住，最后换成"谢谢观看" ----------
const ME = "策划 · 需求拆解 · 飞书配置 · 文案 · 复核评分 · 扮演项目助理";
const CREDITS: [string, string][] = [
  ["代码 · 模拟系统、助手、视频动画", "Claude（Claude Code）"],
  ["同事们的对话和剧情", "DeepSeek"],
  ["AI 进度助手 · 读记录、改表", "DeepSeek"],
  ["10 次核对的逐条评分", "Claude"],
  ["文案和视频评审", "Claude · DeepSeek · ChatGPT"],
  ["制图", "ChatGPT"],
  ["配音", "MiniMax"],
  ["视频合成", "Remotion"],
  ["工作平台", "飞书"],
];

export const Credits: React.FC<SceneProps> = ({ dur }) => {
  const frame = useCurrentFrame();
  const end = dur - 75; // 最后 2.5 秒只留"谢谢观看"
  const list = interpolate(frame, [end - 15, end], [1, 0], clamp);
  const thanks = interpolate(frame, [end, end + 15], [0, 1], clamp);
  const fade = interpolate(frame, [4, 50], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ background: "#000", fontFamily: FONT, color: "#fff", alignItems: "center", justifyContent: "center" }}>
      <div style={{ opacity: list * fade, width: 1440 }}>
        <div style={{ display: "flex", gap: 40, fontSize: 34, marginBottom: 46 }}>
          <span style={{ width: 600, flexShrink: 0, textAlign: "right", color: "#9A9A9A", whiteSpace: "nowrap" }}>我</span>
          <span>{ME}</span>
        </div>
        {CREDITS.map(([k, v]) => (
          <div key={k} style={{ display: "flex", gap: 40, fontSize: 34, height: 66, alignItems: "center" }}>
            <span style={{ width: 600, flexShrink: 0, textAlign: "right", color: "#9A9A9A", whiteSpace: "nowrap" }}>{k}</span>
            <span>{v}</span>
          </div>
        ))}
      </div>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: thanks, fontSize: 72, fontWeight: 600, letterSpacing: 8 }}>谢谢观看</AbsoluteFill>
    </AbsoluteFill>
  );
};
