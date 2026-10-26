// 飞书桌面端风格的界面零件，尺寸按真实客户端（逻辑像素 1440×810，最后整体放大到 1080p）
// 只还原布局和配色，不放飞书 Logo 和第三方产品入口
import React from "react";
import { Img, staticFile } from "remotion";
import { Glyph } from "./main/icons";

export const W = 1440;
export const H = 810;

export const C = {
  bg: "#E9ECF3",
  panel: "#FFFFFF",
  line: "#EFF0F1",
  text: "#1F2329",
  name: "#646A73",
  sub: "#8F959E",
  blue: "#3370FF",
  active: "#E1EAFF",
  bubble: "#F2F3F5",
  mine: "#DCE8FE",
  red: "#F54A45",
};

export const FONT = '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif';

// 机器人后台填的描述（显示在名字后面）
export const TITLES: Record<string, string> = {
  王丽: "知暖电器市场部经理（模拟同事）",
  张伟: "知暖电器市场部活动执行（模拟同事）",
  李想: "知暖电器市场部内容运营（模拟同事）",
  陈悦: "知暖电器市场部设计（模拟同事）",
  周涛: "知暖电器产品部产品经理（模拟同事）",
  孙磊: "印刷供应商对接人（模拟同事）",
  刘敏: "知暖电器人事部 HRBP（模拟同事）",
  黄建国: "知暖电器市场副总裁（模拟同事）",
};

const AVATARS = new Set([...Object.keys(TITLES), "导演"]);
const GROUP_COLOR: Record<string, string> = { "品牌项目组": "#3EC135", "小暖 S2 发布会筹备": "#7B67EE" };

// 你的头像：把图片放到 素材/头像/我.png，导出脚本会复制过来并打开这个开关
export let ME_AVATAR = false;
export const setMeAvatar = (v: boolean) => { ME_AVATAR = v; };

