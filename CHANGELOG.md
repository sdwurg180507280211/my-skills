# Changelog

## Unreleased — 医荟她健康适配层收敛

- 增加通过苍何原生 MD_THEME_DIR 加载的医荟她小型 CSS 配置；完成 390px 手机浏览器计算样式检查和双图离线模拟上传验证，未调用真实微信发布。
- 记录顶层转换入口的图片预览占位符、frontmatter 标题及脚注处理限制，提供已实测的上游直接渲染入口。

- 缩短医学 Skill 入口，增加医荟她自己的文章样式基准与 Codex 显示元数据；保留原名称和私有素材边界。
- 从用户认可的 HPV 长文提炼正文 15px/1.8/1px、克制标题和科学图语义位置；移除按页面百分比放图的建议。
- content-research-writer 改为待医学长文对照评测的默认候选；已有成稿只排版时不强制重写。
- 组件库只保存外部消费与版本规则，不重复维护完整组件注册表；品牌文件仍保留现有图片别名。
- 补充 Codex 本地链接安装说明，区分 Claude 插件命令。
- 复核苍何固定版本：已正确使用 processedHtml；记录 data URI 不支持与单图失败后继续发布的实际限制，要求核对真实草稿。

## 2026-08-28 — v1.12.0

### Added
- `wechat-ai-model-writer`：新增面向 AI 大模型/价格/免费额度/高性价比渠道的微信公众号编辑与编排 Skill，支持 `daily / breaking / weekly` 选题路由，并继续 handoff 给 `content-research-writer` 完成通用研究与正文写作。
- `references/intelligence-contract.md`：沉淀价格单位、币种、缓存/Batch/套餐/活动价、永久免费层/新用户额度/限时免费、上下文、限速和官方/云平台/聚合/中转渠道分类的结构化输入契约。
- `references/layouts/ai-savings-daily.md`、`templates/daily.md` 与 `templates/daily.html`：增加科技情报刊式日报视觉规范、内容骨架和微信 inline-style HTML 组件参考，优先使用结论卡、模型卡、价格表与风险卡，不依赖装饰性 AI 插图。

### Changed
- `utility-skills` bundle 增加 `wechat-ai-model-writer`，Marketplace 版本更新为 `1.12.0`。
- README 与仓库维护规则增加 AI 模型公众号生产链、价格/渠道核验边界和数据视觉要求。

## 2026-08-21 — v1.11.0

### Added
- `git-history-cleanup`：沉淀“最终代码不变、只整理 Git 历史”的安全工作流，覆盖冻结旧 HEAD/Tree、创建恢复分支、按最终净效果合并或删除提交、交互式 rebase 与最终 Tree 驱动重建两种策略，以及强推前后的 Tree SHA 等价校验。
- 增加复杂历史与仅有 Git 托管 API 时的对象级重建规则：优先复用最终 blob/subtree、避免提前吸收后续改动、跳过 no-op commit，并在目标 ref 更新前手工实现 lease 语义。

### Changed
- `development-skills` bundle 增加 `git-history-cleanup`，Marketplace 版本更新为 `1.11.0`。
- README 增加 Git 历史整理 Skill 的用途与目录入口。

## 2026-08-18 — v1.10.0

### Added
- `wechat-medical-writer/scripts/enhance_guangyu_dialogue.py`：接在 `xiaohu-wechat-format` 输出之后的小型品牌视觉适配器，只依赖公开 `data-container` HTML 契约与运行时 speaker→头像/Logo 映射；补入光愈在线式红色完整描边导语卡、左右头像、50px 品牌红头像环、灰色对话卡和 CSS 三角尾巴。
- `wechat-medical-writer/tests/test_guangyu_dialogue.py`：使用合成 xiaohu-like HTML 离线验证左右头像注入、导语重绘、缺失 speaker 映射失败和自定义 accent，不包含用户私有素材。

