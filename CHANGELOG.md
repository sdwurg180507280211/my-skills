# Changelog

## Unreleased — 局域网固定地址与 DHCP 保留

### Changed
- `mac-windows-lan` 增加旧 SSH 地址失效时的 DHCP 地址对照流程，以及路由器地址保留、物理网卡 MAC 核对、随机地址轮换、跨网络适用范围和目标绑定恢复。
- 记录华为随行 WiFi 3 Pro 的“高级设置 → DHCP → IP 和 MAC 地址绑定”实测入口：核对下拉预填旧地址、保存后刷新验证，电脑继续 DHCP，分开报告本机 SSH banner 与跨机登录结果。
- 增加模拟评测用例并更新技能入口与 README；个人地址、网卡标识、路由器凭据和实际截图只留本机。

## Unreleased — 界面净化、出口置顶与无头 SSH Keychain 绕行

### Added
- `claude-maintenance` 与 `china-proxy`：记录云端双账号/多账号对称隔离架构（Twin-Instance Dual-Account Isolation），包含四层物理隔离（独立固定出口、独立 Linux 用户与 `anonymousId`、iptables UID 级 Fail-Closed 绑定、独立 Web 端点与浏览器 Profile）。
- `claude-maintenance` 与 `china-proxy`：记录 Clash Verge 界面降噪净化规范（过滤 `剩余流量`、`套餐到期`、`自动选择`、`故障转移` 等冗余信息），主选择器置顶插入专属出口节点，规则链容错重定向与截断。
- 架构权衡分析：沉淀多异构机场独立订阅 vs 本地静态合并的利弊，推荐保持独立订阅以享受原厂自动更新。
- 凭据容错：记录无头 SSH 登录 macOS 导致 Keychain 锁死时，直接写入 `~/.config/gh/hosts.yml` 绕行鉴权的根治解法。

## Unreleased — Claude 完整卸载

### Changed
- `claude-maintenance` 增加完整卸载分支，与保留程序可用性的维护验收分开；承接已明确给出的清单和永久删除授权。
- 新增并存原生/nvm 安装、npm 成功但 root 属主临时包残留、任务业务成果、Git worktree、共用技能软链接、精确钥匙串和管理器历史备份处理；指定文件按内容与调用关系判断，技能同步限定保留目标，避免重建已卸载目录。
- 同步 README 与 Marketplace；个人机器路径、配置、原始资料及运行日志只留本机，不进入仓库。

## Unreleased — 课件系列模版换页

### Added
- `cleanup_after_swap.py` 和 `references/post-swap-cleanup.md`：按用户 2026-10-23 定的规则，换模版后只删合规编号（包括母版和版式里的，只删对应段落）；压到系列标志的脚注和正文、页面外的文本框、页码、病例待填内容先不删，`audit` 只列出来。
- `swap_template_pages.py` 新增 `--end-clear`、`--cover-title-box`、`--title-color`，`--title` 改为可选：用于没有标题页、结束页图里已经印好感谢语的模版。
- `wps-presentation-batch/scripts/swap_template_pages.py`：按封面、标题页、内容页、结束页四张图整份换页；对另一套模版的课件插入封面、删除旧装饰（包括复制到每页上的）、让标题避开 logo，结束页统一改成模版样式；可以只重跑一份课件。附离线测试，并在 references 第 5 节记录经验。

## Unreleased — 观众统计表整理

### Changed
- 精简规则：处理规则并入 SKILL.md，删除 references/；去掉时区、编码、哈希、私有对照、浮点容差等过度防御检查，交付改为每文件一行结论。保留“不改真实时间、不凑人数”底线。
- 默认成品改为无公式的纯文本XLSX：内部先计算核验，再将全部非空单元格实际写为字符串并设为文本格式；完整日期、零时长和累计小时保持含义，重开全部工作表核验公式数为0。同步主规则、验收场景、行为用例和工具入口，窄范围样式修改维持原范围。

