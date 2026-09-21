# 上游、安装与验证边界

本项目直接使用现成写作、配图、排版和发布能力。版本记录代表审计对象，不代表已安装版本或已通过端到端验收。运行时读取真实 Skill 文件与实现；升级后复核相关接口。

## Writer 选择

当前默认候选为 `CommandCodeAI/agent-skills` 的 `content-research-writer`，审计版本 `f490dd9016f2729311e90f317dcb6c98be1a1500`。它提供通用研究、资料整理、大纲、引用和协作写作，尚未证明中文医学长文表现。不要把“有 research 名称”当成医学证据质量保证。

| 候选 | 当前取舍 | 未完成验证 |
|---|---|---|
| content-research-writer | 可直接用现有独立 Skill，作为默认候选 | 原始来源核验、中文长文、连续论证与医学引用闭环 |
| nashsu/Viral_Writer_Skill | 偏传播表达；按需作为润色层，不默认串联 | 不夸大医学事实的能力；许可证需核对 |
| xstongxue/best-skills 中 wechat-article-writer | 默认绑定“小帅随笔”技术口吻、故事化开头与爆款标题，不推荐直接作为医学主 Writer | 原生中文能力值得评测，但需避免他人品牌与技术场景进入医学稿 |
| 其他研究型候选 | 只有读完实际 SKILL.md、实现与许可证才加入 | 主题到成稿、来源溯源、中文、组合接口、维护与依赖 |

以上是静态取舍，不能代替实测排名。Viral 已审计版本为 `1c76f891fb928ceb22fd101044d100d759f8cee5`；未确认许可证时不复制内容。其他候选未记录固定版本的，不声称已完成版本审计。

对比时使用用户两篇已发布文章的主题（HPV 阳性与宫颈癌、婴儿喂养与成年健康），提供相同受众、来源和篇幅要求，分别按候选原生流程成稿。检查真实引用、关键数字的人群/时间范围、医学错误、中文可读性、长文连续性、营销倾向、依赖、许可证及维护情况。样稿只作风格参考，不是正确答案或医学证据。无实际成稿与来源核验结果，不指定最终获胜者。

目前不默认使用第二个 Writer。表达优化必须保持医学事实与引用关系。

补充源码审计：`wechat-article-writer` 在 `9aa4e555950da6e43e7d98c5f0c7b70264204850` 的 SKILL.md 要求优先当月/当季资料及技术社区来源；其 `reference/writing_style.md` 明确使用“小帅”“我”及软件资源推广式结尾。Viral 的上述固定版本强调恐惧、紧迫感、情感曲线和互动钩子，未提供独立医学检索实现。两者都不能因中文流畅就被视为更强的医学研究依赖。以上是源码审计，不是生成质量盲测。

## 加载与安装

“handoff”是代理执行指令，不是 Skill 间函数接口。开始写作前定位并完整读取 Writer 的 `SKILL.md`；记录实际所用路径/版本即可，不强制新增报告文件。缺失时给出安装路径，不自行重写其工作流。

本仓库现有 `skills/content-research-writer/` 是历史受控 MIT 副本，保留 LICENSE、UPSTREAM.md 与完整性锁；本轮不修改它，也不新增 fork。默认直接依赖上游；以后能直接安装时再统一迁移其他消费者，不在医学改动中破坏 AI 模型写作 Skill 的依赖。

### Codex

官方支持用户级 `~/.agents/skills/` 和符号链接，参见 https://developers.openai.com/codex/skills/ 。在本仓库根目录执行：

```bash
mkdir -p ~/.agents/skills
ln -s "$PWD/skills/wechat-medical-writer" ~/.agents/skills/wechat-medical-writer
ln -s "$PWD/skills/content-research-writer" ~/.agents/skills/content-research-writer
```

先检查目标是否已经存在；已有安装就使用或核对来源，不加覆盖参数。符号链接会随本地仓库更新。Codex 通常自动发现变化，未出现时重启。单个 Skill 不必为了被发现而另建整个插件；`agents/openai.yaml` 只是可选显示元数据。

苍何按其安装说明把需要的三个 Skill 安装到宿主支持的目录；Codex 可用自带 `skill-installer` 从 `freestylefly/canghe-skills` 安装以下真实路径：

```text
skills/canghe-article-illustrator
skills/canghe-markdown-to-html
skills/canghe-post-to-wechat
```

安装 Skill 后仍要按各自说明检查运行时依赖。插件命令、API 凭据和浏览器连接不能互相替代。

### 新电脑复现

仅复制本 Skill 不会自动安装上游、运行时或迁移私有文件。要复现本次验证的排版行为：

1. 获取本仓库同一提交的完整 Skill 目录（包括 references、assets 和 agents），同时安装同仓库的 content-research-writer；按上面的宿主路径发现规则启用。
2. 通过现成安装器安装苍何三个 Skill，明确指定 ref 为 `dd0bf355955b4c82b764740b4183c86a72ba0e0c`。默认下载最新分支不等于复现本次环境。
3. 准备 Bun 与 Node/npm。实测环境为 macOS、Bun 1.3.14、Node 24.13.1；这是已验证版本，不是宣称其他版本不可用。Python 3.12 只在使用现有访谈适配器/相应安装工具时需要。
4. 在实际安装的 `canghe-markdown-to-html/scripts/md/` 目录运行 `npm ci`，使用其 package-lock.json。网络受限时使用新电脑真实可用的代理，不把旧电脑的代理端口视为必然存在。
5. 按 [医荟她文章样式](layouts/yihui-article-style.md) 解析本机 Skill 路径，设置 MD_THEME_DIR 并执行上游 render.ts。不要沿用旧电脑的绝对路径，也不要漏掉外部 yihui 主题。
6. 私有医学资料、原文章、科学图、已选 Logo 和封面通过私有渠道迁移；检查文章图片路径。新写文章不必拥有旧样稿才能使用已提炼样式，但精确重现旧文章需要相同正文与图片。
7. 需要新图时，按配图上游说明配置可用图像生成工具/服务；安装 illustrator 的指导文件不等于已经具备图像生成能力。需要发布时，在新电脑配置微信凭据或登录会话，不能从公开仓库恢复它们。

