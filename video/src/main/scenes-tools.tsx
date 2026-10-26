// 正片第 5 段：把三个痛点逐个交给工具
import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { Avatar, MessageGroup, TimeLabel } from "../feishu";
import { Badge, Glyph, IconName } from "./icons";
import { Appear, C, Card, clamp, cue, GREEN, ORANGE, PURPLE, Scene, Sfx, Status, Tag, useIn } from "./kit";
import { Cursor, type SceneProps } from "./scenes-intro";
import { ChatHead, convAt, Focus, focusOf, K, MAIN, navAt, SEND, Shell, TableHead, tableAt } from "./shell";

// 结论先行：我在飞书上做的三个工具，各一句话说它管什么
export const ToolSet: React.FC<SceneProps> = () => {
  const TOOLS: [IconName, string, string, string][] = [
    ["report", "日报表单", "统一字段，汇报集中进表", GREEN],
    ["robot", "AI 进度助手", "找出要核对的，核实后批量改表", PURPLE],
    ["link", "自动提醒流程", "前置任务返工，马上提醒", C.blue],
  ];
  return (
    <Scene>
      <Appear at={0} style={{ fontSize: 48, fontWeight: 700, color: C.text, marginBottom: 60 }}>我在飞书上做了一套工具</Appear>
      <div style={{ display: "flex", gap: 44 }}>
        {TOOLS.map(([icon, name, what, color], i) => (
          <Appear key={name} at={30 + i * 22} dy={40}>
            <Card style={{ width: 480, height: 320, textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
              borderTop: `8px solid ${color}` }}>
              <Badge name={icon} bg={color} size={100} />
              <div style={{ fontSize: 44, fontWeight: 700, color: C.text, marginTop: 26 }}>{name}</div>
              <div style={{ fontSize: 28, color: C.name, marginTop: 14 }}>{what}</div>
            </Card>
          </Appear>
        ))}
      </div>
      {/* 分工提前说清楚：配置是我，代码是 AI */}
      <Appear at={30 + 3 * 22 + 10} style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 44, fontSize: 30, color: C.name,
        background: "#fff", borderRadius: 999, padding: "12px 34px", boxShadow: "0 6px 24px rgba(31,35,41,0.06)" }}>
        <Glyph name="person" size={30} color={C.blue} />表单和流程我在飞书里配 · 助手的代码由 AI 写，我提需求和验收
      </Appear>
    </Scene>
  );
};

// 三张痛点卡翻面变成三个方案
export const ToolsIntro: React.FC<SceneProps> = ({ dur }) => {
  const frame = useCurrentFrame();
  const TOOLS: [IconName, string, string, string, string][] = [
    ["report", "逐条收集", "结构化日报 + AI 进度助手", GREEN, "①"],
    ["robot", "手动改表", "AI 改表", PURPLE, "②"],
    ["link", "前置变更", "依赖联动提醒", C.blue, "③"],
  ];
  const WHO = ["需求：我拆解", "表单和工作流：我在飞书里配置", "代码：我和 AI"];
  return (
    <Scene>
      {TOOLS.map((_, i) => <Sfx key={i} at={dur * 0.3 + 6 + i * 10} name="whoosh" />)}
      <div style={{ display: "flex", gap: 44 }}>
        {TOOLS.map(([icon, pain, tool, color, n], i) => {
          const flip = interpolate(frame, [dur * 0.3 + i * 10, dur * 0.3 + 18 + i * 10], [0, 1], clamp);
          const back = flip > 0.5;
          return (
            <div key={pain} style={{ transform: `rotateY(${(back ? flip - 1 : flip) * 90}deg)` }}>
              <Card style={{ width: 460, height: 300, textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                borderTop: `8px solid ${back ? color : C.red}` }}>
                <Badge name={back ? icon : "warn"} bg={back ? color : C.red} size={96} />
                <div style={{ fontSize: 26, color: back ? color : C.red, fontWeight: 600, marginTop: 18 }}>{n} {back ? `解决「${pain}」` : "痛点"}</div>
                <div style={{ fontSize: 40, fontWeight: 700, color: C.text, marginTop: 8 }}>{back ? tool : pain}</div>
              </Card>
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", gap: 20, marginTop: 50 }}>
        {WHO.map((s, i) => (
          <Appear key={s} at={Math.round(dur * 0.5) + i * 20} sfx="tick" style={{ fontSize: 28, color: C.text, background: "#fff", borderRadius: 999, padding: "12px 28px" }}>{s}</Appear>
        ))}
      </div>
    </Scene>
  );
};

// 工具 2：按飞书里的真实配置重画（表单、提醒设置），日报表是真实的 6 条记录
const FIELDS: [string, boolean][] = [["提交人", true], ["关联任务", true], ["今日完成", true], ["进度", false], ["明日计划", false], ["卡点", false], ["交付物链接", true]];

const Toggle: React.FC<{ on: boolean }> = ({ on }) => (
  <div style={{ width: 44, height: 24, borderRadius: 12, background: on ? C.blue : "#D0D3D6", position: "relative", flexShrink: 0 }}>
    <div style={{ position: "absolute", top: 3, left: on ? 23 : 3, width: 18, height: 18, borderRadius: 9, background: "#fff" }} />
  </div>
);

const Form: React.FC<{ at: number }> = ({ at }) => (
  <div style={{ width: 620, background: "#fff", borderRadius: 18, overflow: "hidden", boxShadow: "0 10px 40px rgba(31,35,41,0.12)" }}>
    <div style={{ height: 60, background: "linear-gradient(110deg, #245BDB, #3370FF 60%, #7AA2FF)" }} />
    <div style={{ padding: "24px 36px 30px" }}>
      <div style={{ fontSize: 34, fontWeight: 700, color: C.text, textAlign: "center" }}>每日日报</div>
      <div style={{ fontSize: 19, color: C.name, textAlign: "center", marginTop: 8 }}>每天下班前填，2 分钟。填完自动进表，不用再在群里发日报。</div>
      {FIELDS.map(([f, req], i) => (
        <Appear key={f} at={at + i * 6} style={{ marginTop: 12 }}>
          <div style={{ display: "flex", alignItems: "center", fontSize: 21, color: C.text }}>
            {req && <span style={{ color: C.red, marginRight: 4 }}>*</span>}{f}
            <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, fontSize: 17, color: C.name }}><Toggle on={req} />必填</span>
          </div>
          <div style={{ height: 30, border: "1px solid #DEE0E3", borderRadius: 6, marginTop: 6, background: req ? "rgba(51,112,255,0.04)" : "#fff" }} />
        </Appear>
      ))}
    </div>
  </div>
);

const Settings: React.FC = () => (
  <div style={{ width: 620, background: "#fff", borderRadius: 18, padding: "30px 36px", boxShadow: "0 10px 40px rgba(31,35,41,0.12)" }}>
    <div style={{ fontSize: 30, fontWeight: 700, color: C.text, marginBottom: 14 }}>填写设置</div>
    {[["填写需登录验证", true], ["允许修改提交记录", true], ["有人提交后发送通知", false], ["定时发送填写通知", true]].map(([s, on]) => (
      <div key={s as string} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 26, color: C.text, padding: "14px 0", borderTop: `1px solid ${C.line}` }}>
        {s}<Toggle on={on as boolean} />
      </div>
    ))}
    <div style={{ background: "#F5F6F7", borderRadius: 10, padding: "16px 20px", fontSize: 26, color: C.text, lineHeight: 1.7 }}>
      发送时间：<b style={{ color: C.blue }}>17:30</b><br />重复频率：<b>每个工作日</b>
    </div>
  </div>
);

