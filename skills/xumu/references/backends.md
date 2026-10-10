# 后端发现与能力边界

## 发现顺序

本 Skill 随分发包提供 `video-use` 与 `video-shotcraft` 源码，安装后与 `xumu` 位于同一个 `skills/` 目录。每个后端按以下顺序查找，找到即停：

1. **当前会话已加载的同名 Skill 或工具**。Claude Code 中插件 Skill 带前缀，如 `remotion:remotion-create`、`hyperframes:hyperframes`；Codex 中名称可能不同。
2. **用户明确指定的位置**。
3. **相邻目录**：从本文件向上定位 `xumu/`，再到同级的 `video-use/`、`video-shotcraft/`。
4. **个人配置** `backends.local.json`（可选，不随分发包提供；格式见 `backends.local.example.json`）：记录本机解释器、参考库、媒体目录等位置。带版本号的缓存目录用其中的 glob 匹配并取最新版本。

不猜测任何人电脑上的盘符、用户名或插件缓存路径。只检查本次路线需要的后端。路径存在只说明文件在；能否调用、账户是否登录、是否有余额与上传授权，以实际工具调用为准。`project.md` 记录实际使用的版本或文件哈希。

## 各后端

- **Video Use**：读取相邻 `video-use/SKILL.md` 与任务相关的 helper。剪辑和转录前运行 `scripts/setup_env.py`（先 `--check`，经用户同意再安装）。若安装器创建了 `video-use/.venv`，用对应平台的 Python 解释器运行 helper；否则验证当前 Python 环境。转录按引擎自动选择：设置了 `ELEVENLABS_API_KEY` 用 ElevenLabs Scribe（带说话人区分与音频事件），否则改用本地 faster-whisper（单说话人、词级时间戳、输出格式兼容；`VV_WHISPER_MODEL=medium` 或 `large-v3` 中文更准）。缺少密钥不阻塞制作；多人对话需要区分说话人时再建议 Scribe。检查密钥只判断变量是否存在，不输出密钥或整份 `.env`。
- **本地转录的已知问题**：部分 Windows 电脑上 ctranslate2 4.7 / 4.8 一加载模型就崩溃（进程直接退出，Python 捕获不到）。`setup_env.py` 会在独立子进程里试加载模型，检测到崩溃时提示改装已验证可用的 ctranslate2 4.6.0。
- **Video Shotcraft**：读取相邻 `video-shotcraft/SKILL.md`、`references/shots/`、`gallery/api/library.json` 及选定的准确 demo，按 [Shotcraft 选镜头](shotcraft-direction.md) 使用。分发包包含卡片和实现源码，不包含 Mixkit 第三方音频；需要声音时用接收方自己已获授权的素材。读卡不需要 `npm install`，依赖只装在使用它的镜头项目里。本地动态 MP4 样片可能缺席，按导演接入核对在线样片或自行短测，不能冒称已看过。上游 Skill 保持只读。
- **定制 MG 灵感索引**：自带 `references/mg-inspiration-index.json`（32 条精选，只有链接与中文摘要），用 `scripts/mg_inspiration.py` 按用途筛选读取，不整份载入。样片与原提示词在线读取；不可访问时标"未验证动态参考"，不阻塞制作。它只提供写法与手法参考，不附带可复用代码或素材。
- **动效参考库**（只读，可选）：gongnyang/awesome-ai-motion、bang-motion 与 HyperFrames registry 元数据，由 `motion_index.py fetch` 下载到参考库目录（环境变量 `XUMU_REFS`，或个人配置的 `refs`，默认与 `skills/` 同级的 `_refs/`），再 `motion_index.py build` 建索引后检索。许可见 [素材来源](asset-sources.md#7-动效与组件参考库本机只读)。没有下载时，解说语法与风格目录里的组件编号仍可作为线索，在线查阅原仓库。
- **手法库**：手法卡在本 Skill 的 `library/`；素材目录由环境变量 `XUMU_LIBRARY_MEDIA` 或个人配置的 `learning.media_root` 指定。见 [学习模式](learning.md)。个人配置里登记的其他只读参考库，同样只读检索。
- **Remotion**：有可用的官方 Remotion Skill 时按当前安装版本读取 `remotion-best-practices`，按任务再加 `remotion-create`、`remotion-render`；没有时查官方文档并在项目内安装相容的 Remotion 包。工程依赖版本由项目 `package.json` 决定，与文档 Skill 版本无关；升级前先做兼容验证。
- **HyperFrames**：加载 `hyperframes` 及相关子 Skill，按其规范编写与渲染；版本锁定在项目 `package.json`。作为主合成引擎的已验证版本与实测经验见 [制作路线与合成](production.md#hyperframes)；作为按需后端的用法见下文。
- **Python 与 FFmpeg**：Windows 上 `python`、`python3` 可能是微软商店占位符（会静默返回错误结果），用实际可用的解释器路径运行本 Skill 的脚本，数值计算也在该解释器里做。FFmpeg 9 已移除 `-filter_complex_script`，滤镜图写进文件时用 `-/filter_complex <文件>`。
- **HTML 逐帧**：需要 Node、项目内安装的 Playwright 与 FFmpeg。
- **Three.js / p5.js / Manim**：按路线需要装在项目内，先渲一帧验证。
- **外部图像、视频、配音**：通过当前会话的工具确定可调用的具体服务。Skill 或工具名称存在，不证明账户、余额、上传授权或生成能力。

## 不可用时

告诉用户缺少的最小条件，同时推进不依赖它的工作：草案、镜头任务、代码可视化、手工生成交接包。安装插件、购买、切换供应商需用户同意；密钥只留在环境变量里。关键依赖缺失且没有已授权的替代时，停在受阻阶段。

第三方 Skill 的代码只在项目内适配，其全局行为保持原样。序幕吸收 Video Use 的生产正确性、Shotcraft 的选镜头与编排方法、风格技术栈的绘制手法，由一个总控统一时间线与确认流程。

## HyperFrames 按需接入

HyperFrames 是另行安装的独立插件，不随本包分发。除了被选为主合成引擎（见 [风格与技术栈](style-stack.md#3-渲染引擎)），它只在下列三个条件之一成立时使用；每次直接调用对应子 Skill，不经过 `/hyperframes:hyperframes` 入口，不跑它的需求访谈，不建立第二条主时间线。条件不成立就不读取 HyperFrames 文件；它的子 Skill 文档很大，只为实际要做的那一项加载。

| 触发条件 | 调用 | 产物如何回到本片 |
|---|---|---|
| 用户明确要"字幕放在人物后面"、特效字幕、"炸"字幕，或点名其字幕风格 | `/hyperframes:embedded-captions` | 带字幕的人物段 MP4，作为该时间段底片 |
| 用户点名的效果或质感（如 CRT、故障、胶片颗粒、地图、终端窗口）在 Shotcraft 中没有对应卡 | 先 `npx hyperframes catalog --query "<英文描述>" 2>/dev/null \| head -12` 搜一次（按相关度排序，只看前 8 条；查询必须用英文，中文返回空），或用 `motion_index.py search` 查本地元数据；有合适条目再加载 `/hyperframes:hyperframes-registry` 安装使用 | 单独渲染的镜头 MP4，或 `--format webm/mov` 透明叠加层 |
| 需要配乐或音效而用户没有授权素材，且用户同意使用 HeyGen 账户 | `/hyperframes:media-use` 的 `resolve --type bgm/sfx` | 固定到本地的音频文件 |

通用规则：

- **工程位置**：每项在 `edit/shots/<shot_id>/hyperframes/` 独立建工程，不写进用户原素材目录或本 Skill 目录。
- **时间与记录**：时长和起点以 visual-plan.json 为准。效果库镜头记 `route=mg`，并在 assets.json 记条目名和"HyperFrames Registry"；背后字幕人物段记 `route=real`，注明字幕由 embedded-captions 生成；配乐音效在 assets.json 记来源与授权条款。
- **不用的部分**：它的 faceless-explainer、talking-head-recut、product-launch-video、general-video 与本 Skill 功能重叠，本 Skill 主导的项目不调用。
- **权限**：首次运行可能安装 npm 依赖、下载抠像与转录模型，media-use 需要 HeyGen 账户登录；这些都先告知用户再做。不自动运行 `skills update`，不自动发送 `hyperframes feedback` 缺口报告（会把查询发到外部），需要时先问用户。

### 背后字幕的衔接

embedded-captions 要求单人、单镜头、原片不做改动，自己做抠像并把字幕合成进人物画面。接入时：

1. 只把剪辑后人物可见、无全屏覆盖的连续片段逐段送入；全屏 MG 段不送。
2. 转录复用本片已锁定的词级转录：换算成该片段的相对时间，写成 `{ "words": [{ "text", "start", "end", "type": "word" }], "language_code" }` 放进其工程的 `transcript.json`，它检测到后会跳过重新转录。它自己的转录与本片不一致时，以本片锁定文本为准。
3. 字幕规范只有一套：人物段由 embedded-captions 出字幕；全屏 MG 段由本 Skill 按它输出的底部字幕（rail）的字体、字号、颜色和位置补齐，并在 project.md 记录这套规范。
4. 这是"字幕最后烧录"的唯一例外：人物段在叠加覆盖层之前已带字幕，所以这些段的覆盖层不能遮挡字幕区和背后大字；叠加后逐段抽帧检查。
5. 默认用安静的底部字幕，背后大字每个段落最多一个，遵循它自身"embed 要少而精"的规则。

## 配置

分发包不含个人路径配置、凭据、cookie 或已安装的二进制。个人配置 `backends.local.json` 只存非秘密的路径线索，已列入 `.gitignore`；API key、cookie、令牌与服务端点不写进去。作者机上的版本核验值不作为接收方可用性证明。plan_tools 只校验与导出计划；后端调用由 Agent 按路线执行，并留下渲染与验收证据。
