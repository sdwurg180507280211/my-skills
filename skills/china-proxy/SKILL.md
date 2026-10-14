---
name: china-proxy
description: Diagnose network paths under TUN or explicit proxy mode, troubleshoot command-line access, and inspect or configure Clash routing, China-direct rule sets, DNS, and chained proxies when requested. Use for actual network/proxy tasks, not ordinary mentions of international services. Claude-specific routing, fixed exit, exit guard, and OAuth callback setup belong to claude-maintenance.
---

# Network Paths, Clash Routing, and Chained Proxies

先区分 TUN、系统代理和进程环境变量，再检查实际目标及出口。端口开放或某个网页查到的 IP 不能代替对实际请求路径的验证。

## 资料路由

- 普通命令联网、下载失败、代理残留检查：读取 [网络模式与检测](references/network-checks.md)。
- Clash / Mihomo 分流、国内直连、链式代理、订阅继承或 DNS：读取 [Clash 规则与链式代理](references/clash-routing-and-chain.md)。
- Claude 的专用分流、固定出口、出口守护、CLI wrapper 和 OAuth 回调：使用 `claude-maintenance`（[Claude 分流](../claude-maintenance/references/clash-routing.md)、[出口守护](../claude-maintenance/references/fixed-exit.md)）。

用户只要求检查或诊断时只读；修改配置、故障测试和退出应用需当次授权。已有选择从上下文和配置读取，只询问缺失且影响结果的选择。

## 确定网络模式

本机有 `~/.ai-global/PROXY_NETWORK.md` 之类的单一事实源时先完整读取，用户当前说明优先。

- **已启用 TUN**：普通请求走系统路由，不额外注入 `HTTP_PROXY`。系统代理关闭不代表 TUN 无效。
- **用户要求显式代理，或目标在 TUN 下失败**：确认入口后只对当前命令设置代理，有限重试。
- **模式不明**：在本技能目录运行 `python3 scripts/detect_network.py`（Windows 用 `py -3`）。它只读检查 Clash/Mihomo 进程、Clash Verge 生成配置、系统代理（macOS `scutil`，Windows 注册表）和探测 IP 的路由（macOS `utun`，Windows 用 `Find-NetRoute` 查到的 Mihomo/Wintun 网卡），不联网、不输出订阅或凭据。`mode: tun` 表示配置、进程与 TUN 路由互相印证；`tun_configured_unconfirmed` 或 `unknown` 只是证据不足，不代表 TUN 已关闭。具体目标的分流仍需单独验证。
- **遗留覆盖**：只为当前任务移除影响请求的旧环境变量，不永久改全局 Git/npm 配置或系统网络模式。

`scripts/detect_proxy.py` 只探测常见端口能否 TCP 连接，不确认协议、出口或 TUN，不用它决定是否关闭 TUN。

## 修改与验证

1. 找到正在使用的客户端、当前订阅、生效配置及其生成来源，区分源配置、扩展、可视化链式状态和运行配置。
2. 首次写入前备份受影响的文件，报告备份路径和恢复方法。含订阅或认证的备份留在私有目录。
3. 保留用户的节点、订阅和局域网规则；普通代理与专用出口分别处理。
4. 用实际请求验证规则和出口，验证订阅切换和重启后仍生效。
5. 断线保护分别测"节点不可用"和"代理客户端整体退出"，没做的测试标明未测。
6. 交付修改内容、观测结果、未验证项、日常操作和恢复方法。

## 敏感信息

- 不输出节点账号密码、订阅密钥、OAuth `code/state`、Cookie、API Key、邮箱或组织标识。
- 不把完整 Clash YAML、settings、浏览器 profile 或会话日志放进公开仓库，只沉淀参数化步骤和合成测试。
- 公网 IP、ASN、地理库城市和 DNS 解析器分开记录；同一 IP 的城市库不一致不等于出口变化。