### Added
- `audience-report-formatting`：将直播观众Excel/CSV整理为10列测试副本，保存参考表有效列宽、完整日期、最后一行样式、测试ID/IP与公式口径；复用宿主通用表格Skill。
- 分开保留原始直播观看时长与进出时间、首末访问跨度、正式会议内可观看上限和人数计数；严格区分“>20分钟、15条”与核销报告的另一套默认口径。缺失、跨天、时长集中和统计差异列为核验事项，不自动改写真实记录。
- 附三条合成行为用例与边界验收表；同步README、Marketplace和本机Skill链接，不保存用户原始文件、真实身份或本机绝对路径。

## Unreleased — Mac 与 Windows 局域网互访

### Added
- `mac-windows-lan`：两台电脑的双向 SSH、公钥登录、SFTP 和换网排查；区分物理接口与虚拟网卡、Windows 网络类别与防火墙范围、监听可用与实际跨机认证。
- 附 Windows 只读检查脚本及两端配置参考；初版已实测 Windows 检查脚本，后续补验 Mac 客户端连接，不保存个人地址、账号、公钥或私钥。
- README 与 Infrastructure bundle 登记新技能。

### Changed
- 补齐既有非默认密钥找回：SSH 有效配置、agent 与磁盘密钥分开检查，保留主机校验并用指定密钥完成有界认证；默认认证失败不再直接判断没有凭据。
- 增加 Windows 远程 PowerShell/Python 的 UTF-8、EncodedCommand、私有备份、文件哈希校验和 SSH/桌面会话边界，以及跨机维护 Clash 的专项参考；沿用原订阅和出口绑定，区分节点导入、固定出口与自动回退。
- 记录 Windows 服务命名管道与生成配置路径可能不同、订阅 YAML 无损保留（REALITY short-id 与序列缩进）、逐订阅内核校验、双探针出口和 TUN 连接记录验收；临时测试入口用完恢复，恢复脚本只处理变更清单。
- Mac → Windows 既有密钥登录、远程命令与当前 Clash 订阅路径已实测；反向登录、Mac 服务端、切换其他订阅、重启及故障注入保持单独待验收。新增合成行为评测，不提交个人配置与探针记录。
- `claude-maintenance` 的通用远程连接段改为引用 `mac-windows-lan`，避免把既有连接排查误写成重新安装 SSH、生成密钥和修改默认 shell。

## Unreleased — AI 视频（Seedance 短剧与纯代码动画）

### Added
- `seedance-short-drama`：按"Claude 当导演"的流程，用火山方舟 Seedance 2.x API 制作 AI 短剧。流程是需求文档 → 剧本定稿（自查清单）→ 连戏表与分段表 → Seedream 三视图与音色参考 → 分段生成 → 自动审片 → 按剪辑表出片和写自审报告，每次花钱前先报价。经验来自一集 1 分钟写实短剧的完整制作：9 条 2.5 720p 视频，8 段平均每段抽 1.1 次。
- 脚本：`ark_video.py`（单段生成，支持参考图、音色、首尾帧、`--resume`、`--list`）、`seedream.py`（角色图原图原样保存）、`run_segments.py`（按 `分段.json` 批量生成，同时最多 3 个，提交前检查素材，报出花费）、`review.py`（检查图、切镜点、macOS Vision 画面文字、有声区间、首尾音量）、`edit.py`（剪辑表：推近、打码、只换画面保留原声、定格淡出、分段响度、片尾卡）、`end_card.py`（片尾卡）。访问方舟时固定直连，不读环境变量里的代理；提交在网络层失败时不自动重试，避免重复扣费。
- 参考文档：接口、型号、价格与限额、开通门槛、写实人像审核与 Seedream 受信原图、网络与提交中断（`ark-api.md`）；官方提示词写法和"写什么出什么"的实测反例（`prompting.md`）；审片清单、修补优先级、剪辑表与自审报告（`review-and-edit.md`）；项目目录和文档模板（`project-templates.md`）。
- 25 项离线测试（含用合成小视频端到端渲染剪辑表），以及 4 条行为评测用例。不含密钥、账号信息、本机路径和具体剧情。
- `opus-code-video`：纯靠 Claude 写代码做视频，不调视频或图片生成模型。画面是网页 `renderAt(t)` 逐帧渲染的 MG 动画（复用 mg-styles-15 的 MIT 渲染器，不随仓库分发，`new_project.sh` 按需稀疏克隆），配乐和音效用 mgaudio 代码合成；旁白用豆包语音 2.0（新版控制台 API Key、异步接口、逐字时间戳）。
  - 脚本：`doubao_tts.py`（试音与整稿合成）、`retime.py`（以配音为准拉长装不下的段、锚定关键字、按标点切字幕）、`mix_voice.py`（旁白统一响度叠到底乐上、限峰值）、`qc.py`（规格、响度、峰值、黑帧，峰值超标给出重新封装命令）、`cutout.py`（纯色底贴纸抠透明）、`new_project.sh`（渲染器、依赖、字体；Intel Mac 自动装 numba 0.60）。
  - 风格 `styles/sticker-explainer/`：贴纸科普的视觉规范、结构骨架和一支可运行的示例片（《按下回车之后的 1 秒》，账号信息留空）。
  - 参考文档：豆包语音开通、音色实测、写旁白与混音（`narration.md`）；画面代码规矩、关键帧、镜头飞行、运动模糊采样、质检、事实边界（`render-and-qc.md`）；封面、角色贴纸、抖音发布（`publish.md`）。
  - 13 项离线测试（合成时间戳与 ffmpeg 输出，不联网），4 条行为评测。通用版 `retime.py` 用示例片的真实配音数据回归，结果与手写版逐项一致。

