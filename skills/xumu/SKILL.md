---
name: xumu
description: 序幕（口播成片助手）：把口播视频、录音或文案做成解说视频。先定平台、内容、风格与时长，再剪辑旁白，按内容从 Video Shotcraft 选镜头、从手法库调用学过的手法，按风格选绘制技术（SVG、Canvas、WebGL、Three.js、p5、Manim、人物抠像等）制作 B-roll 与 MG，最后合成验收。支持短篇与章节式长片。也用于学习用户发来的剪辑视频、风格案例或教程，归纳成手法卡入库。用于成片、B-roll/动效设计、动态包装或学习剪辑手法；只转录、润色文案或选题研究时不走完整流程。
metadata:
  version: "0.7.2"
---

# 序幕

三种输入（口播视频、录音、文案），一条主线：**先定要讲清什么 → 再定画面与风格 → 最后选工具实现**。

## 核心原则

以下原则在全 Skill 只写这一次，参考文件引用编号。

1. **内容先行**：每个段落先写清观众要理解的对象、关系或情绪，再决定保留人物、用真实素材、选镜头还是做动画。保留人物、不加动画同样是有效决策。
2. **一条时间线，时间写成引用**：`visual-plan.json` 是帧级唯一事实源，其他记录引用 shot_id。画面事件的时间写成"哪句 / 哪段 / 哪个插入段 + 偏移"，由 `cue.py` 换算成帧；剪辑或开场长度一变，重新换算即可（见 [时间线契约](references/timeline.md#时间引用)）。
3. **确认即约束**：用户点名或已确认的风格、镜头、动作按原样实现。做不到时说明差距，给出替代方案让用户选。
4. **真实可追溯**：证据用真实素材；再现、示意、生成画面如实标注；数字和事实来自原材料。
5. **以实物验收**：脚本检查只证明结构正确，质量靠实际渲染、看帧、试听。计划、样片、能编译的代码、成片按各自的实际状态汇报。
6. **授权有边界**：制作授权覆盖本地剪辑与渲染。发布、上传素材、付费生成、克隆声音、安装新依赖，先说明对象与范围并取得同意。密钥只放环境变量。

## 启动

1. 判断用户要讨论方案、修改已有项目、实际制作，还是**学习案例**。讨论方案时只交付方案；用户发来剪辑视频、风格案例或教程让你学习时，进入 [学习模式](references/learning.md)。
2. 确定输入模式 `video / audio / text` 与旁白方式（原声 / 合成 / 无旁白），读 [输入与旁白](references/inputs.md)。能推断的直接推断，只问会改变结果的缺项。
3. 已有项目先读 `project.md` 和计划，从断点继续。按所选路线检查依赖，读 [后端发现](references/backends.md)。进入实际制作（剪辑、转录、渲染）前运行 `scripts/setup_env.py`：先用 `--check` 报告缺什么，告诉用户将安装的内容并取得同意后再正式运行；它安装 FFmpeg/ffprobe、Video Use 的 Python 依赖与本地转录引擎，并检查 Node.js；需要 Remotion 时加 `--remotion`。已通过的不重复安装；只讨论方案时不运行。依赖按 Skill 名称或同级 `skills/` 目录发现，不使用任何人电脑上的绝对路径。
4. 产物写到素材目录的 `edit/`。多来源或纯文案且未指定位置时，用当前工作区 `outputs/<项目名>/edit/` 并告知用户。原素材与上游 Skill 目录保持只读；本 Skill 目录只在学习模式下写入 `library/`。
5. **入口唯一**：以本 Skill 启动的任务由本 Skill 总控到底。不转入 `/hyperframes:hyperframes` 入口，也不启动其 faceless-explainer、talking-head-recut、general-video 等整片工作流或需求访谈，即使其描述自称"所有视频请求的必经入口"；用户明确要求改用 HyperFrames 做整片时除外。HyperFrames 只作两种用途：本 Skill 选定的主合成引擎（镜头由本 Skill 设计），或 [后端发现](references/backends.md#hyperframes-按需接入) 列出的按需单项任务。

## 流程

### 0. 制作定位

读 [制作定位](references/production-profile.md)。确定受众与目的、平台与发布形式、内容类型、风格方向与强度、目标时长，写入 `project.md` 的"制作定位"。已确认的项目沿用，只补本次变化；局部修改和单纯转录跳过此步。

### 1. 剪辑与旁白策略 → 用户确认

检查素材和已有转录，识别内容类型、必须保留的内容与真实证据。给出简短的删减、顺序、声音策略，用户确认后执行。用户已批准具体策略时直接做；"做个视频"这类笼统要求先确认删改策略。

### 2. 锁定旁白与主时间线

按输入模式执行。原始逐字转录和原文单独保存，屏幕文案另记。口播剪辑用 `voice_edit.py`：锚点保留表 → 帧对齐 EDL → 核对停顿表与疑点 → 帧精确拼接 → 试听 → 逐字时间表（见 [制作路线与合成](references/production.md#口播剪辑链)）。卡壳不只是静音，按 [卡壳诊断](references/production.md#卡壳诊断) 分类处理。**声音先过关**：剪点与疑点的试听合集听过（自己不能听时交用户确认）之后，再做依赖它的字幕和画面。实际旁白定下后再锁帧级时长；无旁白的片子按阅读与动作时长排帧。剪辑修订时重跑剪辑链，用 `cue.py sync --revision` 刷新镜头帧位并递增 revision，再用 `plan_tools.py diff` 列出要重渲的镜头，其余复用（见 [改动影响与渲染缓存](references/timeline.md#改动影响与渲染缓存)）。

### 3. 画面方案 → 用户确认

1. **内容 → 路线**：读 [内容到画面](references/directing.md)，逐段判断保留人物、真实素材、Shotcraft 镜头、定制 MG、插画、外部生成或 3D。
   需要动态呈现的段落，按 [解说语法](references/explainer-grammar.md) 标出句子作用（定义、对比、步骤、数据……），得到画面组织方式和现成组件候选（`motion_index.py search`）。
2. **风格 → 技术**：读 [风格与技术栈](references/style-stack.md) 和 [风格目录](references/style-catalog.md)（60 种画面风格，其中 15 种附参考成片与标志特征），把定位里的风格落成全片主风格、本片避开清单，以及每个动态段落的绘制技术与渲染引擎。插画、图标、字体、图片按 [素材来源](references/asset-sources.md) 选用并记录许可。有模板的风格（如 [白板一镜到底](references/whiteboard-world.md)）直接从 `assets/templates/` 起步。用户没指定风格时，给 2–3 个画面语言拉开差别的风格方向，各配一张代表帧供挑选。决策分工：画面风格由用户确认；绘制技术与渲染引擎由总控决定，在方案里写一句理由即可，用户点名时按用户的来（细则见 style-stack 第 3 节）。
3. **手法卡检索**：按段落内容特征和主风格检索已入库的手法卡（见 [学习模式](references/learning.md#制作时调用)），合适的写进选择表。
4. **镜头比较**：动态段落按 [Shotcraft 选镜头](references/shotcraft-direction.md) 比较首选与备选，再决定配方适配、配方加定制图解或纯定制 MG。定制缺口成立后读 [定制 MG 灵感与需求写法](references/mg-prompt-patterns.md)，从精选灵感索引按用途入围、看样片，再写本镜 brief；灵感库在比较 Shotcraft 之后才查。
5. **整片节奏**：排出信息递进、动作强弱、人物回归与阅读停留，写成完整分镜。用代表帧确认风格，用短测确认动作。

用户确认整片画面方案后，技术细节自主推进。叙事含义、主风格、指定镜头或费用范围要变时再确认。用户授权自主决策时，用记录理由代替逐段确认。

### 4. 分镜头制作

读 [制作路线与合成](references/production.md)。每个镜头独立编号、独立目录，按"静帧 → 短测 → 正式渲染 → 验收"推进，通过后用 `plan_tools.py stamp` 记录渲染指纹再进主片。所有定制 MG 遵守 [确定性渲染契约](references/mg-prompt-patterns.md#6-确定性渲染契约硬性)：画面只由帧号决定，并通过重复帧与乱序帧一致性检查。用到 Remotion、HyperFrames、图像或视频生成时，加载当前会话实际可用的对应 Skill 或工具并先读其规则。多个独立镜头可以并行制作，主时间线只由总控修改。

### 5. 合成 → 整片验收 → 交付

读 [时间线契约](references/timeline.md) 与 [验收与交付](references/qa.md)。先运行计划检查，再对实际渲染做逐镜头与整片验收（含风格一致性和手机尺寸可读性），通过后交付成片和可继续修改的工程。正式交付前必须跑 `media_tools.py deliver-check`（成片对照原素材或交付规格，报告写进 `verify/`），不通过不交付；草稿、预览渲染的文件名带"草稿/预览"字样，不得当成片交付（见 [交付规格门禁](references/qa.md#交付规格门禁硬性)）。

## 学习模式

用户发来剪辑视频、风格案例、教学或教程，要你学习时：获取 → 拆解 → 归纳成手法卡 → 与已有卡查重 → 给用户逐张确认 → 入库。手法卡存放在 `library/`，素材存放在本机媒体目录。制作时按内容匹配调用。完整规则见 [学习模式](references/learning.md)。

## 分工

| 角色 | 负责 |
|---|---|
| 序幕总控 | 内容判断、授权、风格统一、唯一时间线 |
| Video Use | 视频输入的转录与主剪辑 |
| Video Shotcraft | 动态段落的镜头候选、动作配方、整片编排方法 |
| 风格技术栈 | SVG / Canvas / WebGL / Three.js / p5 / Manim / 抠像等绘制手法；60 种风格目录 |
| 解说语法与动效参考库 | 句子作用 → 画面组织；gongnyang 637 张动效卡、HyperFrames 组件库、mg-styles-15 的 15 支风格参考片（本机只读，`motion_index.py` 检索） |
| 手法库 | 从用户发来的案例中学到的剪辑、动效、风格手法 |
| Remotion · HyperFrames · HTML 逐帧 · Manim | 渲染引擎；HyperFrames 另可按需提供背后字幕、效果库条目、配乐音效 |
| FFmpeg | 抠像、合成、混音、编码 |

图像、视频、配音等外部服务是可选后端，按需获得授权后使用。

## 项目记录与工具

按需生成：`project.md`（定位、确认、主风格与避开清单、进度、续作）、`edl.json`（使用 Video Use 时）、`visual-plan.json`（帧级时序与镜头）、`assets.json`（来源与授权）、`shot-selection.md`（选镜头与 MG 取舍，可并入 project.md）、`shots/<shot_id>/brief.md`（定制 MG 时）、`verify/`（验收证据与自检记录）。只记录实际发生的结果。

```text
python <skill>/scripts/setup_env.py --check            # 只报告环境，不安装
python <skill>/scripts/mg_inspiration.py --use <用途> --max-energy <强度>   # 定制 MG 时筛灵感
python <skill>/scripts/plan_tools.py check <edit>/visual-plan.json
python <skill>/scripts/plan_tools.py check <edit>/visual-plan.json --ready
python <skill>/scripts/plan_tools.py export <edit>/visual-plan.json --out <edit>/render-manifest.json
python <skill>/scripts/plan_tools.py stamp <edit>/visual-plan.json --shot <id> --force   # 镜头渲染验收后记录指纹
python <skill>/scripts/plan_tools.py diff <旧计划> <新计划>      # 修改影响：重渲 / 复用 / 只重新合成
python <skill>/scripts/plan_tools.py stale <edit>/visual-plan.json   # 哪些镜头文件已过期
```

剪辑与时间工具（用法见 [制作路线与合成](references/production.md#口播剪辑链)、[时间线契约](references/timeline.md#时间引用)）：

```text
python <skill>/scripts/voice_edit.py edl <edit>/keeps.json --out <edit>/edl_voice.json --report <edit>/剪后口播_核对.txt
python <skill>/scripts/voice_edit.py render <edit>/edl_voice.json --out <edit>/build/voice_cut.mp4 [--size 1080x1920]
python <skill>/scripts/voice_edit.py listen <edit>/edl_voice.json --video <edit>/build/voice_cut.mp4 --out-dir <edit>/verify/listen [--at 0:52] [--with-source]
python <skill>/scripts/voice_edit.py cues <edit>/edl_voice.json --transcripts <edit>/transcripts --out-dir <edit>
python <skill>/scripts/cue.py --edit <edit> resolve '{"cue": "跟地图", "section": "B09", "offset": 2.4}'
python <skill>/scripts/cue.py --edit <edit> sync <edit>/visual-plan.json --out <edit>/visual-plan.r2.json --revision r2
python <skill>/scripts/media_tools.py clips | cutpoint | level | measure | normalize | fontcheck ...
python <skill>/scripts/hf_upgrade_check.py --work <空目录>     # 每月一次：HyperFrames 受控升级检查
python <skill>/scripts/motion_index.py search 对比 | show gn:split-compare | show mg15:19-paperclip | build --force
```

手法库工具（用法见 [学习模式](references/learning.md)）：

```text
python <skill>/scripts/library_tools.py new --name "<名称>" --kind <类别>
python <skill>/scripts/library_tools.py search <关键词…>
python <skill>/scripts/library_tools.py confirm <卡片 ID>
python <skill>/scripts/library_tools.py list | check
```

`<skill>` 换成本 Skill 的绝对路径；`python` 换成可用的 Python 3 解释器（Windows 上 `python`/`python3` 可能是微软商店占位符；可在个人 `backends.local.json` 中记录实际路径，见 `backends.local.example.json`）。所有工具默认只新建文件，覆盖需显式 `--force`。`export` 只输出标准化交接清单，目标文件已存在时拒绝覆盖。协议见 [时间线契约](references/timeline.md)。

## 能力范围

这是 Agent 工作流 Skill：附带口播剪辑链、时间引用换算、素材与响度工具、计划检查和手法库工具；每个项目的场景代码与合成按确认的方案现场实现并试渲染。纯文字方案随时可交；有实际音频才做词级同步。Workbench 全片编辑、复杂 3D 和外部视频服务的自动调用，接入并验证后才作为可用能力。