const ROWS: string[][] = [
  ["张伟", "D11", "", "发布会那边在执行统筹，供应商那边在跟。", "推进中", "无"],
  ["李想", "D11", "B11 小红书·倒计时 2 天；B09 公众号·发布会邀请", "B11 文案写完并交了，配图已同步给设计", "B11 文案 100%（已完成）；B09 文案 61%", "无"],
  ["陈悦", "D11", "B11 小红书·倒计时 2 天；A11 演讲 PPT 美化", "B11 配图做了一版出来；A11 美化在推进", "B11 配图 76%（需返工）；A11 32%", "B11 配图需要返工"],
  ["张伟", "D12", "A17 会后传播与线索整理", "会后传播和线索整理在弄，素材先归了一遍", "A17：推进中", "无"],
  ["李想", "D12", "B09 公众号·发布会邀请；B12 公众号·发布会预告", "B09 发布会邀请文案基本收尾了", "B09 文案 93%", "无"],
  ["陈悦", "D12", "A4 邀请函设计；B11；A11", "邀请函电子版设计已出；B11 配图已出", "A4 邀请函设计 100%", "无"],
];
const PERSON: Record<string, string> = { 张伟: "#D5F6F2", 李想: "#FFE8D1", 陈悦: "#E1EAFF" };
const COLS = "110px 90px 360px 420px 360px 180px";

