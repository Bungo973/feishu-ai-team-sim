// 场景：这个模拟是怎么运转的（背景那一段用）
// 中间是飞书（同事机器人、导演、群、任务表），右边是模拟后台（规则引擎 + 大模型），左边是我
import React from "react";
import { AbsoluteFill, interpolate, spring, useVideoConfig } from "remotion";
import { useFrame } from "./time";
import { Avatar, C, FONT, TITLES } from "./feishu";
import { Glyph } from "./main/icons";

const STAFF = Object.keys(TITLES);

// 每一步出现的帧
const T = { staff: 10, director: 100, places: 160, rules: 230, llm: 290, me: 350, note: 420 };

const useIn = (at: number) => {
  const frame = useFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - at, fps, config: { damping: 16 } });
};

const Appear: React.FC<{ at: number; children: React.ReactNode; style?: React.CSSProperties; dy?: number }> = ({ at, children, style, dy = 20 }) => {
  const t = useIn(at);
  return <div style={{ opacity: t, transform: `translateY(${interpolate(t, [0, 1], [dy, 0])}px)`, ...style }}>{children}</div>;
};

const Box: React.FC<{ title: string; children: React.ReactNode; style?: React.CSSProperties }> = ({ title, children, style }) => (
  <div style={{ background: "#fff", borderRadius: 24, padding: "28px 32px", boxShadow: "0 10px 40px rgba(31,35,41,0.08)", ...style }}>
    <div style={{ fontSize: 26, fontWeight: 600, color: C.sub, marginBottom: 22 }}>{title}</div>
    {children}
  </div>
);

const Chip: React.FC<{ icon: string; text: string; color: string }> = ({ icon, text, color }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 12, background: "#F5F6F7", borderRadius: 12, padding: "12px 18px", fontSize: 24, color: C.text }}>
    <div style={{ width: 36, height: 36, borderRadius: 9, background: color, color: "#fff", fontSize: 18, fontWeight: 700,
      display: "flex", alignItems: "center", justifyContent: "center" }}>{icon}</div>
    {text}
  </div>
);

// 双向箭头：从左往右画出来
const Arrow: React.FC<{ at: number; label: string }> = ({ at, label }) => {
  const t = useIn(at);
  return (
    <div style={{ width: 150, display: "flex", flexDirection: "column", alignItems: "center", gap: 10, opacity: t }}>
      <svg width={150} height={24} viewBox="0 0 150 24">
        <line x1={8} y1={12} x2={8 + 134 * t} y2={12} stroke={C.blue} strokeWidth={3} strokeDasharray="8 6" />
        <path d="M14 4 L4 12 L14 20" fill="none" stroke={C.blue} strokeWidth={3} />
        {t > 0.95 && <path d="M136 4 L146 12 L136 20" fill="none" stroke={C.blue} strokeWidth={3} />}
      </svg>
      <div style={{ fontSize: 18, color: C.sub, textAlign: "center", whiteSpace: "pre-line" }}>{label}</div>
    </div>
  );
};

// note：底部那行说明。正片里有字幕和角标，关掉它免得和字幕叠在一起
export const ArchitectureIntro: React.FC<{ note?: boolean }> = ({ note = true }) => {
  const frame = useFrame();
  const rulesGlow = interpolate(frame, [T.rules, T.rules + 20, T.llm, T.llm + 20], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const llmGlow = interpolate(frame, [T.llm, T.llm + 20, T.me, T.me + 20], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ fontFamily: FONT, background: "linear-gradient(135deg, #EEF0F6, #E6EAF3)", alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", alignItems: "center" }}>
        {/* 我 */}
        <Appear at={T.me} style={{ width: 230 }}>
          <Box title="我" style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "28px 20px" }}>
            <Avatar name="我" size={110} />
            <div style={{ fontSize: 26, fontWeight: 600, color: C.text, marginTop: 16 }}>项目助理</div>
            <div style={{ fontSize: 19, color: C.sub, marginTop: 6 }}>唯一的真人</div>
          </Box>
        </Appear>
        <Arrow at={T.me + 10} label={"看群 · 追问\n改表 · 写周报"} />

        {/* 飞书 */}
        <Box title="飞书" style={{ width: 760 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "18px 10px" }}>
            {STAFF.map((p, i) => (
              <Appear key={p} at={T.staff + i * 8} dy={12} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                <Avatar name={p} size={84} />
                <div style={{ fontSize: 22, color: C.text }}>{p}</div>
              </Appear>
            ))}
          </div>
          <Appear at={T.staff + 70} style={{ textAlign: "center", fontSize: 21, color: C.sub, margin: "14px 0 18px" }}>
            8 个同事 = 8 个飞书机器人，能在群里说话，也能私聊
          </Appear>
          <div style={{ display: "flex", gap: 14, alignItems: "stretch" }}>
            <Appear at={T.director} style={{ flex: 1.2 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 14, background: "#FFF7E6", borderRadius: 12, padding: "12px 16px", height: "100%" }}>
                <Avatar name="导演" size={56} />
                <div>
                  <div style={{ fontSize: 23, fontWeight: 600, color: C.text }}>导演机器人</div>
                  <div style={{ fontSize: 18, color: C.sub }}>推进时间 · 自动记录我的动作</div>
                </div>
              </div>
            </Appear>
            <Appear at={T.places} style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
              <Chip icon="群" text="两个工作群" color="#3EC135" />
              <Chip icon="表" text="多维表格任务表" color="#7B67EE" />
            </Appear>
          </div>
        </Box>

        <Arrow at={T.rules - 10} label={"群消息 · 私聊\n表格改动"} />

        {/* 模拟后台 */}
        <Appear at={T.rules - 10} style={{ width: 400 }}>
          <Box title="模拟后台">
            <div style={{ borderRadius: 14, padding: "18px 20px", background: "#F5F6F7",
              boxShadow: `0 0 0 ${3 * rulesGlow}px ${C.blue}`, transform: `scale(${1 + 0.03 * rulesGlow})` }}>
              <div style={{ fontSize: 25, fontWeight: 600, color: C.text, display: "flex", alignItems: "center", gap: 10 }}><Glyph name="gear" size={30} color={C.blue} detail="#F5F6F7" />规则引擎</div>
              <div style={{ fontSize: 19, color: C.name, marginTop: 8, lineHeight: 1.5 }}>进度、工时、审批、突发事件<br />由程序确定性计算</div>
            </div>
            <div style={{ height: 16 }} />
            <Appear at={T.llm}>
              <div style={{ borderRadius: 14, padding: "18px 20px", background: "#F5F6F7",
                boxShadow: `0 0 0 ${3 * llmGlow}px #7B67EE`, transform: `scale(${1 + 0.03 * llmGlow})` }}>
                <div style={{ fontSize: 25, fontWeight: 600, color: C.text, display: "flex", alignItems: "center", gap: 10 }}><Glyph name="bubble" size={30} color="#7B67EE" detail="#F5F6F7" />大模型</div>
                <div style={{ fontSize: 19, color: C.name, marginTop: 8, lineHeight: 1.5 }}>只负责"说话"和"评判"<br />不决定事实</div>
              </div>
            </Appear>
          </Box>
        </Appear>
      </div>

      {note && <Appear at={T.note} style={{ position: "absolute", bottom: 56 }}>
        <div style={{ fontSize: 24, color: C.name, background: "rgba(255,255,255,0.7)", borderRadius: 999, padding: "10px 28px" }}>
          自建模拟演练 · 同事由 AI 扮演 · 工具和搭建过程是真实的
        </div>
      </Appear>}
    </AbsoluteFill>
  );
};
