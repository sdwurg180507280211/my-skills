---
name: wechat-medical-writer
description: 医学类微信公众号/服务号的轻量编排 Skill。它只提供医学领域上下文、必要医学事实约束和 upstream handoff，不自定义文章结构、标题方法、研究流程、模板、Claim Ledger 或发布实现。主题到高质量文章必须交给本仓库随 utility-skills 一起提供的 content-research-writer；普通概念插图、常规排版与发布按需复用苍何，统计图/论文式 Figure/多面板图必须读取本 Skill 的 medical-figure-design 并优先使用可控 plotting/SVG/HTML/vector 锚定数据与文字；访谈/Q&A/卡片等复杂公众号布局可按需使用外部 xiaohu-wechat-format；用户明确要求“光愈在线式”头像访谈时，可在 xiaohu 输出后调用本 Skill 的轻量品牌适配器。当前领域方向为女性健康、妇科、宫颈疾病、HPV、HSIL、CIN2/CIN3、生育力保护、PDT/HAL-PDT 等。用户上传的医学 ZIP/PPT/公众号样本只用于领域方向、当次资料或视觉参考，原件不提交仓库。
---

# Medical WeChat Writer

## 定位

这是一个**医学领域适配与编排层**，不是新的通用写作引擎。

它只负责：

1. 告诉上游 Writer 当前服务号长期关注哪些医学领域；
2. 把用户本次提供的医学资料、参考文章和约束传给上游 Writer；
3. 增加少量医学事实边界，避免把营销材料、样稿或模型常识当成医学证据；
4. 在需要配图、复杂排版或上传时，把成稿继续交给成熟 upstream；
5. 对已经完成的高级排版 HTML，可按用户明确要求叠加极小的品牌视觉适配，不介入写作和医学事实。

它**不负责重新发明**：选题方法、Hook、标题方法、大纲方法、文章节奏、固定文章模板、研究工作流、公众号排版引擎、配图生成或微信发布代码。

## 当前医学方向

当前领域方向来自用户提供的私有医学资料包，但资料包只定义“以后主要写什么”，不定义“文章必须怎么写”。

领域概览：

```text
女性健康
└── 妇科 / 宫颈健康
    ├── HPV 感染与持续感染
    ├── 宫颈癌筛查与防治
    ├── LSIL / HSIL
    ├── CIN2 / CIN3
    ├── 阴道镜 / 病理 / 风险分层
    ├── 生育需求与宫颈功能保护
    ├── 观察与治疗选择
    └── PDT / HAL-PDT
```

更完整的范围见 `references/domains/cervical-health.md`。

注意：这个领域文件只是 taxonomy，不是医学知识库，也不是文章模板。

## 上游优先

### 主题 → 研究 → 高质量文章

必须使用：

```text
content-research-writer
```

它负责其原生的研究、资料整理、大纲、引用、Hook、正文创作、迭代和最终润色流程。本 Skill 不复制或重写这些能力。

由于该 upstream 目前不在用户可用的插件市场中，本仓库已经按 MIT License 将其 vendored 为独立 `skills/content-research-writer/`，并加入 `utility-skills` bundle。安装 `utility-skills@my-skills` 后，应直接使用这个本地 Skill，不再因为“市场里没有 upstream”而启用自制 fallback Writer。

如果用户只手动安装了 `wechat-medical-writer` 而没有安装 `content-research-writer`，应明确提示补装同仓库的 `content-research-writer`，不要自己重写一套 Writer。

### 强制 Handoff Contract

**在开始大纲、研究或正文之前，先把通用写作阶段交给 `content-research-writer`。** 不允许先由本 Skill 自己写一篇，再把 upstream 当作可选润色器。

向主 Writer 传递当前已经知道的上下文，至少包括可获得的：

```text
topic               当前主题 / 核心问题
audience            医生 / HCP / 患者 / 公众 / 其他
goal                教育 / 解读 / 综述 / 证据分析等
format_length       用户指定的形式与篇幅（如有）
user_sources        当前附件、私有资料或指定来源
reference_sample    用户给的优秀公众号样稿（如有）
style_constraints   用户指定的语气、完成度、引用方式（如有）
medical_context     references/domains/cervical-health.md
medical_constraints references/medical-constraints.md
```

