# my-skills

个人维护的 Agent / Claude Code Skills 集合。仓库遵循“一个 Skill 一个目录、`SKILL.md` 为入口、脚本/参考资料/测试就近放置”的结构，尽量保持技能自包含、可验证、可独立安装。

## Skills

| Skill | 分类 | 用途 |
|---|---|---|
| [`spec-mode`](skills/spec-mode) | Development | 规格驱动开发：需求 → 设计 → 实现 |
| [`github-kb`](skills/github-kb) | Development | 本地 GitHub 仓库知识库与检索 |
| [`git-history-cleanup`](skills/git-history-cleanup) | Development | 在最终 Tree 不变的前提下安全压缩、清理并重写 Git 历史 |
| [`github-aliyun-deploy`](skills/github-aliyun-deploy) | Infrastructure | GitHub → 阿里云 ECS 自动部署 |
| [`china-proxy`](skills/china-proxy) | Infrastructure | 命令行访问受阻时探测并应用本地代理 |
| [`wechat-account-bookmarks`](skills/wechat-account-bookmarks) | Utility | 微信公众号 → Edge / Chrome 主页或文章书签 |
| [`wechat-android-shortcuts`](skills/wechat-android-shortcuts) | Utility | ADB 驱动微信官方“添加到桌面”，创建/检查 Android 公众号或小程序快捷方式 |
| [`wechat-ios-shortcuts`](skills/wechat-ios-shortcuts) | Utility | 名称 + URL → Apple Web Clip `.mobileconfig` → iPhone/iPad 主屏幕图标 |
| [`content-research-writer`](skills/content-research-writer) | Utility | 上游 vendored：研究 → 大纲 → 引用 → 高质量文章；用于补足插件市场不可达的主 Writer |
| [`wechat-medical-writer`](skills/wechat-medical-writer) | Utility | 医荟她健康的医学约束、品牌与文章样式；复用现成 Writer 和苍何配图/排版/发布 |
| [`wechat-ai-model-writer`](skills/wechat-ai-model-writer) | Utility | AI 模型/价格/免费额度/高性价比渠道情报 → 日报/重大更新/周报选题 → 价格与渠道核验 → 科技情报刊式公众号排版 |

## 安装

### 推荐：Skills CLI

```bash
npx skills add sdwurg180507280211/my-skills
```

### Claude Code Plugin Marketplace

