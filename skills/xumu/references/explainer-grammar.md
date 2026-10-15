# 解说语法：句子在做什么 → 画面怎么组织

第 3 步画面方案时使用：先标出每段口播里句子的**作用**（定义、对比、步骤、数据……），再按本表组织画面，并从现成库里找实现。内容来源：gongnyang/awesome-ai-motion 的决策表与配方、bang-motion 的解说规则、HyperFrames 组件库，以及序幕实际项目的经验，按中文口播改写。

## 0. 用法

1. 逐段标出句子作用（一段可以有多个），查第 2 节得到画面组织方式和候选实现。
2. 用检索补充候选，用 `show` 读参数、使用场景和禁忌：

   ```text
   python <skill>/scripts/motion_index.py search 对比 --limit 10
   python <skill>/scripts/motion_index.py search 手绘 箭头 --source hf
   python <skill>/scripts/motion_index.py show gn:split-compare hf:before-after-wipe
   ```

3. 候选与 Shotcraft 镜头、手法卡一起进入 [选择表](directing.md#5-给用户确认的画面方案)，写明采用的 ID。
4. 实现前打开原始资料：`gn:` 卡片读 `doc` 指向的 README 与参考片（含 HyperFrames 写法提示），`hf:` 组件按 hyperframes Skill 的 registry 说明装进项目。

ID 前缀：`gn:` gongnyang 动效卡（MIT），`gn-recipe:` gongnyang 组合配方，`hf:` HyperFrames 组件库（Apache-2.0）。本地参考库的下载与位置见 [后端发现](backends.md)；没有下载时可在线查阅原仓库。

## 1. 全片骨架（口播解说）

骨架是起点，按内容取舍，不必每片走满：

1. **钩子（前 5 秒）**：问题或意外结果 → 原理或对比的线索 → 本片承诺。一屏只放一个主张。参考 `gn-recipe:edu-hook`、`gn-recipe:title-opener`。
2. **把问题说出来**："为什么？""怎么做到？"单独上屏。
3. **背景**：地图、实景、截图，带标签和一处重点圈注。
4. **拆解或演示**：机制逐步揭示；真实操作用真实录屏。
5. **证据**：大数字计数后做前后对比；时间线 2–3 个节点；图表自己画出来。
6. **对观众的意义**："这对你意味着……"
7. **收尾回扣开头**，必要时列出来源。

章节长片每章用缩小版：问题 → 证据或演示 → 阶段落点。

## 2. 句子作用 → 画面语法

| 句子作用 | 口播信号 | 画面怎么组织 | 候选实现 | 避免 |
|---|---|---|---|---|
| 定义概念 | "X 就是……""所谓……" | 关键词落定 → 拆成 2–4 个组成部分依次出现，各部分保持身份 | `gn-recipe:concept-explainer` `gn:progressive-disclosure` `hf:hw-title` `hf:hw-callout-circle` | 把整句定义做成一屏大字 |
| 提问、悬念 | "为什么……？""你有没有想过" | 问句单独一屏，留白或慢推，答案下一拍再出 | `gn:mask-reveal` `hf:per-word-rise` `gn:push-in` | 问题和答案同屏出现 |
| 对比 | "以前 / 现在""不是……而是……" | 同一坐标系用前后擦除；构图不同用分屏或翻面；差异处标注 | `gn-recipe:before-after` `gn:split-compare` `hf:before-after-wipe` `hf:comparison-split` `gn:card-flip` | 坐标不同仍用擦除，暗示像素级变化 |
| 步骤、流程 | "第一步……然后……最后" | 一个连续世界里沿站点平移，每站一个动作，结尾拉远看全貌 | `hf:pan-stations` `gn:step-panel-walkthrough` `hf:hw-pipeline` `hf:flowchart` `gn:step-recap` | 每一步硬切成一页 |
| 因果、机制 | "因为……所以""导致" | 来源 → 规则 → 结果，箭头随语义词生长，关键节点高亮 | `gn:dashed-flow` `gn:path-beam` `hf:hw-arrow` `gn:process-loop` `gn:source-result-mapping` | 画出原文没有的因果连线 |
| 列举 | "有三个……""包括" | 逐项出现并打勾；或卡片依次入场后收拢成组 | `hf:marker-checklist-card` `hf:mk-specs-list` `gn:stagger` `hf:stagger-cascade` | 所有项同时出现 |
| 数据、规模 | 数字、百分比、"翻了几倍" | 先大数字计数落定，再图表生长，最后标结论；规模用重复单元网格表现 | `gn-recipe:data-story` `gn:count-up` `gn:bar-grow` `gn:unit-grid` `hf:count-up` `hf:animated-bar-chart` `hf:data-chart` | 没有来源的装饰数字 |
| 排名、趋势 | "排第一""逐年上涨" | 条形赛跑或折线自绘，终点标注 | `hf:bar-chart-race` `gn:line-chart-race` `gn:bump-rank-reveal` `hf:mk-line-graph` | 坐标轴、单位缺失 |
| 时间演进 | 年份、"那时候……后来" | 时间轴横移，2–3 个节点各一句；跨年代可换画风（`era-mix`） | `gn:timeline-scrub` `hf:pan-stations` `hf:split-flap-board` | 时间轴挤满十几个节点 |
| 地点、路线 | 地名、"从 A 到 B" | 地图定位 → 路线描画 → 沿途标注 | `gn:map-route-animation` `gn:route-highlight` `hf:world-map` `hf:nyc-paris-flight` | 与内容无关的装饰地图 |
| 引用、证据 | "官方说""研究发现""你看这里" | 真实截图或文档，荧光笔扫过原句，手写标注，标出来源 | `gn-recipe:quote-card` `hf:vox-annotate` `hf:marker-highlight` `gn:highlight-sweep` `gn:annotation-callout` `hf:yt-feather-highlight` | 合成的假截图、无来源引用 |
| 操作演示 | "点这里""打开……" | 真实录屏；镜头推到将被点击处（约 1.4–2.2 倍，0.6–0.9 秒），点击看得清，再退回看结果 | `gn-recipe:product-demo` `hf:ui-focus-zoom` `gn:zoom-callout` `gn:cursor-click` `hf:yt-camera-move` | 全屏静止录屏只有光标在动；每次点击都推 |
| 强调结论 | "关键是……""记住" | 回到人物或一句大字；关键词荧光或下划线；其他元素退后 | `gn:word-emphasis` `hf:mk-callout-highlight` `hf:hw-underline` `gn:focus-contraction` | 每句都强调，等于没有强调 |
| 介绍主体（角色、岗位、产品） | "X 负责……""它会……" | 主体图形和名称上屏，按口播里的动作词逐个出元素 | `hf:hw-box-label` `gn:character-articulation` `hf:icon-swap`，以及手法库中的相关卡 | 只摆一个图标就结束 |
| 问题升级、压力 | "越来越多""根本处理不过来" | 元素从四周涌入、堆叠、通知堆积 | `hf:overwhelm-surround` `hf:notification-pileup` `gn:overwhelm-surround` | 堆叠后不给出口 |
| 转折 | "但是""然而" | 动作方向反转、划掉旧说法换新说法、有可见触发的换色 | `gn:strikethrough-replace` `hf:strikethrough-replace` `gn:swap-entrance` `gn:match-cut` | 转折处画面没有任何变化 |
| 举例、类比 | "比如""就像" | 进入示例画面，隐喻对象可见，标"示意" | `gn:inline-image-expand` `gn:zoom-to-detail` | 把隐喻当成证据 |
| 章节切换 | "接下来""第二部分" | 章节卡或较强转场；同一证据内部推进保持空间连续 | `gn-recipe:chapter-transition` `gn:chapter-interstitial` `hf:titlecard-lockup` `hf:hw-scribble-transition` | 每个切点换一种炫技转场 |
| AI / 技术原理 | token、模型、算法 | 一镜讲原理：输入拆分 → 关系连线 → 输出选择 | `gn-recipe:ai-principle` `gn:token-split` `gn:attention-lines` `gn:next-token` `gn:embedding-space` | 用发光粒子代替机制 |
| 数学、公式 | 公式、几何关系 | Manim 或 SVG 精确推导，一次只变一处 | `gn:vector-tip-to-tail` `gn:secant-to-tangent` `gn:fourier-winding` `gn:plane-transformation` | 装饰动画代替推导 |

## 3. 一个场景怎么搭

- **逐句累积**：每个语义短语加一个元素，旧元素留在原地；一个场景到 3–5 个元素为止（主体 + 证据 + 规模 + 标签或日期 + 手写标注），合起来把事情讲清楚。
- **点名的实体必须出现**：口播提到的人、公司、产品、地点、事件，在对应场景里都要有画面。来源顺序：用户素材 → 可授权的真实图片（记出处）→ 官方页面图片（记出处）→ 生成图只用于通用物件并标"示意"；不生成真实人物面孔。找不到时先问用户。
- **证据而非装饰**：文档、截图、剪报、来源卡回答"它长什么样"。文档类元素用代码搭（白纸、细边框、等宽字、斜盖的红章），不必生成。
- **用重复表现规模**：一个单元复制成网格，比只给数字更有体感，数字仍保留。
- **一个场景一台镜头**：新元素出现时镜头小幅转视（约 ±200 像素、缩放 1–1.15），不切。
- **素材要活**：漂浮约 ±22–28 像素、1.3–1.8 秒往复，微转 ±1.5°，整场缓慢放大 1→1.06；各物体相位错开。
- **文字层级只有两级**：一句主句加一个标签。主句控制在约 12 个汉字以内，更长就拆成两拍或改成图形；文档、截图、手写批注算画面物体，不算文字层级。

## 4. 动作就是语义

| 动作 | 观众读到的意思 |
|---|---|
| 推近 | 强调、进入细节 |
| 平移 | 逐步揭示、沿着走下去 |
| 拉远 | 揭示全貌、放回语境 |
| 甩镜 | 同层级之间快速跳转 |
| 下潜进屏幕 | 从概念进入实操 |
| 慢推 | 沉思、情绪 |
| 硬切 | 重置、强对比 |
| 定格 | 强调这一瞬间 |
| 弹跳 | 轻松、俏皮 |
| 抖动 | 冲击、警告 |

按句子意思选动作。同一种动作重复使用时要有明确的系列结构。

## 5. 去掉 PPT 感

| 症状 | 改法 |
|---|---|
| 每段一页：眉标 + 两行标题 + 正文 + 徽章 | 一句主句 + 一个主体物 |
| 换场景就是换页（各段依次显隐） | 一个连续的世界，靠镜头或世界运动带出下一场景 |
| 每个切点同一种动作（同款缩放、同款转场） | 按语义选动作；转场至少两种，主次分明 |
| 镜头不动，只有文字进进出出 | 景别跟着讲述对象变：全景与近景交替 |
| 漏光、闪白每个切点都用 | 留给一个特殊时刻 |
| 平移甩到露出世界边缘 | 世界画布足够大，任何时候不露边 |
| 视频片段全屏自顾自播放，其他动画停住 | 视频作为图层绑定时间线，外层的框、设备、标注继续动 |
| 背景整片一个纯色且静止 | 背景至少两层并缓慢运动；换色要有可见触发 |
| 照搬参考视频的配色、字体、布局 | 只学节奏和能量，皮肤来自本片定位；用户点名要参考的排版除外（见 [内容到画面](directing.md#5-给用户确认的画面方案)） |
| 包名、长网址、版本号上屏 | 删掉 |

风格层面的默认陷阱见 [本片避开清单](style-stack.md#7-本片避开清单)。

## 6. 手机可读字号

以 1080 像素宽的竖屏画布为准（横屏按 1080 像素高同比例参考），任何文字不小于 30 像素：

| 文字类型 | 最小 |
|---|---|
| 标题 | 100 px |
| 正文、说明 | 44 px |
| 名称标签、年份 | 34 px |
| 手写批注 | 48 px |
| 来源、署名 | 30 px（不透明度 ≥ 0.6） |

放不下就拆到下一个场景或删掉，不缩小字号。最终以 [验收](qa.md#自检打分) 的 360 像素宽缩略图检查为准。