const ReportTable: React.FC<{ at: number }> = ({ at }) => (
  <div style={{ background: "#fff", borderRadius: 18, overflow: "hidden", boxShadow: "0 10px 40px rgba(31,35,41,0.12)" }}>
    <div style={{ display: "grid", gridTemplateColumns: COLS, fontSize: 20, color: C.sub, background: "#FAFBFC", borderBottom: `1px solid ${C.line}` }}>
      {["提交人", "模拟日", "关联任务", "今日完成", "进度", "卡点"].map((h) => <div key={h} style={{ padding: "14px 16px" }}>{h}</div>)}
    </div>
    {ROWS.map((r, i) => (
      <Appear key={i} at={at + i * 8} dy={10} style={{ display: "grid", gridTemplateColumns: COLS, fontSize: 20, color: C.text, borderBottom: `1px solid ${C.line}` }}>
        {r.map((c, k) => (
          <div key={k} style={{ padding: "14px 16px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {k === 0 ? <span style={{ background: PERSON[c], borderRadius: 4, padding: "2px 8px" }}>{c}</span> : c}
          </div>
        ))}
      </Appear>
    ))}
  </div>
);

// 在飞书界面里走：点「多维表格」→ 点「日报表」→ 聚焦表单和提醒设置（说到"每天五点半"出提醒）→ 回到界面，日报表里一条条进记录
export const ToolReport: React.FC<SceneProps> = ({ dur, talk = dur }) => {
  const frame = useCurrentFrame();
  const F = (x: number) => Math.round(talk * x); // 跟着口播走，说完后画面停住
  const clickNav = F(0.05), clickTable = F(0.1), f1 = F(0.14), u1 = F(0.66);
  const focus = focusOf(frame, f1, u1);
  const inBase = frame >= clickNav;
  const clock = useIn(F(0.52));
  return (
    <Scene>
      <Shell nav={inBase ? "多维表格" : "消息"} active={inBase ? (frame >= clickTable ? "日报表" : undefined) : "张伟"} dim={focus}
        head={inBase ? (frame >= clickTable ? <TableHead name="日报表" /> : null) : <ChatHead name="张伟" />} to={inBase ? undefined : "张伟"}>
        {frame >= clickTable && (
          <div style={{ padding: "26px 30px", transform: "scale(0.9)", transformOrigin: "0 0" }}>
            <ReportTable at={u1 + 8} />
            <Appear at={u1 + 60} style={{ fontSize: 24, color: C.name, marginTop: 20 }}>上线后两天的真实记录 · 填完自动进表</Appear>
          </div>
        )}
      </Shell>
      <Focus on={focus}>
        <div style={{ position: "absolute", top: 60, fontSize: 30, color: GREEN, fontWeight: 600 }}>① 解决收集 · 结构化日报</div>
        <div style={{ display: "flex", gap: 50, alignItems: "flex-start", marginTop: 40, transform: "scale(0.92)" }}>
          <Form at={f1 + 6} />
          <div style={{ opacity: clock, transform: `translateY(${(1 - clock) * 30}px)` }}>
            <Settings />
            <div style={{ marginTop: 22, display: "flex", alignItems: "center", gap: 12, background: C.blue, color: "#fff", borderRadius: 999, padding: "12px 26px",
              fontSize: 28, fontWeight: 600, width: "fit-content" }}>
              <Glyph name="clock" size={32} color="#fff" detail={C.blue} />每个工作日 17:30 自动提醒
            </div>
          </div>
        </div>
      </Focus>
      <Cursor pts={[[2, 1000, 600], [clickNav, ...navAt("多维表格")], [clickTable, ...tableAt(1)], [f1 + 20, 1100, 700], [u1 + 10, 1300, 800]]} click={[clickNav, clickTable]} />
      <Tag text="表单按飞书里的真实配置重画 · 记录是真实的" style={{ bottom: 150, right: 60 }} />
    </Scene>
  );
};

// ---------- 工具 3：AI 进度助手 ----------
const BotAvatar: React.FC<{ size?: number }> = ({ size = 56 }) => <Badge name="robot" bg={PURPLE} size={size} round />;

// 在飞书界面里走：回到「消息」→ 说到"我提需求，让 AI 写代码"时聚焦开发过程（我提需求 → AI 写代码 → 进度助手）
// → 机器人头像飞进会话列表最上面 → 点开是空白会话（它也是个机器人）→ 聚焦：能读什么、能改什么、和模拟程序隔着一道墙
const Dev: React.FC<{ at: number; done: number }> = ({ at, done }) => {
  const frame = useCurrentFrame();
  const bar = interpolate(frame, [at + 20, done], [0, 1], clamp);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
      {([["person", C.blue, "我", "提需求、验收"], ["code", "#24292F", "AI", "写代码"]] as const).map(([icon, bg, who, what], i) => (
        <React.Fragment key={who}>
          {i > 0 && <Appear at={at + 8} style={{ fontSize: 56, color: C.sub }}>→</Appear>}
          <Appear at={at + i * 10} dy={20} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
            <Badge name={icon} bg={bg} size={150} round={i === 0} />
            <span style={{ fontSize: 32, fontWeight: 700, color: C.text }}>{who}</span>
            <span style={{ fontSize: 26, color: C.name }}>{what}</span>
          </Appear>
        </React.Fragment>
      ))}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14, width: 200 }}>
        <span style={{ fontSize: 26, color: C.sub }}>{bar < 1 ? "开发中…" : "完成"}</span>
        <div style={{ width: 200, height: 10, borderRadius: 5, background: "#E5E6EB", overflow: "hidden" }}>
          <div style={{ width: `${bar * 100}%`, height: "100%", background: PURPLE }} />
        </div>
      </div>
      <div style={{ width: 170, height: 220 }} />
    </div>
  );
};
export const Capability: React.FC<SceneProps> = ({ dur, talk = dur }) => {
  const frame = useCurrentFrame();
  const F = (x: number) => Math.round(talk * x); // 跟着口播走；口播说完后画面多停一会儿，让"隔离"看清楚
  const clickNav = F(0.04), dev = F(0.17), built = F(0.36), botIn = F(0.41), clickBot = F(0.47), f2 = F(0.54);
  const focus = Math.max(focusOf(frame, dev, botIn - 10), focusOf(frame, f2));
  const devOn = focusOf(frame, dev, botIn - 10);
  const Col: React.FC<{ at: number; title: string; items: [IconName, string][]; color: string }> = ({ at, title, items, color }) => (
    <Appear at={at} dy={30} sfx="pop">
      <Card style={{ width: 400 }}>
        <div style={{ fontSize: 34, fontWeight: 700, color }}>{title}</div>
        {items.map(([icon, s]) => <div key={s} style={{ fontSize: 32, color: C.text, marginTop: 18, display: "flex", alignItems: "center", gap: 14 }}><Glyph name={icon} size={36} color={color} />{s}</div>)}
      </Card>
    </Appear>
  );
  // 说到"完全隔离"：助手和它能碰的东西被框进一个容器（只连飞书），模拟程序在容器外、上锁，中间的连线被切断
  const box = interpolate(frame, [F(0.8), F(0.8) + 14], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const sim = useIn(F(0.85));
  const cut = interpolate(frame, [F(0.85) + 14, F(0.85) + 22], [0, 1], { ...clamp, easing: Easing.out(Easing.back(2)) });
  const motto = useIn(F(0.93));
  // 机器人头像：开发完成后出现在右边，聚焦退去时飞到会话列表第一行
  const born = useIn(built);
  const fly = interpolate(frame, [botIn - 12, botIn + 2], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const [x0, y0, s0] = [1305, 455, 170], [x1, y1, s1] = [(112 + 4 + 10) * K, (46 + 8) * K, 34 * K];
  const sz = s0 + (s1 - s0) * fly;
  const pop = interpolate(frame, [botIn, botIn + 8, botIn + 40], [0, 1, 0], clamp);
  const onBot = frame >= clickBot;
  return (
    <Scene>
      <Shell nav={frame >= clickNav ? "消息" : "多维表格"} active={frame >= clickNav ? (onBot ? "AI 进度助手" : undefined) : "日报表"} withBot={frame >= botIn} dim={focus}
        head={onBot ? <ChatHead name="AI 进度助手" bot /> : frame < clickNav ? <TableHead name="日报表" /> : null} to={onBot ? "AI 进度助手" : undefined}>
        {frame < clickNav && <div style={{ padding: "26px 30px", transform: "scale(0.9)", transformOrigin: "0 0" }}><ReportTable at={-100} /></div>}
      </Shell>
      <div style={{ position: "absolute", left: (112 + 4) * K, top: (42 + 4) * K, width: 242 * K, height: 50 * K, borderRadius: 8, background: `rgba(100,37,208,${0.18 * pop})` }} />
      <Focus on={devOn}><Dev at={dev} done={built} /></Focus>
      {frame >= built && frame < botIn + 2 && (
        <div style={{ position: "absolute", left: x0 + (x1 - x0) * fly, top: y0 + (y1 - y0) * fly, opacity: born, transform: `scale(${0.6 + 0.4 * born})` }}>
          <BotAvatar size={sz} />
        </div>
      )}
      <Focus on={focusOf(frame, f2)}>
        <div style={{ display: "flex", alignItems: "center", gap: 50, marginTop: -150 }}>
          <Col at={F(0.58)} title="读" items={[["group", "群聊"], ["report", "日报"], ["table", "任务表"]]} color={C.blue} />
          <Appear at={F(0.58)} style={{ fontSize: 60, color: C.sub }}>→</Appear>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 18 }}>
            <BotAvatar size={170} />
            <div style={{ fontSize: 40, fontWeight: 700, color: C.text }}>AI 进度助手</div>
            <div style={{ fontSize: 26, color: C.sub }}>也是一个飞书机器人</div>
          </div>
          <Appear at={F(0.71)} style={{ fontSize: 60, color: C.sub }}>→</Appear>
          <Col at={F(0.71) + 6} title="改" items={[["table", "任务表"]]} color={PURPLE} />
        </div>
        {/* 容器：框住"读 → 助手 → 改" */}
        <div style={{ position: "absolute", left: 150, top: 215, width: 1620, height: 420, borderRadius: 32, border: `4px solid rgba(100,37,208,${0.55 * box})`,
          background: `rgba(100,37,208,${0.04 * box})`, transform: `scale(${1.06 - 0.06 * box})`, opacity: box }}>
          <div style={{ position: "absolute", top: -26, left: 40, display: "flex", alignItems: "center", gap: 10, background: PURPLE, color: "#fff", borderRadius: 999,
            padding: "8px 24px", fontSize: 26, fontWeight: 600 }}>
            <Glyph name="lock" size={26} color="#fff" detail={PURPLE} />助手的运行环境 · 只有飞书权限
          </div>
        </div>
        {/* 容器外：模拟程序（上锁），和容器之间的连线被切断 */}
        <div style={{ position: "absolute", top: 640, left: 0, right: 0, display: "flex", flexDirection: "column", alignItems: "center", opacity: sim }}>
          <svg width={40} height={84}>
            <path d="M20 4 V80" stroke="#A9AEB5" strokeWidth={4} strokeDasharray="10 8" />
          </svg>
          <div style={{ position: "absolute", top: 10, width: 64, height: 64, borderRadius: "50%", background: C.red, display: "flex", alignItems: "center", justifyContent: "center",
            transform: `scale(${cut})`, boxShadow: "0 4px 14px rgba(245,74,69,0.4)" }}>
            <Glyph name="cross" size={40} color="#fff" />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 18, background: "#E5E6EB", borderRadius: 18, padding: "16px 30px", transform: `translateY(${(1 - sim) * 20}px)` }}>
            <Glyph name="lock" size={40} color="#8F959E" detail="#E5E6EB" />
            <div>
              <div style={{ fontSize: 30, fontWeight: 700, color: "#4E5969" }}>模拟程序</div>
              <div style={{ fontSize: 24, color: C.sub, marginTop: 2 }}>剧本、人设、真实进度存档</div>
            </div>
          </div>
        </div>
        <div style={{ position: "absolute", top: 850, fontSize: 40, fontWeight: 700, color: C.text, opacity: motto, transform: `translateY(${(1 - motto) * 16}px)` }}>
          完全隔离：<span style={{ color: PURPLE }}>只有权限，没有剧本</span>
        </div>
      </Focus>
      <Cursor pts={[[2, 1100, 600], [clickNav, ...navAt("消息")], [dev, 900, 800], [botIn + 4, 700, 500], [clickBot, ...convAt(0)], [f2, 1000, 600], [F(0.8), 1780, 760]]} click={[clickNav, clickBot]} />
    </Scene>
  );
};