规则：

- 上下文里已经明确的信息不要重复询问用户；
- 真正影响准确性、受众或任务目标的必要信息缺失时，再按主 Writer 原生流程询问；
- 用户明确说“直接写一篇 / 一口气完成 / 给我成稿”时，仍使用主 Writer 的原生步骤，但可在同一轮连续完成大纲 → 研究 → 草稿 → 引用检查 → 最终润色，不必人为停在每个协作节点等待确认；
- 如果运行环境实际上无法调用或加载 `content-research-writer`，停止正文创作并报告缺少依赖；**不得改成模型自行执行一个隐形 fallback Writer**。

### 可选表达优化

`Viral Writer` 只可在用户明确要求更强的公众号传播表达、标题或节奏时作为**可选润色层**。它不得新增、删除或改写医学事实、数字、指南结论、适应证、监管状态和参考文献。

## 医学约束

只叠加上游通用 Writer 不具备的医学边界，见 `references/medical-constraints.md`。

核心要求：

- 不虚构指南、共识、论文、作者、年份、DOI/PMID、样本量、统计结果或监管状态；
- 不把课件、营销材料或参考文章中的推广语直接升级成医学事实；
- 面向公开发布的医学文章，即使用户没有额外说“核验”，关键医学数字、指南推荐、疗效/安全性、适应证和监管结论也应有可追溯来源；
- 用户明确要求“只基于我提供的资料、不做外部核验”时可以遵从，但最终稿要明确标识这一来源边界；
- 成稿前检查正文引用与参考文献一一对应，具体数字能够回到实际来源；
- 如果当前来源不足以支持某个医学结论，明确说明不足，不替用户补一个确定答案；
- 不强制生成 Claim Ledger、source map、固定审核表或额外工作目录，除非用户明确要求。

## 处理用户资料

### 医学 ZIP / PPT / PDF

用户提供的医学资料可能有两种作用：

- **领域方向**：告诉系统长期关注哪些疾病、诊疗场景和专业主题；
- **当次来源**：用户明确要求基于这些资料写文章时，把资料交给上游 Writer 使用。

不要因为资料曾经被用于定义领域，就默认以后每篇文章只能来自这些资料。

不要把原始 ZIP/PPT/PDF、内部培训材料、未公开资料或患者资料提交到本 GitHub 仓库。

### 参考公众号文章 / HTML 样本

如果用户提供优秀公众号文章、截图、HTML 或文章打包 ZIP 作为样稿：

- 写作层可以把它作为结构、语气、信息密度、标题层级、引用呈现方式和整体完成度的参考；
- 排版层可以把真实 HTML 中反复出现的颜色、尺寸和组件作为**视觉画像**；
- 不把样稿里的医学结论、数字或参考文献自动视为已核验来源；
- 不把某一篇样稿的固定结构硬编码成以后所有文章的写作模板；
- 原始 HTML、图片、视频和打包 ZIP 不提交公共仓库。

#### 参考样稿解析优先级

有真实 HTML 时，**真实 HTML 是排版事实源，截图只是视觉补充**：

```text
真实已发布 HTML      → 精确字号 / 行高 / 间距 / DOM / inline style
截图                 → 色彩 / 视觉比例 / 屏幕密度 / 整体观感
用户口头反馈         → 最终偏好与覆盖规则
浏览器预览猜测       → 最低优先级
```

不要把父容器的继承字号误当成正文实际字号，也不要只看截图肉眼猜 CSS。

如果用户明确点名压缩包里的某一篇文章“从头到尾参考”，优先匹配**该篇**的：

```text
标题密度
正文连续性
Figure 插入节奏
Reference 呈现方式
组件密度
```

不要把整个样本库里出现过的组件全部叠到一篇文章上。

#### 内容结构 ≠ 视觉标题数量

