# wechat-medical-writer

医学类微信公众号 / 服务号的**轻量领域适配与编排 Skill**。

它不自己维护一套文章模板、研究模式、Claim Ledger 或发布代码，而是把职责拆清楚：

```text
医学领域上下文 + 必要医学约束
        ↓
【必须】content-research-writer
负责主题 → 研究 → 引用 → 高质量文章
        ↓
医学引用完整性检查
        ↓
可选：Viral Writer
只做表达/标题/节奏润色，不改变医学事实
        ↓
按需配图：
├─ 普通概念插图 → canghe-article-illustrator
└─ 统计图 / 论文式 Figure / 多面板图
   → references/medical-figure-design.md
   → 可控 plotting / SVG / HTML / vector 优先
        ↓
排版路由：
├─ 常规文章 → canghe-markdown-to-html
├─ 访谈/Q&A/组件化 → xiaohu-wechat-format
├─ 用户指定样式 ID → references/layouts/wechat-component-library.md
└─ “光愈在线式”头像访谈 → xiaohu + 本地轻量品牌适配器
        ↓
统一：canghe-post-to-wechat
```

## 当前领域方向

用户提供的医学 ZIP/PPT 只用于定义后续内容方向或作为某次写作资料，**不决定固定文章结构**。

当前方向包括：女性健康/妇科、HPV、宫颈癌筛查与防治、LSIL/HSIL、CIN2/CIN3、阴道镜/病理/风险分层、生育需求与宫颈功能保护、PDT/HAL-PDT。详细 taxonomy 见 `references/domains/cervical-health.md`。

## Writer handoff

`wechat-medical-writer` 把通用写作阶段强制交给 `content-research-writer`。Handoff 时一次性传递已知的主题、受众、目标、篇幅/形式、用户资料、参考样稿、风格和医学约束；已经明确的信息不要重复问。

如果运行环境确实缺少 `content-research-writer`，停止正文并提示补装；不要悄悄切换成自制 fallback Writer。

## 医学证据边界

面向公开发布的医学文章，具体医学数字、指南/共识推荐、疗效/安全性、适应证、监管状态和其他可能影响临床判断的关键结论应能回到可追溯来源。正文引用与 Reference 在交付前闭环；DOI/PMID/作者/年份/期刊不凭记忆补齐。完整规则见 `references/medical-constraints.md`。

## 参考文章与排版样本

用户提供优秀公众号文章时，可以参考其写作完成度和视觉表现，但不能把样稿医学数字自动当成已核验事实，也不能把单篇结构固化成永久写作模板。

用户运行时提供的 `光愈在线公众号.zip` 包含 11 篇已保存 HTML。仓库只保留跨文章的排版画像：

```text
references/layouts/guangyu-online.md
```

原始 HTML、图片、视频和 ZIP 不进入仓库。layout profile 只回答“怎么排”，不回答“怎么写”，也不是医学事实来源。

此外，已把独立 image-gallery 的公众号样式库接入为稳定 ID 契约：

```text
references/layouts/wechat-component-library.md
```

用户可以直接指定如 `顶部关注-02 + 导语-01 + 标题-02 + 正文-02 + 参考文献-01 + 结尾-01`。此时 ID 是明确排版约束，不再由 formatter 自由替换。

## 医荟她健康品牌资产与封面

目标品牌画像：

```text
references/brands/yihui-she-health.md
```

已正式入库的品牌图片由独立 `image-gallery` 管理，本 Skill 只记录稳定路径与使用边界。当前图片组件 `图片-01` ～ `图片-06` 对应 4 个 Logo 候选方案和马年横/竖版 KV；候选 Logo 在用户明确选定前，不自动认定唯一主 Logo。

公众号封面默认比例为 **2.35:1**，除非用户另有要求。

## 医学 Figure

统计图、论文式 Figure、多面板科学图与普通“正文插图”是两类任务，不走同一默认路由。

### 普通概念插图

可以按需使用 `canghe-article-illustrator` 或其他成熟插图工具。

### 统计图 / 论文式 Figure / 多面板图

必须读取：

```text
references/medical-figure-design.md
```

其中当前关键经验包括：

