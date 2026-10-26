// 正片 5-8、5-9：痛点 ③ 前置变更，在飞书界面底板上操作，讲到重点时聚焦
import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { MessageGroup, TimeLabel, Toast } from "../feishu";
import { Card as BigCard, Chip, EVERY, Reminder, ROWS, RunLog, STEPS, Workflow } from "../ToolDependency";
import { Appear, C, clamp, ORANGE, Sfx, Tag, useIn } from "./kit";
import { Cursor, type SceneProps } from "./scenes-intro";
import { TaskTable } from "./scenes-tools";
import { AUTO_BTN, ChatHead, convAt, Focus, focusOf, K, MAIN, navAt, Shell, TableHead, tableAt } from "./shell";
import { Scene } from "./kit";

// 上一幕改完的任务表（A6 / A10 / A14 已完成，B11 改了日期）
const AFTER_EDIT: [string, string, string][] = [["A6 主视觉 KV 与现场物料设计", "已完成", "—"], ["A10 演讲 PPT 内容", "已完成", "—"], ["A14 直播方案", "已完成", "—"], ["B11 小红书·倒计时 2 天", "", "11-17"], ["A12 新闻通稿", "进行中", "—"]];

// 5-8：说到"前置任务一变，后面的人最后才知道"时聚焦一条链（卖点 → 主视觉 KV → 物料下单）
// → 说到"设计师就提醒过我"时回到界面，点开陈悦的私聊，是她第 3 天的原话
export const DepChain: React.FC<SceneProps> = ({ dur }) => {
  const frame = useCurrentFrame();
  const F = (x: number) => Math.round(dur * x);
  const f1 = F(0.1), hit = F(0.22), u1 = F(0.44), clickNav = F(0.47), clickDm = F(0.52), quoteAt = F(0.56);
  const focus = focusOf(frame, f1, u1);
  const NODES = ["卖点", "主视觉 KV", "物料下单"];
  const nav = frame >= clickNav ? "消息" : "多维表格";
  const onDm = frame >= clickDm;
  const hl = interpolate(frame, [F(0.62), F(0.62) + 8], [0, 1], clamp);
  const quoteIn = useIn(quoteAt);
  return (
    <Scene>
      {[0, 1, 2].map((i) => <Sfx key={i} at={hit + i * 14} name="tick" volume={i ? 1 : 2} />)}
      <Sfx at={quoteAt} name="notify" />
      <Shell nav={nav} active={nav === "多维表格" ? "任务表" : onDm ? "陈悦" : undefined} withBot dim={focus}
        head={nav === "多维表格" ? <TableHead name="任务表" /> : onDm ? <ChatHead name="陈悦" /> : null} to={onDm ? "陈悦" : undefined}>
        {nav === "多维表格" && <TaskTable rows={AFTER_EDIT} />}
        {onDm && (
          <div style={{ transform: `scale(${K * 1.15})`, transformOrigin: "0 0", width: 720, paddingTop: 30 }}>
            <TimeLabel text="第 3 天" />
            <div style={{ borderRadius: 8, margin: "0 12px", boxShadow: `0 0 0 ${2 * hl}px ${ORANGE}`, background: `rgba(227,115,24,${0.06 * hl})`, opacity: quoteIn }}>
              <MessageGroup sender="陈悦" texts={[{ text: "中间要是再来一轮改稿，我就真排不进去了。", style: {} }]} />
            </div>
          </div>
        )}
      </Shell>
      <Focus on={focus}>
        <div style={{ display: "flex", alignItems: "center", gap: 30, marginTop: -60 }}>
          {NODES.map((s, i) => {
            const t = interpolate(frame, [hit + i * 14, hit + i * 14 + 10], [0, 1], clamp);
            const color = i === 0 ? C.red : ORANGE;
            const shake = i === 0 && frame > hit && frame < hit + 16 ? Math.sin(frame * 2) * 8 : 0;
            return (
              <React.Fragment key={s}>
                {i > 0 && <Appear at={f1 + 4 + i * 8} style={{ fontSize: 60, color: t > 0.5 ? ORANGE : C.sub }}>→</Appear>}
                <Appear at={f1 + i * 8} dy={30}>
                  <div style={{ width: 380, height: 170, borderRadius: 24, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                    background: t > 0 ? (i === 0 ? "#FDECEC" : "#FFF4E5") : "#fff", outline: `${4 * t}px solid ${color}`, transform: `translateX(${shake}px)`,
                    boxShadow: "0 10px 40px rgba(31,35,41,0.08)" }}>
                    <div style={{ fontSize: 46, fontWeight: 700, color: C.text }}>{s}</div>
                    <div style={{ fontSize: 26, color, marginTop: 10, opacity: t }}>{i === 0 ? "又改了" : "要重做 · 排不进去"}</div>
                  </div>
                </Appear>
              </React.Fragment>
            );
          })}
        </div>
        <Appear at={hit + 40} style={{ fontSize: 34, color: C.text, marginTop: 50, fontWeight: 600 }}>前置一变，后面的人最后才知道</Appear>
      </Focus>
      <Cursor pts={[[2, 1300, 800], [u1 + 4, 900, 700], [clickNav, ...navAt("消息")], [clickDm, ...convAt(6)], [quoteAt + 20, 900, 300]]} click={[clickNav, clickDm]} />
      <Tag text="原话 · 第 3 天" style={{ bottom: 150, right: 60 }} />
    </Scene>
  );
};