### Changed
- “光愈在线式头像访谈”路由升级为 `content-research-writer → xiaohu formatter → enhance_guangyu_dialogue.py → canghe-post-to-wechat`；本地脚本不解析 Markdown、不写医学内容、不生成头像、不发布微信，也不复制 xiaohu 或用户样本源码。
- `references/layouts/guangyu-online.md` 标记 `intro-card + avatar-dialogue` 已有最小实现；HOT 关注条、完整 Summary、END 品牌装饰等继续保持为独立可选微组件，不预防性实现整套私有模板。
- GitHub Actions 增加医学品牌适配器的 compile + offline unittest。
- Marketplace 版本更新为 `1.10.0`。

## 2026-08-18 — v1.9.0

### Added
- `references/layouts/guangyu-online.md`：基于用户运行时提供的 11 篇“光愈在线”公众号已保存 HTML，归纳跨文章稳定出现的品牌 Token、导语卡、章节标题、专家点评、访谈左右气泡、Summary、END 与合规尾注等视觉组件；不提交原始 HTML、图片、视频或 ZIP。
- `wechat-medical-writer` 增加“光愈在线式”排版路由：用户明确要求类似该样本的视觉时，先读取布局画像，再交给 `xiaohu-wechat-format` 等成熟 formatter；布局画像不参与医学事实判断，也不决定 Writer 的论证结构。

### Changed
- 将“参考公众号文章”进一步拆成写作参考与视觉参考两个维度：样稿可以影响完成度/视觉画像，但不能自动成为医学证据，也不能把单篇结构固化成永久文章模板。
- 明确当前 xiaohu 可复现访谈结构但不能原生 1:1 复刻光愈在线的 50px 品牌头像环、Logo/专家头像、SVG 对话尾巴、HOT 关注条等细节；高还原版本只应补小型品牌组件，不重写 Markdown → 微信 HTML 引擎。
- Marketplace 版本更新为 `1.9.0`。

## 2026-08-18 — v1.8.0

### Added
- 审计并记录外部 `xiaohuailabs/xiaohu-wechat-format`（固定审计 commit `dbddf0fd9c1189a6f3e0bec1bebb1b0e47e8ddf0`），作为专家访谈 / Q&A / 对话气泡 / 卡片 / timeline / hero 等复杂公众号布局的可选 formatter。
- `wechat-medical-writer` 增加排版路由：常规文章继续使用 `canghe-markdown-to-html`；组件化访谈文章可按需使用 `xiaohu-wechat-format`；最终发布统一优先交给 `canghe-post-to-wechat`。

### Changed
- 明确 `xiaohu-wechat-format` 只负责高级排版，不使用其封面生成和 `publish.py`，避免与苍何上游重复。
- 明确当前 `:::dialogue` 原生实现没有头像 / Logo 字段，不能宣称开箱即用 1:1 复刻头像型专家访谈卡。
- 由于该 upstream 虽在 README 声明 MIT，但 GitHub 元数据未识别许可证且仓库没有独立 `LICENSE` 文件，本仓库只记录和调用外部 upstream，不 vendor、不复制其脚本/主题。
- Marketplace 版本更新为 `1.8.0`。

## 2026-08-18 — v1.7.0

### Added
- `wechat-medical-writer` 增加强制 Writer handoff contract：在开始大纲、研究或正文前，必须把通用写作阶段交给 `content-research-writer`；已知上下文一次性传递，不重复询问。
- 医学公开稿增加默认证据门槛与引用完整性检查：关键数字、指南/共识、疗效/安全性、适应证、监管状态等必须能回到可追溯来源；正文引用与 Reference 在交付前闭环。
- `references/medical-constraints.md` 增加医学配图边界：数据图不得补造数字，机制图不得把推测画成确定因果，真实产品/器械优先使用官方素材。
- `content-research-writer/UPSTREAM.lock.json`：锁定 vendored Writer 的来源 commit/blob 与本地 Git blob；仓库校验发现未声明漂移时失败。

### Changed
- 苍何改为按需下游：纯研究/写作不依赖苍何；只有用户要求配图、微信 HTML 或草稿箱时才进行 preflight，并在缺失时给出标准安装命令，不实现 fallback。
- `scripts/validate_skills.py` 增加 `UPSTREAM.lock.json` 离线完整性验证。
- `content-research-writer/UPSTREAM.md` 明确记录 source blob 与本地 vendored blob；当前文本内容与固定上游一致，本地副本仅缺少上游文件末尾换行。
- Marketplace 版本更新为 `1.7.0`。

