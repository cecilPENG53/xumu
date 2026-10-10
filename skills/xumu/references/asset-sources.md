# 素材来源与许可

做 B-roll 需要插画、图标、字体、纹理、图片时查本表。许可信息为 2026-10 核对的结论；每次下载时以素材页面或仓库的当前许可为准，并写进 `assets.json`。

## 1. 使用规则

1. **优先级**：公有领域或 CC0 → MIT / Apache / ISC / OFL（字体）→ CC BY（需署名）→ CC BY-SA（需署名，且改编作品要以相同许可发布，用于视频前先确认）。NC（禁止商用）、ND（禁止改编）以及来源不明的素材，默认不用。
2. **每个素材记一条 `assets.json`**：来源网址、作者、许可、需要的署名文字、是否修改过、用在哪个 shot_id。
3. **需要署名的素材**，交付时把署名整理给用户放进简介或片尾。
4. **真实人物**：不生成真实人物的面孔；真实照片要有授权或属于可用的公开许可。
5. **商标与 Logo**：只在指称该品牌时使用，不改造、不暗示合作。
6. **生成图**：标"示意"，不当作事实证据（核心原则 4）。
7. **外部仓库只读**：从参考库复制到项目里用，不修改原仓库。

## 2. 插画与人物

| 来源 | 内容 | 许可 | 备注 |
|---|---|---|---|
| Open Peeps（openpeeps.com） | 手绘人物，可组合表情与姿态 | CC0（官网标注） | 下载时核对；适合 `cartoon-collage` `flat-vector` |
| Open Doodles（opendoodles.com） | 涂鸦风人物插画 | CC0（官网标注） | 下载时核对 |
| Excalidraw 社区素材库（excalidraw/excalidraw-libraries） | 手绘风图形组件：图标、设备、流程元素 | 仓库 MIT | 每个子库有各自作者，引用时记作者 |
| ClaudeAnimationBase（JohnHeibel） | p5.js + p5.brush 手绘角色动画起步模板，含 31 个表演姿态 | MIT | 适合 `watercolor-storybook` `hand-drawn` |
| Kenney（kenney.nl） | 游戏素材：像素、低多边形、UI | CC0（官网标注） | 适合 `pixel` `low-poly-voxel` |
| unDraw（undraw.co） | 扁平插画，可改主色 | 自有许可：可免费使用，不可打包再分发 | 下载时核对条款 |

## 3. 图标与 Emoji

| 来源 | 许可 | 备注 |
|---|---|---|
| Tabler Icons | MIT | 线性图标，可调描边粗细 |
| Phosphor Icons | MIT | 多种粗细与填充 |
| Lucide | 通常为 ISC（GitHub 未自动识别） | 使用前看仓库 LICENSE |
| Noto Emoji（Google） | OFL | |
| OpenMoji | CC BY-SA 4.0 | 需署名且相同方式共享，默认少用 |

手绘风图标可以先取线性图标，再用 rough.js 或 `svg2roughjs` 转成手绘感。

## 4. 手绘与质感的代码库

| 库 | 作用 | 许可 |
|---|---|---|
| rough.js | 把任意图形画成手绘感 | MIT |
| rough-notation | 手绘圈注、下划线、方框、高亮 | MIT |
| svg2roughjs | 整张 SVG 转手绘风 | MIT |
| p5.brush | 真实笔刷、水彩、纸纹 | MIT |
| Three.js | 3D 场景 | MIT |
| Motion Canvas | 代码驱动的解说动画引擎（可作参考） | MIT |
| lygia | 着色器函数库 | Prosperity 许可：商用需付费，**默认不用** |

## 5. 图片与资料

| 来源 | 许可 | 用法 |
|---|---|---|
| Wikimedia Commons | 逐个文件不同（公有领域 / CC BY / CC BY-SA） | 通过 API 读取每个文件的许可字段，按许可署名 |
| NASA 图像 | 多数为公有领域 | 查看具体页面说明 |
| 官方网站图片 | 版权归官方 | 只在介绍该对象时使用并记出处 |
| 用户提供的素材 | 用户负责授权 | 记录来源 |
| 新闻截图、影视画面 | 版权归原作者 | 默认不用，必要时先问用户 |

## 6. 中文字体

| 字体 | 风格 | 许可 |
|---|---|---|
| 思源黑体 / 思源宋体（Source Han） | 通用黑体、宋体 | OFL |
| Noto Sans SC / Noto Serif SC | 通用 | OFL |
| 霞鹜文楷（LXGW WenKai） | 楷体手写感 | OFL |
| 站酷快乐体（ZCOOL KuaiLe） | 圆润手写 | OFL（Google Fonts 版） |
| 站酷小薇、站酷庆科黄油体 | 文艺、标题 | OFL（Google Fonts 版） |
| 马善政楷书（Ma Shan Zheng） | 毛笔楷书 | OFL（Google Fonts 版） |
| 志莽行书（Zhi Mang Xing）、龙藏体（Long Cang） | 行书、手写 | OFL（Google Fonts 版） |
| Caveat | 英文手写 | OFL |

字体文件放进项目，用 `media_tools.py fontcheck` 检查缺字并生成子集。

## 7. 动效与组件参考库（本机只读）

| 库 | 内容 | 许可 | 本机位置 |
|---|---|---|---|
| gongnyang/awesome-ai-motion | 637 张动效卡（定义、参数、适用、禁忌、HyperFrames 写法）、11 个配方、参考片 | MIT | `<参考库目录>/awesome-ai-motion` |
| bang-motion | 6 种解说风格起始模板、反 PPT 规则、解说结构 | MIT | `<参考库目录>/bang-motion` |
| HyperFrames registry | 210 个场景块、237 个组件（本机只存元数据） | Apache-2.0 | `<参考库目录>/hyperframes-registry` |

参考库目录由环境变量 `XUMU_REFS` 或个人配置指定，默认与 `skills/` 同级的 `_refs/`。下载：`motion_index.py fetch`；建索引：`motion_index.py build`；检索：`motion_index.py search <关键词>`；更新时重新 `fetch` 后 `build --force`。案例合集（yihui-dev/awesome-opus5-5-videos、guanmo-ai/awesome-ai-motion）里的视频版权属于各自作者，只作为 [学习模式](learning.md) 的输入。
