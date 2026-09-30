# 第三方来源与授权 · Third-Party Notices

本仓库整合了以下第三方开源项目。它们的源码与原始许可证文件完整保留在各自目录中，仅做了与本技能包分发相关的最小适配（本机路径发现、分发提示）。

| 目录 | 上游项目 | 许可证 | 许可证文件 |
|---|---|---|---|
| `skills/video-use/` | [browser-use/video-use](https://github.com/browser-use/video-use) | MIT，Copyright (c) 2026 Browser Use | [LICENSE](./skills/video-use/LICENSE) |
| `skills/video-shotcraft/` | [Vincentwei1021/video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft) | Apache License 2.0 | [LICENSE](./skills/video-shotcraft/LICENSE) |

## 已移除的内容

- **Mixkit 音效与音乐**：Shotcraft 原项目中的 MP3 文件**未随本仓库分发**。[Mixkit 音效许可](https://mixkit.co/license/modal/sfxFree/) 禁止将音效作为工具、模板或源码附件再分发；[音乐许可](https://mixkit.co/license/modal/musicFree/) 也有使用范围限制。`skills/video-shotcraft/assets/audio/ATTRIBUTION.md` 保留了来源线索，但无法反查来源的文件不应视为自动获得许可。
- **Shotcraft 动态样片 MP4**：未内置，请访问 [在线 Gallery](https://vincentwei1021.github.io/video-shotcraft/) 查看。
- **任何 API Key、`.env`、虚拟环境、FFmpeg/Node 二进制、用户素材与预渲染成片**。

## 引用但不分发

- `skills/vv-narrative-video/references/mg-inspiration-index.json` 收录 32 条动态图形灵感的**链接与中文摘要**，不包含原提示词全文、代码或素材。
- [HyperFrames](https://github.com/heygen-com/hyperframes)、[Remotion](https://github.com/remotion-dev/remotion) 为可选外部依赖，需使用者自行安装并遵守其许可证（Remotion 对部分商业用途有单独的许可要求）。

## 使用者责任

使用本技能包制作视频时，素材、字体、音乐、声音和外部生成服务的授权由使用者自行核对，并建议记录在项目的 `edit/assets.json` 中。
