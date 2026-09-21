# 光愈在线公众号布局画像

> 用途：这是**视觉/排版参考画像**，不是医学知识库、文章模板或事实来源。
>
> 医荟她普通文章默认使用 [医荟她文章样式](yihui-article-style.md)。本文件只在明确需要光愈参考时加载；这里的参考组件不自动成为医荟她业务或品牌元素。
>
> 来源一：用户运行时提供的 `光愈在线公众号.zip`，包含 11 篇已保存微信公众号 HTML 及本地资源。
>
> 来源二：用户后续提供的已发布文章截图与封面色调反馈，用于补充视觉偏好。
>
> 原始 HTML、截图、图片、视频和 ZIP **不提交本仓库**。

## 1. 样本结论

这套公众号不是整篇长图，而是：

```text
微信公众号富文本 HTML
+ 局部图片 / 统计图
+ 微信原生视频 / 小程序组件
+ 大量 inline style 的 <section> 组件
```

“光愈在线风格”应理解为**品牌组件 + 视觉 Token + 组件密度/阅读节奏**，不是固定写作模板。文章论证结构仍由上游 Writer 和当次内容决定。

样本中常见组件：

```text
brand-follow（HOT / 关注条）
intro-card（红色描边导语）
section-heading-card（编号章节标题卡）
figure + caption
expert-comment
interview-question / interview-answer
summary-chip
expert-profile
END
Reference / 免责声明 / 责任编辑 / 审批编号（按真实业务数据）
```

### 1.1 参考来源优先级

当同时有 HTML、截图和口头反馈时，按以下优先级处理：

```text
真实已发布 HTML      → 精确 CSS / 字号 / 行高 / 间距 / DOM 结构
截图                 → 视觉比例 / 密度 / 色彩 / 屏幕观感
用户口头反馈         → 最终偏好与覆盖规则
浏览器预览猜测       → 最低优先级
```

不要从截图肉眼估算精确 `font-size`，也不要把上层容器继承值误当成正文实际值。

如果用户点名某一篇样稿“从头到尾参考”，应优先分析**那一篇**的组件密度与阅读节奏；跨 11 篇的稳定 Token 只作为兜底，不要把所有已知组件一次性塞进文章。

## 2. 品牌色

```text
brand_accent          #F24D60
brand_red             #FF4545
soft_pink             #FFEEEA
dialogue_bg           #F2F2F2
follow_outer_bg       #F1F8FD
body_text             #3E3E3E
heading_text          #333333
secondary_gray        #6F6E6E
```

### 2.1 已确认的封面主色调

宫颈健康 / HPV 系列封面优先采用偏沉稳的**玫瑰红、豆沙红、暖医学红**，不要默认做成过浅的粉白少女色。

```text
cover_deep_rose       #B84C5A
cover_mid_rose        #CB626E
cover_warm_red        #D96D78
cover_glow_pink       #F2A1AA
cover_light_pink      #F8D6D9
cover_title           #FFF9F8
```

视觉方向：

```text
深玫瑰红 → 暖红 → 柔粉渐变
+ 轻暗角 / 中心柔光
+ 半透明医学线框
+ 低对比网络节点 / DNA / 分子纹理
+ 同色系丝带 / 曲面
+ 白色高对比标题
```

2.35:1 公众号封面必须保证缩略图状态下标题仍清楚；封面是主 KV，不做成信息图，不塞正文数据。

## 3. 正文字号：以真实 HTML 为准

### 3.1 重要纠正

不要把 `#js_content` 或上层容器继承到的 `16px` 误判为正文实际字号。

对用户提供的真实 HTML 检查后，正文主要内容区反复出现的是：

```text
正文                 15px
line-height           1.8
body color            #3E3E3E
letter-spacing        常见 0.5~1px
```

用户重点参考的《HPV高危型怎么界定？标准与中国流行特征解析》正文块实际接近：

```text
font-size             15px
padding               0 8px
line-height           1.8
letter-spacing        1px
```

所以：

- **光愈在线式正文默认 15px / 1.8**；
- 不默认升到 16px；
- 局部标签、视频组件或上层容器出现 16px，不能据此放大全文；
- 如果用户提供的新样本明确不同，再按新样本覆盖。

推荐层级：

```text
普通正文              15px / 1.8
导语正文              15px / 1.8 / letter-spacing 0.5px
访谈问答              15px / 1.8
重点结论块            15px / 1.8 / font-weight 600~700
章节标题文字          18px / 700
章节编号              21px / 700
图注                  12px / 1.6~1.7
References            12px / 1.6
免责声明              12px / 1.7~1.8
```