一篇文章逻辑上可以回答 8～10 个问题，但视觉上不一定需要 8～10 个标题组件。

高还原排版优先：

```text
少量真正的大章节
+ 连续正文
+ Figure / 表格在论证位置穿插
+ 粗体承担局部强调
```

不要机械执行：

```text
每个问题 → 一个大标题卡
每个重点 → 一个 Quote 卡
每个列表 → 一个新卡片
```

**High fidelity 不是“把所有品牌组件都用上”，而是复用最接近参考文章的组件语法与密度。**

如果用户直接给出公众号样式编号（如 `标题-02 + 正文-02 + 参考文献-01`），先读取：

```text
references/layouts/wechat-component-library.md
```

这些稳定 ID 是明确的排版约束。优先复用 image-gallery 当前组件实现，不擅自换成别的同类样式，也不要在用户指定组合之外堆叠大量大型组件。

当用户明确要求“光愈在线式 / 类似我提供的光愈在线公众号排版”时，排版前读取：

```text
references/layouts/guangyu-online.md
```

这个文件只记录视觉 Token、组件画像、真实 HTML 参数、组件密度和 formatter 映射，不参与医学事实判断，也不决定上游 Writer 的论证结构。

## 配图 / 排版 / 草稿箱

这些步骤是**按需下游**，不要阻塞纯写作任务。

### 0. 品牌资产与封面

只要成品明确属于“医荟她健康”，需要 Logo / KV / 品牌图或公众号封面时，先读取：

```text
references/brands/yihui-she-health.md
```

已入库品牌图片以独立 `image-gallery` 为二进制事实源；不要因为本 Skill 仓库没有 PNG 就重新生成近似 Logo/KV。4 个 Logo 当前是候选方案，用户未指定主 Logo 时不要擅自固定其中一个。

公众号封面无特殊说明时按 **2.35:1** 生成或裁切，并按移动端缩略图检查主题识别度。

### 1. 配图

先区分两类任务，不再把所有“正文插图”都统一路由到 illustration generator。

#### 普通概念插图

没有精确坐标、真实统计数字、复杂表格或多 Panel 专业文字时，可优先使用：

```text
canghe-article-illustrator
```

医学配图继续遵守 `references/medical-constraints.md`。

#### 统计图 / 论文式 Figure / 多面板科学图

只要图中包含精确数字、坐标、表格、图例、多 Panel 或大量专业文字，就视为 scientific figure。必须读取：

```text
references/medical-figure-design.md
```

这类任务优先：

```text
可控 plotting / SVG / HTML / vector
→ 锁定数据与文字
→ 必要时再用 image generation 做视觉润色
```

**不要因为“正文插图默认走 canghe-article-illustrator”而覆盖 scientific figure 的可控绘图路由。**

最重要的 Figure Contract：

```text
current_article      决定画什么
verified_sources     决定数字和医学结论能不能画
visual_references    只决定复杂度 / Panel 密度 / 视觉语法
```

即：

> **借复杂度，不借内容；借版式，不借证据。**

生成 Figure 前，从当前冻结稿或最终 HTML 反推 Panel 内容；不要因为参考 Figure 里有弦图、年龄分层、季节曲线，就在当前文章没有这些内容或数据时照搬。

如果文章本身有多个互补信息结构，而参考图也是论文式高复杂度 Figure，不要无故把它压缩成低信息密度卡通图；复杂度应来自真实数据、矩阵、分组与 Panel，而不是装饰。

两张及以上高信息密度 Figure 时，先按整篇文章做 placement map。避免连续堆图；必要时可连同只服务于该 Figure 的“最小支撑段落”一起移动，并通过前向提示与桥接句维持论证连续性。具体规则见 `references/medical-figure-design.md`。

中英文版本视为同一 Figure 的本地化重绘；Caption 语言跟随目标场景和用户要求，不默认“英文 Figure caption + 中文图注”。文本密集科学图不要把生成模型当作唯一翻译/排版层。