// 5-9 用的任务表：12 行，带「前置任务」列（测试表里 A0 和它的 9 个后置任务，状态是触发前的真实值）
const RH = 56, X0 = MAIN.x + 40, Y0 = MAIN.y + 40;
const COLS = "460px 120px 260px 1fr";
const OPTS = ["进行中", "已完成", "受影响-待确认"];
const DepTable: React.FC<{ preHl: number; flip: number; openAt: number; cascade: number }> = ({ preHl, flip, openAt, cascade }) => {
  const frame = useCurrentFrame();
  const open = frame >= openAt && frame < flip;
  return (
    <div style={{ margin: 40, width: 1100, background: "#fff", borderRadius: 14, border: `1px solid ${C.line}`, position: "relative" }}>
      <div style={{ display: "grid", gridTemplateColumns: COLS, fontSize: 20, color: C.sub, background: "#FAFBFC", height: RH, alignItems: "center", padding: "0 24px", borderBottom: `1px solid ${C.line}` }}>
        <span>任务</span><span>负责人</span><span>状态</span><span style={{ color: preHl > 0.5 ? C.blue : C.sub, fontWeight: preHl > 0.5 ? 700 : 400 }}>前置任务</span>
      </div>
      {ROWS.map((r, i) => {
        // A0 改回后，9 个后置任务一个接一个变成「受影响-待确认」，变的那一下整行闪黄
        // p：状态格像翻牌一样往上换成「受影响-待确认」（旧的滑出去、新的从下面滑进来）；flash：整行淡黄亮一下再退掉，和变紫叠在一起，不跳色
        const at = cascade + r.hit * EVERY;
        const p = r.hit >= 0 ? interpolate(frame, [at, at + 10], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) }) : 0;
        const ft = r.hit >= 0 ? interpolate(frame, [at, at + 30], [0, 1], clamp) : 0;
        const flash = Math.sin(Math.PI * ft) ** 2;
        const old = i === 0 && frame >= flip ? "进行中" : r.status;
        const chip = (st: string) => (st ? <Chip s={st} /> : <span style={{ color: C.sub, fontSize: 20 }}>（空）</span>);
        const base = i === 0 && (open || frame >= flip) ? "#FFF7E6" : "#fff";
        return (
          <div key={r.name} style={{ display: "grid", gridTemplateColumns: COLS, alignItems: "center", height: RH, padding: "0 24px", fontSize: 22, color: C.text,
            borderBottom: i < ROWS.length - 1 ? `1px solid ${C.line}` : "none",
            background: `linear-gradient(rgba(255,214,102,${0.35 * flash}), rgba(255,214,102,${0.35 * flash})), linear-gradient(rgba(247,243,255,${p}), rgba(247,243,255,${p})), ${base}` }}>
            <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", paddingRight: 12 }}>{r.name}</span>
            <span style={{ color: C.name }}>{r.owner}</span>
            <span style={{ display: "grid", overflow: "hidden", outline: i === 0 && open ? `2px solid ${C.blue}` : "none", borderRadius: 6, padding: 2, width: "fit-content" }}>
              {p < 1 && <span style={{ gridArea: "1 / 1", transform: `translateY(${-120 * p}%)` }}>{chip(old)}</span>}
              {p > 0 && <span style={{ gridArea: "1 / 1", transform: `translateY(${120 * (1 - p)}%)` }}>{chip("受影响-待确认")}</span>}
            </span>
            <span style={{ background: r.pre ? `rgba(51,112,255,${0.14 * preHl})` : "transparent", borderRadius: 6, padding: "2px 10px", width: "fit-content", color: r.pre === "A0" ? C.blue : C.text, fontWeight: r.pre === "A0" ? 600 : 400 }}>{r.pre}</span>
          </div>
        );
      })}
      {open && (
        <div style={{ position: "absolute", left: 24 + 460 + 120, top: RH * 2 - 6, zIndex: 5, background: "#fff", borderRadius: 10, boxShadow: "0 8px 30px rgba(0,0,0,0.18)", padding: 10, display: "flex", flexDirection: "column", gap: 8 }}>
          {OPTS.map((s, k) => <div key={s} style={{ padding: "4px 8px", background: k === 0 && frame >= flip - 8 ? "#EAF1FF" : "transparent", borderRadius: 6 }}><Chip s={s} /></div>)}
        </div>
      )}
    </div>
  );
};

