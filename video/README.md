# 求职视频（Remotion）

## 正片（Main）

文案：`视频脚本.md`（画面 + 口播 + 出处），`口播稿.md`（纯口播，给配音用）。

1. 把 `口播稿-MiniMax.txt` 整篇粘进 MiniMax，一次生成配音，存成 `public/voice/全片.mp3`。
   - 这个文件由脚本从 `口播稿.md` 导出：去掉了【】标题，段落之间有 `<#1.2#>` 的长停顿（别删，切配音靠它）。
   - 想调停顿，改 `口播稿.md` 里的 `<#秒数#>`，再跑下一步重新导出。句中停顿要短于 0.9 秒。
2. `python3 scripts/narration.py`：读口播稿，用静音检测把配音切回 24 个画面，生成 `src/data/narration.json`。改了口播稿或换了配音都要重跑。
3. `npm run studio` 预览；出片：`npx remotion render src/index.ts Main out/正片.mp4`。

- 口播稿里每个自然段对应一个画面（`src/main/Main.tsx` 的 `SHOTS`），改口播稿时别增删自然段，否则要同步改 `SHOTS`。
- 字幕按标点自动切句、按字数分配时间；有配音后会和声音大致对齐。
- 画面全部用代码绘制，不用截图（截图里有浏览器插件、账号名和现实日期）。工具 1、工具 2 按飞书里的真实配置重画。
- 图标都是自绘的扁平矢量图（`src/main/icons.tsx`），界面上不用 emoji；同事聊天原文里的表情保持原样。
- 画面上标了「示意」的是演示操作（比如鼠标点格子），消息内容都是原话。
- 较长的场景（架构图、工具 1）在正片里会按口播时长加速播放，见 `src/time.ts`。
- 背景音乐是代码合成的（`scripts/bgm_warm.py`，用法见文件开头），存成 `public/music/bgm.mp3`。

## 素材场景

用真实聊天记录生成"飞书风格"的回放动画。真实的飞书录屏（搭工具过程）另外录，剪辑时拼在一起。

```bash
python3 scripts/export_day.py 1   # 导出 D1（只能导出已经下班的日子，只读你收到过的消息）
npm run studio                     # 浏览器里预览、拖时间轴
npm run render                     # 输出 out/chat-replay.mp4
```

- `src/feishu.tsx`：飞书风格的零件（头像、气泡、文件卡片、侧边栏）
- `src/ChatReplay.tsx`：聊天回放场景 + 当天手工工作量统计卡
- `src/Root.tsx`：每个场景的参数（哪天、哪个群、放几条、多快）
- 头像来自 `素材/头像/`
- 飞书真实截图（`public/素材/`）里有账号名，没有上传；用到它们的素材场景（`ToolDependency`）在仓库里渲染不出截图，正片不受影响。