- **借复杂度，不借内容；借版式，不借证据**；
- Figure 复杂度既不能超过证据，也不应无故低于文章本身的信息密度；
- 精确数字、坐标、表格、图例和专业文字优先使用可控 plotting / SVG / HTML / vector 锚定，生成模型不承担唯一的数据和文字层；
- 两张以上高信息密度 Figure 应先做全文 placement map，避免连续多屏堆叠；必要时可以连同“最小支撑段落”一起移动，并增加前向提示与桥接句；
- 中英文版本应视为同一 Figure 的本地化重绘，Caption 语言跟随目标场景，不再默认“英文 Figure caption + 中文图注”；
- 图片底部已经有完整 Caption 时，HTML 不再重复同一段 Caption；
- 论文 Figure 放进公众号后要按约 650～700px 正文宽度复核可读性。

## Upstream

- 主 Writer：`content-research-writer`
- 可选表达润色：`Viral Writer`
- 普通概念插图 / 常规排版 / 发布：苍何 `canghe-article-illustrator`、`canghe-markdown-to-html`、`canghe-post-to-wechat`
- 统计图 / 论文式 Figure：`references/medical-figure-design.md` + 可控绘图工具优先
- 高级访谈/Q&A/组件化排版：`xiaohuailabs/xiaohu-wechat-format`

### 常规文章

```text
普通插图（按需）→ canghe-article-illustrator
论文式 Figure（按需）→ medical-figure-design + controllable plotting
→ canghe-markdown-to-html
→ canghe-post-to-wechat
```

### 普通专家访谈 / Q&A

用 `xiaohu-wechat-format` 的 `interview` 主题与 `:::intro` / `:::dialogue` 等容器生成微信兼容 HTML。xiaohu 只作为 formatter；不使用它自己的 `publish.py` 或封面生成。

### 光愈在线式头像访谈

当前已增加一个**小型后处理适配器**：

```text
scripts/enhance_guangyu_dialogue.py
```

它不重写 xiaohu，也不是另一个 Markdown 引擎。流程是：

```text
article.md
→ xiaohu-wechat-format
→ formatted.html
→ enhance_guangyu_dialogue.py + avatars.json
→ formatted.guangyu.html
→ canghe-post-to-wechat
```

适配器目前负责：

- 把 xiaohu `:::intro` 改成样本中的 `#F24D60` 完整描边导语卡；
- 给左右 dialogue 注入用户提供的品牌 Logo / 专家头像；
- 生成 60px 头像列、50px 品牌红圆环、约 40px 内图；
- 使用 `#F2F2F2` 灰色问题/回答卡；
- 使用自行实现的 CSS 三角尾巴，不复制用户样本中的 SVG；
- speaker 缺头像映射时明确失败，不静默降级。

`avatars.json` 示例：

```json
{
  "光愈在线": "assets/logo.png",
  "梁静教授": "assets/liang.png"
}
```

执行：

```bash
python3 scripts/enhance_guangyu_dialogue.py \
  --input /path/to/formatted.html \
  --avatars /path/to/avatars.json \
  --output /path/to/formatted.guangyu.html
```

头像/Logo 必须是用户提供或有权使用的真实素材，运行时文件不提交仓库。适配器只使用 Python 标准库，并有离线测试 `tests/test_guangyu_dialogue.py`。

当前还**没有**宣称全篇 1:1：顶部 HOT/关注条、完整 Summary 线条、END 品牌装饰、专家资料专属皮肤仍可作为后续独立微组件，不应塞进同一个脚本无限扩张。

### xiaohu License 边界

xiaohu README 声明 MIT，但当前仓库没有独立 `LICENSE` 文件且 GitHub 元数据未识别许可证，所以本仓库只外部调用它，不 vendor、不复制脚本/主题。品牌适配器只依赖其输出 HTML 的 `data-container` 契约。

## 仓库边界

原始医学 ZIP/PPT/PDF、公众号 HTML/图片/视频、头像、Logo、内部培训材料、未公开研究、患者资料和运行时文章都不进入公共仓库。

本 Skill 保留领域定义、医学约束、Figure 设计/插入/本地化规则、布局画像、公众号稳定组件 ID 契约、医荟她健康品牌资产路径与封面规则、小型可测试品牌适配器和 upstream 编排；通用写作仍由 `content-research-writer` 负责，微信 formatter/publisher 仍优先复用现有 upstream。