export const Avatar: React.FC<{ name: string; size?: number }> = ({ name, size = 32 }) => {
  if (name === "AI 进度助手") return (
    <div style={{ width: size, height: size, borderRadius: "50%", background: "#6425D0", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
      <Glyph name="robot" size={size * 0.6} color="#fff" detail="#6425D0" />
    </div>
  );
  if (AVATARS.has(name) || (name === "我" && ME_AVATAR))
    return <Img src={staticFile(`avatars/${name}.png`)} style={{ width: size, height: size, borderRadius: "50%", objectFit: "cover", flexShrink: 0 }} />;
  const group = GROUP_COLOR[name];
  return (
    <div style={{ width: size, height: size, borderRadius: "50%", background: group ?? C.blue, color: "#fff", flexShrink: 0,
      display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center",
      fontSize: group ? size * 0.24 : size * 0.42, lineHeight: 1.1, fontWeight: 600, padding: group ? 3 : 0 }}>
      {group ? name.replace(/\s/g, "").slice(0, 6) : name.slice(0, 1)}
    </div>
  );
};

export const BotTag: React.FC = () => (
  <span style={{ fontSize: 9.5, color: "#C17D00", background: "#FFF1CC", borderRadius: 3, padding: "1px 4px", marginLeft: 5,
    fontWeight: 500, flexShrink: 0 }}>机器人</span>
);

// ---------- 图标（简单线条） ----------
const I: React.FC<{ d: string; size?: number; color?: string }> = ({ d, size = 15, color = "#646A73" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const ICON = {
  chat: "M4 5h16v11H9l-5 4z",
  doc: "M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h5",
  table: "M4 4h16v16H4zM4 10h16M10 4v16",
  video: "M3 7h12v10H3zM15 11l6-4v10l-6-4",
  contact: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c0-4 4-6 8-6s8 2 8 6",
  calendar: "M4 6h16v14H4zM4 10h16M8 3v4M16 3v4",
  more: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM21 21l-5-5",
  plus: "M12 7v10M7 12h10M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z",
  member: "M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM3 19c0-3 3-5 6-5s6 2 6 5M16 5a3 3 0 0 1 0 6M18 14c2 .5 3 2.5 3 5",
  emoji: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01",
  at: "M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM16 12v1.5a2.5 2.5 0 0 0 5 0V12a9 9 0 1 0-4 7.5",
  send: "M4 12l16-8-6 16-3-7z",
  phone: "M5 4h4l2 5-3 2a11 11 0 0 0 5 5l2-3 5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2",
  dots: "M5 12h.01M12 12h.01M19 12h.01",
};
export const Icon: React.FC<{ name: keyof typeof ICON; size?: number; color?: string }> = ({ name, ...p }) => <I d={ICON[name]} {...p} />;

// ---------- 最左边：导航 ----------
export const NAV: [keyof typeof ICON, string][] = [
  ["chat", "消息"], ["doc", "云文档"], ["table", "多维表格"], ["video", "视频会议"], ["contact", "通讯录"], ["calendar", "日历"], ["more", "更多"],
];

export const NavBar: React.FC<{ unread: number; active?: string }> = ({ unread, active = "消息" }) => (
  <div style={{ width: 112, padding: "10px 8px", display: "flex", flexDirection: "column", gap: 4 }}>
    <div style={{ display: "flex", gap: 6, padding: "2px 4px 12px" }}>
      {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: "#D5D7DC" }} />)}
    </div>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 4px 8px" }}>
      <Avatar name="我" size={24} />
      <Icon name="plus" size={16} />
    </div>
    <div style={{ display: "flex", alignItems: "center", gap: 5, background: "rgba(255,255,255,0.6)", borderRadius: 6, padding: "5px 7px",
      fontSize: 10.5, color: C.sub, marginBottom: 6 }}>
      <Icon name="search" size={11} color={C.sub} />搜索 (⌘+K)
    </div>
    {NAV.map(([icon, label], i) => (
      <div key={label} style={{ display: "flex", alignItems: "center", gap: 7, padding: "6px 8px", borderRadius: 6, fontSize: 12,
        color: C.text, background: label === active ? C.panel : "transparent", fontWeight: label === active ? 600 : 400 }}>
        <Icon name={icon} size={13} color={label === active ? C.blue : "#646A73"} />
        {label}
        {i === 0 && unread > 0 && <Badge n={unread} style={{ marginLeft: "auto" }} />}
      </div>
    ))}
  </div>
);

export const Badge: React.FC<{ n: number; style?: React.CSSProperties }> = ({ n, style }) => (
  <div style={{ minWidth: 15, height: 15, borderRadius: 8, background: C.red, color: "#fff", fontSize: 9.5, fontWeight: 600,
    display: "flex", alignItems: "center", justifyContent: "center", padding: "0 4px", ...style }}>{n}</div>
);

// ---------- 中间：会话列表 ----------
export type Conv = { name: string; bot: boolean; time: string; preview: string; unread: number };

export const ConvList: React.FC<{ items: Conv[]; active: string }> = ({ items, active }) => (
  <div style={{ width: 250, background: C.panel, borderRadius: 8, margin: "4px 4px 4px 0", overflow: "hidden" }}>
    <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "10px 12px", fontSize: 13, fontWeight: 600, color: C.text }}>
      <Icon name="chat" size={13} color={C.text} />消息
    </div>
    {items.map((c) => (
      <div key={c.name} style={{ display: "flex", gap: 9, padding: "8px 10px", margin: "0 4px", borderRadius: 6,
        background: c.name === active ? C.active : "transparent" }}>
        <div style={{ position: "relative" }}>
          <Avatar name={c.name} size={34} />
          {c.unread > 0 && <Badge n={c.unread} style={{ position: "absolute", top: -4, right: -6 }} />}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center" }}>
            <span style={{ fontSize: 12.5, color: C.text, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", minWidth: 0 }}>{c.name}</span>
            {c.bot && <BotTag />}
            <span style={{ marginLeft: "auto", paddingLeft: 6, flexShrink: 0, fontSize: 10, color: C.sub }}>{c.time}</span>
          </div>
          <div style={{ fontSize: 10.5, color: C.sub, marginTop: 3, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {c.preview}
          </div>
        </div>
      </div>
    ))}
  </div>
);

// ---------- 右边：消息 ----------
// 演员写的 "[表情:握手]" 换成真表情，认不出的就去掉
const EMOJI: Record<string, string> = { OK: "👌", 握手: "🤝", 奶茶: "🧋", 赞: "👍", 捂脸: "🤦", 加油: "💪", 微笑: "🙂", 哭: "😭", 拜托: "🙏", 庆祝: "🎉" };
export const emoji = (s: string) => s.replace(/\[表情[:：]([^\]]+)\]/g, (_, k: string) => EMOJI[k] ?? "");

const FILE = /^\[([^\]]+\.(?:xlsx|xls|csv|docx|pdf))\]\s*/;

const Bubble: React.FC<{ text: string; mine: boolean }> = ({ text, mine }) => {
  const file = text.match(FILE);
  const body = emoji(file ? text.slice(file[0].length) : text).trim();
  return (
    <>
      {file && (
        <div style={{ display: "flex", gap: 10, alignItems: "center", background: "#fff", border: "1px solid #DEE0E3",
          borderRadius: 8, padding: "10px 12px", width: 260 }}>
          <div style={{ width: 28, height: 34, borderRadius: 4, background: "#2EA121", color: "#fff", fontSize: 9,
            fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>XLS</div>
          <div>
            <div style={{ fontSize: 12.5, color: C.text }}>{file[1]}</div>
            <div style={{ fontSize: 10, color: C.sub, marginTop: 2 }}>Excel 文件</div>
          </div>
        </div>
      )}
      {body && (
        <div style={{ background: mine ? C.mine : C.bubble, borderRadius: 6, padding: "6px 10px", fontSize: 13, lineHeight: 1.6,
          color: C.text, whiteSpace: "pre-wrap", maxWidth: 520 }}>{body}</div>
      )}
    </>
  );
};

// 同一个人连续发的几条合成一组：只在第一条显示头像和名字。和飞书默认一样全部靠左，自己的是浅蓝气泡
export const MessageGroup: React.FC<{ sender: string; texts: { text: string; style: React.CSSProperties }[]; showName?: boolean }> = ({ sender, texts, showName = true }) => {
  const mine = sender === "我";
  return (
    <div style={{ display: "flex", gap: 10, padding: "6px 18px" }}>
      <Avatar name={sender} size={30} />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 6, minWidth: 0 }}>
        {!mine && showName && (
          <div style={{ display: "flex", alignItems: "center", fontSize: 11, color: C.name, height: 14 }}>
            {sender}
            {TITLES[sender] && <><BotTag /><span style={{ color: C.sub, marginLeft: 6 }}>{TITLES[sender]}</span></>}
          </div>
        )}
        {texts.map((t, i) => (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 6, ...t.style }}>
            <Bubble text={t.text} mine={mine} />
          </div>
        ))}
      </div>
    </div>
  );
};

