# 从 Mac 维护 Windows 的 Clash

本文件只补充跨机发现、Windows 控制通道、无损暂存和验收。分流/DNS/链式代理的规则读取 [china-proxy](../../china-proxy/SKILL.md) 及它的链式参考；Claude 固定出口、专用 listener 和守护读取 [claude-maintenance](../../claude-maintenance/SKILL.md) 及其分流/出口守护参考。不要在这里维护另一套 Claude 域名清单。

## “与本机一样”先拆成约定字段

分别检查两台机器当前配置，不整份复制。通常同步的是指定出口的协议、地址、端口、认证和显示名称；远端自己的订阅 UID、扩展 UID、文件路径、普通节点选择、前置节点引用、系统代理与 TUN 状态继续使用远端值。

特别核对远端的 `expected_ip`、`exit_node`、专用 listener、Claude 规则/固定组和 DNS 指向：两台机器可能使用同一批落地节点，却正在固定使用不同出口。用户只要求“加入两个出口”时保持远端既有绑定，不让它跟随本机的当前出口变化。添加备用节点与启用自动回退是不同的动作。

前置应引用该订阅里实际存在的普通节点，不能照抄另一台机器/订阅的名称，也不复制一个永久专用前置。已有可视化链式关系时保留；确实缺失、且任务包括使该链可用时，在用户指定或明确可复用的普通前置范围内补齐并说明。前置缺少依据时询问，不从一个测速结果自动替用户选线。

## 找到实际配置与控制通道

Windows 常见源目录为 `%APPDATA%\io.github.clash-verge-rev.clash-verge-rev`。核对运行中的 Clash Verge/Mihomo 进程与命令行；服务模式的实际 `-d`、`-f` 可能位于 `%ProgramData%\clash-verge-service\users\<实例标识>\runtime`，不写死用户 SID/哈希。

检查 `profiles.yaml`：当前订阅、各订阅的 `option.proxies/merge/rules/groups/script` 指向，以及 `selected`。扩展文件名从这个索引找，不假定 Mac 与 Windows UID 相同。继续按[远程维护参考](remote-operations.md#私有备份与有限范围写入)备份。

Windows 服务模式可通过命名管道控制内核，不需要另开一个局域网 TCP controller：

- 从实际内核命令行的 `-ext-ctl-pipe` 发现控制管道；必要时只读枚举管道名，与进程实例核对。生成 YAML 中的 `external-controller-pipe` 可能是 sidecar 路径，与服务正在使用的 production 管道不同。
- 使用 Windows 本机 API/文件句柄打开该管道，传送 HTTP。Python 可用 `open(pipe, 'r+b', buffering=0)`，以适配 `makefile()` 的包装交给 `http.client.HTTPResponse` 解析状态码、Content-Length 或 chunked 正文；写入时确保请求全部发送。
- 从私有配置读 controller secret，仅在内存中组装 Authorization。将整个探测放在有总超时的子进程中，避免无应答的管道读阻塞主任务。
- 先用只读 `/configs`、`/proxies`、`/rules`、`/providers/rules` 和 `/connections` 核对运行态。`PUT /configs?force=false` 与 `PUT /proxies/<编码后组名>` 只在本次修改授权内使用。

HTTP 204 只说明内核接受了加载请求；继续查询代理列表、组的 `now/all`、规则和实际出口。管道不可用时报告真实通道问题，不通过关闭认证或开放公网 controller 绕过。

## 保留订阅原始 YAML

凭据保存在每个订阅持久化的代理扩展中；生成配置只用于当前加载和对照。按落地的协议/服务器/端口及已确认身份识别迁移目标，保留无关节点，防止同一出口以旧名和新名重复出现。

全量 `safe_load` → JSON/JS → `safe_dump` 可能改变未加引号的数字样式。例如 REALITY 的全数字 `short-id` 可能被当作数字，丢失前导零或改写进制，随后报 `invalid REALITY short ID`。本次没有要更改这些节点时，保留其原始 YAML 块，只对目标节点块和已确认引用做局部修改。

拼装校验候选也要保留供应商的节点块。合并顶层 `proxies` 序列时处理缩进差异；源序列可能缩进数格，生成文件可能顶格 `- name:`。顶格列表项的 `-` 不是下一个顶层映射键，不能用“任意非空白行”截断整个代理块。拼装后先解析，再用目标实际安装的 Mihomo 验证。

逐个订阅检查以下关联：

- 两个出口名称唯一、身份/认证正确，前置引用存在且无循环。
- 普通手动组能看到新增出口；Claude 固定组仍只含原来选定的那个出口，不添加 DIRECT、自动切换或备用出口。
- 重命名更新代理、组/规则引用、listener、保存的选择和守护 `exit_node`。只改名称时 `expected_ip` 不变；DNS 中引用旧名称时一并更名。
- 使用最终生成阶段的已有全局/订阅扩展时，沿用已有架构，只补齐本次需要的节点引用；不为了两个节点重写整套规则或另装后台同步任务。

## 加载与验收

1. 将所有订阅的候选配置交给实际内核 `-d <运行目录> -f <候选文件> -t`；保留私有日志。这样校验的是该平台内核及现有规则文件，不是仅证明 YAML 能解析。
2. 写前核对哈希，写入持久化源及必要的当前生成文件，通过实际 controller 热加载。保存并恢复普通组的 `now`，核对当前订阅未变。
3. 经每个出口分别用两个探针查询公网 IP，例如 IPify 与 Claude Trace；不切换正常流量组来“借用”另一个出口。
4. 没有现成的逐出口测试入口时，可在内核内临时添加一个未占用的 loopback listener，显式绑定被测出口；不写进长期扩展。用 `try/finally` 恢复正式配置和原选择，确认临时端口已释放。测试不通过不自动改 IP 白名单。
5. 再从 Windows 执行不加显式代理参数的新请求。仅为该诊断子进程清理影响路径的旧 proxy 变量；用 `/connections` 核实 Claude 命中固定出口、国内网站命中直连规则。仅有 listener 探针不能证明 TUN 分流正确。
6. 查询运行模式、TUN、系统代理、固定组成员、国内规则 provider 和专用入口。守护进程正在运行时确认它已读取新名称；没有运行则说明下次启动读取，不因此启动新的常驻进程。

交付时分开列出“源扩展已保存”“候选内核校验通过”“当前订阅实测通过”“切换/重启/节点失效/整个客户端退出是否实测”。不把前三者写成全部订阅及断线保护都已验收。切换订阅、重启或故障注入会影响使用时，先确认用户允许并记录恢复点。
