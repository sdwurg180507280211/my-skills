# 认证和配置残留审计

## 配置来源与输出范围

先核对实际 CLI 版本、真实二进制、shell alias/function/wrapper、配置根目录。独立启动器与 Dock App 不一定读取同一环境。不要运行启动文件、未知 `apiKeyHelper` 或 hooks 来“检查”它们。

检查范围：当前进程环境；`.zshrc`、`.zshenv`、`.zprofile`、`.bashrc`、`.bash_profile`、`.profile`；用户、项目、local 和托管设置；启动器额外 `--settings`；npm/yarn/pnpm、Git、Homebrew 的代理覆盖。文件不存在和工具未安装都不是脏配置。

先读解析后的相关键与来源，不把 `env | grep ...`、完整 `cat settings.json`、Git/npm 配置或完整 shell 匹配行直接输出。只报告名称、是否配置、所属类别和影响。安全报告中也不包含邮箱/组织标识或私有地址。

只读 JSON 帮手位于 `scripts/audit_settings.py`，从技能根目录运行；将已经发现的实际路径传给 `--settings`，按输入次序识别 `settings[1]` 等标签。`--include-process-env` 是显式选项，只检查执行帮手时的子进程，不代表用户现有终端的环境。它不做合并、认证、shell 文本解析或完整 schema 校验。

## 区分这些键，而不是“非空就删”

| 配置 | 意义与判断 |
|---|---|
| HTTP/HTTPS/ALL_PROXY，含小写 | 进程代理；可能是用户主动使用的专用入口，保留直到确认是过时覆盖 |
| NO_PROXY/no_proxy | 绕过范围；必要 loopback 回调正常，远程域名/通配符可能绕过保护 |
| `ANTHROPIC_BASE_URL` | API 地址；不是代理变量，正确拼写含下划线；自定义网关也不等于违反规则 |
| API Key、Auth Token、OAuth | 不同认证来源；不能把配置存在直接判为被封依据 |
| `apiKeyHelper`、`forceLoginMethod`、provider 选择 | 可能改变认证/服务提供方；先确认用户要官方订阅还是合法 API/provider |
| `CLAUDE_CONFIG_DIR` | 更改数据根目录；只清默认目录可能漏掉实际环境 |
| `CLAUDE_CODE_*`、遥测/功能开关 | 各有语义，不是所有项都要清空；见 [功能开关](features-and-sessions.md) |

当前 [官方环境变量](https://code.claude.com/docs/en/env-vars) 说明 API Key 可以覆盖订阅认证；用户明确要官方订阅 OAuth 时才处理冲突的第三方接口、provider 和 API 认证来源。用户合法使用 API 时保留其必要认证，不自动切回 OAuth。

托管设置、CLI 额外设置及 shell 环境的优先级须按当前 [设置文档](https://code.claude.com/docs/en/settings) 核对；扫描用户 settings 一处不能证明整个有效环境已干净。管理员策略不可由本技能绕过。

## 最小修复与登录验收

备份实际来源，再只移除/修正确认冲突的键。比较修改前后结构，核对代理键、默认模型、权限、hooks 和其他环境不变。不把某个非必要流量开关替换成一批未经要求的隐私开关。已停用旧脚本只报告它们会重新注入配置；未获当前授权不修改或重新运行它们。

删除文件中的环境键后重新启动新 CLI 进程；已有进程不会因为文件删键就必然 unset。shell 变量也要从实际生效来源处理，新开终端并核对，而不是替用户全局删除 Git/npm 的代理。

当前版本支持时用官方 `auth status`，但在本机解析，仅报告是否登录、认证方式和 provider；不要原样输出账户 JSON。交互式 `/status` 可让用户自己核对账号/组织。退出/登录是单独的认证操作；不要在只读审计时执行 `/logout`。

OAuth localhost 报错、地区不可用、额度耗尽和封禁通知分别排查。需要回调/网络验证时读取 `china-proxy`；不重放真实 `code/state`，不以认证成功证明模型可用或账号免封。

官方来源（维护时重新核验，2026-10-14 核对）：[认证](https://code.claude.com/docs/en/authentication)、[设置](https://code.claude.com/docs/en/settings)、[环境变量](https://code.claude.com/docs/en/env-vars)。
