# 时间线与镜头交接契约 v1

## 使用范围

`visual-plan.json` 是本 Skill 的中间协议，不是 Video Use 的 EDL，也不是 Remotion props。保留 Video Use 的原 EDL；从其实际输出构建本计划。项目脚本负责把标准化清单转成具体 Sequence 或合成参数。

v1 使用整数 fps、整数帧、半开窗口 `[from, from+duration)`，支持硬切背景与可重叠覆盖。29.97 等素材需要先确定精确的交付帧率并转码，不能把原始分数 fps 随意四舍五入；分数帧率、变速和重叠背景转场不在当前自动检查协议内。

文件相对 `visual-plan.json` 所在目录解析，可使用绝对本地路径；外部生成 URL 先通过正式工具回收为实际文件再进入交接。跨 Windows/其他系统的路径不能直接复用。JSON 不包含凭据。

## 最小计划示例：3 秒无旁白 MG

下面是计划示例，不代表素材已生成。`--ready` 前必须实际制作、验收并更新状态和资产版本。

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

- `schema_version`：固定整数 1。
- `input_mode`：`video | audio | text`。
- `timeline`：非空 revision、locked 布尔值、整数 fps（1–120）、total_frames、偶数正 width/height。首次镜头规划与最终渲染分别记录锁定状态。
- `narration.kind`：`original | tts | none`。非 none 时包含 `file`、`locked`、`timeline_revision`；就绪时文件存在、旁白已确认、revision 与时间线一致。none 时不提供旁白文件。该字段不决定是否保留底片音轨，合成者必须按下述声音约束处理。
- 可选 `base_video`：仅 video 模式允许，包含 `file`、`timeline_revision`、`verified`，代表已经实际完成的整条主剪辑底片。就绪时存在且已验收；不能凭输入源路径假称它已经是剪后底片。
- `shots`：零个或更多镜头；有完整 video 底片时允许零个增强镜头。无底片则必须由 background shots 从第 0 帧无缝覆盖到 total_frames。背景之间不能重叠，overlay 可重叠且按数组顺序由后者压前者。
- 镜头：唯一非空 `id`、`timeline_revision`、`role=background|overlay`、`route=real|shotcraft|mg|illustration|external|three`、非负 `from_frame`、正 `duration_frames`、非空 `purpose`、`quote`（可无旁白）、`screen_text`、`status=planned|awaiting_approval|waiting_external|rendered|verified`。
- `audio_policy`：固定 `silent` 或 `separate`。所有视觉文件自身音轨不自动混入。`separate` 必须有对应 SFX 条目，避免口头说保留音效但实际上未交接。
- Shotcraft 路线另有 `card` 和 `style_key`；实际名称必须通过上游索引校验，当前计划工具只检查非空，不冒充语义验证。
- 镜头 `asset`：正式素材包含 `file`、`timeline_revision`、布尔 `alpha`。就绪时镜头为 verified，文件存在且资产绑定当前 revision；background 不允许透明空底，透明内容归 overlay。透明 asset 需符合媒体实际编码，不靠改 JSON 变透明。
- `sfx`：数组，每项为唯一 `id`、绑定 `shot_id`、当前 `timeline_revision`、非负 `offset_frames`、正 `duration_frames`、`gain`（有限、0–4）、`file`。必须位于绑定镜头内部且该镜头 audio_policy=separate。全片音效自行分配相应镜头窗口；不要把主旁白塞进 sfx。

持续 BGM 暂不进入此镜头协议，在 `project.md` 记录来源、起止、音量与淡入淡出，制作工程单独管理。`narration.kind=none` 不表示禁止 BGM；底片自带人声则须明确静音或提升为唯一旁白。

## 运行工具

```text
python <skill>/scripts/plan_tools.py check <edit>/visual-plan.json
python <skill>/scripts/plan_tools.py check <edit>/visual-plan.json --ready
python <skill>/scripts/plan_tools.py export <edit>/visual-plan.json --out <edit>/render-manifest.json
```

工具无网络、无生成调用、无媒体渲染，不修改输入计划。`check` 检查类型、时间范围、版本、画面覆盖、声音归属；`--ready` 额外要求锁定、验证状态和本地文件存在。缺文件/旧版本不静默通过。`export` 执行 ready 检查后输出绝对文件路径、秒数和输入计划 SHA256；目标已存在则拒绝覆盖，改用版本文件名。

`render-manifest.json` 不是“可直接运行的 EDL”：保留 frame 时序与 routes，增加 `start_seconds`、`duration_seconds`，SFX 增加全片 `from_frame`。生成项目级 Remotion/FFmpeg 实现时读取这些值。

## 与原时间的关系

无变速/无交叉转场：`output_time = output_segment_start + source_time - source_segment_start`。同一个源片重复使用须绑定不同 segment_instance_id；跨剪切的动效应拆分或明确重新设计。不能只用原文件名和时间戳定位镜头。

## 检查工具没有证明什么

工具不检查 MP4 是否可解码、帧数/画幅是否真的相符、Alpha 是否存在、声音是否准确、引用数据是否真实、镜头卡是否匹配。即使文件为零字节，文件存在检查也不替代媒体探测。提交前必须执行 ffprobe、静帧/短测、试听与整片 QA，见 qa.md。

实际音视频合成必须决定唯一主声音：使用锁定 narration 时禁用底片及所有视觉片段的内嵌音轨；若主剪辑底片音轨就是目标原声，先把它提取/记录为 narration，或在项目脚本中明确只映射它一次。不得同时映射二者。
