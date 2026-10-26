// 飞书界面底板：痛点部分每一幕都先在这个界面上操作（点导航、点会话、发消息），讲到重点时底板褪去、聚焦成大卡片
// 界面按 1440×810 画、整体放大 4/3 到 1080p；children 按 1080p 的原尺寸画（里面再缩回 3/4 抵消）
import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { Avatar, C, ChatHeader, Conv, ConvList, FONT, H, Icon, InputBox, NAV, NavBar, W } from "../feishu";

export const K = 1920 / W;
const px = (v: number) => Math.round(v * K);
// 1080p 坐标：导航第几项、会话列表第几行、多维表格列表第几行（给鼠标用）
export const navAt = (label: string): [number, number] => [px(48), px(112 + 31 * NAV.findIndex(([, l]) => l === label))];
export const convAt = (i: number): [number, number] => [px(230), px(67 + 50 * i)];
export const tableAt = (i: number): [number, number] => [px(200), px(64 + 34 * i)];
export const SEND: [number, number] = [px(1405), px(780)]; // 输入框右边的发送键
export const MAIN = { x: px(366), y: px(50) }; // 主区域内容的左上角（1080p）

const PEOPLE = ["品牌项目组", "张伟", "小暖 S2 发布会筹备", "王丽", "李想", "陈悦", "周涛", "孙磊", "刘敏", "黄建国"];
// 会话列表（不放预览文字，避免编造消息）；withBot：AI 进度助手排在最上面
export const convs = (withBot: boolean, extra: Conv[] = []): Conv[] => [...extra,
  ...[...(withBot ? ["AI 进度助手"] : []), ...PEOPLE].map((name) => ({
    name, bot: name !== "品牌项目组" && name !== "小暖 S2 发布会筹备", unread: 0, preview: "",
    time: name === "AI 进度助手" || name === "品牌项目组" ? "17:25" : "昨天",
  }))].slice(0, 11); // 最多 11 行，下面留给左下角的痛点卡

export const TABLES = ["任务表", "日报表"];
const TableList: React.FC<{ active?: string }> = ({ active }) => (
  <div style={{ width: 250, background: C.panel, borderRadius: 8, margin: "4px 4px 4px 0", overflow: "hidden" }}>
    <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "10px 12px", fontSize: 13, fontWeight: 600, color: C.text }}>
      <Icon name="table" size={13} color={C.text} />进度跟踪
    </div>
    {TABLES.map((t) => (
      <div key={t} style={{ display: "flex", alignItems: "center", gap: 8, height: 30, padding: "0 12px", margin: "2px 4px", borderRadius: 6, fontSize: 12.5,
        color: C.text, background: t === active ? C.active : "transparent", fontWeight: t === active ? 600 : 400 }}>
        <Icon name="table" size={13} color={t === active ? C.blue : "#646A73"} />{t}
      </div>
    ))}
  </div>
);

export const AUTO_BTN: [number, number] = [px(1395), px(27)]; // 表头右边的「自动化」按钮
export const TableHead: React.FC<{ name: string; view?: string; auto?: boolean }> = ({ name, view = "表格视图", auto }) => (
  <div style={{ height: 46, display: "flex", alignItems: "center", gap: 14, padding: "0 14px", borderBottom: `1px solid ${C.line}`, flexShrink: 0 }}>
    <Icon name="table" size={16} color={C.blue} />
    <span style={{ fontSize: 14, fontWeight: 600, color: C.text }}>{name}</span>
    <span style={{ fontSize: 11.5, color: C.blue, background: C.active, borderRadius: 4, padding: "2px 8px" }}>{view}</span>
    {auto && <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: C.text, border: `1px solid #DEE0E3`, borderRadius: 6, padding: "4px 10px" }}>
      <Icon name="send" size={12} color={C.blue} />自动化</span>}
  </div>
);

export const ChatHead = ChatHeader;

export const Shell: React.FC<{
  nav?: string; active?: string; withBot?: boolean; extra?: Conv[]; head?: React.ReactNode; to?: string; dim?: number; children?: React.ReactNode;
}> = ({ nav = "消息", active, withBot = false, extra, head, to, dim = 0, children }) => (
  <AbsoluteFill style={{ opacity: 1 - 0.93 * dim, transform: `scale(${1 + 0.03 * dim})` }}>
    <div style={{ width: W, height: H, transform: `scale(${K})`, transformOrigin: "0 0", display: "flex", fontFamily: FONT, background: "linear-gradient(135deg, #EEF0F6, #E6EAF3)" }}>
      <NavBar unread={0} active={nav} />
      {nav === "多维表格" ? <TableList active={active} /> : <ConvList items={convs(withBot, extra)} active={active ?? ""} />}
      <div style={{ flex: 1, background: C.panel, borderRadius: 8, margin: "4px 4px 4px 0", display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
        {head}
        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          <div style={{ position: "absolute", left: 0, top: 0, width: `${100 * K}%`, height: `${100 * K}%`, transform: `scale(${1 / K})`, transformOrigin: "0 0" }}>{children}</div>
        </div>
        {to && <InputBox to={to} />}
      </div>
    </div>
  </AbsoluteFill>
);

// 聚焦层：底板褪去时，大卡片从稍小放大到原尺寸
export const Focus: React.FC<{ on: number; children: React.ReactNode }> = ({ on, children }) => (
  <AbsoluteFill style={{ opacity: on, transform: `scale(${0.94 + 0.06 * on})`, alignItems: "center", justifyContent: "center", pointerEvents: "none" }}>{children}</AbsoluteFill>
);

// 进出聚焦：[开始, 结束]，前后各 10 帧过渡
export const focusOf = (frame: number, a: number, b = 1e9) => interpolate(frame, [a, a + 10, b, b + 10], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

export { Avatar };