验收顺序：本地图片完整 → 原版渲染器输出 → 390px 手机预览 → 引用与 H1 检查 → 用户要求发布时核对真实草稿。不要将安装成功等同于文章质量或发布成功。

可复用的是医学约束、品牌规则、CSS 参数和上游接口。文章质量还受模型、资料和检索能力影响；相同主题不能保证逐字相同。系统字体、屏幕与微信客户端差异会影响换行和像素表现；相同 CSS 不保证跨系统截图完全一致。当前仅完成本机验证，未声称已在全新电脑或 Windows/Linux 验证。

### Claude Code

```text
/plugin marketplace add sdwurg180507280211/my-skills
/plugin install utility-skills@my-skills
/plugin marketplace add freestylefly/canghe-skills
/plugin install content-skills@canghe-skills
/plugin install utility-skills@canghe-skills
```

这些是 Claude 的命令，不是 Codex 的命令。纯写作不要求安装苍何。

## 苍何

来源：https://github.com/freestylefly/canghe-skills
审计版本：`dd0bf355955b4c82b764740b4183c86a72ba0e0c`。

普通配图交给 `canghe-article-illustrator`；Markdown → 微信 HTML 交给 `canghe-markdown-to-html`；草稿上传交给 `canghe-post-to-wechat`。医学 Skill 不复制其实现。科学图仍叠加本目录的证据与精确文字约束。

### 发布器已知限制

经重新读取该版本 [wechat-api.ts](https://github.com/freestylefly/canghe-skills/blob/dd0bf355955b4c82b764740b4183c86a72ba0e0c/skills/canghe-post-to-wechat/scripts/wechat-api.ts)：

- `uploadImage` 支持 HTTP(S) 图片和本地文件；data URI 会被当成文件路径，不能直接输入。
- `uploadImagesInHtml` 捕获单张图片上传异常后继续执行，可能创建含失效图片的草稿。离线故障注入已复现：第二张图返回上传错误，仍调用 draft/add 并输出 success。
- 上传后已执行 `htmlContent = processedHtml`，最终正文使用了替换结果。“processedHtml 未用于发布”是早先审计误报，已撤回。
- `--dry-run` 在获取 token 和上传图片之前返回；它验证输入处理，不验证图片上传或真实草稿。

当前可用输入策略：新图保存为本地 PNG/JPEG，成稿引用实际文件路径；不要为了单文件预览而默认嵌入 base64。旧的内嵌图样本需要先由支持该输入的上游转换，或明确报告输入限制。发布后核对每张正文图与封面；有上传错误时即使获得草稿 ID 也不能报告整篇成功。

2026-09-21 本地验证：已安装该固定版本三个苍何 Skill。用私有 HPV 样本的两张独立 PNG 与内嵌数据逐字节比对，在私有工作副本中仅替换图片 src；拦截全部 fetch 后运行原版 API 脚本，确认两次模拟上传及最终请求的两张 CDN 图片地址。未访问微信接口、未创建真实草稿；不将模拟结果视为凭据、账号权限或微信服务端兼容性验证。该测试发现发布器默认会用首图作封面，正式发布应明确提供 2.35:1 封面。

排版使用上游外部主题接口与原版渲染器，已验证入口和限制见 [医荟她文章样式](layouts/yihui-article-style.md)。不把 EXTEND.md 中的一句字号偏好误当成已经执行的 CSS。

上游改进应在上游独立提交：支持明确的 data URI 类型，图片失败中止创建草稿，增加模拟上传回归。未经测试不得声称这些改进已完成；不在本仓库长期维护发布器补丁或第二套微信上传逻辑。

## 可选复杂布局

来源：https://github.com/xiaohuailabs/xiaohu-wechat-format
审计版本：`dbddf0fd9c1189a6f3e0bec1bebb1b0e47e8ddf0`。

只用 formatter 的 interview、intro、dialogue 等容器，不用其封面生成或 publish.py。按仓库 README 安装到实际宿主 Skill 目录，并安装其要求的运行依赖。纯排版不需要填写公众号凭据。审计时 README 声明 MIT，但没有独立 LICENSE，故不复制实现或维护 fork；安装时重新确认。

只有明确需要头像访谈才使用现有 `scripts/enhance_guangyu_dialogue.py`，输入 xiaohu 带 data-container 标记的 HTML 和运行时 speaker → 真实头像 JSON：

```bash
python3 scripts/enhance_guangyu_dialogue.py \
  --input /path/to/formatted.html \
  --avatars /path/to/avatars.json \
  --output /path/to/formatted.yihui.html
```

speaker 使用医荟她健康及文章真实受访者名称，与正文完全一致。素材与映射留在私有目录。该适配器只补 intro 与头像样式，不能证明整篇复刻或发布成功；上游支持等价能力后优先移除它。