## 2026-08-18 — v1.6.0

### Added
- 将 `CommandCodeAI/agent-skills` 的 `content-research-writer` 按 MIT License 原样 vendored 到 `skills/content-research-writer/`，解决上游不在用户可用插件市场中的安装缺口。
- `skills/content-research-writer/UPSTREAM.md`：记录上游仓库、路径、已审计 commit/blob 与同步规则。
- `skills/content-research-writer/LICENSE`：保留上游 MIT License 与版权声明。

### Changed
- `utility-skills` bundle 现在同时包含 `content-research-writer` 与 `wechat-medical-writer`；安装本仓库 utility bundle 后不再因主 Writer 缺失而触发自制 fallback。
- `wechat-medical-writer` 明确优先调用同仓库 vendored `content-research-writer`，医学上下文与医学事实约束仍只维护在医学 Skill 中，不修改通用 Writer 原文。
- Marketplace 版本更新为 `1.6.0`。
- 仓库维护原则增加受控 vendoring 例外：仅在 upstream 安装不可达、许可证允许且当前链路必需时使用，并必须保留许可证、来源和固定版本。

## 2026-08-18 — v1.5.0

### Changed
- `wechat-medical-writer` 从“自建医学写作系统”重构为轻量医学领域适配与 upstream 编排层：用户医学 ZIP/PPT 只定义内容方向或作为当次资料，不再决定固定文章结构、研究流程和输出契约。
- 主题到高质量文章默认复用 `CommandCodeAI/agent-skills` 的 `content-research-writer`；不在本仓库复制其大纲、研究、引用、Hook、正文和润色流程。
- `Viral Writer` 仅作为用户明确要求时的可选表达润色层，不允许改变医学事实、数字、指南、适应证、监管状态和引用。
- 公众号配图、Markdown → 微信 HTML、上传草稿箱继续直接复用苍何 `canghe-article-illustrator`、`canghe-markdown-to-html`、`canghe-post-to-wechat`。
- `references/domains/cervical-health.md` 收敛为纯领域 taxonomy，不再包含固定文章选题、文章结构或研究/核验工作流。
- Marketplace 版本更新为 `1.5.0`。

### Added
- `references/medical-constraints.md`：只保留通用 Writer 不具备的医学事实边界，不规定文章结构。
- `references/upstreams.md`：记录主 Writer、可选润色层、苍何生产链的职责和已审计 upstream 版本。

### Removed
- 删除 `source-only` / `source-first` / `research-update` 自定义资料模式。
- 删除固定 `hcp-academic.md` / `patient-education.md` 模板。
- 删除 Claim Ledger、`validate_claim_ledger.py` 及对应测试。
- 删除本地 `medical-writing-style.md`、`evidence-policy.md`、`source-policy.md`，避免重复实现成熟 upstream 已负责的写作/研究能力。
- GitHub Actions 删除已经不再存在的医学 Claim Ledger 编译/测试步骤。

## 2026-08-18 — v1.4.0

### Added
- `wechat-medical-writer`：面向医学类微信公众号/服务号的专业写作 Skill，支持 `source-only` / `source-first` / `research-update` 三种资料模式，要求关键医学结论进入 Claim Ledger。
- `wechat-medical-writer/references/domains/cervical-health.md`：第一版妇科/宫颈疾病领域包，覆盖 HPV、HSIL、CIN2/CIN3、生育力保护、风险分层与 PDT/HAL-PDT 等主题结构；不包含用户上传课件原件。
- `wechat-medical-writer/scripts/validate_claim_ledger.py`：离线校验医学 Claim Ledger 的字段、来源类型、核验状态和公开使用状态。
- `wechat-medical-writer/tests/test_claim_ledger.py`：覆盖有效 Claim、重复 ID、模型推断直接发布、未核验直接发布与缺少来源引用等规则。