export const TimeLabel: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ textAlign: "center", fontSize: 10.5, color: C.sub, padding: "8px 0 4px" }}>{text}</div>
);

export const ChatHeader: React.FC<{ name: string; members?: number; bot?: boolean }> = ({ name, members, bot }) => (
  <div style={{ height: 46, display: "flex", alignItems: "center", gap: 8, padding: "0 14px", borderBottom: `1px solid ${C.line}`, flexShrink: 0 }}>
    <Avatar name={name} size={26} />
    <span style={{ fontSize: 14, fontWeight: 600, color: C.text }}>{name}</span>
    {bot && <BotTag />}
    {members !== undefined && <span style={{ display: "flex", alignItems: "center", gap: 2, fontSize: 10.5, color: C.sub }}>
      <Icon name="member" size={11} color={C.sub} />{members}
    </span>}
    <div style={{ marginLeft: "auto", display: "flex", gap: 14 }}>
      {(["emoji", "search", "video", "member", "calendar", "dots"] as const).map((n) => <Icon key={n} name={n} size={14} />)}
    </div>
  </div>
);

export const InputBox: React.FC<{ to: string }> = ({ to }) => (
  <div style={{ margin: "8px 14px 12px", border: "1px solid #DEE0E3", borderRadius: 6, height: 36, display: "flex", flexShrink: 0,
    alignItems: "center", padding: "0 10px", fontSize: 12, color: "#BBBFC4" }}>
    发送给 {to}
    <div style={{ marginLeft: "auto", display: "flex", gap: 10 }}>
      {(["emoji", "at", "plus", "send"] as const).map((n) => <Icon key={n} name={n} size={14} color="#8F959E" />)}
    </div>
  </div>
);

// 别的会话来消息时，屏幕右上角弹出的系统通知（macOS 样式）
export const Toast: React.FC<{ chat: string; sender: string; text: string; style?: React.CSSProperties }> = ({ chat, sender, text, style }) => (
  <div style={{ width: 300, display: "flex", gap: 10, padding: "10px 12px", borderRadius: 14, background: "rgba(246,246,248,0.94)",
    boxShadow: "0 8px 28px rgba(0,0,0,0.18), 0 0 0 0.5px rgba(0,0,0,0.12)", backdropFilter: "blur(20px)", ...style }}>
    <Avatar name={chat} size={34} />
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ display: "flex", alignItems: "center" }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: C.text }}>{chat}</span>
        <span style={{ marginLeft: "auto", fontSize: 10, color: C.sub }}>现在</span>
      </div>
      <div style={{ fontSize: 11.5, color: "#3B3F45", marginTop: 2, lineHeight: 1.45, display: "-webkit-box",
        WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
        {chat === sender ? "" : `${sender}: `}{preview(text)}
      </div>
    </div>
  </div>
);

export const preview = (text: string) => emoji(text).replace(/^\[([^\]]+\.(?:xlsx|xls|csv|docx|pdf))\]\s*/, "[文件] $1 ").replace(/\n+/g, " ");