// 简化的飞书私聊窗口
const Window: React.FC<{ children: React.ReactNode; width?: number }> = ({ children, width = 1300 }) => (
  <div style={{ width, background: "#fff", borderRadius: 18, boxShadow: "0 10px 40px rgba(31,35,41,0.12)", overflow: "hidden" }}>
    <div style={{ height: 70, display: "flex", alignItems: "center", gap: 14, padding: "0 26px", borderBottom: `1px solid ${C.line}` }}>
      <BotAvatar size={40} />
      <span style={{ fontSize: 26, fontWeight: 600, color: C.text }}>AI 进度助手</span>
      <span style={{ fontSize: 16, color: "#C17D00", background: "#FFF1CC", borderRadius: 4, padding: "2px 6px" }}>机器人</span>
    </div>
    <div style={{ padding: "18px 26px 26px", display: "flex", flexDirection: "column", gap: 18 }}>{children}</div>
  </div>
);

const Me: React.FC<{ at: number; children: React.ReactNode }> = ({ at, children }) => (
  <Appear at={at} sfx="pop" style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
    <Avatar name="我" size={48} />
    <div style={{ background: C.mine, borderRadius: 10, padding: "12px 18px", fontSize: 30, color: C.text, lineHeight: 1.6 }}>{children}</div>
  </Appear>
);

const Bot: React.FC<{ at: number; children: React.ReactNode }> = ({ at, children }) => (
  <Appear at={at} sfx="notify" style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
    <BotAvatar size={48} />
    <div style={{ background: C.bubble, borderRadius: 10, padding: "16px 22px", fontSize: 24, color: C.text, lineHeight: 1.6, flex: 1 }}>{children}</div>
  </Appear>
);

