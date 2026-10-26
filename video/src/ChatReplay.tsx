// 场景：按真实记录回放某一天某个群的聊天，最后弹出当天的手工工作量
import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, ChatHeader, setMeAvatar, Conv, ConvList, FONT, H, InputBox, MessageGroup, NavBar, TITLES, TimeLabel, Toast, W, preview } from "./feishu";

export type Msg = { time: string; group?: string; sender: string; text: string };
export type DayData = { day: number; meAvatar?: boolean; messages: Msg[]; dms: Record<string, Msg[]>; stats: { 追问?: number; 改表?: number } };

export type ChatReplayProps = {
  data: DayData;
  group: string;
  count: number; // 回放前几条
  every: number; // 每条间隔（帧）
  statsAt: number; // 第几帧弹出统计卡
};

const GROUPS: Record<string, number> = { "品牌项目组": 5, "小暖 S2 发布会筹备": 9 };
const mins = (t: string) => +t.slice(0, 2) * 60 + +t.slice(3, 5);

// 会话列表：按"现在"之前最后一条消息排序；回放开始后新来的算未读
function conversations(data: DayData, active: string, shown: Msg[], start: string, now: number): Conv[] {
  const items: (Conv & { key: number })[] = [];
  const add = (name: string, bot: boolean, msgs: Msg[]) => {
    const seen = msgs.filter((m) => mins(m.time) <= now);
    const last = seen[seen.length - 1];
    const unread = name === active ? 0 : seen.filter((m) => m.time > start && m.sender !== "我").length;
    items.push({ name, bot, unread, key: last ? mins(last.time) : -1,
      time: last ? last.time : "昨天",
      preview: last ? `${last.sender === "我" ? "" : last.sender + ": "}${preview(last.text)}` : "" });
  };
  // 当前群只算已经放出来的消息，别的会话按模拟时间算
  for (const g of Object.keys(GROUPS)) add(g, false, g === active ? shown : data.messages.filter((m) => m.group === g));
  for (const p of Object.keys(TITLES)) add(p, true, data.dms[p] ?? []);
  return items.sort((a, b) => b.key - a.key);
}

// 别的会话（另一个群、私聊）在回放这段时间里收到的同事消息：弹通知 + 响一声
function elsewhere(data: DayData, active: string): { chat: string; sender: string; text: string; t: number }[] {
  const out = data.messages.filter((m) => m.group !== active).map((m) => ({ chat: m.group!, sender: m.sender, text: m.text, t: mins(m.time) }));
  for (const [who, msgs] of Object.entries(data.dms)) out.push(...msgs.map((m) => ({ chat: who, sender: m.sender, text: m.text, t: mins(m.time) })));
  return out.filter((e) => e.sender !== "我").sort((a, b) => a.t - b.t);
}

