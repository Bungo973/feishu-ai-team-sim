import React from "react";
import { Composition } from "remotion";
import { ArchitectureIntro } from "./ArchitectureIntro";
import { ChatReplay, ChatReplayProps, DayData } from "./ChatReplay";
import D1 from "./data/D1.json";
import { setMeAvatar } from "./feishu";
import { ToolDependency } from "./ToolDependency";
import { FPS, Main, TIMELINE } from "./main/Main";

// 素材/头像 里有你的头像就用（导出脚本会写进数据）
setMeAvatar(!!(D1 as DayData).meAvatar);

export const Root: React.FC = () => (
  <>
    {/* 正片：按 口播稿.md 排的完整视频 */}
    <Composition id="Main" component={Main} durationInFrames={TIMELINE.total} fps={FPS} width={1920} height={1080} />
    {/* 样片：D1 品牌项目组前 14 条，20 秒 */}
    <Composition
      id="ChatReplay"
      component={ChatReplay as React.FC<any>}
      durationInFrames={600}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{ data: D1 as DayData, group: "品牌项目组", count: 14, every: 32, statsAt: 470 } satisfies ChatReplayProps}
    />
    {/* 背景：这个模拟是怎么运转的，16 秒 */}
    <Composition id="ArchitectureIntro" component={ArchitectureIntro} durationInFrames={480} fps={30} width={1920} height={1080} />
    {/* 第二幕 · 工具 1：依赖联动提醒，36 秒 */}
    <Composition id="ToolDependency" component={ToolDependency} durationInFrames={1080} fps={30} width={1920} height={1080} />
  </>
);