// 结论段的操作证据：问一句 / 核实完说一句 / 返工马上提醒，三个真实记录的节选（和后面 AskChat、EditChat、ToolDependency 同源）
const ProofCard: React.FC<{ at: number; oldAt: number; old: [string, React.ReactNode]; n: string; title: string; color: string; children: React.ReactNode }> = ({ at, oldAt, old, n, title, color, children }) => {
  const frame = useCurrentFrame();
  const gone = interpolate(frame, [at - 8, at], [0, 1], clamp); // 新做法的卡片出来时，原来的做法淡出
  const box = (c: string): React.CSSProperties => ({ background: "#fff", borderRadius: 18, boxShadow: "0 10px 40px rgba(31,35,41,0.12)", padding: 26, minHeight: 330,
    display: "flex", flexDirection: "column", gap: 16, borderTop: `8px solid ${c}` });
  return (
    <div style={{ width: 570, position: "relative" }}>
      <Appear at={oldAt} dy={30} style={{ position: "absolute", left: 0, right: 0, top: 0, opacity: 1 - gone }}>
        <div style={{ fontSize: 34, fontWeight: 700, color: C.text, marginBottom: 16, textAlign: "center" }}>{old[0]}</div>
        <div style={box("#C9CDD4")}>{old[1]}</div>
      </Appear>
      <Appear at={at} dy={40}>
        <div style={{ fontSize: 34, fontWeight: 700, color, marginBottom: 16, textAlign: "center" }}>{n} {title}</div>
        <div style={box(color)}>{children}</div>
      </Appear>
    </div>
  );
};
// 以前的做法：每张卡片里几行例子依次冒出来（口播很快带过，间隔要短）
const OldRows: React.FC<{ at: number; rows: React.ReactNode[]; foot: string }> = ({ at, rows, foot }) => (
  <>
    {rows.map((r, i) => <Appear key={i} at={at + 4 + i * 5} dy={8} style={{ fontSize: 24, color: C.text, lineHeight: 1.45 }}>{r}</Appear>)}
    <Appear at={at + 4 + rows.length * 5} style={{ fontSize: 23, color: C.sub, marginTop: "auto" }}>{foot}</Appear>
  </>
);
const Src: React.FC<{ s: string }> = ({ s }) => (
  <span style={{ fontSize: 19, color: C.name, background: "#F2F3F5", borderRadius: 5, padding: "2px 8px", marginRight: 10 }}>{s}</span>
);
const Mine: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
    <Avatar name="我" size={44} />
    <div style={{ background: C.mine, borderRadius: 10, padding: "10px 16px", fontSize: 28, color: C.text, lineHeight: 1.5 }}>{children}</div>
  </div>
);
const Reply: React.FC<{ at: number; children: React.ReactNode }> = ({ at, children }) => (
  <Appear at={at} sfx="notify" style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
    <BotAvatar size={44} />
    <div style={{ background: C.bubble, borderRadius: 10, padding: "12px 16px", fontSize: 27, color: C.text, lineHeight: 1.55, flex: 1 }}>{children}</div>
  </Appear>
);
export const Proof: React.FC<SceneProps> = ({ dur, talk = dur, text }) => {
  const F = (x: number) => Math.round(dur * x);
  const a = cue(text, "现在，日报表单", talk), b = cue(text, "AI 助手帮我", talk), c = cue(text, "前置任务一返工", talk);
  const o1 = cue(text, "翻记录", talk), o2 = cue(text, "对进度", talk), o3 = cue(text, "改表格", talk);
  const red = (t: string) => <b style={{ color: "#D83931", marginLeft: 8 }}>{t}</b>;
  return (
    <Scene>
      {/* 每列先出一张"以前怎么做"的例子卡（口播说"翻记录、对进度、改表格"时），讲到对应的工具时换成新卡片 */}
      <div style={{ display: "flex", gap: 30, marginTop: 20 }}>
        <ProofCard at={a} oldAt={o1} old={["翻记录", <OldRows at={o1} foot="往上还有 34 条未读……" rows={[
          <><Src s="群聊" />李想：文案差不多了</>, <><Src s="私聊" />陈悦：配图还在改</>, <><Src s="简报" />B09 公众号，文案九成</>, <><Src s="私聊" />周涛：PPT 发你了</>]} />]} n="①" title="日报表单：汇报收进一张表" color={GREEN}>
          <div style={{ borderRadius: 10, overflow: "hidden", border: `1px solid ${C.line}`, fontSize: 23 }}>
            {[["提交人", "关联任务", "进度"], ["李想", "B11 小红书", "文案 100%"], ["陈悦", "B11 小红书", "配图 76%"], ["李想", "B09 公众号", "文案 93%"]].map((r, i) => (
              <Appear key={i} at={a + 8 + i * 6} dy={8} style={{ display: "grid", gridTemplateColumns: "90px 1fr 120px", padding: "9px 14px",
                background: i ? "#fff" : "#FAFBFC", color: i ? C.text : C.sub, borderTop: i ? `1px solid ${C.line}` : "none" }}>
                {r.map((c) => <span key={c}>{c}</span>)}
              </Appear>
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 23, color: C.name }}>
            <Glyph name="clock" size={28} color={GREEN} detail="#fff" />每天 17:30 自动提醒填写
          </div>
        </ProofCard>
        <ProofCard at={b} oldAt={o2} old={["对进度", <OldRows at={o2} foot="一条一条问、一条一条对" rows={[
          <b>A10 演讲 PPT</b>, <span style={{ color: C.name }}>群里：王丽说以周涛这版为准</span>, <>表上：<Status s="待审核" size={21} />{red("对不上？")}</>,
          <b>A14 直播方案</b>, <>表上：<Status s="待审核" size={21} />{red("过了没？")}</>]} />]} n="②" title="AI 助手：对进度、批量改表" color={PURPLE}>
          <Mine>帮我看看要核对哪些</Mine>
          <Reply at={b + 12}>
            <div style={{ fontSize: 23 }}><b>A10 演讲 PPT</b> 待审核 → 已完成？</div>
            <div style={{ color: C.name, fontSize: 21 }}>依据：周涛 11:06 交稿，王丽 11:14 说以他这版为准</div>
          </Reply>
          <Appear at={b + 34}><Mine>KV 过了，A14、A10 可以完成了……</Mine></Appear>
          <Reply at={b + 50}><div style={{ fontSize: 23 }}>改好了，4 条，每格列出改前改后</div></Reply>
        </ProofCard>
        <ProofCard at={c} oldAt={o3} old={["改表格", <OldRows at={o3} foot="前面的改回了，还得挨个去通知后面的人" rows={[
          <>A14 直播方案 <Status s="待审核" size={21} /> → <Status s="已完成" size={21} /></>, <>A10 演讲 PPT <Status s="待审核" size={21} /> → <Status s="已完成" size={21} /></>,
          <>A6 主视觉 KV <Status s="已完成" size={21} /> → <Status s="进行中" size={21} /></>, <span style={{ color: C.name }}>一格一格点开，手动改</span>]} />]} n="③" title="自动提醒：返工马上知道" color={C.blue}>
          <Appear at={c + 10} sfx="notify" style={{ borderRadius: 12, overflow: "hidden", border: `1px solid ${C.line}` }}>
            <div style={{ background: "linear-gradient(90deg, #F1EAFE, #F8F5FF)", padding: "14px 18px", fontSize: 27, fontWeight: 700, color: "#6425D0", display: "flex", alignItems: "center", gap: 10 }}>
              <Glyph name="warn" size={28} color={ORANGE} />前置任务被改回，后置任务受影响
            </div>
            <div style={{ padding: "14px 18px", fontSize: 26, color: C.text, lineHeight: 1.6 }}>
              <div>1 个前置任务被改回</div>
              <div style={{ fontSize: 30, fontWeight: 700, marginTop: 6 }}>9 个后置任务自动标记</div>
            </div>
          </Appear>
        </ProofCard>
      </div>
      <Appear at={c + 40} style={{ marginTop: 44, fontSize: 36, fontWeight: 700, color: C.text }}>重复的活交给工具，判断留给我</Appear>
      <Tag text="按真实记录重建 · 节选" style={{ bottom: 150, right: 60 }} />
    </Scene>
  );
};

// 原话节选（ai-assistant/data/对话.json 第 4 条，11-16 17:25）
// 在飞书界面的助手私聊里：我点发送 → 回复分两组出现 → A14 那行亮一下 → 聚焦：依据（谁、几点、原话）→ 对比「过了」和「看完的」
export const AskChat: React.FC<SceneProps> = ({ dur }) => {
  const frame = useCurrentFrame();
  const F = (x: number) => Math.round(dur * x);
  const sendAt = F(0.03), zoomAt = F(0.5), cmpAt = F(0.78);
  const focus = focusOf(frame, zoomAt);
  const zoom = interpolate(frame, [zoomAt, zoomAt + 12, cmpAt, cmpAt + 10], [0, 1, 1, 0], clamp);
  const cmp = interpolate(frame, [cmpAt, cmpAt + 12], [0, 1], clamp);
  const hl = interpolate(frame, [zoomAt - 24, zoomAt - 14], [0, 1], clamp); // 聚焦前，A14 那一行先亮起来
  const Item: React.FC<{ id: string; a: string; b: string; ask?: boolean; hl?: number }> = ({ id, a, b, ask, hl = 0 }) => (
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 6, borderRadius: 8, padding: "2px 8px", margin: "6px -8px 0",
      boxShadow: `0 0 0 ${3 * hl}px ${GREEN}`, background: `rgba(46,161,33,${0.08 * hl})` }}>
      <b>{id}</b><Status s={a} size={20} /><span>→</span><Status s={b} size={20} />
      {ask && <span style={{ fontSize: 20, color: "#fff", background: ORANGE, borderRadius: 6, padding: "1px 10px" }}>先问一句</span>}
    </div>
  );
  const Src: React.FC<{ k: string; v: string; at: number }> = ({ k, v, at }) => (
    <Appear at={at} dx={-20} dy={0} style={{ display: "flex", alignItems: "baseline", gap: 18, marginTop: 14 }}>
      <span style={{ width: 70, fontSize: 24, color: "#fff", background: GREEN, borderRadius: 8, textAlign: "center", padding: "2px 0" }}>{k}</span>
      <span style={{ fontSize: 32, color: C.text, fontWeight: 600 }}>{v}</span>
    </Appear>
  );
  return (
    <Scene>
      <Shell active="AI 进度助手" withBot head={<ChatHead name="AI 进度助手" bot />} to="AI 进度助手" dim={focus}>
        <div style={{ padding: "24px 34px", display: "flex", flexDirection: "column", gap: 22, width: 1100 }}>
          <Me at={sendAt}>帮我看看要核对哪些</Me>
          <Bot at={F(0.14)}>
            <div>看了今天最新的群聊（到 16:46），有几条状态跟表里对不上。按「能直接改」和「得先问人」分开：</div>
            <Appear at={F(0.3)}>
              <div style={{ fontWeight: 700, marginTop: 12, color: GREEN }}>一、今天下午已有结论，表该跟着改（等你点头）</div>
              <Item id="A14 直播方案" a="待审核" b="已完成" hl={hl} />
              <Item id="A10 演讲 PPT 内容" a="待审核" b="已完成" />
              <Item id="A6 主视觉 KV" a="进行中" b="已完成" ask />
            </Appear>
            <Appear at={F(0.38)}>
              <div style={{ fontWeight: 700, marginTop: 12, color: ORANGE }}>二、得先核实的（信息冲突或没人接）</div>
              <div style={{ color: C.name }}>A11 PPT 美化 · B11 · A8 物料印刷 · A5 回执统计 ……</div>
            </Appear>
          </Bot>
        </div>
      </Shell>
      <Focus on={focus}>
        {/* 依据 */}
        <div style={{ position: "absolute", width: 1000, opacity: zoom, transform: `scale(${0.94 + 0.06 * zoom})` }}>
          <Card style={{ borderTop: `8px solid ${GREEN}`, padding: "40px 50px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 42, fontWeight: 700, color: C.text }}>A14 直播方案<Status s="待审核" size={28} />→<Status s="已完成" size={28} /></div>
            <div style={{ fontSize: 28, color: C.sub, marginTop: 24 }}>依据</div>
            <Src k="谁" v="王丽（组长）" at={zoomAt + 12} />
            <Src k="几点" v="15:40 · 发布会群" at={zoomAt + 22} />
            <Src k="原话" v="「直播方案过了」" at={zoomAt + 32} />
          </Card>
        </div>
        {/* 过了 vs 看完的 */}
        <div style={{ position: "absolute", width: 1100, opacity: cmp, transform: `scale(${0.94 + 0.06 * cmp})` }}>
          <div style={{ fontSize: 44, fontWeight: 800, color: C.text, marginBottom: 28, textAlign: "center" }}>别把「看过」当「通过」</div>
          {([["「直播方案过了」", "明说通过", "可以改", GREEN, "check"], ["「KV 流程稿一起看完的」", "只说看完", "先问一句", ORANGE, "warn"]] as const).map(([q, what, act, color, icon], i) => (
            <Appear key={q} at={cmpAt + 8 + i * 14} dy={20}>
              <Card style={{ display: "flex", alignItems: "center", gap: 22, padding: "26px 32px", marginTop: i ? 20 : 0, borderLeft: `8px solid ${color}` }}>
                <Glyph name={icon} size={46} color={color} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 34, fontWeight: 700, color: C.text }}>{q}</div>
                  <div style={{ fontSize: 24, color: C.sub, marginTop: 6 }}>王丽 15:40 · {what}</div>
                </div>
                <div style={{ fontSize: 32, fontWeight: 700, color }}>{act}</div>
              </Card>
            </Appear>
          ))}
        </div>
      </Focus>
      <Cursor pts={[[0, 1500, 900], [sendAt, ...SEND], [sendAt + 30, 1300, 700], [zoomAt - 20, 760, 470]]} click={[sendAt]} />
      <Tag text="按真实对话记录重建 · 节选" style={{ bottom: 150, right: 60 }} />
    </Scene>
  );
};