// 5-9：在任务表里标好任务间的前后关系（前置任务列）→ 点「自动化」看工作流（按真实配置重画）→ 回到任务表，把 A0 改回「进行中」
// → 表里 9 个后置任务依次变成「受影响-待确认」→ 右上角弹通知，点开是真实收到的提醒 → 聚焦：运行日志，飞书里配置、没写代码
const NOTIFIER = "品牌项目组 · 多维表格";
export const DepFlow: React.FC<SceneProps> = ({ dur }) => {
  const frame = useCurrentFrame();
  const F = (x: number) => Math.round(dur * x);
  const preAt = F(0.05), clickAuto = F(0.17), flowAt = F(0.19), clickBack = F(0.31), openAt = F(0.34), flip = F(0.37), cascade = F(0.41);
  const toastAt = F(0.66), clickToast = F(0.71), f2 = F(0.82);
  const focusSum = focusOf(frame, f2);
  const view = frame < clickAuto ? "table" : frame < clickBack ? "flow" : frame < clickToast ? "table" : "msg";
  const preHl = interpolate(frame, [preAt, preAt + 10], [0, 1], clamp) * (frame < clickAuto ? 1 : 0.6);
  const toast = interpolate(frame, [toastAt, toastAt + 10, clickToast, clickToast + 6], [0, 1, 1, 0], clamp);
  const statusX = X0 + 24 + 460 + 120 + 50, a0Y = Y0 + RH + RH / 2;
  return (
    <Scene>
      <Sfx at={toastAt} name="notify" />
      <Shell nav={view === "msg" ? "消息" : "多维表格"} active={view === "msg" ? NOTIFIER : "任务表"} withBot
        extra={frame >= toastAt ? [{ name: NOTIFIER, bot: true, unread: 0, preview: "⚠️ 前置任务被改回，后置任务受影响", time: "17:40" }] : []}
        dim={focusSum}
        head={view === "msg" ? <ChatHead name={NOTIFIER} bot /> : view === "flow" ? <TableHead name="任务表" view="自动化 · 前置变更提醒" auto /> : <TableHead name="任务表" auto />}
        to={view === "msg" ? NOTIFIER : undefined}>
        {view === "table" && <DepTable preHl={preHl} flip={flip} openAt={openAt} cascade={cascade} />}
        {view === "flow" && (
          <div style={{ display: "flex", gap: 30, padding: "20px 30px", background: "#F5F6F7", height: "100%" }}>
            <div style={{ transform: "scale(0.75)", transformOrigin: "0 0", width: 750, height: 580 }}><Workflow at={flowAt} /></div>
            <div style={{ display: "flex", flexDirection: "column", gap: 18, width: 300, marginTop: 40 }}>
              {STEPS.map((s, i) => (
                <Appear key={s} at={flowAt + 20 + i * 16} style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 22, color: C.text, lineHeight: 1.4 }}>
                  <div style={{ width: 38, height: 38, borderRadius: 19, background: C.blue, color: "#fff", fontSize: 20, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{i + 1}</div>
                  {s}
                </Appear>
              ))}
            </div>
          </div>
        )}
        {view === "msg" && (
          <div style={{ padding: "30px 40px" }}>
            <Appear at={clickToast + 4} dy={20}><Reminder /></Appear>
          </div>
        )}
      </Shell>
      {/* 右上角的系统通知 */}
      <div style={{ position: "absolute", top: 14 * K, right: 14 * K, transform: `scale(${K}) translateX(${(1 - toast) * 60}px)`, transformOrigin: "top right", opacity: toast }}>
        <Toast chat={NOTIFIER} sender={NOTIFIER} text="⚠️ 前置任务被改回，后置任务受影响" />
      </div>
      <Focus on={focusSum}>
        <div style={{ display: "flex", gap: 40, alignItems: "center" }}>
          <BigCard at={f2 + 5} big="1 处" small="前置任务被改回" color={C.text} />
          <div style={{ fontSize: 50, color: C.sub }}>→</div>
          <BigCard at={f2 + 15} big="9 个" small="后置任务自动标记" color="#6425D0" />
          <div style={{ fontSize: 50, color: C.sub }}>→</div>
          <BigCard at={f2 + 25} big="1 条" small="提醒直达，不用挨个问" />
        </div>
        <Appear at={f2 + 40} style={{ display: "flex", alignItems: "center", gap: 30, marginTop: 50 }}>
          <RunLog />
          <div style={{ fontSize: 28, color: C.name, lineHeight: 1.6 }}>运行日志：每个节点都执行成功<br /><b style={{ color: C.text }}>飞书里配置，没写一行代码</b></div>
        </Appear>
      </Focus>
      <Cursor pts={[[2, 1200, 800], [clickAuto, ...AUTO_BTN], [flowAt + 30, 1300, 700], [clickBack, ...tableAt(0)], [openAt, statusX, a0Y], [flip - 4, statusX + 10, a0Y + RH + 30], [flip + 14, 1500, 900],
        [toastAt + 4, 1300, 500], [clickToast, 1650, 70], [f2, 1300, 800]]}
        click={[clickAuto, clickBack, openAt, flip - 4, clickToast]} />
      {view === "flow" && <Tag text="按飞书里的真实配置重画 · 8 个节点" style={{ bottom: 150, right: 60 }} />}
      {view === "msg" && <Tag text="真实收到的提醒（文字原样）" style={{ bottom: 150, right: 60 }} />}
    </Scene>
  );
};
