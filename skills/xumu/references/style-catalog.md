# 风格目录：画面语言速查

镜头的 `style` 字段取本目录的 key。选法与分层规则见 [风格与技术栈](style-stack.md)；句子级的画面组织见 [解说语法](explainer-grammar.md)；素材与字体的许可见 [素材来源](asset-sources.md)。表中 `gn:` / `hf:` 为 `motion_index.py` 可查的现成实现。

每部片通常一个主风格加至多一个辅助风格。用户没指定时，从不同大类里挑 2–3 个拉开差别的方向，各配一张代表帧。需要新风格时，先在 project.md 写下 key、观感、标志动作与实现，再使用。

标注说明：**已验证** = 在序幕实际成片中跑通；**有模板** = `assets/templates/` 下有可运行模板；**需素材** = 依赖生成图或授权图片，代码无法独立完成。其余风格目前只有目录条目与组件指引，首次实际使用时按 [风格与技术栈](style-stack.md#9-风格模板的沉淀) 沉淀模板。

## A. 教学解说

| key | 观感（底色 · 字体 · 图形） | 标志动作 | 适合内容 | 实现与素材 |
|---|---|---|---|---|
| `whiteboard-world` 白板一镜到底 **已验证 · 有模板**（[做法](whiteboard-world.md)） | 白底大画布、手写体、灰色手绘箭头串起各站点 | 一台镜头推、甩、拉，下潜进手绘显示器接真实录屏；画笔手跟随 | 教程、案例拆解、工作流讲解 | HyperFrames；`hf:whiteboard-ink` `hf:hw-arrow` `hf:pan-stations` `gn:infinite-pan`；站酷快乐体 |
| `whiteboard-ink` 白板手画 | 白板 + 马克笔，图和字一笔一笔画出来 | 描边画出、手写出字，跟口播节奏 | 知识科普、流程讲解 | `hf:whiteboard-ink` `hf:hw-write-title` `gn:handwriting-write-on`；rough.js |
| `chalkboard` 黑板粉笔 | 墨绿或黑板底、粉笔纹理、手写 | 粉笔描画、擦除转场 | 课堂感、数学、复盘 | SVG 描边 + 粉笔纹理滤镜；`gn:line-boil` `gn:scribble-wipe` |
| `notebook-doodle` 笔记本涂鸦 | 方格或横线纸、圆珠笔蓝、便利贴 | 涂鸦圈注、便利贴贴上、翻页 | 学习笔记、个人经验 | rough-notation；`hf:hw-underline` `hf:hw-callout-circle` `gn:page-turn` |
| `flat-diagram` 扁平图解 | 浅底、SVG 分层图形、实体色块 | 实体保持身份，按阅读顺序登场 | 概念、机制、流程 | `hf:flowchart` `gn:progressive-disclosure` `gn:dashed-flow` |
| `isometric` 等距 2.5D | 等距网格、立体方块、柔和阴影 | 分层抬升、爆炸拆解、镜头缓移 | 系统架构、产品结构、空间 | SVG 或 Three.js 正交相机；`gn:exploded-assembly` `gn:layer-separation` |
| `cartoon-collage` 卡通拼贴 | 米色纸纹、扁平插画剪贴、色块胶囊、手写 | 剪贴落地、近景 → 滑行 → 拉远 | 科普、轻教育 | 插画剪贴 **需素材**（Open Peeps 或生成后去背）；`hf:hw-box-label` |
| `cartoon-stage` 卡通舞台 | 明亮扁平、一景一个舞台、关节角色、无字幕 | 角色动作讲故事，机器、水、植物自己动 | 有角色的科普、社会议题 | SVG 关节角色；`gn:character-articulation` `gn:walk-cycle` `hf:lottie-character-walk` |
| `blueprint` 蓝图工程 | 蓝底白线、网格、尺寸标注、等宽字 | 线条描出结构、尺寸线展开、局部放大 | 产品原理、结构拆解、技术方案 | `gn:line-draw` `gn:outline-then-fill` `hf:svg-stroke-trace` |
| `math` 原理推导 | 素底、精确图形与公式 | 一次只变一处 | 数学、物理、算法 | Manim 或 SVG；`gn:vector-tip-to-tail` `gn:plane-transformation` |

## B. 新闻纪实

| key | 观感 | 标志动作 | 适合内容 | 实现与素材 |
|---|---|---|---|---|
| `visual-journalism` 视觉新闻 | 黑底、真实照片配来源标签、黄色荧光笔、红色警示、虚线标注 | 照片推近、荧光扫过、圈注、数字计数 | 时事、行业事件、争议话题 | `hf:vox-annotate` `hf:marker-highlight` `gn:annotation-callout`；真实图片 **需素材** 且需授权 |
| `editorial-light` 杂志编辑 | 白或米底、大留白、细线、衬线标题配小号无衬线 | 线条描出、平稳滑入 | 深度分析、商业、观点 | `hf:caption-editorial-emphasis` `gn:underline-draw`；思源宋体 |
| `documentary-archive` 档案纪录 | 老照片、胶片框、打字机文字、档案夹、日期戳 | 慢推老照片、盖章、打字 | 人物史、公司史、复盘 | `gn:ken-burns` `gn:typewriter` `gn:stamp-impact` `gn:film-dust-scratches` |
| `data-viz` 数据图解 | 干净底色、坐标与单位清晰 | 数据驱动的生长、计数、排序 | 指标、对比、趋势 | `gn-recipe:data-story` `hf:data-chart` `hf:bar-chart-race`；数值来自来源文件 |
| `map-journey` 地图叙事 | 简化地图、路线、定位钉 | 定位 → 路线描画 → 沿途标注 | 旅行、物流、地缘、扩张 | `gn:map-route-animation` `hf:world-map` `hf:nyc-paris-flight` |
| `vintage-engraving` 复古版画 | 棕黄旧纸、铜版或木刻插图、古典衬线、锈红批注 | 版画逐层显现、手写批注 | 历史、传记、发明史 | 版画插图 **需素材**（公版图或生成）；`gn:hatch-fill` `gn:outline-then-fill` |

## C. 界面与产品

| key | 观感 | 标志动作 | 适合内容 | 实现与素材 |
|---|---|---|---|---|
| `clean-ui` 干净界面 | 真实截图或真实网页为底 | 镜头推到真实按钮；尺寸与圆角变化用弹簧 | 工具教程、产品功能 | `hf:ui-focus-zoom` `gn-recipe:product-demo` `hf:browser-device-stage` |
| `white-catalog` 白底目录 | 白色网格、产品抠图、混排字体、涂鸦 | 网格逐格填入、盖章、日期块 | 产品介绍、品牌、合集盘点 | `hf:grid-card-assemble` `hf:mk-placeholder-grid` `gn:stamp-impact` |
| `glass-ui` 液态玻璃 | 半透明玻璃卡片、柔光、模糊背景 | 卡片浮起、折射扫光 | 科技产品、苹果风界面 | `hf:vfx-liquid-glass` `hf:ios26-liquid-glass` `gn:glass-refraction` |
| `terminal-code` 终端代码 | 深色编辑器或终端、等宽字、语法高亮 | 打字、逐行高亮、diff 对比 | 编程、AI 工具、开发教程 | `hf:code-typing` `hf:code-diff` `hf:code-highlight` `hf:terminal-simulator` |
| `brutalist-mono` 粗野等宽 | 黑白硬网格、等宽与窄体字、光标闪烁 | 硬切、方块位移、乱码解码 | 开发者、极客、冷观点 | `gn:hard-cut` `gn:hard-appearance` `hf:scramble-reveal` |

## D. 平面设计流派

| key | 观感 | 标志动作 | 适合内容 | 实现与素材 |
|---|---|---|---|---|
| `kinetic-type` 大字排版 | 一屏一句、字号层级克制 | 遮罩揭示，在语义词处落定 | 观点、金句、章节标题 | `gn-recipe:title-opener` `hf:per-word-rise` `gn:mask-reveal` |
| `poster-colorblock` 海报色块 | 大面积纯色场、超粗大字被画框裁切 | 色块擦除、字撞画框 | 观点冲击、口号、活动 | `hf:headline-slam` `hf:caption-kinetic-slam` `gn:kinetic-type-sweep` |
| `swiss-grid` 瑞士国际主义 | 严格网格、无衬线、不对称、红黑白 | 沿网格滑入、对齐落定 | 理性分析、方法论、设计话题 | `gn:grid-draw` `gn:motion-hierarchy` `hf:dynamic-grid` |
| `bauhaus-geometric` 包豪斯几何 | 原色圆、方、三角，几何构成 | 形状组合拼成意象、旋转咬合 | 抽象概念、结构关系 | `gn:shape-split-merge` `gn:piece-assembly` `gn:shape-built-letters` |
| `memphis` 孟菲斯 | 撞色、波浪线、点阵、几何碎片 | 弹跳、抖动、贴纸弹出 | 轻松话题、年轻向、生活方式 | `gn:jello` `gn:wobble` `hf:spring-pop` |
| `risograph` 孔版印刷 | 有限套色、套印错位、颗粒 | 图层错位抖动、颗粒闪动 | 文艺、独立品牌、读书 | 多色图层 + 混合模式；`gn:animated-dither` `gn:halftone-motion` |
| `halftone-comic` 美漫网点 | 网点阴影、粗描边、分格、拟声字 | 分格推进、拟声字爆出、速度线 | 故事化讲述、反转、娱乐 | `hf:halftone-field` `hf:halftone-dissolve` `gn:radial-speed-lines` |
| `manga` 日漫 | 黑白网点、速度线、集中线、竖排对白 | 集中线冲击、分镜格切换 | 情绪高点、二次元、游戏 | `gn:radial-speed-lines` `gn:stamp-impact`；角色 **需素材** |

## E. 插画与手作

| key | 观感 | 标志动作 | 适合内容 | 实现与素材 |
|---|---|---|---|---|
| `hand-drawn` 手绘线条 | 线条手绘、轻微抖动 | 笔触每秒变 12 次、镜头逐帧平滑 | 故事、经验分享 | p5.brush 或 SVG 描边；`gn:line-boil` `hf:hw-boil` |
| `watercolor-storybook` 水彩绘本 | 水彩晕染、纸纹、柔和笔触 | 笔刷铺色、角色轻动、翻页 | 故事、情感、童趣 | p5.brush、ClaudeAnimationBase；`gn:page-turn` `gn:popup-book`；渲染慢 |
| `paper-craft` 纸艺定格 | 纸片、撕边、投影、定格抖动 | 纸片按 8–12fps 定格移动、撕纸转场 | 手作感科普、生活 | `hf:stop-motion-cadence` `gn:paper-crumple` `gn:perforated-tear` `gn:papercut-placement` |
| `flat-vector` 扁平矢量 | 实色填充、风格化的手、扁平界面 | 形状轻微回弹 | 金融科技、App 宣传 | SVG；`gn:spring-overshoot`；Open Peeps |
| `sticker-pop` 贴纸照片 | 浅底与品牌色块交替、照片抠图、贴纸 | 抠图弹出、色块随节拍切换 | 种草、消费、电商 | `hf:badge-pop` `hf:spring-pop` `gn:scale-pop`；照片 **需素材** |
| `collage` 拼贴综艺 | 抠图贴纸、胶带、分屏、花字 | 贴纸活泼回弹，元素随节拍换 | 轻综艺、生活、反差 | HTML/CSS + 抠图；花字与原话字幕样式区分 |

## F. 复古年代

| key | 观感 | 标志动作 | 适合内容 | 实现与素材 |
|---|---|---|---|---|
| `pixel` 像素复古 | 小画布整数倍放大、关闭平滑 | 姿势按 8–12fps 量化，特效逐帧动 | 游戏、怀旧、科技史 | Canvas 2D；`gn:stepped-motion` |
| `crt-film` 老电视 / 胶片 | 扫描线、弧面、荧光点、颗粒、光晕 | 作为质感层叠在其他风格上 | 回忆、年代感 | WebGL 质感层；`gn:crt-scanlines` `gn:film-grain` `gn:vhs-tracking` |
| `retro-analog` 模拟复古 | 褪色、颗粒、70–90 年代几何字体 | 可控故障、粗推、定格 | 怀旧、音乐、娱乐 | `gn:gate-weave` `gn:film-grain` `hf:grain-overlay` |
| `vaporwave-y2k` 蒸汽波 / Y2K | 粉紫渐变、铬金属字、网格地平线、旧系统窗口 | 网格滚动、铬字旋转 | 互联网文化、潮流 | `gn:perspective-grid-drift` `hf:liquid-metal` `gn:liquid-metal` |

## G. 科技与氛围

| key | 观感 | 标志动作 | 适合内容 | 实现与素材 |
|---|---|---|---|---|
| `cinematic-dark` 电影暗调 | 近黑渐变、粒子、辉光只给物体 | 推入穿越、镜头前的光 | 发布、AI、游戏 | `hf:cinematic-zoom` `hf:godrays` `gn:atmospheric-depth` |
| `grainy-gradient` 颗粒渐变 | 深底、饱和发光形状、细颗粒 | 层层打开、镜头穿过形状 | AI、科技品牌、音乐 | `hf:mesh-gradient` `hf:flowing-gradient` `gn:mesh-gradient-flow` |
| `cyber-hud` 赛博 HUD | 深色、青与品红、扫描线、数据面板 | 扫描、解码、故障 | 科技、安全、游戏 | `hf:telemetry-hud` `hf:camcorder-hud` `hf:matrix-decode` `gn:glitch-scan-band` |
| `neon` 霓虹 | 黑底霓虹灯管字、辉光 | 闪烁点亮 | 夜生活、娱乐、潮流 | `gn:neon-sign-flicker` `hf:caption-neon-glow` `hf:lt-neon-border` |
| `luxury-dark` 奢华暗金 | 黑配金铜、柔和阴影、高挑衬线 | 慢动作、扫光、纵深 | 高端产品、品牌 | `gn:light-sweep` `hf:gloss-sweep` `hf:light-sweep-pass` |
| `pastel-playful` 糖果童趣 | 叠加粉彩、大圆形、圆体粗字 | 弹性回弹、形状绽放 | 亲子、健康、生活方式 | `gn:squash-stretch` `gn:bounce-landing` `hf:spring-pop` |

## H. 东方传统

| key | 观感 | 标志动作 | 适合内容 | 实现与素材 |
|---|---|---|---|---|
| `ink-wash` 水墨 | 宣纸底、墨晕、留白、朱红印章、楷书或行书 | 墨迹晕开揭示、毛笔描写、印章落下 | 传统文化、历史、东方美学、哲思 | `hf:ink-bleed-reveal` `gn:ink-bleed` `gn:fluid-ink` `gn:stamp-impact`；马善政楷书、霞鹜文楷 |
| `paper-cut` 剪纸皮影 | 红纸镂空、剪影、多层叠放 | 剪影分层视差、皮影关节动作 | 民俗、节日、传统故事 | SVG 镂空；`gn:papercut-placement` `gn:layer-separation` `gn:deep-parallax` |
| `guochao` 国潮 | 高饱和撞色、传统纹样、描金、粗标题 | 纹样展开、描金扫光、印章 | 国货、消费、文化 | `gn:light-sweep` `gn:stamp-impact` `gn:tiled-pattern-drift`；纹样 **需素材** 或自绘 |
| `ukiyoe-print` 浮世绘版画 | 平涂、勾线、浪纹、和纸 | 平面分层视差、浪纹循环 | 日本文化、艺术史 | **需素材**（公版图或生成）；`gn:deep-parallax` `gn:wave-warp` |

## I. 三维空间

| key | 观感 | 标志动作 | 适合内容 | 实现与素材 |
|---|---|---|---|---|
| `3d-scene` 三维场景 | 代码几何、材质、灯光 | 镜头真实推拉环绕，主体占画面三分之一以上 | 产品展示、空间结构、宏大开场 | Three.js；`gn:camera-orbit` `gn:object-turntable`；写实产品需模型文件 |
| `low-poly-voxel` 低多边形 / 体素 | 小镇、方块世界、平涂明暗 | 搭建、绕转 | 游戏、世界观、过程 | Three.js；`gn:depth-assemble` |
| `exploded-diagram` 爆炸拆解 | 部件分离悬浮、引线标注 | 分离 → 标注 → 合拢 | 产品结构、硬件 | `gn:exploded-assembly` `gn:layer-separation` |

## J. 组合方式

| key | 说明 |
|---|---|
| `person-in-scene` 人物入景 | 口播人物抠像后放进任一场景风格，见 [人物抠像进场景](style-stack.md#5-人物抠像进场景) |
| `era-mix` 年代混合 | 每个时代一种画法（如像素 → 质感层 → 3D），换风格跟着时代走，配乐与字体贯穿全片 |