不要为了“强调”把大量结论块升到 16px；应优先使用粗体、边线、浅底和留白建立层级。

## 4. 内容结构与视觉标题不是一回事

这是高还原排版的关键约束：

> **内容结构 ≠ 视觉标题数量。**

一篇文章可以在逻辑上回答 8～10 个问题，但不代表需要 8～10 个大标题卡或小标题组件。

参考文章好读的共同特征是：

```text
少量视觉重量高的章节入口
+ 连续正文
+ Figure / 表格在论证位置自然穿插
+ 粗体承担大部分局部强调
```

默认原则：

- 不把每个问句、每个 bullet、每个段落都升级成标题；
- 不为了“设计感”连续使用 `标题卡 → 引用框 → 卡片 → 图 → 小标题`；
- 一个手机屏幕内尽量不要同时出现多种高视觉重量组件；
- 对患者科普，优先把相关问题合并成较大的论述块；
- 对 HCP 学术长文，可按研究逻辑保留更多层级，但仍以样稿实际密度为准；
- 用户明确点名某篇参考文章时，**优先复用该篇的标题密度**，而不是把组件库中的所有标题样式都用上。

高还原不等于组件越多越像：

> **High fidelity = 相同的组件语法与密度；不是把所有已知组件都堆进一篇文章。**

## 5. 核心组件

### 5.1 `brand-follow`

```text
outer background     #F1F8FD
outer radius         20px
HOT background       #F24D60
HOT radius           12px
HOT font             9px / white
label font           14px 左右
```

属于品牌 chrome，不由 Writer 生成医学事实。

### 5.2 `intro-card`

真实样本常见：

```text
background           #FFFFFF
border               2px solid #F24D60
border-radius        10px
padding              22px 23px
margin               20px 0 10px
box-shadow           rgb(160,160,160) 3px 4px 7px 0
body                 15px / 1.8 / letter-spacing 0.5px
```

导语卡内部不要再叠多个 Quote 卡；优先保持一段连续引入。

### 5.3 `section-heading-card`

用户提供的代表性真实 HTML 中，章节标题组件实际参数接近：

```text
outer background     #FFFFFF
outer border         顶部 1px #FDF1F4
outer radius         20px
outer shadow         #F24D60 1px 2px 0 0
outer padding        10px
outer margin         30px 0 20px

number column        20%
title column         80%
number box           34x34px
number radius        8px
number gradient      #FD495D → rgba(242,77,96,0.2)
number text          21px / white / 700
corner decoration    25x21px 品牌红 L 形线

title                18px / #333 / 700
```

原则：

- 编号和标题在同一横向视觉组；
- 标题文字不要擅自放大到 20~22px；
- 不使用“44px 编号块 + 21px 标题”的近似值作为默认；
- 最终微信 HTML 使用 inline style；复杂效果被微信清理时允许轻量降级，但保持 34px 编号、18px 标题和 20/80 结构；
- **该组件是高视觉重量组件，不应机械地套到每个逻辑问题上。**

### 5.4 `expert-comment`

```text
background           #F24D60
text                 white
left border          12px solid #FFEEEA
padding              4px 12px
```

### 5.5 访谈左右气泡

```text
avatar column        60px
avatar ring          50x50px
inner image          40px 左右
bubble bg            #F2F2F2
bubble radius        5px
text                 15px / 1.8
```

左侧问题常见 `padding 10px 20px`，右侧回答常见 `padding 15px 20px`。

`scripts/enhance_guangyu_dialogue.py` 只负责 xiaohu 已生成 HTML 的 intro + avatar dialogue 后处理，不负责 Markdown、医学内容、图片生成或发布。

### 5.6 `summary-chip`

```text
label text           #F24D60
label background     rgba(249,204,219,0.46)
padding              3px 5px
```

按文章结构需要使用，不强制每篇出现。

### 5.7 `END`

```text
2px 红色横线
白底 END 标签
END color            #FF4545
```

真实品牌装饰图必须来自用户可用素材，不自动仿造。

## 6. 文章标题与正文标题区分

微信公众号的文章主标题属于平台标题区，不应在 `#js_content` 顶部再重复插入一遍大号 H1。

高还原输出默认：

```text
微信标题字段
↓
brand-follow
↓
intro-card / 正文
```

只有用户明确要求“正文内再显示一次标题”时才重复放置。

## 7. Figure / 论文图

用户已确认：医学文章涉及真实数据时，优先使用**论文式统计图 / 科学 Figure**，而不是卡通信息图。

详细规则见：

```text
../medical-figure-design.md
```

