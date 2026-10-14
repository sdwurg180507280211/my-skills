# 功能开关、云端请求和会话分叉

## 非必要流量开关不是防封开关

已遇到的故障类型：用户设置和旧启动脚本生成的配置都含 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`，创建远程任务报 `Remote triggers unavailable: essential-traffic-only`。先查本地功能门禁，不因这条错误直接重做 GitHub 授权或清掉登录。

当前官方文档说明 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`、`DISABLE_TELEMETRY`、`DISABLE_ERROR_REPORTING` 按非空值启用，包括字符串 `0`、`false`；不要用这两个字符串当关闭办法。`DISABLE_GROWTHBOOK` 等其他开关有自己的真值规则，不能把同一规则套给所有变量。

这些变量的效果不同：禁止非必要流量、禁止事件上报、禁止错误报告、禁止特性获取不是一个操作。隐私选择可能限制某些功能，不能把功能兼容性推断为账号安全性；管理员/用户选择的隐私策略须保留或解释影响后确认修改。

处理流程：

1. 检查 shell、用户/项目/托管 settings、专用 settings 与启动脚本模板，报告来源，不输出完整文件。
2. 只改变用户同意的当前来源。删除需要解除的键；不写成 `0`/`false`，不顺带加别的遥测限制。确认未改变专用入口/模型/认证。
3. 开新进程，防止旧环境仍带该变量。保留旧会话，不擅自杀掉它们。
4. 用现有受保护入口执行 doctor/只读状态或最小无工具请求，记录 CLI 本机 socket、Clash inbound/节点链以及通过同一入口的出口。新启用的启动/事件请求也要观察；只测 curl 或旧浏览器不够。
5. 限制测试时长和消耗，不加载无关项目/MCP，不存测试历史，不打印 debug 中的凭据。创建真实云端任务、启动后台任务或开启 Remote Control 另行获得当前授权；未测就标明未测。

解除本地门禁并不证明 GitHub 权限、套餐、组织策略或远端任务创建已成功。最新功能行为按实际版本和官方文档核验；Remote Control、云端任务和特性获取的限制不完全一样，不能因某版本允许关闭遥测的 Remote Control 就保证云端触发也可用。

## 四种会话不要混淆

| 入口 | 作用 | 网络/文件边界 |
|---|---|---|
| `--resume <ID> --fork-session` | 加载已有历史，生成新会话 ID | 新进程要经用户的受保护入口；不会自动隔离项目文件 |
| `/branch [name]` | 当前终端切换到对话分支，保留原对话 | 同进程仍需核对其有效配置；共享目录可能相互影响 |
| `/fork [prompt]` | 在支持版本且 Agent View 开启时复制为独立后台会话，原对话继续 | 无 prompt 时等待；带 prompt 会立即工作。关闭 Agent View/旧版本可能是结果回到原对话的 forked subagent |
| `--cloud` / 云端会话 | 任务在云端执行 | 本机创建请求与云端 worker 不同路径；云端不会继承本机 Clash 和守护 |

`/subtask` 是继承上下文、结果返回父对话的子代理，不等于独立后台聊天。`/clone` 不应仅凭旧 Issue 认定为内置命令；先看本机 help 和当前官方命令表。后台本机会话不等于云端任务。

要获得“保留原对话，副本在新终端独立聊天”，使用用户已有 wrapper 加 `--resume ... --fork-session`，或创建 `/fork` 后在 Agent View / `attach` 打开；不要因为讨论方法就自动复制用户会话。

CLI 监督进程、后台会话、重连和升级可能具有独立环境。前台 wrapper 正常不证明已有后台 supervisor 继承其代理。核对实际后台新请求、父终端退出后的 guard 租约、入口不可用时阻断，以及 `attach` 前后路径；`attach` 不会追溯修复后台进程的启动环境。故障注入、退出应用、结束会话分别获得许可。

独立对话并不自动等于独立工作区。某些版本会提示副本创建 worktree，但仍需核验实际目录，不把提示当隔离已实现。

来源（2026-10-14 核对，之后按版本复查）：[环境变量](https://code.claude.com/docs/en/env-vars)、[命令](https://code.claude.com/docs/en/commands)、[CLI 参数](https://code.claude.com/docs/en/cli-reference)、[云端执行](https://code.claude.com/docs/en/claude-code-on-the-web)。