### Changed
- `opus-code-video` 流程加"剧本与审稿"一步：旁白稿交 DeepSeek 两路审（复用 seedance-short-drama 的 `review_script.py`），意见交用户批，定稿前不配音、不渲染整片；故事类先做无声版。
- `seedance-short-drama` 加上"剧本审好再生成"的关口（起因是做医生 IP 样片时，剧本经过多轮外部审稿才定下来，用户要求以后写完剧本先审、不能草率生成视频）：
  - 新增 `scripts/review_script.py`：把剧本交给 DeepSeek（默认 `deepseek-flash`、推理强度 `max`），分两路审：A 专业事实与真实性，B 台词表演与可拍性；`--prev` 复查上一轮，自动判断两路是否"必须改：无"。密钥读 `DEEPSEEK_API_KEY` 或 `~/.config/deepseek/api-key`，固定直连。6 项离线测试。
  - SKILL.md：剧本两路都"必须改：无"之前不做素材、不生成视频；写实题材先过"真实关"；花钱前先给用户看分镜预览图和提示词汇总，分辨率等选项让用户明确选。
  - `run_segments.py`：`分段.json` 的"图片"里可以直接写 `asset://` 真人素材编号，原样传入。新增 1 项测试。
  - `prompting.md`：每段写明"画面里只有谁"、道具写明归属；镜头位置决定屏幕朝向；说话的人一切过来就开口；小诊室要写明"只有一张检查床"。
  - `ark-api.md`：个人账号可以在网页上免费录真人脸（`asset://`），真人声音会被拦、音频入库只对企业账号开放。
  - 版权、合规少使劲（用户定）：`review_script.py` 的审稿提示词写明不审批文号、注册证号、广告法、超说明书、平台规则，这些不算必须改；SKILL.md 同步写明。新增 1 项测试。
  - 分辨率默认改成 480p（用户定：没提就用 480p）：`ark_video.py`、`run_segments.py` 的默认值和 SKILL.md、模板、写法说明同步改；新增 1 项测试。
  - 第一次用 DeepSeek 审已拍完的剧本（两路共 2 分半）：抓到一个审了多轮都漏掉的逻辑问题（给了两个选项，病人没说选哪个，医生就开了单）。据此在剧本自查清单加"选项要说出来"一条；`prompting.md` 加"人物固定姿态写进公共部分"；SKILL.md 写明审稿意见要逐条判断、用试跑验证，重抽前说清原因。
