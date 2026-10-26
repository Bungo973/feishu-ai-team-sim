// 场景：③ 前置变更 · 依赖联动提醒（约 36 秒）
// 真实截图（工作流、收到的提醒、运行日志）+ 用代码重建的表格动画；截图在 public/素材/工具1/
import React from "react";
import { AbsoluteFill, interpolate, spring, useVideoConfig } from "remotion";
import { useFrame } from "./time";
import { C, FONT } from "./feishu";
import { Glyph, IconName } from "./main/icons";

const T = { title: 0, flow: 120, table: 330, flip: 400, cascade: 440, msg: 720, sum: 900, end: 1080 };

const useIn = (at: number) => {
  const frame = useFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - at, fps, config: { damping: 16 } });
};
const fade = (frame: number, a: number, b: number) =>
  interpolate(frame, [a, a + 15, b - 15, b], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

const Appear: React.FC<{ at: number; children: React.ReactNode; style?: React.CSSProperties; dy?: number }> = ({ at, children, style, dy = 20 }) => {
  const t = useIn(at);
  return <div style={{ opacity: t, transform: `translateY(${interpolate(t, [0, 1], [dy, 0])}px)`, ...style }}>{children}</div>;
};

const Tag: React.FC<{ text: string; style?: React.CSSProperties }> = ({ text, style }) => (
  <div style={{ position: "absolute", fontSize: 22, color: C.name, background: "rgba(255,255,255,0.8)", borderRadius: 999, padding: "8px 22px", ...style }}>{text}</div>
);

// 和飞书任务表里的颜色接近
export const STATUS: Record<string, [string, string]> = {
  已完成: ["#FDE2E2", "#D83931"],
  进行中: ["#D5F6F2", "#078372"],
  "受影响-待确认": ["#ECE2FE", "#6425D0"],
};
export const Chip: React.FC<{ s: string }> = ({ s }) =>
  s ? <span style={{ background: STATUS[s][0], color: STATUS[s][1], borderRadius: 6, padding: "3px 10px", fontSize: 21, fontWeight: 500 }}>{s}</span> : null;

// 测试表里 A0 和它的 9 个后置任务（另放 A1、A4 两行，看出没被误改）；状态是触发前的真实值
export type Row = { name: string; owner: string; status: string; pre: string; hit: number };
export const ROWS: Row[] = [
  { name: "A0 产品卖点与定价确认", owner: "周涛", status: "已完成", pre: "", hit: -1 },
  { name: "A1 场地确认与合同签订", owner: "张伟", status: "已完成", pre: "", hit: -1 },
  { name: "A3 邀请函文案", owner: "李想", status: "已完成", pre: "A0", hit: 0 },
  { name: "A4 邀请函设计（电子版）", owner: "陈悦", status: "进行中", pre: "A3", hit: -1 },
  { name: "A6 主视觉 KV 与现场物料设计", owner: "陈悦", status: "进行中", pre: "A0", hit: 1 },
  { name: "A9 发布会流程（Run-down）与主持稿", owner: "李想", status: "", pre: "A0", hit: 2 },
  { name: "A10 演讲 PPT 内容", owner: "周涛", status: "进行中", pre: "A0", hit: 3 },
  { name: "A12 新闻通稿", owner: "李想", status: "", pre: "A0", hit: 4 },
  { name: "B06 小红书·神秘新品倒计时", owner: "李想", status: "已完成", pre: "A0", hit: 5 },
  { name: "B07 公众号·小暖 S2 首曝", owner: "李想", status: "已完成", pre: "A0", hit: 6 },
  { name: "B08 小红书·三大卖点一次看懂", owner: "李想", status: "已完成", pre: "A0", hit: 7 },
  { name: "B14 公众号·小暖 S2 正式发布", owner: "李想", status: "", pre: "A0", hit: 8 },
];
export const EVERY = 14; // 后置任务一个接一个变色的间隔（帧）

// 树状图：A0 在上，9 个后置任务在下，A0 被改回后依次标成「受影响-待确认」（大字，手机上也看得清）
const HITS = ROWS.filter((r) => r.hit >= 0).sort((x, y) => x.hit - y.hit);
export const Tree: React.FC<{ flip?: number; cascade?: number; table?: number }> = ({ flip = T.flip, cascade = T.cascade, table = T.table }) => {
  const frame = useFrame();
  const flipped = frame >= flip;
  const marked = Math.max(0, Math.min(9, Math.floor((frame - cascade) / EVERY) + 1));
  const a0 = ROWS[0];
  const flash0 = interpolate(frame, [flip, flip + 6, flip + 30], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const lines = interpolate(frame, [table + 20, table + 40], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: -40 }}>
      <div style={{ width: 640, background: flash0 > 0 ? `rgba(255,214,102,${0.5 * flash0})` : flipped ? "#FFF7E6" : "#fff", borderRadius: 18, padding: "20px 28px",
        border: `3px solid ${flipped ? "#E37318" : "#DDE1E8"}`, boxShadow: "0 10px 40px rgba(31,35,41,0.08)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 24, color: C.blue, fontWeight: 600 }}>A0 · 前置任务</span>
          <Chip s={flipped ? "进行中" : a0.status} />
        </div>
        <div style={{ fontSize: 36, fontWeight: 700, color: C.text, marginTop: 8 }}>产品卖点与定价确认</div>
      </div>
      <svg width={1300} height={60} style={{ opacity: lines }}>
        <path d="M650 0 V30 M216 30 H1084 M216 30 V60 M650 30 V60 M1084 30 V60" stroke="#B8C0CC" strokeWidth={3} fill="none" />
      </svg>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 410px)", gap: "16px 22px", opacity: lines }}>
        {HITS.map((r) => {
          const at = cascade + r.hit * EVERY;
          const hit = frame >= at;
          const flash = interpolate(frame, [at, at + 6, at + 30], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const [code, ...rest] = r.name.split(" ");
          const name = rest.join(" ").replace("与现场物料设计", "").replace("（Run-down）", "");
          return (
            <div key={r.name} style={{ background: flash > 0 ? `rgba(255,214,102,${0.5 * flash})` : hit ? "#F7F3FF" : "#fff", borderRadius: 14, padding: "14px 18px",
              border: `2px solid ${hit ? "#B79CF0" : "#E5E6EB"}` }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 10, whiteSpace: "nowrap", overflow: "hidden" }}>
                <b style={{ fontSize: 26, color: C.blue }}>{code}</b>
                <span style={{ fontSize: 26, color: C.text, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis" }}>{name}</span>
              </div>
              <div style={{ marginTop: 8 }}>{hit ? <Chip s="受影响-待确认" /> : r.status ? <Chip s={r.status} /> : <span style={{ fontSize: 21, color: C.sub }}>（未开始）</span>}</div>
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: 22, fontSize: 28, color: C.text }}>
        {frame >= cascade
          ? <>已自动标记 <b style={{ color: "#6425D0" }}>{marked} / 9</b> 项 · 标记受影响，实际是否返工由人确认</>
          : flipped ? "A0 被改回「进行中」→ 工作流自动运行" : "A0 是这 9 个任务的前置"}
      </div>
    </div>
  );
};

// 工作流的逻辑，配在真实截图旁边
export const STEPS = ["任务「状态」被修改", "它以前完成过吗？（看「曾完成」列）", "找出所有把它当前置的任务", "全部标为「受影响-待确认」", "飞书消息提醒我"];

export const Card: React.FC<{ at: number; big: string; small: string; color?: string }> = ({ at, big, small, color = C.blue }) => (
  <Appear at={at} style={{ background: "#fff", borderRadius: 22, padding: "34px 40px", boxShadow: "0 10px 40px rgba(31,35,41,0.08)", width: 360 }}>
    <div style={{ fontSize: 56, fontWeight: 700, color }}>{big}</div>
    <div style={{ fontSize: 26, color: C.name, marginTop: 10 }}>{small}</div>
  </Appear>
);

// 工作流的 8 个节点（按飞书里的真实配置重画）
type Node = { n: number; kind: "trigger" | "if" | "edit" | "find" | "msg"; title: string; sub: string; x: number; y: number };
const NODES: Node[] = [
  { n: 1, kind: "trigger", title: "修改记录时", sub: "任务表 · 状态被修改", x: 330, y: 20 },
  { n: 2, kind: "if", title: "条件判断", sub: "状态 等于 已完成？", x: 330, y: 130 },
  { n: 3, kind: "edit", title: "修改记录", sub: "标记「曾完成」", x: 60, y: 260 },
  { n: 4, kind: "if", title: "条件判断", sub: "以前完成过？", x: 600, y: 260 },
  { n: 5, kind: "find", title: "查找记录", sub: "前置里有它的任务", x: 600, y: 380 },
  { n: 6, kind: "edit", title: "修改记录", sub: "后置标「受影响-待确认」", x: 600, y: 480 },
  { n: 7, kind: "edit", title: "修改记录", sub: "更新辅助列", x: 600, y: 580 },
  { n: 8, kind: "msg", title: "发送飞书消息", sub: "提醒项目助理", x: 600, y: 680 },
];
const KIND: Record<Node["kind"], [string, IconName]> = { trigger: ["#D83C8F", "bolt"], if: ["#2B2F36", "branch"], edit: ["#D83C8F", "edit"], find: ["#3370FF", "search"], msg: ["#3370FF", "mail"] };
const NW = 340;

export const Workflow: React.FC<{ at: number }> = ({ at }) => {
  const frame = useFrame();
  const shown = (i: number) => frame >= at + i * 10;
  const line = (x1: number, y1: number, x2: number, y2: number, i: number, label?: string, ok = true) => shown(i) && (
    <g key={`${x1}-${y1}-${x2}-${y2}`}>
      <path d={`M${x1} ${y1} V${(y1 + y2) / 2} H${x2} V${y2}`} fill="none" stroke="#C9CDD4" strokeWidth={2.5} />
      {label && <text x={x2 + 10} y={(y1 + y2) / 2 - 8} fontSize={19} fill={ok ? "#2EA121" : "#D83931"}>{label}</text>}
    </g>
  );
  const cx = (n: Node) => n.x + NW / 2;
  const N = NODES;
  return (
    <div style={{ position: "relative", width: 1000, height: 760 }}>
      <svg width={1000} height={760} style={{ position: "absolute" }}>
        {line(cx(N[0]), N[0].y + 70, cx(N[1]), N[1].y, 1)}
        {line(cx(N[1]), N[1].y + 70, cx(N[2]), N[2].y, 2, "是：记下它完成过")}
        {line(cx(N[1]), N[1].y + 70, cx(N[3]), N[3].y, 3, "否", false)}
        {line(cx(N[3]), N[3].y + 70, cx(N[4]), N[4].y, 4, "是：被改回了")}
        {[4, 5, 6].map((i) => line(cx(N[i]), N[i].y + 70, cx(N[i + 1]), N[i + 1].y, i + 1))}
      </svg>
      {N.map((n, i) => {
        const t = spring({ frame: frame - at - i * 10, fps: 30, config: { damping: 16 } });
        const [color, icon] = KIND[n.kind];
        return (
          <div key={n.n} style={{ position: "absolute", left: n.x, top: n.y, width: NW, height: 70, background: "#fff", borderRadius: 12, opacity: t,
            transform: `scale(${0.9 + 0.1 * t})`, boxShadow: "0 4px 16px rgba(31,35,41,0.1)", display: "flex", alignItems: "center", gap: 14, padding: "0 16px" }}>
            <div style={{ fontSize: 16, color: C.sub, width: 14 }}>{n.n}</div>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: color, color: "#fff", fontSize: 22, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}><Glyph name={icon} size={24} color="#fff" detail={color} /></div>
            <div>
              <div style={{ fontSize: 21, fontWeight: 600, color: C.text }}>{n.title}</div>
              <div style={{ fontSize: 16, color: C.name, marginTop: 2 }}>{n.sub}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// 真实收到的提醒（文字照抄）
const AFFECTED = ["A3 邀请函文案", "A6 主视觉 KV 与现场物料设计", "A9 发布会流程（Run-down）与主持稿", "A12 新闻通稿", "B07 公众号·小暖 S2 首曝：巴掌大的暖风机",
  "B08 小红书·小暖 S2 三大卖点一次看懂", "B14 公众号·小暖 S2 正式发布", "A10 演讲 PPT 内容", "B06 小红书·神秘新品倒计时｜猜猜它有多小"];
export const Reminder: React.FC = () => (
  <div style={{ width: 860, background: "#fff", borderRadius: 18, overflow: "hidden", boxShadow: "0 10px 40px rgba(31,35,41,0.12)" }}>
    <div style={{ background: "linear-gradient(90deg, #F1EAFE, #F8F5FF)", padding: "20px 28px", fontSize: 30, fontWeight: 700, color: "#6425D0", display: "flex", alignItems: "center", gap: 12 }}><Glyph name="warn" size={34} color="#E37318" />前置任务被改回，后置任务受影响</div>
    <div style={{ padding: "20px 28px", fontSize: 23, color: C.text, lineHeight: 1.65 }}>
      <div>被改回的任务：A0 产品卖点与定价确认</div>
      <div>受影响的后置任务（已自动标为“受影响-待确认”）：</div>
      <div style={{ margin: "10px 0" }}>{AFFECTED.map((a) => <div key={a}>· {a}</div>)}</div>
      <div>请找对应负责人确认影响范围，确认后再改回原状态。</div>
    </div>
  </div>
);

const RUN = ["修改记录时", "条件判断", "条件判断", "查找记录", "修改记录", "修改记录", "发送飞书消息"];
export const RunLog: React.FC = () => (
  <div style={{ width: 520, background: "#fff", borderRadius: 14, padding: "18px 26px", boxShadow: "0 6px 24px rgba(31,35,41,0.1)" }}>
    <div style={{ fontSize: 24, fontWeight: 600, color: C.text, marginBottom: 8 }}><span style={{ color: "#2EA121" }}>●</span> 运行成功</div>
    {RUN.map((s, i) => (
      <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 20, color: C.text, padding: "5px 0", borderTop: `1px solid ${C.line}` }}>
        <span>{i + 1}. {s}</span><Glyph name="check" size={22} color="#2EA121" />
      </div>
    ))}
  </div>
);

export const ToolDependency: React.FC = () => {
  const frame = useFrame();
  return (
    <AbsoluteFill style={{ fontFamily: FONT, background: "linear-gradient(135deg, #EEF0F6, #E6EAF3)" }}>
      {/* 1. 标题 */}
      <AbsoluteFill style={{ opacity: fade(frame, T.title, T.flow), alignItems: "center", justifyContent: "center" }}>
        <Appear at={5} style={{ fontSize: 30, color: C.blue, fontWeight: 600 }}>③ 前置变更</Appear>
        <Appear at={12} style={{ fontSize: 76, fontWeight: 700, color: C.text, marginTop: 14 }}>依赖联动提醒</Appear>
        <Appear at={30} style={{ fontSize: 32, color: C.name, marginTop: 24 }}>前置任务被改回时，后置任务自动标记、自动通知</Appear>
      </AbsoluteFill>

      {/* 2. 真实工作流截图 + 逻辑 */}
      <AbsoluteFill style={{ opacity: fade(frame, T.flow, T.table), flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 60 }}>
        <div style={{ borderRadius: 18, background: "#F5F6F7", padding: "20px 10px", boxShadow: "0 10px 40px rgba(31,35,41,0.08)", transform: "scale(0.86) translateY(-40px)" }}>
          <Workflow at={T.flow + 5} />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 22, width: 560 }}>
          {STEPS.map((s, i) => (
            <Appear key={s} at={T.flow + 30 + i * 22} style={{ display: "flex", alignItems: "center", gap: 18, fontSize: 30, color: C.text }}>
              <div style={{ width: 46, height: 46, borderRadius: 23, background: C.blue, color: "#fff", fontSize: 24, fontWeight: 700,
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{i + 1}</div>
              {s}
            </Appear>
          ))}
        </div>
        <Tag text="按飞书里的真实配置重画 · 8 个节点" style={{ top: 50, right: 60 }} />
      </AbsoluteFill>

      {/* 3. 表格动画 */}
      <AbsoluteFill style={{ opacity: fade(frame, T.table, T.msg), alignItems: "center", justifyContent: "center" }}>
        <Tree />
        <Tag text="画面根据真实配置重建" style={{ bottom: 150, right: 60 }} />
      </AbsoluteFill>

      {/* 4. 真实收到的提醒 */}
      <AbsoluteFill style={{ opacity: fade(frame, T.msg, T.sum), alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 70 }}>
        <Appear at={T.msg + 5} dy={40}>
          <Reminder />
        </Appear>
        <div style={{ width: 640 }}>
          <Appear at={T.msg + 30} style={{ fontSize: 40, fontWeight: 700, color: C.text }}>不到一分钟，提醒直接到我手上</Appear>
          <Appear at={T.msg + 50} style={{ fontSize: 28, color: C.name, marginTop: 20, lineHeight: 1.6 }}>
            哪个任务被改回、牵连了谁，一目了然。<br />我只需要去找负责人确认影响范围。
          </Appear>
        </div>
        <Tag text="真实收到的提醒（文字原样）" style={{ top: 50, right: 60 }} />
      </AbsoluteFill>

      {/* 5. 小结 */}
      <AbsoluteFill style={{ opacity: fade(frame, T.sum, T.end + 15), alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 50 }}>
        <div style={{ display: "flex", gap: 40, alignItems: "center" }}>
          <Card at={T.sum + 5} big="1 处" small="前置任务被改回" color={C.text} />
          <div style={{ fontSize: 50, color: C.sub }}>→</div>
          <Card at={T.sum + 20} big="9 个" small="后置任务自动标记" color="#6425D0" />
          <div style={{ fontSize: 50, color: C.sub }}>→</div>
          <Card at={T.sum + 35} big="1 条" small="提醒直达，不用挨个问" />
        </div>
        <Appear at={T.sum + 60} style={{ display: "flex", alignItems: "center", gap: 30 }}>
          <RunLog />
          <div style={{ fontSize: 26, color: C.name, lineHeight: 1.6 }}>运行日志：每个节点都执行成功<br />飞书低代码配置，没写一行代码</div>
        </Appear>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
