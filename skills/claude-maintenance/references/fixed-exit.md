# 出口守护与 CLI 入口

实现是 `scripts/exit_guard.py`，macOS、Windows、Linux 通用（Python 3.9+，链路检查需要 PyYAML）。本机已有其他实现时先读它的配置和启动入口，迁移前确认用户同意。

## 架构

```text
专用 Chrome / claude-safe
  → exit_guard（示例 17890）
  → Clash 专用 listener（示例 17891，见 clash-routing.md）
  → 普通前置 → 固定落地 → Claude
```

普通 TUN 流量和使用守护的流量是两个作用域；守护到 listener 走 loopback，不被 TUN 接管。

## 配置

一个 JSON 文件，默认位置：macOS `~/Library/Application Support/Claude Dedicated Guard/config.json`，Windows `%APPDATA%\Claude Dedicated Guard\config.json`；也可用 `--config` 或环境变量 `CLAUDE_GUARD_CONFIG` 指定。

| 键 | 含义 |
|---|---|
| `expected_ip` | 用户确认的固定出口公网 IP |
| `listen_host` / `listen_port` | 守护监听地址，默认 `127.0.0.1` |
| `upstream_host` / `upstream_port` | Clash 专用 listener |
| `exit_node` | 固定落地节点名，用于链路检查 |
| `clash_config` | Clash Verge 生成的运行配置（`clash-verge.yaml`） |
| `profile` | 专用 Chrome 的 user-data-dir |
| `state_dir` | 锁、日志、租约和 CLI 代理设置所在目录 |
| `chrome` | Chrome 可执行文件 |
| `claude_bin` | 官方 Claude Code 可执行文件（`cli` 子命令需要） |
| `browser_helper` | `install-wrappers` 生成的 OAuth helper 路径 |
| `check_interval_seconds` 等 | 默认 20 / 10 / 40 秒，见下节 |
| `chrome_lang` | 默认 `en-US`：专用 Chrome 的界面语言和 Accept-Language；空字符串表示不指定 |
| `strip_api_env` | 默认 true：为官方订阅登录移除继承的 `ANTHROPIC_*` 和第三方 provider 变量；合法 API 用户设为 false |

CLI 用的代理变量由 `listen_host`/`listen_port` 在运行时生成，写到 `state_dir/cli-network-settings.json` 并通过 `--settings` 传入，不再手写第二份。

## 子命令

| 命令 | 作用 |
|---|---|
| `browser`（默认） | 启动或复用守护，检查通过后打开专用 Chrome |
| `serve` | 只运行守护；`cli` 在守护未运行时自动后台启动它 |
| `cli [参数...]` | 守护就绪后启动官方 CLI，设置代理、`NO_PROXY`（只放 loopback）和 `BROWSER` |
| `open-url URL...` | OAuth helper：在专用 Chrome 打开授权页，只接受 http/https |
| `status` | 输出守护状态 JSON，已确认出口时退出码 0 |
| `install-wrappers --bin-dir DIR` | 生成 `claude-safe` 和 `claude-oauth-browser`（Windows 为 `.cmd`） |

## 守护行为

- 每 20 秒复查；新连接距上次确认超过 10 秒先复查；确认最长有效 40 秒。
- 两个探针（IPify、Cloudflare）经 listener 查询出口：任一返回非期望 IP → 阻断；都无法确认 → 阻断；一个确认、一个失败 → 放行并在状态里标明检测降级。
- 先校验链路：listener 绑定 `exit_node`，该节点有真实前置（不是 DIRECT/REJECT/GLOBAL）。
- 阻断时拒绝新连接并关闭已有隧道，确认恢复后放行。只读状态页在 `/__claude_guard_status`。
- 浏览器和 CLI 都退出 60 秒后守护自动停止。CLI 用租约文件表示在用；入口转发 SIGHUP，关闭终端也会删租约；守护会删除进程已不存在的租约。
- 守护不改 Clash、不切节点、不自动接受新 IP，也不会直连目标。这是周期检测，存在发现窗口；绕过守护的应用不受保护。

## CLI 入口

- 官方二进制保持原样，受保护入口叫 `claude-safe`；需要简写时用 shell function（Git Bash/zsh）或 PowerShell function 调用它。用 `type claude` / `Get-Command claude` 确认实际调用的是哪个。
- `claude-safe` 拒绝 `--settings`，避免覆盖网络设置。
- `~/.claude/settings.json` 里可以再放一份同样的代理变量，让直接运行官方二进制或 App 内的 Claude Code 也走守护（守护未运行时失败而不是直连）。这份要与守护端口保持一致。
- Claude 会话里执行的命令（git、npm、curl）继承这组代理变量，走固定出口。需要直连的目标在命令里清空代理（`curl --proxy ''`、`env -u HTTPS_PROXY ...`）。

## OAuth 回调

已发生的故障：Chrome 只设 `--proxy-bypass-list=<-loopback>` 时，本机回调被送进代理，CLI 仍在监听 `127.0.0.1:<临时端口>`，浏览器显示 localhost 无法访问。现在的参数只放行字面 loopback，见 [专用 Chrome](browser-setup.md)。

排查顺序：

1. 查 CLI 的临时 listener 是否还在（macOS `lsof -nP -iTCP -sTCP:LISTEN`，Windows `Get-NetTCPConnection -State Listen`），区分代理绕行、解析失败、进程退出和授权过期。不重放用户粘贴的 `code`/`state`。
2. 修改参数后完整退出专用 Chrome 实例再打开。
3. 用临时 profile 和合成 `TEST_ONLY` 参数测试 localhost、127.0.0.1 回调。
4. 让用户重新发起官方登录，成功后用 `claude auth status` 核对。

## 模型升级

通过 `claude-safe` 执行升级并观察下载。只为当前选择设置 `model`，不为换模型改 API 地址或代理。用禁用工具的最小请求验证，以返回结果中的模型 ID 为准。

## 测试与恢复

`tests/test_exit_guard.py` 用合成配置和本机 socket 覆盖：出口判定、链路检查、阻断关闭连接、状态页、租约清理、进程判断、CLI 环境、Chrome 参数和两种平台的 wrapper。它们不能代替真实节点故障、Clash 整体退出、Windows 实机和 Claude App 的验证。

按层保留上一份：Clash 扩展和链式选择、守护配置、桌面入口、wrapper、shell function。恢复只覆盖本次修改；停止守护时按状态里的 PID，不按进程名批量结束。
