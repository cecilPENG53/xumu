# 后端与能力边界

## 跨电脑发现

本 Skill 随分发包提供 `video-use` 与 `video-shotcraft` 源码。安装后，它们应与 `vv-narrative-video` 位于同一个 Codex `skills/` 目录。优先使用当前会话已加载的同名 Skill；需要读取源码时，从本文件向上定位 `vv-narrative-video/`，再到相邻的 `video-use/`、`video-shotcraft/`。用户明确指定的其他安装位置优先。不得猜测 `C:` 盘、作者用户名或插件缓存路径。

- **Video Use**：读取相邻 `video-use/SKILL.md` 与任务相关的 helper。剪辑和转录前运行 `../scripts/setup_env.py` 自动安装 Python 依赖、FFmpeg/ffprobe 与 faster-whisper。若安装器创建了 `video-use/.venv`，调用对应平台的 Python 解释器运行 helper；否则验证当前 Python 环境。转录默认按引擎自动选择：设置了 `ELEVENLABS_API_KEY` 用 ElevenLabs Scribe（带说话人区分与音频事件），否则自动改用本地免费的 faster-whisper（单说话人，词级时间戳，输出格式兼容；`VV_WHISPER_MODEL=medium` 或 `large-v3` 可提高中文准确率）。不因缺少密钥阻塞制作；多人对话需区分说话人时再向用户建议 Scribe。只检查变量是否存在，不输出密钥或整份 `.env`。
- **Video Shotcraft**：读取相邻 `video-shotcraft/SKILL.md`、`references/shots/`、`gallery/api/library.json` 及选定的准确 demo。分发包包含卡片和实现源码，但不包含 Mixkit 第三方音频；需要声音时使用接收方自己已获授权的素材。本地动态 MP4 样片也可能缺席，应按 [导演接入](shotcraft-direction.md) 核对在线样片或自行做短测，不能冒称已看过。
- **定制 MG 灵感索引**：本 Skill 自带 `references/mg-inspiration-index.json`（32 条精选，仅链接与中文摘要），用 `scripts/mg_inspiration.py` 按用途筛选读取，不整份载入。样片与提示词原文在线读取，需要网络；不可访问时标“未验证动态参考”，不阻塞制作。它只提供写法与手法参考，不附带任何可复用代码或素材。
- **HyperFrames（可选，按需）**：见下方“HyperFrames 按需接入”。未安装或不可用时直接跳过，不阻塞任何流程。
- **Remotion**：有可用的官方 Remotion Skill 时按当前安装版本读取；没有时可查官方文档并在实际项目内安装相容的 Remotion 包。Skill 文档版本不等于工程依赖版本。Node.js、浏览器渲染环境、字体和素材需在接收方电脑验证。
- **外部图像、视频与配音**：通过当前会话工具发现具体服务。Skill 或工具名称存在，不证明账户、余额、上传授权或生成能力。

按所选路线检查依赖，不在只讨论方案时安装全部工具。缺少能力时说明最小条件，并继续能独立完成的草案、镜头任务或交接包。初版 `plan_tools.py` 只校验和导出计划，不自动调用上述后端。

## HyperFrames 按需接入

HyperFrames 是另行安装的独立插件，不随本包分发。它只在下列三个条件之一成立时使用，每次直接调用对应子 Skill，不经过 `/hyperframes:hyperframes` 入口，不跑它的需求访谈，不建立第二条主时间线。条件不成立就不读取任何 HyperFrames 文件；它的子 Skill 文档很大，只为实际要做的那一项加载。

| 触发条件 | 调用 | 产物如何回到本片 |
|---|---|---|
| 用户明确要“字幕放在人物后面”、特效字幕、“炸”字幕，或点名其字幕风格 | `/hyperframes:embedded-captions` | 带字幕的人物段 MP4，作为该时间段底片 |
| 用户点名的效果或质感（如 CRT、故障、胶片颗粒、地图、终端窗口）在 Shotcraft 中没有对应卡 | 先 `npx hyperframes catalog --query "<英文描述>" 2>/dev/null \| head -12` 搜一次（结果按相关度排序，一次可能返回 50 条以上，只看前 8 条；查询必须用英文，中文返回空）；有合适条目再加载 `/hyperframes:hyperframes-registry` 安装使用 | 单独渲染的镜头 MP4，或 `--format webm/mov` 透明叠加层 |
| 需要配乐或音效而用户没有授权素材，且用户同意使用 HeyGen 账户 | `/hyperframes:media-use` 的 `resolve --type bgm/sfx` | 固定到本地的音频文件 |

通用规则：
- **工程位置**：每项在 `edit/shots/<shot_id>/hyperframes/` 独立建工程，不写进用户原素材目录或本 Skill 目录。
- **时间与记录**：时长和起点以 visual-plan.json 为准。效果库镜头记 `route=mg`，并在 assets.json 记条目名和“HyperFrames Registry”；背后字幕人物段记 `route=real`，注明字幕由 embedded-captions 生成；配乐音效在 assets.json 记来源与授权条款。
- **不用的部分**：它的 faceless-explainer、talking-head-recut、product-launch-video、general-video 与本 Skill 功能重叠，vv 主导的项目不调用。
- **权限**：首次运行可能安装 npm 依赖、下载抠像与转录模型，media-use 需要 HeyGen 账户登录；这些都先告知用户再做。不自动运行 `skills update`，不自动发送 `hyperframes feedback` 缺口报告（会把查询发到外部），需要时先问用户。

### 背后字幕的衔接

embedded-captions 要求单人、单镜头、原片不做改动，自己做抠像并把字幕合成进人物画面。接入时：
1. 只把剪辑后人物可见、无全屏覆盖的连续片段逐段送入；全屏 MG 段不送。
2. 转录复用本片已锁定的词级转录：换算成该片段的相对时间，写成 `{ "words": [{ "text", "start", "end", "type": "word" }], "language_code" }` 放进其工程的 `transcript.json`，它检测到后会跳过重新转录。它自己的转录与本片不一致时，以本片锁定文本为准。
3. 字幕负责人仍只有一个规范：人物段由 embedded-captions 出字幕；全屏 MG 段由本 Skill 按它输出的底部字幕（rail）的字体、字号、颜色和位置补齐，并在 project.md 记录这套规范。
4. 这是“字幕最后烧录”的唯一例外：人物段在叠加覆盖层之前已带字幕，所以这些段的覆盖层不能遮挡字幕区和背后大字；叠加后逐段抽帧检查。
5. 默认用安静的底部字幕，背后大字每个段落最多一个，跟随它自身“embed 要少而精”的规则。

## 配置与记录

分发包不含个人路径配置、凭据、cookie 或已安装二进制。需要自定义位置时，由接收方在自己的项目记录中写实际位置；`project.md` 记录真正用到的版本或哈希。不得把作者机上的版本核验值当作接收方可用性证明。