Codex 安装见 [医学 Skill 的宿主安装说明](skills/wechat-medical-writer/references/upstreams.md#codex)：支持将两个 Skill 链接到 `~/.agents/skills/`。下面的 `/plugin` 命令只用于 Claude Code。

```text
/plugin marketplace add sdwurg180507280211/my-skills
```

然后按需安装：

```text
/plugin install development-skills@my-skills
/plugin install infrastructure-skills@my-skills
/plugin install utility-skills@my-skills
```

`utility-skills` 会同时安装 `content-research-writer`、`wechat-medical-writer` 与 `wechat-ai-model-writer`。

### 手动安装单个 Skill

```bash
cp -R skills/<skill-name> ~/.claude/skills/
```

如果手动安装 `wechat-medical-writer` 或 `wechat-ai-model-writer`，同时复制 `skills/content-research-writer/`。

### 公众号下游（按需）

纯研究/写作不要求安装排版或发布 upstream。常规文章需要配图、微信公众号 HTML 或上传草稿箱时安装苍何：

```text
/plugin marketplace add freestylefly/canghe-skills
/plugin install content-skills@canghe-skills
/plugin install utility-skills@canghe-skills
```

专家访谈 / Q&A / 对话气泡 / 卡片 / timeline / hero 等复杂布局，可额外安装 `xiaohu-wechat-format`：

```bash
cd ~/.claude/skills/
git clone https://github.com/xiaohuailabs/xiaohu-wechat-format.git
cp xiaohu-wechat-format/config.example.json xiaohu-wechat-format/config.json
pip3 install markdown requests
```

本项目只使用它的 formatter；封面、配图和最终草稿箱发布仍优先走苍何。xiaohu README 声明 MIT，但仓库当前没有独立 `LICENSE` 文件，因此本仓库不 vendor 它。

### AI 模型省钱公众号

`wechat-ai-model-writer` 面向“AI模型省钱情报”一类素材，先把每日采集结果编辑成读者决策内容，而不是机械搬运新闻。默认路由：

```text
AI模型省钱情报
→ 判断 daily / breaking / weekly
→ 价格、免费额度、渠道与风险字段规范化
→ content-research-writer
→ 数据表 / 信息卡 / 微信 HTML
→ 人工复核
→ 发布
```

首版日报视觉与结构位于：

```text
skills/wechat-ai-model-writer/references/layouts/ai-savings-daily.md
skills/wechat-ai-model-writer/templates/daily.md
skills/wechat-ai-model-writer/templates/daily.html
```

重点使用结论卡、模型信息卡、价格对比表与风险卡，默认不依赖装饰性 AI 插画。

### “光愈在线式”公众号布局

用户运行时提供的公众号 HTML/ZIP 不进入仓库。对 11 篇“光愈在线”样本归纳出的跨文章视觉规律保存在：

```text
skills/wechat-medical-writer/references/layouts/guangyu-online.md
```

其中记录 `#F24D60` 品牌色、红色描边导语卡、学术章节标题、专家点评、左右访谈气泡、Summary、END 与合规尾注等组件画像。它只影响排版，不决定医学文章怎么写，也不作为医学证据来源。

对头像型访谈，已增加一个不依赖第三方源码的小型 HTML 后处理器：

```text
skills/wechat-medical-writer/scripts/enhance_guangyu_dialogue.py
```

它接在 xiaohu 输出之后，读取 `data-container` 标记和运行时 speaker→头像/Logo JSON，补入 50px 品牌头像环、左右灰色气泡和红色描边导语卡。它不解析 Markdown、不写医学内容、不生成头像、不发布微信；头像/Logo 和生成 HTML 都是运行时文件。离线测试位于 `skills/wechat-medical-writer/tests/test_guangyu_dialogue.py`。

## 仓库结构

```text
my-skills/
├── .claude-plugin/marketplace.json
├── .github/workflows/validate-skills.yml
├── scripts/validate_skills.py
├── skills/
│   ├── china-proxy/
│   ├── content-research-writer/
│   ├── git-history-cleanup/
│   ├── github-aliyun-deploy/
│   ├── github-kb/
│   ├── spec-mode/
│   ├── wechat-account-bookmarks/
│   ├── wechat-android-shortcuts/
│   ├── wechat-ios-shortcuts/
│   ├── wechat-ai-model-writer/
│   └── wechat-medical-writer/
├── CHANGELOG.md
├── CLAUDE.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## 校验

```bash
python3 scripts/validate_skills.py
```

GitHub Actions 会检查：Skill/frontmatter/Marketplace 结构、vendored upstream 完整性，以及 WeChat bookmarks、Android shortcuts、iOS shortcuts 和 Guangyu HTML adapter 的编译与离线测试。

## 维护原则

- 优先成熟 upstream 和最简单实现；大型通用 upstream 默认不复制。
- `content-research-writer` 是受控 vendored 例外；医学逻辑与 AI 模型省钱逻辑都不得写进它。
- 不提交 Cookie、Token、登录态、用户原始 ZIP/PPT/PDF/公众号 HTML、图片、视频、头像、Logo、患者资料或未公开研究。
- 公众号样本可在运行时用于提炼视觉画像，但画像不能成为医学事实来源，也不能把单篇样稿固化成所有文章的写作模板。
- `wechat-medical-writer` 保持医学与医荟她品牌适配：现成 Writer 使用原生流程，`content-research-writer` 为待医学对照评测的默认候选；常规排版与发布用苍何，复杂组件按需用 xiaohu；新图保存本地文件，发布时核对图片上传与实际草稿。
- `wechat-ai-model-writer` 只维护模型情报特有的选题路由、价格/免费额度/渠道风险约束和科技媒体排版；不复制通用研究写作，不把每日采集条目机械变成固定 5+2 新闻稿。
- 微信浏览器书签、Android 真机自动化、iOS Web Clip 与公众号内容编排保持独立，通过文件/数据契约松耦合。

## License

根目录代码默认使用 [MIT License](LICENSE)。个别包含独立许可证的 Skill，以其目录内许可证为准；`content-research-writer` 保留其上游 MIT License 与版权声明。
