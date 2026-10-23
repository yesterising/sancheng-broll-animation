# 三橙 B-roll 分镜与动画

给口播补上能解释内容的画面：用户把视频放入当前剪映工程并提供对应 SRT 后，默认由 agent 判断哪里用积木动画、哪里全屏展示、哪里切圆形或方形画中画、哪里恢复人物主导，无需用户逐段安排。判断依据是口播语义、实际画面与内容可读性。

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

## 自动导演默认规则

先选择解释内容的形式，再选择内容占比与人物窗口；例如可以同时采用“全屏积木生产线＋同期口播小圆窗”。抽象流程和因果适合时用积木演示，工具功能与真实数据优先用真实界面；密集内容让人物缩进小圆窗，需要手势时用方形/圆角矩形窗口，观点和情绪段让人物主导。切换跟随观点或步骤边界，不按固定秒数轮换。

完整包装范围内的全屏展示与画中画区间由 agent 自主安排；SRT 明显不匹配、必需素材无法读取或工具确实阻塞时才补问具体缺口。全片素材从 00:00 对齐、声音保留一份，用户最后拖入时间线。用户本次限定的范围、只加字幕等要求优先。

具体判断、内部计划和交付衔接见 [自动导演规则](references/automatic-direction.md)。

## Blender 积木动画默认路径

当前基线为已完成的 14 秒、720p、24fps 重制案例：人物按键 → 底件进站停稳 → 吸盘从料架取盖并转运放料 → 吸盘退出 → 压头压合 → 成品输出。固定骨长右臂、实体零件和传动共用事件时序，带原创本地合成机械声，保留声音已打包的 Blender 工程。动作、镜头与声音源码随仓库提供，不捆绑运行时、第三方资产或渲染成品。

制作/返修时先读 [完整优化迭代方案](references/iteration-and-quality.md)，再按 [Blender 制作流程](references/blender-workflow.md) 执行。旧 `brick_factory.py` 只作为几何种子；新 `press_line_remake.py` 会重建固定骨长控制与工作单元。复制源码到任务工作目录后，先创建种子，再创建新工程：

```bash
blender --background --factory-startup --python-exit-code 1 --python work/brick_factory.py -- --project-dir work/seed
blender --background work/seed/brick_factory.blend --python-exit-code 1 --python work/press_line_remake.py -- --project-dir work/remake
```

继续按方案生成完整 PNG 序列、机械声并编码，人物布局与素材交付沿用 [自动导演规则](references/automatic-direction.md)。本例固定 14 秒、24fps；新主题需 agent 同步改模型、动作、相机与声音，不是任意口播一键转三维。独立动画不需要 SRT，接入口播才使用对应字幕。

优化记录区分已实现、局部验证、待开发和用户实际反馈。完整步态、通用动作库、自动三维缓存与本地视频大模型仍未作为默认生产能力；不能把技术通过说成用户已认可画面。

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

发布时验证了 SRT 的中文/多行原文、BOM/CRLF、空档/重叠、分数帧率、异常输入、时长错配与拒绝覆盖；使用合成图形验证了渲染器的绝对时间运动、QTRLE/ARGB 输出和全透明/半透明像素。另已完成旧 9 秒案例及新 14 秒重制动画的完整渲染与带声视频合成；新模板验证新工程创建、固定骨长/接触、单帧渲染、机械声生成与音频打包。未以此声称完成真实口播案例、剪映导入、所有动作或跨平台兼容验收；当前渲染路径在 macOS 验证。

仓库自有文本与脚本使用 [MIT License](LICENSE)。未包含第三方 skill 原文件、用户媒体、字体、音效或运行时；实际制作素材和依赖各自遵守其许可。