- `seedance-short-drama` 补上表演把关（起因是第一集看片反馈"女主表情像要杀人，太正式"，并对照了参考博主的流程）：
  - 需求增加"关键时刻"和"人物基调"两栏，作为表演的验收标准。
  - 三视图一律用中性表情、自然站姿；性格写进人物基调，情绪写进每段提示词。
  - 表演提示词改为写看谁、要做什么、情绪怎么变、呼吸和细微动作，替换"一字一顿""压低声音、带着威胁"这类示例。
  - 剧本自查清单分成结构和人物两部分，新增五项：同一信息有没有说两遍、主角对要救的人有没有关心的互动、行为合不合职业常识、台词是不是全是判断和命令、身份落差说不说得通。定稿前请另一个模型挑刺。
  - 审片清单增加逐句表演核对，自审报告单列表演结论。
  - 新增 1 条行为评测。
- `seedance-short-drama` 按 S5 对照实验修正结论（2.5 480p，同一提示词、同一 seed，只换参考图）：
  - 表演主要靠提示词写法，冷脸三视图的影响小；换中性三视图会换脸，已开拍的项目不要为了表情换图。
  - "写什么出什么"补充两条：没给动作人物就会立正；道具没写清形状就会被画错。
  - 试跑和对照实验改用 2.5 的 480p，不用 Mini 测表演。
  - 更新女主表情那条评测，新增 1 条"能不能用 Mini 测表演"的评测。
- `seedance-short-drama` 新增拆解参考视频（借鉴 OpenMontage 的参考视频分析思路，未复制其代码）：
  - `breakdown.py`：按切镜点出带编号和时间的镜头总览图，识别画面底部字幕并去重挂到镜头上，生成拆解草稿；`--compare` 和自己的成片比时长、镜头数、平均镜头长度、开头 12 秒的镜头数。中间一帧会被淡入淡出和叠化骗过，所以开头 20 秒每秒、超过 10 秒的镜头每 4 秒另抽一张带时间的拼图，草稿里长镜头会指向它。
  - `references/reference-breakdown.md`：来源边界（视频由用户自己保存，不从播放器抠地址下载）、拆解步骤、"看什么"清单、局限。
  - 需求阶段：用户给了参考视频时先拆再定需求。新增 5 项离线测试。
- `seedance-short-drama` 的本地网页工作台（`studio.py` 等）迁出为独立项目 ai-video-workbench，同时展示两类做法；项目模板改为按做法分类的总文件夹（`短剧/`、`技术解说/`、`共用/参考视频/`），作品目录放 `作品.json`；确认过时的归档可以删除。

## Unreleased — Claude 环境维护

### Fixed
- 记录“减少额外上报、优先保留云端任务”的最小配置：单独关闭错误报告与会话满意度调查，不默认设置遥测或仅必要流量总开关；区分本机管理、已保存云端任务和本地定时任务。审计器识别调查布尔开关并标记功能开关获取限制，补充离线测试与行为场景；环境检查区分来源和有效专用代理，不凭时区或非空变量判断平台异常标记。

### Added
- `claude-maintenance`：清理 Claude 本地空间、缓存、会话和旧组织数据，维护认证/第三方接口与代理残留，备份和恢复。
- 增加脱敏只读 JSON 设置审计器和合成数据离线测试；记录非必要流量开关的真值差异、新进程验证、云端与本机后台会话的网络边界及新电脑验收。
- 增加专用 Chrome 创建流程：参数发现、独立 profile、持久桌面入口、CLI OAuth、本机回调、验收和恢复；新增启动命令离线测试，保留用户精简后的文档措辞。