### 7.1 视觉复杂度与医学内容分离

当用户给一张复杂论文 Figure 作为参考时：

- 可以借鉴其多面板密度、A/B/C/D 编号、图例、坐标、分隔线、Caption 和论文感；
- **不能因为参考图里有弦图、年龄分层、月份曲线，就把这些内容照搬到当前文章**；
- 新 Figure 的 Panel 必须从当前冻结稿/HTML 中反推；
- 图中的数字必须来自当前文章已经核验的来源。

核心口令：

> **借复杂度，不借内容；借版式，不借证据。**

### 7.2 Figure 与正文的连接方式

参考样稿中更成熟的节奏是：

```text
正文引入句 / 数据结论
↓
灰色分隔线
↓
Figure
↓
English Figure caption（样稿有时）
↓
灰色分隔线
↓
中文图注 + [n]
↓
继续正文
```

图前解释“为什么现在看这张图”，图后只解释核心 takeaway，不重复朗读整张图。

### 7.3 数据与来源

```text
白底
黑 / 深灰标题与坐标
克制医学配色
真实数值标签
95% CI / n（来源支持时）
Figure caption
真实来源 / PMID / DOI（经核验）
```

数据值必须来自已核验来源；不要让图像生成模型自行补数字。

若生成模型自动写错 PMID/DOI/作者/期刊，优先裁掉或移除图内来源文字，由正式 HTML 图注与 References 管理引用。

## 8. Reference 组件

用户重点参考的真实文章采用了明确的 Reference 区域视觉语法：

```text
Reference
↓
灰色横线
↓
参考文献：
↓
固定高度文献列表
```

代表性实现：

```text
font-size            12px
line-height          1.6 左右
height               240px
 overflow-y           auto
```

因此文献列表较长时，可以使用**固定高度 + 上下滚动**，避免 References 把正文尾部拉得过长。

注意：

- 滚动的是文献列表，不是 `Reference` 标题本身；
- 正文 `[n]` 与 References 必须一一对应；
- 删除 Figure 后，重新判断仅服务于该 Figure 的文献是否还需要保留；
- 不把样稿里的文献复制到新文章；
- 不为了“显得学术”保留正文没有使用的文献。

## 9. 排版路由

```text
普通医学长文
→ canghe-markdown-to-html

光愈在线式学术长文
→ 读取本文件
→ 正文 15px / 1.8
→ 先匹配参考文章的标题/组件密度
→ section-heading-card 仅用于真正的大章节
→ Figure 内容从当前冻结稿反推
→ 微信 inline HTML

专家访谈 / Q&A
→ xiaohu interview + :::intro / :::dialogue

光愈在线式头像访谈
→ xiaohu
→ enhance_guangyu_dialogue.py + 用户真实头像 / Logo
→ canghe-post-to-wechat
```

## 10. 发布前视觉 QA

当用户要求“像样稿 / 高还原 / 光愈在线式”时，至少检查：

```text
[ ] 精确字号是否来自真实 HTML，而不是截图猜测或父容器继承？
[ ] 正文是否为 15px / 1.8（除非当前点名样稿不同）？
[ ] 正文是否连续，还是被标题/Quote/卡片切得过碎？
[ ] 内容上的 8~10 个问题是否被错误地做成 8~10 个视觉标题？
[ ] 是否只有真正的大章节才使用 section-heading-card？
[ ] 章节编号是否接近 34x34px / 21px？
[ ] 章节标题是否接近 18px？
[ ] 图注是否约 12px，明显小于正文？
[ ] Figure 内容是否来自当前文章，而不是照搬参考图？
[ ] Figure 每个数字是否有来源？
[ ] References 是否与正文 [n] 闭环？
[ ] 长 References 是否按样稿采用 240px 左右滚动列表？
[ ] 主标题是否只在微信标题区出现一次？
[ ] 手机端真机预览中行高、字距、图片宽度是否正常？
[ ] 封面是否继续使用已确认的深玫瑰红 / 暖红色调？
[ ] 未虚构审批号、责任编辑、专家身份、Logo 或产品资产？
```

浏览器预览与微信草稿箱不一致时，以**微信草稿箱 / 手机端真机预览**为最终验收标准。

## 11. 扩展边界

若继续提高还原度，只补缺失的品牌组件，不重写 Markdown / 微信 HTML 引擎：

```text
brand-follow
section-heading-card postprocessor（若 upstream 无法稳定实现）
summary-chip
end-divider
expert-profile skin
```

每个组件只接收已完成内容和真实品牌素材；不负责医学写作、事实生产、配图生成或微信发布。
