# 三橙 B-roll 分镜与动画

给口播补上能解释内容的画面：用 SRT 找时间，用语义决定动作，用阅读需求安排人物大小。支持人物主导、全屏演示＋小圆窗、方形/圆角矩形画中画，以及按需切回人物。

积木人物、完整积木场景、生产线和机械动作默认用 Blender 本地三维制作。这是供 Codex 等支持 SKILL.md 的 agent 使用的制作技能，包含分镜、布局与交付规则、时间与网页辅助脚本，以及可复用的 Blender 场景和合成音效模板。agent 仍需根据实际口播编写动画、准备素材与选择媒体处理路径。

## 能做什么

- 用真实三维模型、塑料材质、灯光和关键帧制作积木人物与场景，保留可修改的 Blender 工程。
- 保留 SRT 原文和时间，识别空档、重叠及工程时长不匹配。
- 把“工具切换、流程连接、输入变输出、对比与筛选”等概念变成可见动作。
- 在内容需要阅读时放大资料、缩小人物；在态度和结论重要时恢复人物主导。
- 使用原始截图、Logo 和文字做精确合成，避免生成模型重绘细节。
- 将本地网页图形渲染为真正保留 Alpha 的 MOV，并按全片时间提前同步。

## 安装

将仓库克隆到 Codex 的个人 skills 目录；若已经安装了同名技能，先比较内容再更新，不覆盖个人定制。

```bash
git clone https://github.com/yesterising/sancheng-broll-animation.git "${CODEX_HOME:-$HOME/.codex}/skills/sancheng-broll-animation"
```

下一轮对话可使用 `$sancheng-broll-animation`，也可直接描述任务，技能已允许自动匹配。其他 agent 宿主按其技能安装机制使用。

示例请求：

> 按这份 SRT 给当前剪映口播补 B-roll 和解释性动画。讲软件操作时让界面铺满画面，人物放小圆窗；解释观点时用较大的方形画中画或恢复人物。所有素材从 00:00 对齐，最后我自己拖入时间线。

## Blender 积木动画默认路径

已完成的案例是“人物走近控制台 → 按按钮 → 指示灯亮起 → 传送带启动 → 产品装配 → 运转全景”，9 秒、720p、24fps。场景与声音源码随仓库提供，无需第三方角色模型或付费生成服务；不捆绑 Blender 安装包和渲染成品。

复制 [积木工厂模板](assets/blender/brick_factory.py) 到项目的 `work/brick_factory.py` 后，可运行：

```bash
blender --background --factory-startup --python work/brick_factory.py -- --project-dir work/brick-project --render
```

输出新的 `.blend` 工程与 216 帧 PNG，再用本地媒体工具合成视频。该模板固定 9 秒、24fps；新的主题由 agent 修改模型、动作和镜头，不能只换标题重复工厂案例。独立积木动画不需要口播 SRT，接入实际口播时才使用对应 SRT。

完整方法、构图修正、装配行程、依赖定位、透明边界和示例命令见 [Blender 制作流程](references/blender-workflow.md)。

## 运行依赖

| 部分 | 依赖与限制 |
| --- | --- |
| 分镜与布局设计 | 支持本技能的 agent；实际剪辑需要用户提供对应 SRT 与可读取媒体 |
| 积木三维场景与动作 | 已安装的 Blender；本次用 4.5.15 LTS 在 macOS Apple Silicon 跑通，无付费插件；图形运行效果不代表其他平台已验收 |
| SRT 时间底稿 | Python 3，标准库，无额外 Python 包 |
| 网页图形渲染 | Node.js、已安装的 Playwright 与匹配 Chromium、支持 QTRLE 的 FFmpeg |
| 人物画中画、音轨与装配 | FFmpeg/FFprobe 或已可用的精确媒体渲染工具；由 agent 按工程时序实现 |
| 剪映素材导入 | 当前环境可用的界面或自动化入口；本仓库不捆绑剪映控制插件 |

脚本不会安装运行时或下载浏览器。`render_alpha.mjs --help` 提供参数；用 `--playwright-from` 指向已有 Playwright 项目的 package.json，`--ffmpeg` 指向已有二进制。仅克隆技能不等于已安装上述运行依赖。

本仓库独立可读，Blender 模板可独立运行；不要求安装其他技能。环境中已有视频剪辑总规则、HyperFrames、剪映工具或画中画工具时，agent 可按实际能力配合使用；这些 companion skills 没有打包在仓库里。

## 文件与使用边界

入口见 [SKILL.md](SKILL.md)；按需要读取 [分镜与动作](references/storyboard-and-motion.md)、[布局与画中画](references/layouts-and-pip.md)、[本地制作](references/local-production.md)、[Blender 制作流程](references/blender-workflow.md)。

本技能主要制作解释性动画和真实资料展示。网页 helper 不处理 video/audio，不自带“一键自动剪辑”或人物视频圆窗引擎；画中画提供可执行的制作流程，由 agent 调用媒体工具完成。它不保证电影级角色生成、播放量或剪映原生可编辑动画。

默认完成后交付同步素材并在有可用入口时导入素材库，用户最后拖入；不主动保存剪映工程或导出整条口播成片；Blender 动画保留制作工程。明确要求先看分镜时，只交付分镜阶段。缺少素材、依赖或编辑器入口会如实报告。

## 验证与许可

发布时验证了 SRT 的中文/多行原文、BOM/CRLF、空档/重叠、分数帧率、异常输入、时长错配与拒绝覆盖；使用合成图形验证了渲染器的绝对时间运动、QTRLE/ARGB 输出和全透明/半透明像素。另已完成 Blender 9 秒积木工厂动画的建模、关键帧、216 帧渲染与视频合成，并验证了可移植模板的新项目创建和单帧渲染。未以此声称完成真实口播案例、剪映导入、所有动作或跨平台兼容验收；当前渲染路径在 macOS 验证。

仓库自有文本与脚本使用 [MIT License](LICENSE)。未包含第三方 skill 原文件、用户媒体、字体、音效或运行时；实际制作素材和依赖各自遵守其许可。