### Changed
- 理顺与 `china-proxy` 的分工：Claude 专属的域名规则、固定出口组、DNS 策略和专用 listener 归入 `claude-maintenance/references/clash-routing.md`；原 `china-proxy/references/claude-fixed-exit.md` 移为 `claude-maintenance/references/fixed-exit.md` 并与浏览器、认证文档去重；国内直连名单来源与转换、通用 DNS、链式代理和故障测试方法保留在 `china-proxy`。两个技能的描述与路由同步更新。
- 专用浏览器启动示例补齐本机实现已在用的 `--host-resolver-rules`、`--disable-background-networking`、`--disable-sync`，测试同步断言；`fixed-exit.md` 记录租约清理、端口单一来源、两层代理变量的作用及会话内命令继承固定出口。
- `china-proxy` 的 SKILL.md 精简为路由、模式判断、修改验证和敏感信息四部分，去掉 Claude 账号相关声明和重复的边界说明。
- `china-proxy` 记录订阅自带规则与兜底组的清理：Clash Verge Rev 2.5.7 生成顺序中订阅 Script 最后执行，用通用脚本删除前置 MATCH 之后永远不会命中的订阅规则，并从 MATCH 兜底组去掉 DIRECT；附离线测试与重新激活后的核对项。
- `claude-maintenance` 支持 Windows：新增跨平台 `scripts/exit_guard.py`（出口守护、专用 Chrome、`claude-safe` CLI 入口、OAuth helper、wrapper 生成，单一 JSON 配置，CLI 代理设置由端口自动生成），处理 Windows 的进程判断、端口独占绑定、文件锁和提示框差异；探测改用 urllib、链路检查改用 PyYAML。新增 `references/platforms.md` 对照两平台路径、命令、shell 约定与安装步骤，并列出待 Windows 实机验证项。浏览器文档改为基于守护，删除被取代的 sh 启动示例及其测试；新增 26 项离线测试和 Windows 场景评测。
- `china-proxy/scripts/detect_network.py` 支持 Windows：进程用 `tasklist`，配置目录用 `%APPDATA%`，系统代理读注册表（含 PAC），路由用 `Find-NetRoute` 和 `Get-NetAdapter` 判断是否经过 Mihomo/Wintun 网卡；输出新增 `platform`，`through_utun` 改为通用的 `through_tun`。新增 Windows 合成测试，macOS 实测结果不变。
- Windows 实机验证与修复：`exit_guard.py` 在 Windows 上调用 PowerShell 时加 `CREATE_NO_WINDOW`，修复 `pythonw` 下每 5 秒弹出命令行窗口；`platforms.md` 记录实测结果（守护链路与出口检查、转发、TUN 网卡 `Meta`、检测器）、快捷方式失效与落地缺前置等排查经验、执行策略、远程 SSH 排查方法和用一次性计划任务在桌面会话重启守护。
- 专用 Chrome 默认英文：`exit_guard.py` 加 `--lang=en-US` 和 `--accept-lang=en-US,en`（配置 `chrome_lang`，空字符串关闭）；实测 `--accept-lang` 会覆盖 profile 中存的中文。`browser-setup.md` 新增英文环境核对表；记录 macOS 上 Chrome 忽略 `--lang`、`-AppleLanguages` 启动参数会多开标签页，改用 Chrome Beta 单独设置应用语言，以及正确的 Beta 下载地址和签名校验注意事项。
- 精简防御性内容：删除账号风险参考，常见报错区分并入认证文档；清理改为按风险分级，低风险的已结束任务临时文件和缓存确认一次即可移入废纸篓；去掉各文档重复的禁令，安全底线集中在 SKILL.md。
- README 与 Infrastructure bundle 登记新技能，保持既有版本和其他本地修改；技能安装不修改本机账号、代理或数据。

## Unreleased — 技术号说文解字槽位修正

### Fixed
- `wechat-tech-writer` 的确定性组装将已有主角定义统一放在导语后、正文章节前，兼容独立定义和段首“定义＋后续说明”；保留后续段落，去除抽取定义后遗留的句号，不改原稿。
- 补充组件位置、定义唯一性、说明保留及不编造术语的离线回归测试；Skill 和 README 明确验收顺序而非仅统计组件。未提交真实文章、图片或本机路径。

## Unreleased — 技术号确定性排版

### Added
- `wechat-tech-writer/scripts/render_xiaotuanzi.py`：从图库 `styles.json` 读取 `layout-xiaotuanzi` 组件，把 Markdown（导语、说文解字、章节、小节、代码块、`>` 注意框、表格、列表、配图、参考资料与资料说明）映射填槽，输出只含正文的公众号 HTML；不复制样式，附离线测试。参考资料中的链接改为可见网址文字，因为公众号正文会去掉外部链接。
- `wechat-tech-writer/scripts/deliver_draft.py`：小团子Java 草稿入口客户端，`check` 只传文件哈希查询交付状态，`deliver` 提交成品并轮询结果；地址与令牌来自环境变量，不含凭据，提交后不重复提交。附离线测试。