// 任务表（在飞书界面里画，1080p 原尺寸）：rows = [任务, 状态, 截止日期]；hot：正在改的行号；cell：状态格里显示什么
export const TASK_X = MAIN.x + 40, TASK_Y = MAIN.y + 40, TASK_RH = 92;
export const TaskTable: React.FC<{ rows: [string, string, string][]; render?: (i: number) => { status?: React.ReactNode; date?: React.ReactNode; bg?: string; outline?: string; extra?: React.ReactNode } }> = ({ rows, render }) => (
  <div style={{ margin: 40, width: 1100, background: "#fff", borderRadius: 14, border: `1px solid ${C.line}`, boxShadow: "0 6px 24px rgba(31,35,41,0.06)" }}>
    <div style={{ display: "grid", gridTemplateColumns: "560px 280px 1fr", fontSize: 22, color: C.sub, background: "#FAFBFC", height: 60, alignItems: "center", padding: "0 30px", borderBottom: `1px solid ${C.line}`, borderRadius: "14px 14px 0 0" }}>
      <span>任务</span><span>状态</span><span>截止日期</span>
    </div>
    {rows.map(([name, st, date], i) => {
      const r = render?.(i) ?? {};
      return (
        <div key={name} style={{ display: "grid", gridTemplateColumns: "560px 280px 1fr", alignItems: "center", height: TASK_RH, padding: "0 30px", position: "relative",
          borderBottom: i < rows.length - 1 ? `1px solid ${C.line}` : "none", background: r.bg ?? "#fff", outline: r.outline, outlineOffset: -3, zIndex: r.extra ? 5 : 1 }}>
          <span style={{ fontSize: 28, color: C.text }}>{name}</span>
          <span>{r.status ?? (st ? <Status s={st} size={26} /> : <span style={{ fontSize: 24, color: C.sub }}>（空）</span>)}</span>
          <span style={{ fontSize: 26, color: C.text }}>{r.date ?? date}</span>
          {r.extra}
        </div>
      );
    })}
  </div>
);