数据图只使用已核验数据并保留来源；机制图不得把推测画成已证实因果；产品/器械优先使用用户提供的官方素材，不让生成模型虚构官方产品资产。

若图像生成模型自动写错作者、期刊、DOI/PMID、来源、数字、图例或术语，优先移除/重绘错误内容，由可控绘图层和正式 HTML References 管理事实与引用。

### 2. 排版路由

不要把所有文章强制交给同一个 formatter。根据用户要求和参考样稿选择：

```text
用户明确指定组件 ID
→ 读取 references/layouts/wechat-component-library.md
→ 按指定稳定 ID 组合对应 inline HTML

普通学术长文 / 常规公众号正文
→ canghe-markdown-to-html

专家访谈 / Q&A / 对话气泡 / 导语卡 / 卡片 / timeline / hero 等组件化布局
→ xiaohu-wechat-format（外部可选 upstream）

用户明确指定“光愈在线式”视觉
→ 先读取 references/layouts/guangyu-online.md
→ 匹配点名参考文章的正文密度 / 标题密度 / Figure / Reference 语法
→ xiaohu-wechat-format 负责 Markdown → 微信兼容 HTML（适用时）
→ 若需要高还原头像访谈卡，再调用 scripts/enhance_guangyu_dialogue.py
```

`xiaohu-wechat-format` 已审计能力包括 Markdown → 微信兼容 inline HTML、`:::dialogue`、`:::intro`、gallery/stat/timeline/steps/compare 等容器，以及 interview 等主题。它只作为**高级布局 formatter** 使用；不要同时启用它自己的封面生成或 `publish.py`，避免和现有苍何配图/发布链重复。

当前审计版本的 `:::dialogue` 原生实现是“说话人文本 + 左右交替气泡”，没有头像字段。本 Skill 的 `scripts/enhance_guangyu_dialogue.py` **不是另一个 formatter**：它只读取 xiaohu 已生成、带 `data-container` 标记的 HTML，把 `:::intro` 的视觉改成样本中的红色完整描边导语卡，并给已存在的左右 dialogue 注入用户提供的 Logo / 专家头像和品牌红头像环、灰色气泡与轻量 CSS 对话尾巴。

高还原头像访谈的最小流程：

```text
article.md
→ xiaohu-wechat-format（建议 interview 主题 + :::intro / :::dialogue）
→ formatted.html
→ enhance_guangyu_dialogue.py + avatars.json
→ formatted.guangyu.html
→ canghe-post-to-wechat
```

`avatars.json` 是运行时输入，例如：

```json
{
  "光愈在线": "assets/logo.png",
  "梁静教授": "assets/liang.png"
}
```

执行示例：

```bash
python3 scripts/enhance_guangyu_dialogue.py \
  --input /path/to/formatted.html \
  --avatars /path/to/avatars.json \
  --output /path/to/formatted.guangyu.html
```

约束：

- 头像/Logo 必须由用户提供或使用用户有权使用的真实素材；不让生成模型冒充真实专家头像或官方 Logo；
- `avatars.json`、头像、Logo 和生成 HTML 都是运行时文件，不提交本仓库；
- speaker 名称必须与 `:::dialogue` 中的说话人文本一致；缺少头像映射时脚本失败并列出缺失 speaker，**不静默降级**；
- 脚本不解析 Markdown、不生成医学内容、不生成图片、不上传微信、不读取用户原始样本；
- 当前只补 `intro + avatar-dialogue`。顶部 HOT 关注条、完整 Summary 线条组合、END 品牌装饰等仍是独立的小型品牌组件，不宣称已经 1:1 完整复刻。

此外，xiaohu 仓库 README 声明 MIT，但当前 GitHub 仓库元数据未识别许可证且根目录没有独立 `LICENSE` 文件。因此本仓库**只记录和调用外部 upstream，不 vendor、不复制其实现**，直到许可证文本明确。我们的品牌适配器只依赖它输出的公开 `data-container` HTML 契约，不复制 xiaohu 源码或主题。

外部安装方式以其仓库 README 为准，当前为：

