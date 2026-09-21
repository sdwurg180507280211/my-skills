# Repository Guide

本仓库是自包含 Agent Skills 集合。

## 目录约定

- 每个 Skill 放在 `skills/<skill-name>/`。
- `SKILL.md` 必须存在，frontmatter 至少包含 `name` 与 `description`。
- 脚本、测试、示例、参考资料都放在对应 Skill 目录内。
- 不把运行结果、用户输入、Cookie、Token、session、二维码、缓存提交到仓库。

## 质量要求

1. Skill 的触发描述要具体，避免劫持无关任务。
2. 优先成熟依赖和简单实现，不为了未来功能增加额外兼容层。
3. 可确定验证的解析/转换能力应提供离线测试。
4. 新增或删除 Skill 时同步更新 `README.md`、`.claude-plugin/marketplace.json` 和 `CHANGELOG.md`。
5. 提交前运行 `python3 scripts/validate_skills.py`，并运行对应 Skill 的测试。
6. 默认不复制大型通用 upstream；若 upstream 实际安装不可达、许可证明确允许且是当前链路必需，可保留受控 vendored 副本，但必须附许可证、固定版本、来源说明和完整性锁，避免长期魔改分叉。

## WeChat Skills

- `wechat-account-bookmarks` 只负责微信公众号身份 / 文章 / `biz` 到 Edge / Chrome 书签的编排与输出；微信侧复杂发现和文章解析优先复用固定版本的苍何上游 Skill。只使用正常扫码登录与公开可访问数据，不绕过验证码、登录限制、访问控制、频率限制或微信风控。
- `wechat-android-shortcuts` 只负责 Android 真机上的微信“添加到桌面”自动化；使用 ADB + OCR 操作官方 UI，不修改微信数据库、不伪造 ShortcutInfo，不与其他微信 Skill 互相 import。
- `wechat-ios-shortcuts` 只负责名称 + 已知 HTTP/HTTPS URL 到 Apple Web Clip `.mobileconfig` 的转换；不发现公众号、不控制微信 App、不静默安装配置描述文件。个人 iPhone/iPad 安装必须由用户确认，MDM 下发不属于当前实现。
- `wechat-medical-writer` 是薄医学领域适配/编排层，不自己定义通用文章结构、标题方法、研究模式、固定模板或发布实现。用户医学 ZIP/PPT 只用于定义内容方向或作为当次资料。
- `wechat-ai-model-writer` 是 AI 模型性价比公众号的编辑/编排层。它只维护 daily / breaking / weekly 选题路由、模型价格与免费额度字段、官方/云平台/聚合/中转渠道分类、风险提示与科技情报刊式排版；不用于医学内容，也不得把每日采集条目机械拼成固定新闻列表。
- AI 模型公开稿的价格、免费额度、上下文、限速与渠道信息优先回到官方公告、官方定价页或官方文档；标准按量价、缓存价、Batch 价、包月摊销价、新用户额度和限时活动不得混写。无法核实的价格必须明确标记，不能补造数字。
- AI 模型渠道必须区分 `[官方]`、`[云平台官方接入]`、`[正规聚合平台]`、`[非官方中转]`；禁止推荐盗号、共享 API Key、来源不明密钥、绕过地区限制或明显违反服务条款的渠道。非官方中转即使便宜，也必须同时呈现数据隐私、稳定性、版本真实性、封号和跑路风险。
- AI 模型日报的视觉优先级是“结论卡 / 数据表 / 模型信息卡 / 必要的数据图 > 装饰性 AI 插图”。没有可信数据时不得生成伪价格图、伪排行榜或模型主观评分雷达图。默认布局画像维护在 `skills/wechat-ai-model-writer/references/layouts/ai-savings-daily.md`。
- 医学主题使用现成 Writer 的原生流程，`content-research-writer` 是当前默认候选，未通过医学中文长文对照评测，不锁定为唯一选项。AI 模型写作仍使用该 Writer。现有 MIT vendored 副本和完整性锁保留；不得在上游 `SKILL.md` 中加入领域逻辑。
- `content-research-writer` 的本地副本必须由 `UPSTREAM.lock.json` 锁定；`scripts/validate_skills.py` 会检查 Git blob 指纹，未同步更新 lock 的本地改动应直接失败。
- 写作时先定位并读取所选 Writer 的真实 SKILL.md；缺失则提供对应宿主的安装方法，不实现 fallback Writer。已有文章仅排版不要求重新经过 Writer。
- Handoff 时把已知的主题、受众、目标、篇幅/形式、用户资料、参考样稿、风格要求和领域约束一次性传给主 Writer；已经知道的信息不要重复问。用户明确要求“一口气成稿”时，可让主 Writer 连续执行原生的大纲、研究、草稿、引用检查和最终润色步骤。
- 面向公开发布的医学文章，关键数字、指南/共识推荐、疗效/安全性、适应证、监管状态和可能影响临床判断的事实默认要求可追溯来源；正文引用与参考文献在交付前必须闭环。只有用户明确要求“仅按提供资料、不做外部核验”时才允许限制在用户来源，并在成稿中说明该边界。
- `Viral Writer` 仅可作为用户明确要求时的可选表达润色层，不得修改或新增医学事实、数字、指南、适应证、监管状态或引用。
- 苍何不是纯写作的前置依赖。用户要求正文配图时优先 `canghe-article-illustrator`；普通学术文章/常规公众号排版优先 `canghe-markdown-to-html`；最终草稿箱发布统一优先 `canghe-post-to-wechat`。
- 专家访谈、Q&A、对话气泡、导语卡、卡片、timeline、hero 等组件化公众号布局可按需调用外部 `xiaohuailabs/xiaohu-wechat-format`，只用其 formatter，不使用其封面生成或 `publish.py`，避免和苍何重复。
- 当前已审计的 `xiaohu-wechat-format` `:::dialogue` 只支持“说话人文本 + 左右交替气泡”，没有头像/Logo 字段。其 README 声明 MIT，但 GitHub 元数据未识别许可证且仓库缺独立 `LICENSE` 文件，因此本仓库不得 vendor、复制脚本/主题或长期 fork，除非许可证文本明确。
- 用户运行时提供公众号截图、HTML 或 ZIP 时，可以从真实 HTML 和明确偏好提炼视觉画像；原件不提交，画像不成为医学事实或固定文章结构。医荟她默认样式在 `references/layouts/yihui-article-style.md`，正文 15px/1.8/1px，科学图按证据语义放置，不按页面百分比硬排。
- “光愈在线式”布局画像维护在 `skills/wechat-medical-writer/references/layouts/guangyu-online.md`。它不是固定文章模板；仅在用户明确要求相似视觉或样本确实匹配时读取。
- `光愈在线` 仅是参考品牌，最终医学公众号输出默认属于 **“医荟她健康”**。生成或排版前读取 `skills/wechat-medical-writer/references/brands/yihui-she-health.md`，不得把光愈在线 Logo、名称、二维码、小程序、项目落款等带入医荟她健康成品。
- `医荟她健康` 当前没有小程序。除非用户后续明确提供真实小程序名称、AppID、path、二维码、截图和已上线功能，否则不得生成小程序卡片、二维码、入口或把未来规划写成已上线能力。
- 光愈在线首篇上线文章的图片化格式研究维护在 `skills/wechat-medical-writer/references/layouts/guangyu-launch-first-article.md`；它可用于借鉴 2.35:1 封面、9:16 主 KV、1080px 级正文图和“图片主导 + 少量富文本”的首篇发布节奏，但不能复制光愈在线业务内容。
- 高还原头像访谈使用本地 `scripts/enhance_guangyu_dialogue.py`，它只能后处理 xiaohu 已生成的 `data-container` HTML，并接收运行时 speaker→头像/Logo 映射。不得让该脚本解析 Markdown、写医学内容、生成头像、下载用户样本、上传微信或成长为第二套 formatter。
- `enhance_guangyu_dialogue.py` 的确定性转换必须保持离线测试。speaker 缺头像映射时必须明确失败，不能静默输出“有的带头像、有的不带”的半成品。测试只用合成 HTML 和虚拟路径，不提交真实品牌资产。
- 头像/Logo 必须来自用户提供或用户有权使用的真实素材；不得生成或伪造真实专家头像、官方 Logo。运行时 `avatars.json`、头像、Logo、生成 HTML 均不提交仓库。
- 继续提高“光愈在线式”还原度时，只按实际需求新增 `brand-follow`、`summary-chip`、`end-divider` 等独立微组件；不要预防性实现整套私有模板，也不要复制用户样本 HTML/SVG/图片。
- 医学配图的数据只能来自已经核验的正文来源；不得补造数字，不得把机制推测画成确定因果，真实产品/器械/包装优先使用用户提供的官方素材。
- 五个本仓库微信 Skill 保持独立，通过 Markdown、CSV/XLSX、`target_url`、结构化情报等文件/数据契约松耦合，不直接互相 import。
- Android 脚本不得提交开发机绝对路径、固定设备 serial、固定用户输入法；设备和工具路径通过自动发现或环境变量提供，临时切换输入法后必须恢复运行前的默认输入法。
- 医学 Skill 不得提交用户上传的原始 ZIP/PPT/PDF、公众号 HTML/图片/视频、头像/Logo、内部培训材料、患者资料或未公开研究。仓库只保存领域 taxonomy、必要医学约束、布局画像、小型确定性适配器和 upstream 编排说明。
- 用户提供的优秀公众号文章可以作为结构/文风/信息密度参考，但其医学结论和参考文献不能因为出现在样稿中就自动视为已核验事实；也不得把样稿结构固化为永久模板。