// 痛点 ②：以前全靠手动。在飞书界面里：群里陈悦说"主视觉KV定稿了"（第 10 天原话）→ 点开任务表，A6 还是"进行中"
// → 鼠标一格一格点开下拉框去改（示意）→ 改完还要去群里通知
const OPTS = ["进行中", "待审核", "已完成", "阻塞"];
const HAND: [string, string, string][] = [["A6 主视觉 KV 与现场物料设计", "进行中", "已完成"], ["A9 发布会流程与主持稿", "", "待审核"], ["A14 直播方案", "进行中", "待审核"]];
const HAND_ROWS: [string, string, string][] = [...HAND.map(([n, a]): [string, string, string] => [n, a, "—"]), ["A10 演讲 PPT 内容", "待审核", "—"], ["A12 新闻通稿", "进行中", "—"]];
export const EditByHand: React.FC<SceneProps> = ({ dur }) => {
  const frame = useCurrentFrame();
  const F = (x: number) => Math.round(dur * x);
  const clickGroup = F(0.2), mark = F(0.38), clickNav = F(0.48), clickTable = F(0.53);
  const t0 = F(0.62); // 口播说到"一格一格点开去改"前一点开始点
  const step = (F(0.9) - t0) / HAND.length;
  const notify = useIn(F(0.88));
  const nav = frame >= clickNav ? "多维表格" : "消息";
  const inTable = frame >= clickTable;
  const hl = interpolate(frame, [mark, mark + 8], [0, 1], clamp);
  const statusX = TASK_X + 30 + 560 + 40, rowY = (i: number) => TASK_Y + 60 + i * TASK_RH;
  return (
    <Scene>
      <Sfx at={F(0.88)} name="pop" />
      <Shell nav={nav} active={nav === "多维表格" ? (inTable ? "任务表" : undefined) : frame >= clickGroup ? "品牌项目组" : "AI 进度助手"} withBot
        head={nav === "多维表格" ? (inTable ? <TableHead name="任务表" /> : null) : frame >= clickGroup ? <ChatHead name="品牌项目组" members={5} /> : <ChatHead name="AI 进度助手" bot />}
        to={nav === "消息" ? (frame >= clickGroup ? "品牌项目组" : "AI 进度助手") : undefined}>
        {nav === "消息" && frame >= clickGroup && (
          <div style={{ transform: `scale(${K * 1.15})`, transformOrigin: "0 0", width: 720, paddingTop: 40 }}>
            <TimeLabel text="第 10 天 10:52" />
            <div style={{ borderRadius: 8, margin: "0 12px", boxShadow: `0 0 0 ${2 * hl}px ${ORANGE}`, background: `rgba(227,115,24,${0.06 * hl})` }}>
              <MessageGroup sender="陈悦" texts={[{ text: "主视觉KV定稿了", style: {} }]} />
            </div>
          </div>
        )}
        {inTable && (
          <TaskTable rows={HAND_ROWS} render={(i) => {
            if (i >= HAND.length) return {};
            const [, a, b] = HAND[i];
            const at = t0 + i * step;
            const open = frame >= at + 11 && frame < at + 28;
            const done = frame >= at + 28;
            const stale = i === 0 && frame < at; // A6：群里说定稿了，表上还是进行中
            return {
              bg: open || (frame >= at && frame < at + 40) ? "#FFFBE6" : stale ? "#FFF1F0" : undefined,
              outline: stale ? `3px solid ${C.red}` : undefined,
              status: <span style={{ outline: open ? `2px solid ${C.blue}` : "none", borderRadius: 6, padding: 4 }}>{(done ? b : a) ? <Status s={done ? b : a} size={26} /> : <span style={{ fontSize: 24, color: C.sub }}>（空）</span>}</span>,
              date: stale ? <span style={{ color: ORANGE, fontSize: 24 }}>截止已过 2 天</span> : undefined,
              extra: open && (
                <div style={{ position: "absolute", left: 590, top: TASK_RH - 10, zIndex: 5, background: "#fff", borderRadius: 10, boxShadow: "0 8px 30px rgba(0,0,0,0.18)", padding: 10, display: "flex", flexDirection: "column", gap: 8 }}>
                  {OPTS.map((s) => <div key={s} style={{ padding: "4px 8px", background: s === b && frame >= at + 21 ? "#EAF1FF" : "transparent", borderRadius: 6 }}><Status s={s} size={22} /></div>)}
                </div>
              ),
            };
          }} />
        )}
      </Shell>
      {/* 先点状态格，再点下拉框里要选的那一项（下拉选项间隔 48） */}
      <Cursor pts={[[2, 1100, 700], [clickGroup, ...convAt(1)], [mark, 760, 200], [clickNav, ...navAt("多维表格")], [clickTable, ...tableAt(0)],
        ...HAND.flatMap(([, , b], i): [number, number, number][] => {
          const at = t0 + i * step, k = OPTS.indexOf(b);
          return [[at + 8, statusX, rowY(i) + 40], [at + 22, statusX + 10, rowY(i) + 108 + k * 48]];
        }), [F(0.92), 1120, 880]]} move={10}
        click={[clickGroup, clickNav, clickTable, ...HAND.flatMap((_, i) => [Math.round(t0 + i * step + 10), Math.round(t0 + i * step + 24)])]} />
      <div style={{ position: "absolute", bottom: 170, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: notify }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 30, color: C.text, background: "#fff", borderRadius: 999, padding: "12px 30px", boxShadow: "0 6px 24px rgba(31,35,41,0.12)" }}>
          <Glyph name="group" size={32} color={C.blue} />改完，还要去群里通知相关的人
        </div>
      </div>
      <Tag text="群消息是原话 · 改表操作是示意" style={{ bottom: 150, right: 60 }} />
    </Scene>
  );
};