## Unreleased — 仓库校验

### Changed
- `scripts/validate_skills.py` 只检查 Git 会提交的文件（已跟踪加未被忽略的新文件），本地运行测试产生的 `__pycache__` 等已忽略缓存不再导致校验失败；不在 Git 仓库中时仍扫描全部文件。

## Unreleased — 医荟她健康全生命周期定位

### Changed
- `wechat-medical-writer` 新增 `references/domains/womens-lifecycle.md`，按青春期、育龄期、孕产期、围绝经期与绝经后、老年期及贯穿全程的乳腺、肿瘤筛查、心理与生活方式组织选题；宫颈健康保留为细分领域，仅在相关主题时加载。
- 品牌画像写入宗旨“聚专业医学力量，为女性提供全生命周期健康知识与服务的媒体平台”，默认读者为普通女性；补充健康宣传日的核对要求与科普范围边界。

## Unreleased — PPT 批量替换背景

### Added
- `wps-presentation-batch/scripts/replace_backgrounds.py`：`inspect` 显示每页背景实际来自幻灯片、版式还是母版，并指出版式整页图片遮住母版背景的页；`apply` 输出到新目录，母版换正文图、封面换封面图、清除其余背景覆盖和母版/版式中的整页旧背景图，删除孤立媒体，逐页校验生效背景、遮挡与新增断链，默认不覆盖已存在输出。附合成演示文稿离线测试。
- `references/background-replacement.md`：背景继承链、两类实测结构、WPS 手动“应用到全部”清掉封面背景与另存重算自动缩放的副作用、他人并行编辑时从原始副本读取、删除图片人工复核、Quick Look 封面抽查，以及背景图压缩到 2560×1440 JPEG 的体积与画质结论。

### Changed
- `wps-presentation-batch` 的描述、路由、资源清单与评测加入背景替换；README 同步。未提交任何用户演示文稿、模板图片或本机路径。
- PPTX↔PPTM 转换改为包级无损实现 `convert_presentation_format.py`：只改主部件内容类型，PPTM→PPTX 时移除 VBA 工程及其关联部件，其余部件逐字节保留；不再经 LibreOffice 整体重存，避免 think-cell、SmartArt、动画等被改写。删除原 `convert_presentation_format.sh`。
- `render_slides_to_png.sh` 支持 `first-last` 页码范围和 `RENDER_DPI`；以独立配置目录启动 LibreOffice，避免已打开的 LibreOffice 静默吞掉任务；修复 10 页及以上演示文稿因 pdftoppm 页码补零而找不到输出的问题。
- SKILL.md 不再假定宿主是 Codex；三个脚本均有离线测试，渲染测试以桩替代 LibreOffice。

## Unreleased — 医荟她排版与真实草稿交付经验

### Changed
- `wechat-medical-writer` 沉淀已确认模板的参考文献内部滚动：240px 列表区域、12px 文献、完整条目与链接，桌面及手机宽度验到最后一条；用户本次要求优先，不把图库组件默认展开视为用户主动改选。
- 补充医学/技术账号配置隔离、同账号草稿与素材映射核验；兼容微信返回的 `data-src`、微信 CDN 与素材尺寸 URL 差异，区分本地预览、真实返回内容核验和真实客户端验收。
- 已有私有交付回执的内容指纹排除主题、模板和生成 HTML，保留重复交付与结果不明时的查询边界；草稿交付不等于医学审稿或正式发布。
- 同步 README 与 Marketplace 说明，保留版本号和其他既有改动。未复制本篇正文、素材、凭据或私有脚本，没有新增 Writer、渲染器或发布器。

## Unreleased — 会议资料网站上传

### Added
- `meeting-materials-upload`：从已执行的单人、多人和跨项目上传记录沉淀实时对账、建会、页面同源 Aura 预签名、本机 S3 直传、精确类别登记、断点续传和终验流程。
- 保存最新版资料替换及经授权删除未审核会议后重建的方法，分别核对审核状态、会议业务状态、项目全量和任务目标；不猜删除方法，不自动改审批完成会议，不将栏目勾选等同对象或内容验收。
- 增加只读批次/列表检查器、合成资料离线测试和三种流程复核场景；修正历史手抄 URL、跨批错绑、超时重发与临时目录归档的事故入口。

