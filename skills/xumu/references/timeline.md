# 时间线与镜头交接契约 v1

## 范围

`visual-plan.json` 是本 Skill 的中间协议，由 Video Use 的实际 EDL 输出构建，与 EDL、Remotion props 相互独立。项目脚本负责把标准化清单转成具体的 Sequence 或合成参数。

v1 规则：整数 fps、整数帧、半开窗口 `[from, from+duration)`，背景硬切，覆盖层可以重叠。29.97 等分数帧率素材先确定交付帧率并转码。分数帧率、变速与背景交叉转场，扩展协议后再使用。

文件路径相对 `visual-plan.json` 所在目录解析，也可以用本地绝对路径。外部生成的 URL 先回收为本地文件。路径按当前系统书写；JSON 里不放凭据。

## 示例：3 秒无旁白 MG

以下是规划示例。`--ready` 前需要实际制作、验收，并更新状态与资产版本。

```json
{
  "schema_version": 1,
  "input_mode": "text",
  "timeline": {
    "revision": "edit-v1", "locked": false,
    "fps": 30, "total_frames": 90, "width": 1080, "height": 1920
  },
  "narration": {"kind": "none"},
  "shots": [
    {
      "id": "shot-001", "timeline_revision": "edit-v1",
      "role": "background", "route": "mg",
      "engine": "remotion", "style": "flat-diagram",
      "from_frame": 0, "duration_frames": 90,
      "quote": "把三个来源的资料统一分类。",
      "purpose": "解释多来源汇聚到一个分类步骤",
      "screen_text": "收集 → 分类",
      "audio_policy": "silent", "status": "planned"
    }
  ],
  "sfx": []
}
```

## 字段

- `schema_version`：整数 1。
- `input_mode`：`video | audio | text`。
- `timeline`：非空 `revision`、布尔 `locked`、整数 `fps`（1–120）、`total_frames`、正偶数 `width`/`height`。首次镜头规划与最终渲染分别记录锁定状态。
- `narration.kind`：`original | tts | none`。非 none 时包含 `file`、`locked`、`timeline_revision`；就绪时文件存在、旁白已锁定、revision 与时间线一致。none 时不带旁白文件。是否保留底片音轨按下文"唯一主声音"处理。
- 可选 `base_video`：仅 video 模式可用，包含 `file`、`timeline_revision`、`verified`，代表已实际完成的整条主剪辑底片。就绪时文件存在且已验收。
- `shots`：零个或多个镜头。有完整 video 底片时可以没有增强镜头；没有底片时，background 镜头从第 0 帧无缝覆盖到 `total_frames`。背景之间不重叠；overlay 可以重叠，按数组顺序后者压在前者之上。
- 镜头必填：唯一非空 `id`、`timeline_revision`、`role=background|overlay`、`route=real|shotcraft|mg|illustration|external|three`、非负 `from_frame`、正 `duration_frames`、非空 `purpose`、`quote`（无旁白时可为空）、`screen_text`、`status=planned|awaiting_approval|waiting_external|rendered|verified`、`audio_policy`。
- 镜头可选：
  - `engine`：`remotion | hyperframes | html | manim | ffmpeg | external`，填写时校验取值。
  - `style`：非空字符串，取 [风格目录](style-catalog.md) 的 key，或 project.md 中定义的新 key。
  - `anchor`：这个镜头时间的来源，`{"start": <引用>, "end": <引用>}` 或 `{"start": <引用>, "frames": N}`，见下节。有 anchor 的镜头，`from_frame`/`duration_frames` 由 `cue.py sync` 生成。
  - `props`：镜头的可调参数（文案、颜色、数值、开关），镜头代码从这里读取。
  - `inputs`：渲染这个镜头用到的源文件或目录（代码、brief、props 文件、素材），相对计划目录。只列源文件；目录按内容递归计算，跳过点开头的文件夹及 `node_modules`、`__pycache__`、`dist`、`build`、`out`，任何镜头的 `asset.file` 都不计入。
  - `inner_cues` / `inner_frames`：镜头内部跟字的时刻（某个词出现时弹出、敲击）。`inner_cues` 写 `{"名称": <引用>}`，`cue.py sync` 换算成 `inner_frames`（相对镜头起点的帧），镜头代码从 `inner_frames` 读取。
