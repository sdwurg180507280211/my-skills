# 认证与配置残留

## 检查范围

当前进程环境；`.zshrc`、`.zshenv`、`.zprofile`、`.bashrc`、`.bash_profile`、`.profile`；Windows 上还有用户/系统环境变量、PowerShell `$PROFILE` 和 Git Bash 的 `~/.bashrc`（见 [平台差异](platforms.md)）；用户、项目、local 和托管设置；启动器额外传入的 `--settings`；npm/yarn/pnpm、Git、Homebrew 的代理设置。另核对 `which claude` 的实际二进制和 shell alias/wrapper。

只报告键名、来源和类别，不用 `env | grep` 或 `cat settings.json` 直接输出。JSON 设置可用 `scripts/audit_settings.py`（从技能根目录运行）。不要运行未知的 `apiKeyHelper`、hooks 或启动脚本来"检查"它们。

## 各类键的含义

检查有意代理与遗留覆盖时，分别报告当前检查进程继承环境、shell 静态定义、launchd/Windows 用户与系统环境、Claude 用户/项目设置和 wrapper 的来源。读取 shell 所引用的本地附加配置，区分赋值、unset 和代码引用；不执行未知启动脚本。当前检查进程不能代表用户已经打开的所有终端，文件检查也不能代表 Claude 合并后的有效环境。

时区可报告系统设置与 `TZ` 覆盖是否存在；终端环境可被本机进程读取，不代表所有变量都被上传。存在代理变量或时区不同本身不是平台“直接标记异常”的证据。用实际认证、请求与错误记录判断，不把非空代理当作风险清单一律清空。

| 配置 | 判断 |
|---|---|
| `HTTP(S)_PROXY`、`ALL_PROXY`（含小写） | 进程代理；可能是用户有意设置的，确认过时后再删 |
| `NO_PROXY` | 绕过范围；只含本机地址正常。若需在受保护环境中调用国内自建服务/私有网关（如国内云主机），必须加入其 IP 豁免，避免跨国经海外出口回流导致握手重置 |
| `ANTHROPIC_BASE_URL` | API 地址，不是代理；指向第三方网关时与官方订阅冲突 |
| `ANTHROPIC_API_KEY`、`ANTHROPIC_AUTH_TOKEN` | 会覆盖订阅登录；用户要用官方订阅时才移除 |
| `apiKeyHelper`、`forceLoginMethod`、`CLAUDE_CODE_USE_*` | 改变认证方式或服务提供方 |
| `CLAUDE_CONFIG_DIR` | 改变数据根目录，清理时以它为准 |
| `CLAUDE_CODE_*`、遥测开关 | 各有语义，见 [功能开关](features-and-sessions.md) |

优先级以官方 [设置文档](https://code.claude.com/docs/en/settings) 和 [环境变量](https://code.claude.com/docs/en/env-vars) 为准。托管设置由管理员控制，本技能不修改。

## 修复与验证

备份要改的文件，只删或改冲突的键，比较修改前后其他内容不变。shell 里的变量从实际定义它的文件处理，不改 Git/npm 的全局代理。改完新开终端、新启动 CLI 验证，已在运行的进程不会因文件改动而 unset 变量。

用 `claude auth status` 核对是否已登录、认证方式和 provider，只报告这三项。

## 常见报错

| 报错 | 先查什么 |
|---|---|
| `essential-traffic-only` | 非必要流量开关，见 [功能开关](features-and-sessions.md) |
| `App unavailable in region` | 出口地区；网络问题交给 `china-proxy` |
| OAuth localhost 回调失败 | `NO_PROXY` 是否包含本机地址、回调端口是否被代理接管 |
| 私有网关握手中断 (`SSL_ERROR_SYSCALL`) | 请求被全局/进程代理带入海外出口；需将国内私有 IP 加入 `NO_PROXY` 保持直连 |
| 401/403 | 认证来源冲突（API Key 覆盖订阅）、令牌过期，再看网络 |
| 账号停用通知 | 按官方 [申诉流程](https://support.claude.com/en/articles/8241253-safeguards-warnings-and-appeals) 处理，本地清理无法解决 |