### Changed
- README 与 Marketplace 登记新技能，保持当前版本号和既有未提交改动；私有项目、认证、签名地址与原始资料不进入公开仓库。

## Unreleased — 图库登录与技术号默认配图风格

### Changed
- `wechat-tech-writer` 与 `wechat-medical-writer` 的图库读取说明改为“需登录”：匿名请求返回 401，本机用图库项目的 `read-wechat-recipe.py` 读取，不把密码写进链接或参数；无法登录时使用用户提供的完整方案文件。
- 移除公开仓库中的图库服务器真实 IP，改为 `<图库站点>` 占位，地址以用户给出的链接为准。
- `wechat-tech-writer` 未指定方案时，正文图与封面默认统一使用内置案例 `canghe-article-editorial`（杂志信息图），封面改为约 2.35:1 并重留标题区；不改写医学号在用的图库默认方案。
- `wechat-tech-writer` 的参考资料区与医荟她一致，固定 240px 高、内部滚动，交付时检查滚到底最后一条可见。
- `wechat-tech-writer` 默认排版改为图库模板 `layout-xiaotuanzi`（沿用医荟她模板骨架、换技术蓝，含说文解字卡、代码块、注意框和可滑动表格），按 ID 读取，不改图库默认；图库不可读时退回 `xiaotuanzi.css`。提醒类内容在 Markdown 中写成 `> ` 引用块，排版为注意框。
- `wechat-tech-writer` 写作偏好：只对文章主角用一句“缩写 = 英文全称（中文译名）”说文解字；讲用法前用横纵分析交代来历与同类对比；篇幅服从讲清楚、不设字数上限；正文用确定表述，核实不了就不写，来源只列在文末参考资料，括号只作解释。

## Unreleased — 本机 skill 收拢与软链接

### Added
- `scripts/link_skills.py`：仓库作为本机唯一来源，把 `skills/*` 软链接到 `~/.claude/skills`、`~/.agents/skills`、`~/.workbuddy/skills`；默认只读检查，`--apply` 前把旧副本移入 `~/.skill-backups/`，内容不同的副本需 `--force`。附临时目录离线测试。
- 从本机工具目录收回 4 个自沉淀 skill：`codex-dream-skin-fix`、`baidu-netdisk-syncspace-recovery`（WorkBuddy），`google-flow-story-video`、`wps-presentation-batch`（Codex）。`google-flow-story-video` 的个人项目个案含私有 Flow 链接与本地路径，只留本机并加入 `.gitignore`。
- 重新收回 `chrome-devtools`（以 `~/.agents` 中 2026-09 的版本为准），同时给出 Codex 与 Claude Code 的注册命令；只是 MCP 使用规范，不安装 MCP。
- `china-proxy/scripts/detect_network.py`：收回 Codex 版本的只读 TUN 检测器并接入文档，附合成配置离线测试。

### Changed
- `github-aliyun-deploy` 合并 WorkBuddy 版的同机多环境（develop→测试/main→生产）、webroot + SAN 证书 HTTPS 落地与踩坑 D–J；服务器公网 IP 改为占位符。
- `codex-dream-skin-fix` 的状态文件路径改为按当前用户 home 解析。
- `hatch-pet`、`codex-theme-from-image` 等第三方 skill 不复制进仓库。

## Unreleased — 会议核销资料审核

### Fixed
- 截图口径改为“有头像即合格”：不再要求正脸、完整五官或无遮挡，侧脸、遮挡、裁切和默认占位头像均不判不合格；只有背景/课件、没有参会头像或人像画面才不合格。批量检查快速浏览，有头像直接通过，仅对疑似缺失者回看整张原图，不逐张放大检查五官。同步 README、Marketplace 与技能显示说明，不保存真实会议图片或结果。
- 参会人员匹配更正为用户确认的“用户ID + 姓名”，不再按“姓名 + 医院 + 科室”推断重合；同名不同ID不重复，医院科室仅用于展示，ID/姓名缺失或冲突需核查。同步修正脚本并新增离线回归测试，不保存真实参会记录。