- `audio_policy`：`silent` 或 `separate`。视觉文件自身的音轨一律不自动混入；`separate` 必须有对应的 SFX 条目。
- `route=shotcraft` 时另需 `card` 与 `style_key`。计划工具只检查非空，名称真实性对照上游索引人工核对。
- 镜头 `asset`：`file`、`timeline_revision`、布尔 `alpha`，可选 `render_key`（由 `plan_tools.py stamp` 写入，见 [改动影响与渲染缓存](#改动影响与渲染缓存)）。就绪时镜头为 verified、文件存在，资产绑定当前 revision，或 `render_key` 与当前渲染输入一致。background 不透明，透明内容放在 overlay；透明与否由媒体实际编码决定。
- `sfx`：数组，每项含唯一 `id`、`shot_id`、当前 `timeline_revision`、非负 `offset_frames`、正 `duration_frames`、`gain`（有限值，0–4）、`file`。音效位于绑定镜头内部，该镜头 `audio_policy=separate`。全片音效分配到相应镜头窗口；主旁白不放进 sfx。

持续 BGM 暂不进入镜头协议：在 `project.md` 记录来源、起止、音量与淡入淡出，由制作工程单独管理。`narration.kind=none` 时也可以有 BGM。

## 时间引用

画面事件（镜头起止、动画元素出现、贴纸、人像放大、音效）的时间写成**引用**，由工具换算成秒和帧。开场长度、剪辑、插入段一变，重新换算就全部顺延，不必逐处改秒数。

**数据来源**（都在 edit 目录）：
- `cue_chars.json`、`sections.json`：`voice_edit.py cues` 生成，逐字记录剪后口播里每个字的起止秒数，以及每段的起止。
- `timing.json`：fps、插在口播之间的非口播段（开场混剪、片头）、片尾留白：

```json
{"fps": 30,
 "inserts": [{"id": "montage", "after_section": "O1", "frames": 588}],
 "tail_frames": 18}
```

插入段的位置可写 `after_section`、`before_section` 或 `at_voice`（口播时间秒数）；它之后的所有口播时刻自动后移。

**引用写法**（`offset` 为秒，可选）：

| 写法 | 含义 |
|---|---|
| `{"cue": "跟地图", "section": "B09"}` | 这段里"跟地图"第一个字开始的时刻；标点忽略 |
| `{"cue": "跟地图", "edge": "end", "occurrence": 2}` | 第 2 次出现时最后一个字结束的时刻 |
| `{"section": "B02", "edge": "start" \| "end"}` | 段落起止（段尾落在紧随其后的插入段之前） |
| `{"insert": "montage", "edge": "start" \| "end"}` | 插入段起止 |
| `{"at": 0.0}` | 节目绝对时间，只用于片头、片尾这类与口播无关的时刻 |

规则：
- 能用 `cue` 就用 `cue`，跟着语义词走；`at` 只用于与口播无关的时刻。
- 只匹配到文本前缀时，工具会给出 warning，说明转录与引用文本有出入，检查后改准引用。
- 在项目的合成生成脚本里通过 `from cue import Timing` 调用同一套解析，不在脚本里另写换算或手填秒数。
- 剪辑或插入段变化后：重跑 `voice_edit.py cues` → `cue.py sync --revision <新版本>` 生成新版计划（计划、镜头、音效的 revision 一起递增）→ 更新 `total_frames` → `plan_tools.py diff` 列出影响 → 只重渲需要的镜头 → `plan_tools.py check`。sync 会把窗口或 `inner_frames` 变过的 verified 镜头降为 rendered，提醒重新检查。
- 镜头内部跟字的时刻写进 `inner_cues`，不要在镜头代码里另用 `Timing` 解析。代码里自行解析的时刻不进渲染指纹，剪辑后会被误判为可复用；实在需要时把 `cue_chars.json` 列入该镜头的 `inputs`（代价是每次剪辑都重渲）。

```text
python <skill>/scripts/cue.py --edit <edit> sections
python <skill>/scripts/cue.py --edit <edit> resolve '{"cue": "跟地图", "section": "B09", "offset": 2.4}'
python <skill>/scripts/cue.py --edit <edit> sync <edit>/visual-plan.json --out <edit>/visual-plan.r2.json --revision r2
```

## 改动影响与渲染缓存

改一处不应整片重做。每个镜头从局部第 0 帧渲染，**渲染指纹**决定它的文件能否继续用。指纹包含：画布 `fps`/`width`/`height`，镜头的 `role`、`route`、`engine`、`style`、`screen_text`、`card`、`style_key`、`props`、`inner_frames`、`duration_frames`，以及 `inputs` 里每个文件的内容。不包含 `from_frame`、`quote`、`purpose`、`status`、`anchor` 与音效：只挪位置的镜头复用原文件，由合成放到新位置。

1. **渲染并验收一个镜头后**：`stamp` 把当时的指纹写进 `asset.render_key`，同时把资产绑定到当前 revision。指纹一致的资产在 revision 递增后仍然有效，不必重新绑定。
2. **修改前后**：`diff <旧计划> <新计划>` 给出影响清单，动手前把摘要告诉用户：
   - `rerender`：需要重渲，附原因（如 `duration_frames: 90 -> 60`、`props changed`、`input changed: shots/s1`）；
   - `reuse_moved`：只换了位置，复用原文件，复查新位置的接缝；
   - `unchanged`：不动；`added` / `removed`：新增或删除；
   - `unverified`：旧资产没有 `render_key`，只比较了计划字段，源文件改动看不到，需确认或重渲后 `stamp`；
   - `composite`：旁白、底片、音效或总长变化，只需重新合成。
3. **随时**：`stale <计划>` 列出哪些镜头文件仍然有效、哪些过期。`check` 也会对有 `render_key` 但已过期的资产报错。

```text
python <skill>/scripts/plan_tools.py stamp <edit>/visual-plan.json --shot <id> [--shot <id> …] --force
python <skill>/scripts/plan_tools.py diff <edit>/visual-plan.r1.json <edit>/visual-plan.r2.json
python <skill>/scripts/plan_tools.py stale <edit>/visual-plan.json
```

`stamp` 用 `--out` 写新文件，或用 `--force` 原地更新计划（只改被盖章镜头的 asset）。指纹只认 `inputs` 里声明的文件：没列进去的源码、共享设计规范或字体改了，工具发现不了，所以共享文件也要列进依赖它的镜头。整片作为一个合成工程渲染的路线（如 HyperFrames 白板一镜到底）是一个大镜头，任何改动都整片重渲。

## 运行工具

```text
python <skill>/scripts/plan_tools.py check <edit>/visual-plan.json
python <skill>/scripts/plan_tools.py check <edit>/visual-plan.json --ready
python <skill>/scripts/plan_tools.py export <edit>/visual-plan.json --out <edit>/render-manifest.json
```

工具离线运行，不调用生成服务、不渲染媒体；除 `stamp --force` 外不修改输入计划。`check` 检查类型、时间范围、版本、画面覆盖、声音归属、engine 取值与 anchor 结构；`--ready` 额外要求锁定、verified 状态与本地文件存在。`export` 先执行 ready 检查，再输出绝对文件路径、秒数与输入计划的 SHA256；目标已存在时拒绝覆盖，改用带版本的文件名。

`render-manifest.json` 保留帧时序、route、engine、style，增加 `start_seconds`、`duration_seconds`，SFX 另加全片 `from_frame`。项目级 Remotion/FFmpeg 实现从这里读取数值。

## 与原片时间的关系

无变速、无交叉转场时：`output_time = output_segment_start + source_time - source_segment_start`。同一源片段重复使用时绑定不同的 `segment_instance_id`；跨剪切的动效拆分或重新设计。定位镜头用实例 ID，而不只是原文件名加时间戳。

## 工具检查的范围

工具不检查：媒体能否解码、帧数与画幅是否真实相符、Alpha 是否存在、声音是否准确、引用数据是否真实、镜头卡是否匹配（零字节文件也能通过存在性检查）。这些由 ffprobe、静帧与短测、试听和 [整片验收](qa.md) 完成。

## 唯一主声音

使用锁定的 narration 时，禁用底片与所有视觉片段的内嵌音轨。若主剪辑底片的音轨就是目标原声，先把它提取并记录为 narration，或在项目脚本中明确只映射它一次。
