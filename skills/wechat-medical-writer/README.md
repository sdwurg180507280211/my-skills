# wechat-medical-writer

“医荟她健康”的医学公众号适配层。保留医学领域与证据约束、品牌资产规则以及用户喜欢的 HPV 文章样式；研究写作、普通配图、HTML 与草稿发布交给上游。

入口见 [SKILL.md](SKILL.md)，默认排版基准见 [医荟她文章样式](references/layouts/yihui-article-style.md)。光愈在线仅为视觉来源，访谈与首发参考按需加载。

## 使用

- 给主题：加载已安装 Writer 的原生流程，传入医学约束。`content-research-writer` 是当前默认候选，医学中文长文能力尚待对照评测。
- 给成稿：保留医学事实和引用，使用医荟她样式排版，不强制重写文章。
- 要科学图：读取 Figure 约束，用当前文章与已核验证据决定内容，按语义放图。
- 要草稿：加载苍何发布器，检查图片输入兼容性并查看真实草稿。完成本地 HTML 不等于完成发布。

依赖路径、版本记录、安装方法和发布器限制统一维护在 [upstreams.md](references/upstreams.md)。Codex 与 Claude 使用不同安装方式，不能把 Claude 的 `/plugin` 命令当作 Codex 命令。

换电脑请按 [新电脑复现](references/upstreams.md#新电脑复现) 安装固定版本上游和渲染依赖、加载主题，并私下迁移所需资料。仅安装本 Skill 不代表依赖、图片、模型服务或微信登录已配置。

## 维护边界

原始 ZIP/PPT、样本 HTML、图片、Logo、文章和凭据留在用户私有工作目录。品牌二进制资产由独立 image-gallery 管理。本目录不创建通用 Writer、排版器、发布器或新的固定文章模板。

现有 `scripts/enhance_guangyu_dialogue.py` 只补访谈头像样式，保持按需使用；其离线测试不代表整篇医学文章或微信发布已经验收。
