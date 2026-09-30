# 贡献规范

欢迎提 Issue 和 PR！为了让技能包保持可移植、可验证，请遵守以下约定。

## 提 Issue

请附上：

- 使用环境（Claude Code / Cowork / Codex / 其他）与操作系统
- 输入模式（视频 / 音频 / 文案）和你的原始需求
- 出问题的阶段（定位、剪辑、选镜头、制作、合成）
- `setup_env.py --check` 的输出（**删掉任何 Key 或私人路径**）
- 如涉及时间线，附 `visual-plan.json` 或 `plan_tools.py check` 的输出

## 提 PR

1. **改哪里**
   - 工作流与规则：`skills/xumu/SKILL.md` 与 `references/`
   - 工具脚本：`skills/xumu/scripts/`，请同步更新或新增 `test_*.py`
   - 第三方目录 `skills/video-use/`、`skills/video-shotcraft/`：尽量只做分发适配；功能改进请优先提交给上游项目
2. **保持可移植**：不写死任何绝对路径、用户名或插件缓存路径；依赖通过「同级 `skills/` 目录」发现。
3. **保持确定性**：定制 MG 示例必须遵守 `references/mg-prompt-patterns.md` 的确定性渲染契约（画面只由帧号决定，禁止实时计时、累积状态与无种子随机）。
4. **不提交**：`.env`、API Key、个人素材、渲染成片、`node_modules/`、`.venv/`、无授权的音乐/音效/字体。
5. **版本号**：功能变化时同步更新 `.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json` 和 `SKILL.md` 中的 `version`。
6. **自测**：

   ```bash
   python -m pytest skills/xumu/scripts
   python skills/xumu/scripts/setup_env.py --check
   ```

## 文档风格

- 中文为主，面向使用者的说明放在 `README.md` 与 `docs/USAGE.md`；英文摘要同步到 `README.en.md`。
- SKILL.md 与 references 写给 Agent 读：规则明确、可执行、少形容词。