export const ChatReplay: React.FC<ChatReplayProps> = ({ data, group, count, every, statsAt }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  setMeAvatar(!!data.meAvatar);
  const msgs = data.messages.filter((m) => m.group === group).slice(0, count);
  const n = msgs.filter((_, i) => frame >= i * every).length;
  // 模拟时钟：在相邻两条消息之间按帧线性走
  const T = msgs.map((m) => mins(m.time));
  const clockAt = (f: number) => {
    const i = Math.floor(f / every);
    return i >= T.length - 1 ? T[T.length - 1] : T[i] + ((T[i + 1] - T[i]) * (f - i * every)) / every;
  };
  const frameOf = (t: number) => {
    const i = T.findIndex((x, k) => k < T.length - 1 && x <= t && t < T[k + 1]);
    return i * every + (T[i + 1] === T[i] ? 0 : (every * (t - T[i])) / (T[i + 1] - T[i]));
  };
  const events = elsewhere(data, group).filter((e) => e.t > T[0] && e.t < T[T.length - 1]).map((e) => ({ ...e, at: Math.round(frameOf(e.t)) }));
  const convs = conversations(data, group, msgs.slice(0, n), msgs[0].time, clockAt(frame));

  // 连续同一个人的消息合成一组；间隔 30 分钟以上插一个时间
  const blocks: React.ReactNode[] = [];
  for (let i = 0; i < n; i++) {
    const m = msgs[i];
    if (i === 0 || mins(m.time) - mins(msgs[i - 1].time) >= 30) blocks.push(<TimeLabel key={`t${i}`} text={m.time} />);
    const texts = [];
    let j = i;
    for (; j < n && msgs[j].sender === m.sender && (j === i || mins(msgs[j].time) - mins(msgs[j - 1].time) < 30); j++) {
      const t = spring({ frame: frame - j * every, fps, config: { damping: 18 } });
      texts.push({ text: msgs[j].text, style: { opacity: t, transform: `translateY(${interpolate(t, [0, 1], [14, 0])}px)` } });
    }
    const t0 = spring({ frame: frame - i * every, fps, config: { damping: 18 } });
    blocks.push(<div key={i} style={{ opacity: t0 }}><MessageGroup sender={m.sender} texts={texts} /></div>);
    i = j - 1;
  }

  const card = spring({ frame: frame - statsAt, fps, config: { damping: 16 } });
  const unread = convs.reduce((s, c) => s + c.unread, 0);

  return (
    <AbsoluteFill style={{ background: C.bg }}>
      {/* 只有别的会话来消息才响（正在看的这个群不响） */}
      {events.filter((e, i) => i === 0 || e.at - events[i - 1].at > 15).map((e, i) => (
        <Sequence key={`s${i}`} from={e.at} durationInFrames={25}>
          <Audio src={staticFile("sfx/ding.wav")} volume={0.6} />
        </Sequence>
      ))}
      <div style={{ width: W, height: H, transform: `scale(${width / W})`, transformOrigin: "0 0", display: "flex", position: "relative",
        fontFamily: FONT, background: "linear-gradient(135deg, #EEF0F6, #E6EAF3)" }}>
        <NavBar unread={unread} />
        <ConvList items={convs} active={group} />
        <div style={{ flex: 1, background: C.panel, borderRadius: 8, margin: "4px 4px 4px 0", display: "flex", flexDirection: "column", minWidth: 0 }}>
          <ChatHeader name={group} members={GROUPS[group]} />
          {/* 和飞书一样：消息从顶部开始往下排，排满以后旧的从上面滚出去（column-reverse + marginBottom:auto） */}
          <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column-reverse", paddingBottom: 4 }}>
            <div style={{ marginBottom: "auto" }}>{blocks}</div>
          </div>
          <InputBox to={group} />
        </div>

        {/* 右上角通知：滑入，停 2.5 秒，淡出；同时有几条就往下排 */}
        <div style={{ position: "absolute", top: 14, right: 14, display: "flex", flexDirection: "column", gap: 8 }}>
          {events.filter((e, i) => frame >= e.at && frame < e.at + 90
              // 同一个会话只留最新一条（新的顶掉旧的），最多同时显示 2 条
              && !events.some((x, k) => k > i && x.chat === e.chat && frame >= x.at))
            .slice(-2).reverse().map((e) => {
            const t = spring({ frame: frame - e.at, fps, config: { damping: 20 } });
            const out = interpolate(frame - e.at, [75, 90], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            return <Toast key={e.chat} chat={e.chat} sender={e.sender} text={e.text}
              style={{ opacity: out, transform: `translateX(${interpolate(t, [0, 1], [340, 0])}px)` }} />;
          })}
        </div>
      </div>

      {frame >= statsAt && (
        <AbsoluteFill style={{ background: `rgba(31,35,41,${0.45 * card})`, alignItems: "center", justifyContent: "center", fontFamily: FONT }}>
          <div style={{ background: "#fff", borderRadius: 20, padding: "48px 72px", transform: `scale(${0.85 + 0.15 * card})`,
            opacity: card, textAlign: "center", boxShadow: "0 20px 60px rgba(0,0,0,0.25)" }}>
            <div style={{ fontSize: 26, color: C.sub }}>D{data.day} · 项目助理的手工活</div>
            <div style={{ display: "flex", gap: 80, marginTop: 28 }}>
              <Stat label="私聊追问" value={data.stats.追问 ?? 0} unit="条" />
              <Stat label="手动改表" value={data.stats.改表 ?? 0} unit="处" />
            </div>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

const Stat: React.FC<{ label: string; value: number; unit: string }> = ({ label, value, unit }) => (
  <div>
    <div style={{ fontSize: 96, fontWeight: 700, color: C.blue, lineHeight: 1 }}>
      {value}<span style={{ fontSize: 32, marginLeft: 8 }}>{unit}</span>
    </div>
    <div style={{ fontSize: 24, color: C.text, marginTop: 12 }}>{label}</div>
  </div>
);