// 一句话改四处（改表记录.jsonl，11-16 17:25）。在飞书界面里：回到助手私聊发一句 → 它回复改了哪四格 → 点开任务表，四格已经变了
export const EditChat: React.FC<SceneProps> = ({ dur, talk = dur, text }) => {
  const frame = useCurrentFrame();
  const F = (x: number) => Math.round(talk * x);
  // 说到"我还给它定了规矩"：聚焦一段真实对话（11-18），它自己推断的那条没改，先问我
  const ruleAt = cue(text, "我还给它定了规矩", talk);
  const rule = focusOf(frame, ruleAt - 6);
  const mark = interpolate(frame, [ruleAt + 40, ruleAt + 58], [0, 1], clamp);
  const Code: React.FC<{ c: string; label: string; at: number }> = ({ c, label, at }) => {
    const t = useIn(at);
    return (
      <span style={{ position: "relative", display: "inline-block" }}>
        {c}
        <span style={{ position: "absolute", left: "50%", top: -40, transform: `translateX(-50%) scale(${t})`, opacity: t, whiteSpace: "nowrap",
          fontSize: 20, background: PURPLE, color: "#fff", borderRadius: 6, padding: "2px 10px" }}>{label}</span>
      </span>
    );
  };
  const EDITS: [string, string, string, string][] = [
    ["A6 主视觉 KV", "状态", "进行中", "已完成"],
    ["A10 演讲 PPT 内容", "状态", "待审核", "已完成"],
    ["A14 直播方案", "状态", "待审核", "已完成"],
    ["B11 小红书·倒计时 2 天", "截止日期", "11-16", "11-17"],
  ];
  const clickNav0 = F(0.02), clickBot = F(0.06), sendAt = F(0.1), r0 = F(0.42), clickNav = F(0.53), clickTable = F(0.57);
  const nav = frame >= clickNav ? "多维表格" : frame >= clickNav0 ? "消息" : "多维表格";
  const inTable = nav === "多维表格" && (frame >= clickTable || frame < clickNav0);
  const ROWS4: [string, string, string][] = [["A6 主视觉 KV 与现场物料设计", "进行中", "—"], ["A10 演讲 PPT 内容", "待审核", "—"], ["A14 直播方案", "待审核", "—"], ["B11 小红书·倒计时 2 天", "", "11-16"], ["A12 新闻通稿", "进行中", "—"]];
  return (
    <Scene>
      <Shell nav={nav} active={nav === "多维表格" ? (inTable ? "任务表" : undefined) : frame >= clickBot ? "AI 进度助手" : undefined} withBot dim={rule}
        head={nav === "多维表格" ? (inTable ? <TableHead name="任务表" /> : null) : frame >= clickBot ? <ChatHead name="AI 进度助手" bot /> : null}
        to={nav === "消息" && frame >= clickBot ? "AI 进度助手" : undefined}>
        {nav === "消息" && frame >= clickBot && (
          <div style={{ padding: "60px 34px 24px", display: "flex", flexDirection: "column", gap: 22, width: 1100 }}>
            <Me at={sendAt}>
              <Code c="KV" label="主视觉" at={sendAt + 14} /> 过了，然后 <Code c="A14" label="直播方案" at={sendAt + 22} /> 以及 <Code c="A10" label="演讲 PPT" at={sendAt + 30} /> 可以完成了，帮我改一下。<Code c="B11" label="小红书" at={sendAt + 38} /> 明天发。其他的先不动
            </Me>
            <Bot at={r0}>
              <div>改好了，4 条：</div>
              {EDITS.map(([task, field, a, b], i) => (
                <Appear key={task} at={r0 + 14 + i * 12} sfx="tick" style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 10, fontSize: 26 }}>
                  <b style={{ width: 340 }}>{task}</b>
                  <span style={{ color: C.sub, width: 110 }}>{field}</span>
                  {field === "状态" ? <Status s={a} /> : <span>{a}</span>}
                  <span style={{ color: C.sub }}>→</span>
                  {field === "状态" ? <Status s={b} /> : <b style={{ color: C.blue }}>{b}</b>}
                </Appear>
              ))}
              <Appear at={r0 + 70} sfx="chime" style={{ marginTop: 12, color: C.name }}>其他都没动。</Appear>
            </Bot>
          </div>
        )}
        {inTable && (
          <TaskTable rows={ROWS4} render={(i) => {
            if (i >= EDITS.length || frame < clickNav0) return i === 3 ? { status: <span style={{ fontSize: 24, color: C.sub }}>—</span> } : {};
            const t = interpolate(frame, [clickTable + 10 + i * 12, clickTable + 20 + i * 12], [0, 1], clamp);
            const [, field, a, b] = EDITS[i];
            const cell = (v: string) => field === "状态" ? <Status s={v} size={26} /> : <b style={{ color: t > 0.5 ? C.blue : C.text }}>{v}</b>;
            const shown = t > 0.5 ? b : a;
            return {
              bg: `rgba(46,161,33,${0.1 * t})`,
              status: field === "状态" ? <span style={{ display: "flex", alignItems: "center", gap: 12 }}>{cell(shown)}{t > 0.5 && <Glyph name="check" size={28} color={GREEN} />}</span> : <span style={{ fontSize: 24, color: C.sub }}>—</span>,
              date: field !== "状态" ? <span style={{ display: "flex", alignItems: "center", gap: 12 }}>{cell(shown)}{t > 0.5 && <Glyph name="check" size={28} color={GREEN} />}</span> : undefined,
            };
          }} />
        )}
      </Shell>
      <Cursor pts={[[0, 1100, 700], [clickNav0, ...navAt("消息")], [clickBot, ...convAt(0)], [sendAt, ...SEND], [r0, 1300, 700], [clickNav, ...navAt("多维表格")], [clickTable, ...tableAt(0)], [clickTable + 30, 1500, 820], [ruleAt, 1850, 1000]]}
        click={[clickNav0, clickBot, sendAt, clickNav, clickTable]} />
      <div style={{ position: "absolute", bottom: 160, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 30, opacity: 1 - rule }}>
        {([["undo", "最近一次修改可撤销"]] as const).map(([icon, t], i) => (
          <Appear key={t} at={cue(text, "最近一次修改", talk)} dy={20} sfx="pop" style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 32, fontWeight: 600, color: C.text,
            background: "#fff", borderRadius: 999, padding: "12px 30px", boxShadow: "0 6px 24px rgba(31,35,41,0.14)" }}>
            <Glyph name={icon} size={36} color={PURPLE} />{t}
          </Appear>
        ))}
      </div>
      <Tag text="真实对话 · 真实改表记录" style={{ bottom: 150, right: 60, opacity: 1 - rule }} />
      <Focus on={rule}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 36, fontWeight: 700, color: "#fff", background: PURPLE, borderRadius: 999, padding: "12px 34px", marginBottom: 30 }}>
          <Glyph name="ask" size={40} color="#fff" detail={PURPLE} />我定的规矩：它自己推断的改动，先问我
        </div>
        <div style={{ width: 1240, background: "#fff", borderRadius: 18, boxShadow: "0 10px 40px rgba(31,35,41,0.16)", padding: "28px 34px", display: "flex", flexDirection: "column", gap: 20 }}>
          <Me at={ruleAt + 4}>帮我更新一下</Me>
          <Bot at={ruleAt + 18}>
            <div style={{ color: C.name }}>改好了，3 条：B11、A4、A9 …… 没动的三条，说一下原因：</div>
            <div style={{ marginTop: 10, fontSize: 28, lineHeight: 1.7 }}>
              <b>A7 印刷下单</b>：还是“进行中”。物料都印完了，这条基本等于完成，但
              <span style={{ fontWeight: 700, background: `linear-gradient(transparent 55%, rgba(227,115,24,0.35) 55%)`, backgroundSize: `${mark * 100}% 100%`, backgroundRepeat: "no-repeat" }}>
                这是我自己推的——要不要改你定</span>，改的话我一并做。
            </div>
          </Bot>
        </div>
        <div style={{ marginTop: 22, fontSize: 24, color: C.sub }}>真实对话 · 11-18 · 节选</div>
      </Focus>
    </Scene>
  );
};