### Changed
- Marketplace 增加 `wechat-medical-writer`，版本更新为 `1.4.0`。
- GitHub Actions 增加医学写作 Skill 的脚本编译和离线测试。
- 仓库文档明确：用户原始医学 ZIP/PPT/PDF、内部培训材料、患者资料和未公开研究默认不提交公共仓库。

## 2026-08-17

### Added
- `wechat-android-shortcuts`：从浏览器书签 Skill 中拆出的独立 Android 真机自动化 Skill，通过 ADB + 微信 UI + macOS Vision OCR 调用微信官方“添加到桌面”。
- `wechat-android-shortcuts/tests/test_core.py`：离线覆盖设备列表解析、名称匹配、候选排序、Activity 解析和输入法恢复逻辑。
- `wechat-ios-shortcuts`：把公众号名称 + HTTP/HTTPS 目标 URL 批量生成 Apple Web Clip `.mobileconfig`，用于 iPhone/iPad 主屏幕图标；可直接读取 `wechat-account-bookmarks` 输出的 `wechat_accounts.csv`。
- `wechat-ios-shortcuts/tests/test_generate_webclips.py`：离线覆盖输入列识别、重复/无效 URL 过滤、多 Web Clip payload 和 PNG 图标嵌入。

### Changed
- `wechat-account-bookmarks` 回归单一职责，只负责公众号身份 / 文章 URL / `biz` → Edge / Chrome 书签。
- `wechat-android-shortcuts/scripts/batch_add_wechat.py` 收敛为唯一批量入口，删除拆分时遗留的 `_batch_add_wechat_impl.py` 包装层。
- Android 批量脚本不再包含开发机绝对路径、固定设备 serial 或固定搜狗输入法；单设备自动选择 serial，多设备要求 `ANDROID_SERIAL`。
- Android 批量脚本运行前记录系统当前默认输入法，并在正常结束或异常后通过 `try/finally` 恢复原输入法。
- GitHub Actions 新增 `wechat-android-shortcuts` 离线测试，并增加 `wechat-ios-shortcuts` 依赖安装、编译和离线测试。

## 2026-08-16

### Added
- `wechat-account-bookmarks`: 批量解析微信公众号名称、历史文章 URL 或已知 `biz`，生成公众号主页 URL 与 Edge/Chrome 可导入的 `bookmarks.html`。
- `wechat-account-bookmarks/scripts/validate_output.py`：校验 identity、biz、主页 URL、书签和汇总输出契约。
- `.claude-plugin/marketplace.json`，支持按 Skill bundle 安装。
- GitHub Actions + `scripts/validate_skills.py` 仓库结构校验。
- `CONTRIBUTING.md` 与 `CLAUDE.md` 维护规范。

### Changed
- `wechat-account-bookmarks` v2 改为上游优先架构：直接复用 `freestylefly/wechat-article-archive-skill` 的公众号发现能力和 `freestylefly/wechat-article-extractor-skill` 的复杂微信页面解析能力，不再重复维护微信搜索/解析实现。
- 公众号身份解析优先级调整为 `input biz > input article URL > upstream extractor > upstream archive search`。
- 拆分 `identity_status` 与 `bookmark_status`；主页无法明确证明正常时标记 `unknown`，不再把普通 HTTP 200 当成成功。
- `state.json` 升级为 v2 schema，并使用 identity fingerprint，避免名称/URL/biz 变化后误复用旧结果。
- 重写根 README，使安装方式、目录结构和 Skill 清单与真实仓库保持一致。
- 收窄 `china-proxy` 与 `github-kb` 的触发范围，减少误触发和机器相关假设。

### Removed
- `wechat-account-bookmarks/scripts/wechat_mp.py`：删除与苍何上游重复的微信公众平台搜索和文章解析实现。
- 根目录 `install.sh`：硬编码 Skill 列表已经出现遗漏，改用标准 Skills CLI / Claude Code Plugin Marketplace。
- `skills/skill-creator/`：属于体积较大的通用上游 Skill，不再在个人仓库复制维护；需要时直接使用维护中的上游版本。