### Added
- 海报审核仅检查主体背景透明、缺失或明显截断，不检查文字、时间、头像或二维码；正常透明边缘和底部留白不判不合格，实际图片格式与透明区域位置辅助判断。先快速浏览，再核对异常候选原图；海报背景问题独立成表，文件缺失与待核实另列，不扩大用户指定范围，不保存真实海报或当次结果。
- `meeting-reimbursement-audit`：沉淀报告在线时长 ≥20 分钟、去重合格人数 ≥10 人、完整参会名单逐对重合率与课前/课中正脸截图的审核口径；默认仅输出不合格项，参会明细与截图分表。
- 新增只读 `.xlsx` 核对脚本与合成数据离线测试，固定等号边界、不扣会前时间、组合去重、全名单比较、双分母披露和缺值待核实逻辑。截图仍需查看原图判断，不上传网站、不修改证明原件、不保存私有名单或图片。

### Changed
- README 和 Marketplace 登记新技能；保留既有未提交改动，不发布新版本或修改已安装技能。

## Unreleased — china-proxy 路径与固定出口维护

### Changed
- 更新现有 `china-proxy`：TUN 优先按系统路由验证，显式代理按当前任务作用域使用；标明端口探测器的结果不能证明 TUN、协议或出口。
- 沉淀 Clash 国内域名/cncidr 分流、DNS 与规则顺序、原生链式代理、订阅继承、持久化、断线与整客户端退出的独立验证步骤。
- 整理 Claude 浏览器/CLI 共享出口守护、官方认证、模型选择、localhost OAuth 回调修复、桌面 App 保护范围及恢复方法。参数化端口和路径，不提交个人凭据、出口身份或运行副本。
- README 同步现有技能的用途与参考入口；保留原名称和 Marketplace 注册，不修改本机正在运行的代理或已安装 skill。

## 2026-10-09 — v1.14.0

### Added
- `baidu-netdisk`：新增百度网盘 MCP 操作技能，按真实 schema 路由浏览、文件名/正文/OCR/语义检索、整理、分享、文本保存和 URL 转存；明确现有连接器的下载、本地二进制上传和删除能力边界。
- `scripts/netdisk_mcp.py`：使用官方 MCP Python SDK，从本机已启用的 WorkBuddy / CodeBuddy 配置读取认证，支持脱敏配置检查、工具发现和 JSON 参数调用；默认总超时 45 秒，不自动切换账号或重试写操作。

### Changed
- Marketplace 的 `utility-skills` 增加 `baidu-netdisk`，版本更新为 `1.14.0`；同步 README。私有认证和服务响应不进入仓库。

## 2026-10-06 — v1.13.0

### Added
- `wechat-tech-writer`：新增小团子Java的软件推荐与实用技术图文适配层，沉淀朋友分享口吻、官方资料与实测边界、有效扩写和图文交付检查；研究、配图、排版与发布仍复用现成 Skill，不固定文章结构或图片数量。
- `assets/themes/xiaotuanzi.css`：提炼已验证技术图文的简洁视觉参数，通过苍何原生 `MD_THEME_DIR` 加载，不新增渲染器或提交私有文章、图片与凭据。

### Changed
- 补齐医学 Skill 已引用的 Image Gallery 接口说明，按当前三个具体案例更新，移除旧的独立画风/布局组合规则；固定方案链接优先，匿名读取不依赖本机维护项目，区分原始完整提示词与上游摘录。
- Marketplace 增加 `wechat-tech-writer`，版本更新为 `1.13.0`；同步安装说明与账号隔离边界。
- 补登记仓库已有但遗漏于 Marketplace/README 的 `openmaic`，不修改其实现。

## Unreleased — 医荟她健康适配层收敛

- 根据文章实际反馈沉淀连续正文、减少短句独立成段和单一段间距规则；正文默认段距调整为 16px。补充私有 HPV 样稿的导语、标题卡、参考文献与结尾视觉参数，明确基础 CSS 不等于完整组件复刻，不引入新渲染器或私有文章。

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