```bash
cd ~/.claude/skills/
git clone https://github.com/xiaohuailabs/xiaohu-wechat-format.git
cp xiaohu-wechat-format/config.example.json xiaohu-wechat-format/config.json
pip3 install markdown requests
```

纯排版不需要填写其微信公众号 AppID/AppSecret。

### 3. 发布

发布统一保留一条链：

```text
canghe-post-to-wechat
```

无论 HTML 来自 `canghe-markdown-to-html`、`xiaohu-wechat-format`，还是在 xiaohu HTML 上经过本地品牌适配，最终都优先交给苍何发布，不同时维护两套草稿箱上传逻辑。

公众号草稿有独立的标题字段，成稿正文的 HTML 里不要再放 `<h1>` 大标题，避免草稿里标题重复；副题、引言行这类非标题元素可以保留。

### Downstream preflight

如果用户只要求研究或写文章，不要求任何排版/发布 upstream。

需要苍何时，缺少则给出标准安装方式：

```text
/plugin marketplace add freestylefly/canghe-skills
/plugin install content-skills@canghe-skills
/plugin install utility-skills@canghe-skills
```

需要高级访谈/组件化布局且 `xiaohu-wechat-format` 未安装时，给出上面的外部安装方式；不要静默退化成自己编造一套复杂 HTML 组件。

详细 upstream 审计与职责见 `references/upstreams.md`。

## 推荐编排

```text
用户主题 / 用户资料 / 参考文章
        ↓
wechat-medical-writer
只补充领域上下文 + 医学约束
        ↓
【MANDATORY】content-research-writer
使用其原生写作流程完成研究与成稿
        ↓
引用完整性 / 医学事实边界检查
        ↓
（可选）Viral Writer
只做表达/标题/节奏润色，不改变医学事实
        ↓
按需配图路由：
├─ 普通概念插图 → canghe-article-illustrator
└─ 统计图 / 论文式 Figure / 多面板图
   → medical-figure-design.md
   → controllable plotting / SVG / HTML / vector
   → 必要时视觉润色
        ↓
排版路由：
├─ 指定样式 ID → wechat-component-library.md → 精确组件组合
├─ 常规文章 → canghe-markdown-to-html
├─ 访谈/Q&A/组件化 → xiaohu-wechat-format
└─ 光愈在线式 → 读取 guangyu-online.md；头像访谈再叠加本地 adapter
        ↓
统一：canghe-post-to-wechat
        ↓
微信公众号草稿箱
```

## 输出

本 Skill 不规定固定输出文件集合。

默认以**上游 Writer 的原生输出**为准。通常是一篇可继续处理的 Markdown 文章；是否同时输出研究笔记、引用列表、标题方案、配图建议等，由上游 Skill 和用户当前要求决定。排版和品牌适配产生的 HTML、头像映射 JSON 仍属于运行时产物，不进入公共仓库。

## 仓库边界

`wechat-medical-writer` 自身保存：

```text
SKILL.md
README.md
references/domains/cervical-health.md
references/medical-constraints.md
references/medical-figure-design.md
references/upstreams.md
references/layouts/guangyu-online.md
references/layouts/guangyu-launch-first-article.md
references/layouts/wechat-component-library.md
references/brands/yihui-she-health.md
scripts/enhance_guangyu_dialogue.py
tests/test_guangyu_dialogue.py
```

用户原始医学资料、第三方公众号 HTML、图片、视频、头像、Logo 和 ZIP 不进入本 Skill 仓库。用户已经明确授权并正式入库的品牌图片可存放在独立 image-gallery 资产仓库；本 Skill 只保存稳定路径、ID 与使用规则，不复制二进制资产。唯一的 Writer 提示词副本是独立目录 `skills/content-research-writer/`，它是为解决安装可用性而保留的、带 MIT License、upstream provenance 和完整性锁的 vendored 副本，不在医学 Skill 内进行二次改写。`xiaohu-wechat-format` 与苍何保持外部依赖，不复制进本仓库。
