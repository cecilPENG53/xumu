# 序幕

<p align="center">
  <a href="./README.md"><img alt="简体中文" src="https://img.shields.io/badge/简体中文-当前-D97757?style=for-the-badge"></a>
  <a href="./README.en.md"><img alt="English" src="https://img.shields.io/badge/English-Switch-555555?style=for-the-badge"></a>
</p>

![GitHub stars](https://img.shields.io/github/stars/cecilPENG53/xumu?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![Version](https://img.shields.io/badge/version-0.7.3-orange?style=flat-square)
![Skill](https://img.shields.io/badge/Skill-Agent-111111?style=flat-square)
![Remotion](https://img.shields.io/badge/Remotion-MG-0B84F3?style=flat-square)
![Claude](https://img.shields.io/badge/Claude-支持-D97757?style=flat-square)
![GPT](https://img.shields.io/badge/GPT%20%2F%20Codex-支持-222222?style=flat-square)
![豆包](https://img.shields.io/badge/豆包-可用-1E6FFF?style=flat-square)
![More](https://img.shields.io/badge/更多%20AI%20Agent-可用-6B5B95?style=flat-square)

> 📘 **使用规范：[docs/USAGE.md](./docs/USAGE.md)**

一个适配 Claude、GPT、豆包等 AI Agent 的**口播视频成片技能包**。把**口播视频、一段录音或一份文案**交给 Agent，它会先判断「发到哪、讲什么、什么风格、多长」，再完成剪辑、选镜头、定制动态图形（MG）、字幕与合成，最后交付**成片 + 可继续修改的工程**。

它不是「一键出片」的黑盒，而是一套有确认点的导演工作流：

- **先想清楚再动手**：平台 × 内容 × 风格 × 时长的制作定位，决定叙事结构、剪辑策略和镜头强弱。
- **不把所有内容都变成卡片**：保留人物、不加动画也是有效决策；需要动态呈现的段落才去选镜头。
- **镜头有出处**：从 157 张电影感镜头配方卡里比较首选与备选，确有表达缺口才写定制 MG。
- **风格与讲法有章法**：61 种画面风格目录（15 种附参考成片与可检验的标志特征）+ 解说语法表，把"这句话在做什么"（定义、对比、步骤、数据……）对应到具体画面和现成组件。
- **每一步可验证**：唯一主时间线、逐镜头小样验证、结构检查工具、真实渲染验收。

> 由 **VVAI** 在实际口播视频制作中沉淀而成，整合并适配了 [Video Use](https://github.com/browser-use/video-use)（MIT）与 [Video Shotcraft](https://github.com/Vincentwei1021/video-shotcraft)（Apache-2.0）。

## 工作流一览

```mermaid
flowchart LR
    A["🎬 输入<br/>口播视频 / 录音 / 文案"] --> B["🧭 0. 制作定位<br/>平台 × 内容 × 风格 × 时长"]
    B --> C["✂️ 1. 剪辑 / 旁白策略<br/>✅ 用户确认"]
    C --> D["🔒 2. 锁定旁白与主时间线"]
    D --> E["🎞 3. 选镜头 + 整片节奏<br/>✅ 画面方案确认"]
    E --> F["🛠 4. 分流制作<br/>逐镜头小样验证"]
    F --> G["📦 5. 合成 · 验收 · 交付<br/>成片 + 工程"]
```

## 30 秒开始

不管你用 **Claude、GPT、豆包**还是其他 AI，只要它能读写文件、执行命令（Agent / 智能体 / 编程模式），把这段话直接发给它：

```text
帮我安装「序幕」口播成片技能包。请把 https://github.com/cecilPENG53/xumu 克隆到临时目录，
再把其中 skills/ 下的 xumu、video-use、video-shotcraft 三个文件夹一起复制到你的 skills 目录
（例如 ~/.claude/skills/ 或 ~/.codex/skills/，其他 Agent 请放到它读取技能的目录），
安装完成后检查三个文件夹里都有 SKILL.md。
```

安装后直接对 AI 说：

```text
用序幕，把 D:\素材\口播01.mp4 做成 B 站横屏解说视频，3 分钟左右，先给我制作方案。
```

也可以试这些请求：

```text
这段录音 podcast.m4a 帮我做成小红书竖屏视频，保留原声，画面用插画 + 图解。
我只有一份文案 script.md，先帮我出分镜和镜头方案，不要生成配音。
把这支口播里讲数据的三段做成动态图表，其他段落保留人物画面。
这是上次的项目 outputs/ai-agents/edit/，把第 3 章节奏改快一点，重新导出。
```

## 包含什么

这是一个包含 **3 个 skill** 的技能包，平时只需要从总控入口开始，它会在需要时调用另外两个：

| Skill | 作用 |
|---|---|
| 🎛 **xumu** | **总控入口**：制作定位、剪辑策略、选镜头、主时间线、验收与交付 |
| ✂️ **video-use** | 剪辑工具：转录、剪切、调色、字幕烧录（基于 browser-use/video-use） |
| 🎞 **video-shotcraft** | 镜头库：157 张镜头配方卡、Remotion 组件与模板、动效工作台（基于 Vincentwei1021/video-shotcraft） |

> 💡 **怎么调用**：最简单的是直接对 AI 说「用序幕……」。也可以用命令：Claude 里是 `/xumu`（以插件方式安装时为 `/xumu:xumu`，冒号前是插件名、冒号后是 skill 名），GPT（Codex）里是 `$xumu`。

## 效果

- 🎙 **三种输入**：口播视频（剪辑原片）/ 录音（全片配画面）/ 纯文案（原声后录、合成配音或无旁白）
- 🧭 **制作定位**：按受众、平台、内容类型、风格强度、目标时长决定叙事结构，短篇与章节式长片分别规划
- ✂️ **原声剪辑**：逐字转录，按"从哪句到哪句"写保留表，剪点按音量对到真实停顿，帧精确拼接（音画误差不超过 1 帧）；ElevenLabs 可选，默认本地免费 faster-whisper
- ⏱ **时间写成"哪句话 + 偏移"**：画面事件跟着口播走，插入开场或改剪辑后自动顺延，不用逐处改秒数
- 🎞 **内容选镜头**：157 张 Shotcraft 镜头配方卡（开场、运镜、转场、数据、排版、节奏…），先比较首选与备选再定案
- 🎨 **61 种画面风格**：教学解说、新闻纪实、界面产品、平面设计流派、插画手作、复古、科技、东方传统（水墨、剪纸、国潮）、三维、综艺花字、贴纸科普等，每种写明观感、标志动作、适合内容和现成实现；其中 15 种可直接看 [mg-styles-15](https://github.com/Vincentwei1021/mg-styles-15) 的参考成片
- 🗣 **解说语法**：20 种句子作用 → 画面组织方式 + 去 PPT 感清单 + 手机可读字号
- 🧩 **白板一镜到底模板**：世界坐标镜头、画笔手、手绘显示器衔接真实录屏、圆形人像；已在 7 分钟成片中验证（HyperFrames）
- ✨ **定制 MG**：32 条精选灵感索引 + brief 模板 + **逐帧确定性渲染契约**（画面只由帧号决定）
- 📚 **学习模式**：把喜欢的剪辑视频、风格案例或教程发给它，归纳成"手法卡"，以后按内容自动调用
- 🔎 **动效参考检索**（可选）：一条命令下载 637 张动效卡与 HyperFrames 组件说明，用中文关键词检索
- 🧱 **唯一主时间线**：`visual-plan.json` + `plan_tools.py` 结构检查与交接清单导出
- ♻️ **改一处不重做整片**：每个镜头记录渲染指纹，修改后 `plan_tools.py diff` 列出哪些镜头要重渲、哪些只挪位置可复用；剪辑后镜头内部跟字的时刻自动顺延
- 🔌 **HyperFrames**：可作主合成引擎（如白板一镜到底）；另在「背后字幕 / Shotcraft 缺的效果 / 配乐音效」三种情况下按需调用，始终由序幕总控
- 🛠 **一键环境**：`setup_env.py` 自动检测并安装 FFmpeg、Python 依赖、faster-whisper，检查 Node.js；在独立进程里试加载转录模型，遇到部分 Windows 电脑上的 ctranslate2 崩溃会自动改装可用版本

## 适合 / 不适合

**✅ 合适**：知识科普口播 / 观点评论 / 教程讲解 / 播客切片 / 产品与方案讲解 / 章节式长视频

**❌ 不合适**：纯音乐 MV / 多机位影视剪辑 / 需要双击即用的剪辑软件 / 不允许 Agent 执行命令的环境

## 常见使用场景

| 任务 | 推荐方式 |
|------|---------|
| 口播视频做精剪 + 包装 | 视频模式：先确认删减策略，人物段保留，数据/流程段落上镜头或 MG |
| 播客 / 录音做成视频 | 音频模式：保留原声，画面需要**完整覆盖全片**（插画、录屏、图解、设计背景） |
| 只有文案 | 文案模式：先出结构和分镜；再选择原声后录、合成配音或无旁白字幕片 |
| 讲数据、讲流程 | 先比较 Shotcraft 数据/排版类配方，不够再写定制 MG brief |
| 长视频（10 分钟+） | 章节式规划，每章独立节奏与回归人物的节点 |
| 修改已有项目 | 指向项目的 `edit/` 目录，只重做受影响的镜头和字幕，不重转录未变化的源文件 |

## 使用规范（摘要）

完整版见 **[docs/USAGE.md](./docs/USAGE.md)**。

1. **先说清四件事**：发到哪个平台、给谁看、想要什么风格、大概多长。缺的 Agent 会问，但只问会影响结果的。
2. **两个确认点必须过**：剪辑/旁白策略确认、整片画面方案确认。笼统的「做个视频」不等于批准删改。
3. **素材不会被覆盖**：所有产物写在素材目录下的 `edit/`，或 `outputs/<项目名>/edit/`。
4. **授权不越界**：发布、克隆声音、上传素材、付费生成都需要你单独同意；API Key 只放环境变量，不写进计划和日志。
5. **音频自备授权**：本仓库**不包含**任何第三方音乐/音效文件。
6. **验收看真实渲染**：`plan_tools.py check` 通过只代表结构正确，不代表成片质量通过；转录对得上也不代表口播听起来顺，没试听过的声音标为「待试听确认」。
7. **交付不降规格**：正式交付前跑 `media_tools.py deliver-check`，成片分辨率不得低于原素材（竖屏 1080×1920 起），不通过不交付；草稿/预览渲染文件名带「草稿/预览」字样，不当成片交付。

## 平台支持

| AI | 状态 | 说明 |
|------|------|------|
| Claude（Claude Code / 桌面版 Cowork） | 支持 | 可用插件方式一次装齐，调用 `/xumu` |
| GPT（Codex） | 支持 | 放到 `~/.codex/skills/`，用 `$xumu` 触发 |
| 豆包 | 可用 | 需使用能读写文件、执行命令的智能体 / 编程模式 |
| Cursor / 其他 AI Agent | 可用 | 需要能读写文件、执行 shell 命令 |
| 网页 / App 聊天（ChatGPT、Claude 网页版等） | **不支持** | 剪辑和渲染要在你的电脑上执行，网页版装不了也跑不起来 |

> 判断标准只有一个：**你的 AI 能不能在你电脑上读写文件、运行命令**。能，就能用序幕。

## 安装

> ⚠️ **只能在电脑端安装和使用。** 不要把 GitHub 下载的 zip 上传到网页版的「技能」页面，也不要让网页聊天里的 AI 代装，都会失败。

### 方式一：把下面这段话直接发给 AI（通用，推荐）

> 帮我安装「序幕」技能包。请按下面步骤做：
>
> 1. 执行 `git clone https://github.com/cecilPENG53/xumu.git` 到一个临时目录
> 2. 找到你读取技能（skills）的目录，不存在就创建
> 3. 把其中 `skills/xumu`、`skills/video-use`、`skills/video-shotcraft` **三个文件夹**都复制进去
> 4. 验证三个文件夹里都有 `SKILL.md`
> 5. 告诉我安装好了，之后我说「把这段口播做成视频」就会触发

### 方式二：手动命令行

macOS / Linux：

```bash
git clone https://github.com/cecilPENG53/xumu.git
cp -r xumu/skills/* ~/.claude/skills/
```

Windows（PowerShell）：

```powershell
git clone https://github.com/cecilPENG53/xumu.git
Copy-Item -Recurse xumu\skills\* "$HOME\.claude\skills\"
```

上面以 Claude 的 `~/.claude/skills/` 为例；GPT（Codex）换成 `~/.codex/skills/`，其他 AI 换成它读取技能的目录。

### 方式三：Claude 插件命令（仅 Claude Code）

```text
/plugin marketplace add cecilPENG53/xumu
/plugin install xumu@vvai
```

更新：`/plugin marketplace update vvai`

> ⚠️ **三个 skill 必须放在同一个 `skills/` 目录下**。总控 skill 通过「同级目录」找到 video-use 和 video-shotcraft，不依赖任何作者电脑上的绝对路径。

### 运行环境

| 依赖 | 用途 | 如何获得 |
|---|---|---|
| Python 3.10+ | 剪辑、转录、计划检查 | 自行安装 |
| FFmpeg / ffprobe | 媒体处理与合成 | `setup_env.py` 自动安装 |
| faster-whisper | 本地免费转录 | `setup_env.py` 自动安装 |
| Node.js 18+ | Remotion 动画渲染 | 自行安装；`setup_env.py --remotion` 预取依赖 |
| ElevenLabs API Key | 可选：云端转录 + 说话人区分 | 设置环境变量 `ELEVENLABS_API_KEY` |
| 动效参考库 | 可选：解说语法与风格的组件检索 | `python skills/xumu/scripts/motion_index.py fetch` 后 `build`（约 155MB，需要 git 与网络） |

首次实际制作时 Agent 会自动运行环境检查；也可以手动：

```bash
python skills/xumu/scripts/setup_env.py --check   # 只报告，不安装
python skills/xumu/scripts/setup_env.py            # 缺什么装什么
python skills/xumu/scripts/setup_env.py --remotion # 需要 Remotion 动画时
```

## 仓库结构

```text
xumu/
├── .claude-plugin/
│   ├── plugin.json            # 插件清单
│   └── marketplace.json       # 插件市场清单（/plugin marketplace add 用）
├── skills/
│   ├── xumu/                  # 🎛 总控：SKILL.md + references/ + scripts/ + assets/templates/ + library/
│   ├── video-use/             # ✂️ 剪辑 helper（MIT，保留原许可证）
│   └── video-shotcraft/       # 🎞 镜头卡库 + Remotion 源码（Apache-2.0，保留原许可证）
├── docs/USAGE.md              # 使用规范
├── CONTRIBUTING.md            # 贡献规范
├── THIRD_PARTY_NOTICES.md     # 第三方来源与授权
└── LICENSE                    # MIT（仅覆盖 VV 原创部分）
```

## 项目产物

每个视频项目在 `edit/` 下产生（按需生成，不预填虚构结果）：

| 文件 | 作用 |
|---|---|
| `project.md` | 制作定位、确认记录、续作说明 |
| `edl.json` | 剪辑决定表（使用 Video Use 时） |
| `keeps.json` / `edl_voice.json` | 口播保留表与帧对齐剪辑表（`voice_edit.py`） |
| `cue_chars.json` / `sections.json` / `timing.json` | 逐字时间表、段落起止、插入段登记，供"哪句话 + 偏移"换算时间 |
| `visual-plan.json` | **唯一主时间线**：帧级时序与镜头 |
| `assets.json` | 素材来源与授权 |
| `shots/<shot_id>/` | 每个镜头独立目录；定制 MG 附 `brief.md` |
| `verify/` | 验收证据；`verify/listen/` 是剪点与疑似卡壳处的试听合集；`verify/deliver_check.json` 是成片对照原素材的交付规格报告 |

## 许可证与致谢

- VV 原创部分（`skills/xumu/`、仓库根目录文档与配置）以 [MIT](./LICENSE) 开源。
- [`skills/video-use/`](./skills/video-use/) 来自 [browser-use/video-use](https://github.com/browser-use/video-use)，保留其 MIT 许可证。
- [`skills/video-shotcraft/`](./skills/video-shotcraft/) 来自 [Vincentwei1021/video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft)，保留其 Apache-2.0 许可证；原项目的 Mixkit 音效/音乐**未随本仓库分发**。
- 风格参考片来自 [Vincentwei1021/mg-styles-15](https://github.com/Vincentwei1021/mg-styles-15)（MIT），按需用 `motion_index.py fetch` 下载到本机，不随本仓库分发。
- 详见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。

欢迎提 Issue 和 PR，参与方式见 [CONTRIBUTING.md](./CONTRIBUTING.md)。
